"""Motor analítico de comparação determinística e semântica de apólices D&O.
Calcula divergências campo a campo, interseção de coberturas e exclusões, e score de similaridade composto.
"""
from datetime import datetime
import re
import unicodedata
from typing import List, Tuple, Set, Dict, Any, Optional
from core.schemas import ApoliceDAO, FieldDiff, ComparisonResult


def normalize_text(text: Optional[str]) -> str:
    """Normaliza texto para comparação (minúsculas, remoção de acentos e pontuação excedente)."""
    if not text:
        return ""
    # Decompõe caracteres acentuados
    normalized = unicodedata.normalize('NFKD', text)
    ascii_text = ''.join([c for c in normalized if not unicodedata.combining(c)])
    # Remove caracteres não alfanuméricos e converte para minúsculas
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', ascii_text).lower()
    return ' '.join(cleaned.split())


def normalize_currency_or_number(value: Optional[str]) -> str:
    """Extrai valor numérico normalizado em centavos ou unidades para comparação financeira."""
    if not value:
        return ""
    # Remove sufixos de centavos zerados (,00 ou .00)
    cleaned = re.sub(r'[,.]00$', '', value.strip())
    # Extrai apenas dígitos
    digits = re.sub(r'[^\d]', '', cleaned)
    return digits


def are_values_equal(val_a: Optional[str], val_b: Optional[str], is_financial: bool = False) -> bool:
    """Verifica equivalência entre dois valores textuais ou financeiros."""
    if val_a is None and val_b is None:
        return True
    if val_a is None or val_b is None:
        return False
    
    norm_a = normalize_text(val_a)
    norm_b = normalize_text(val_b)
    
    if norm_a == norm_b:
        return True

    if is_financial:
        digits_a = normalize_currency_or_number(val_a)
        digits_b = normalize_currency_or_number(val_b)
        if digits_a and digits_b and digits_a == digits_b:
            return True

    return False


def compare_scalar_field(
    campo: str,
    rotulo: str,
    val_a: Optional[str],
    val_b: Optional[str],
    is_financial: bool = False
) -> FieldDiff:
    """Gera o objeto FieldDiff para um campo escalar com classificação semântica do diff."""
    if not val_a and not val_b:
        return FieldDiff(
            campo=campo,
            rotulo=rotulo,
            valor_apolice_a=val_a,
            valor_apolice_b=val_b,
            ha_diferenca=False,
            tipo_diferenca="ambos_ausentes"
        )
    if val_a and not val_b:
        return FieldDiff(
            campo=campo,
            rotulo=rotulo,
            valor_apolice_a=val_a,
            valor_apolice_b=val_b,
            ha_diferenca=True,
            tipo_diferenca="ausente_b"
        )
    if not val_a and val_b:
        return FieldDiff(
            campo=campo,
            rotulo=rotulo,
            valor_apolice_a=val_a,
            valor_apolice_b=val_b,
            ha_diferenca=True,
            tipo_diferenca="ausente_a"
        )

    equals = are_values_equal(val_a, val_b, is_financial=is_financial)
    return FieldDiff(
        campo=campo,
        rotulo=rotulo,
        valor_apolice_a=val_a,
        valor_apolice_b=val_b,
        ha_diferenca=not equals,
        tipo_diferenca="igual" if equals else "valor"
    )


def compare_list_items(list_a: List[str], list_b: List[str]) -> Tuple[List[str], List[str], List[str]]:
    """Compara duas listas de cláusulas (coberturas ou exclusões) usando casamento de texto aproximado.
    
    Retorna:
        Tuple: (exclusivas_a, exclusivas_b, comuns)
    """
    map_a = {normalize_text(item): item for item in list_a if item.strip()}
    map_b = {normalize_text(item): item for item in list_b if item.strip()}

    set_a = set(map_a.keys())
    set_b = set(map_b.keys())

    matched_a = set()
    matched_b = set()

    # 1. Casamento exato na chave normalizada
    for k in set_a:
        if k in set_b:
            matched_a.add(k)
            matched_b.add(k)

    # 2. Casamento difuso (subtermo ou sobreposição de tokens)
    remaining_a = set_a - matched_a
    remaining_b = set_b - matched_b

    for item_a in list(remaining_a):
        tokens_a = set(item_a.split())
        best_match_b = None
        best_score = 0.0

        for item_b in list(remaining_b):
            tokens_b = set(item_b.split())
            if not tokens_a or not tokens_b:
                continue
            
            token_jaccard = len(tokens_a & tokens_b) / len(tokens_a | tokens_b)
            score = token_jaccard
            
            # Domínio D&O: 'dic' (Difference in Conditions) é uma cobertura distinta de Side A pura
            if ("dic" in tokens_b and "dic" not in tokens_a) or ("dic" in tokens_a and "dic" not in tokens_b):
                score *= 0.2

            if (item_a in item_b or item_b in item_a) and ("dic" not in tokens_b or "dic" in tokens_a):
                score = max(score, 0.7)

            if score > best_score:
                best_score = score
                best_match_b = item_b

        if best_match_b and best_score >= 0.40:
            matched_a.add(item_a)
            matched_b.add(best_match_b)
            remaining_b.discard(best_match_b)

    exclusivas_a = [map_a[k] for k in (set_a - matched_a) if k in map_a]
    exclusivas_b = [map_b[k] for k in (set_b - matched_b) if k in map_b]
    comuns = [map_a[k] for k in matched_a if k in map_a]

    return exclusivas_a, exclusivas_b, comuns


def calculate_similarity_score(
    diffs: List[FieldDiff],
    coberturas_stats: Tuple[int, int, int],
    exclusoes_stats: Tuple[int, int, int]
) -> float:
    """Calcula um score percentual composto (0 a 100%) ponderando campos escalares e cobertura/exclusão.
    
    Pesos:
        - Campos Escalares: 40%
        - Coberturas (Índice de Jaccard): 40%
        - Exclusões (Índice de Jaccard): 20%
    """
    # 1. Escalares
    total_scalar = len(diffs)
    if total_scalar > 0:
        equal_scalar = sum(1 for d in diffs if not d.ha_diferenca)
        scalar_score = (equal_scalar / total_scalar) * 40.0
    else:
        scalar_score = 40.0

    # 2. Coberturas (Jaccard: comuns / total_único)
    excl_a, excl_b, comuns_cob = coberturas_stats
    total_cob = excl_a + excl_b + comuns_cob
    cob_score = ((comuns_cob / total_cob) * 40.0) if total_cob > 0 else 40.0

    # 3. Exclusões (Jaccard)
    excl_ea, excl_eb, comuns_exc = exclusoes_stats
    total_exc = excl_ea + excl_eb + comuns_exc
    exc_score = ((comuns_exc / total_exc) * 20.0) if total_exc > 0 else 20.0

    total_score = scalar_score + cob_score + exc_score
    return round(max(0.0, min(100.0, total_score)), 1)


def compare_policies(apolice_a: ApoliceDAO, apolice_b: ApoliceDAO) -> ComparisonResult:
    """Executa a comparação analítica completa entre duas instâncias de ApoliceDAO."""
    diffs: List[FieldDiff] = [
        compare_scalar_field("segurado", "Empresa Segurada", apolice_a.segurado, apolice_b.segurado),
        compare_scalar_field("cod_ramo", "Ramo SUSEP", f"{apolice_a.cod_ramo or '0378'} - {apolice_a.ramo_descricao or 'D&O'}", f"{apolice_b.cod_ramo or '0378'} - {apolice_b.ramo_descricao or 'D&O'}"),
        compare_scalar_field("tipo_movimento", "Tipo de Movimento", f"{apolice_a.tipo_movimento or '101'} - {apolice_a.tipo_movimento_descricao or 'Emissão'}", f"{apolice_b.tipo_movimento or '101'} - {apolice_b.tipo_movimento_descricao or 'Emissão'}"),
        compare_scalar_field("vigencia_inicio", "Início de Vigência", apolice_a.vigencia_inicio, apolice_b.vigencia_inicio),
        compare_scalar_field("vigencia_fim", "Término de Vigência", apolice_a.vigencia_fim, apolice_b.vigencia_fim),
        compare_scalar_field("limite_responsabilidade", "Limite Máximo de Garantia (LMG)", apolice_a.limite_responsabilidade, apolice_b.limite_responsabilidade, is_financial=True),
        compare_scalar_field("franquia", "Franquia / Retenção", apolice_a.franquia, apolice_b.franquia, is_financial=True),
        compare_scalar_field("premio_total", "Prêmio Total", apolice_a.premio_total, apolice_b.premio_total, is_financial=True),
        compare_scalar_field("retroatividade", "Data de Retroatividade", apolice_a.retroatividade, apolice_b.retroatividade),
        compare_scalar_field("territorio", "Âmbito Territorial", apolice_a.territorio, apolice_b.territorio),
        compare_scalar_field("legislacao_aplicavel", "Legislação e Foro", apolice_a.legislacao_aplicavel, apolice_b.legislacao_aplicavel),
    ]

    # Análise de Coberturas
    cob_excl_a, cob_excl_b, cob_comuns = compare_list_items(apolice_a.coberturas, apolice_b.coberturas)

    # Análise de Exclusões
    exc_excl_a, exc_excl_b, exc_comuns = compare_list_items(apolice_a.exclusoes, apolice_b.exclusoes)

    # Cálculo do Score de Similaridade
    score = calculate_similarity_score(
        diffs=diffs,
        coberturas_stats=(len(cob_excl_a), len(cob_excl_b), len(cob_comuns)),
        exclusoes_stats=(len(exc_excl_a), len(exc_excl_b), len(exc_comuns))
    )

    nome_a = apolice_a.seguradora or apolice_a.nome_arquivo
    nome_b = apolice_b.seguradora or apolice_b.nome_arquivo

    return ComparisonResult(
        apolice_a_id=apolice_a.id or "apolice_a",
        apolice_b_id=apolice_b.id or "apolice_b",
        apolice_a_nome=nome_a,
        apolice_b_nome=nome_b,
        data_comparacao=datetime.now().isoformat(),
        score_similaridade=score,
        diffs=diffs,
        coberturas_exclusivas_a=cob_excl_a,
        coberturas_exclusivas_b=cob_excl_b,
        coberturas_comuns=cob_comuns,
        exclusoes_exclusivas_a=exc_excl_a,
        exclusoes_exclusivas_b=exc_excl_b,
        exclusoes_comuns=exc_comuns
    )
