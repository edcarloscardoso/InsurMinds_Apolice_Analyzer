"""Motor analítico de comparação determinística e semântica de apólices D&O.
Calcula divergências campo a campo, normaliza valores financeiros e temporais,
classifica assimetrias por categoria taxonômica e avalia equivalência semântica de cláusulas.
"""
from datetime import datetime
import re
import unicodedata
import logging
from typing import List, Tuple, Set, Dict, Any, Optional
from core.schemas import ApoliceDAO, FieldDiff, ComparisonResult, EvidenceItem, SemanticMatchItem

logger = logging.getLogger(__name__)

# =============================================================================
# ETAPA 1 — TAXONOMIA DE COMPARAÇÃO D&O
# =============================================================================

TAXONOMY_CATEGORIES: Dict[str, str] = {
    # 1. Identificação
    "seguradora": "1. Identificação",
    "numero_apolice": "1. Identificação",
    "processo_susep": "1. Identificação",
    "segurado": "1. Identificação",

    # 2. Temporalidade
    "vigencia_inicio": "2. Temporalidade",
    "vigencia_fim": "2. Temporalidade",
    "retroatividade": "2. Temporalidade",

    # 3. Limites
    "limite_responsabilidade": "3. Limites Financeiros",

    # 4. Franquias / Dedutíveis
    "franquia": "4. Franquias e Retenções",

    # 5. Parâmetros Comerciais e Prêmio
    "premio_total": "5. Parâmetros Comerciais e Prêmio",

    # 6. Coberturas
    "coberturas": "6. Garantias e Coberturas",

    # 7. Exclusões
    "exclusoes": "7. Riscos Excluídos",

    # 8. Cláusulas Especiais e Endossos
    "clausulas_especiais": "8. Cláusulas Especiais e Endossos",

    # 9. Âmbito Territorial e Jurisdição
    "territorio": "9. Escopo Territorial e Foro",
    "legislacao_aplicavel": "9. Escopo Territorial e Foro",

    # 10. Classificação Regulatória
    "cod_ramo": "10. Classificação Regulatória",
    "tipo_movimento": "10. Classificação Regulatória",
}

# =============================================================================
# ETAPA 2 — NORMALIZAÇÃO DETERMINÍSTICA
# =============================================================================

MONTHS_PT: Dict[str, str] = {
    "janeiro": "01", "fevereiro": "02", "marco": "03", "março": "03",
    "abril": "04", "maio": "05", "junho": "06", "julho": "07",
    "agosto": "08", "setembro": "09", "outubro": "10", "novembro": "11",
    "dezembro": "12"
}


def normalize_text(text: Optional[str]) -> str:
    """Normaliza texto para comparação (minúsculas, remoção de acentos, pontuação e abreviações corporativas)."""
    if not text:
        return ""
    normalized = unicodedata.normalize('NFKD', str(text))
    ascii_text = ''.join([c for c in normalized if not unicodedata.combining(c)])
    # Normalização de sufixos societários comuns (S.A., S/A -> sa; Ltda. -> ltda)
    ascii_text = re.sub(r'\b[sS][./\s]+[aA]\b', ' sa ', ascii_text)
    ascii_text = re.sub(r'\b[lL][tT][dD][aA][.]?', ' ltda ', ascii_text)
    # Remove caracteres não alfanuméricos e converte para minúsculas
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', ascii_text).lower()
    return ' '.join(cleaned.split())


def format_currency_brl(val: float) -> str:
    """Formata valor numérico em formato canônico monetário BRL (R$ 10.000.000,00)."""
    formatted = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def normalize_money(value: Optional[str]) -> Optional[Tuple[float, str]]:
    """Extrai e normaliza valor monetário para tupla (float, string_canonica_brl).

    Suporta formatos como 'R$ 10.000.000,00', '10 milhões', 'R$ 10M', 'R$ 50 mil', 'isento'.
    Valores ambíguos ou não numéricos retornam None.
    """
    if not value or not str(value).strip():
        return None
    val_clean = str(value).strip()
    norm = unicodedata.normalize('NFKD', val_clean)
    ascii_clean = ''.join([c for c in norm if not unicodedata.combining(c)]).lower()

    # Isenções e valores zerados
    if ascii_clean in ("isento", "isenta", "sem franquia", "nao aplicavel", "n/a", "zero", "0", "0,00", "0.00"):
        return (0.0, "R$ 0,00")

    # Padrão por extenso / multiplicadores: "10 milhões", "10M", "50 mil"
    word_pattern = re.search(
        r'(\d+(?:[.,]\d+)?)\s*(milh[a-z]+|bilh[a-z]+|mil\b|m\b|k\b|b\b)',
        ascii_clean
    )
    if word_pattern:
        num_str = word_pattern.group(1).replace(',', '.')
        try:
            base_num = float(num_str)
            unit = word_pattern.group(2)
            multiplier = 1.0
            if 'bilh' in unit or unit == 'b':
                multiplier = 1_000_000_000.0
            elif 'milh' in unit or unit == 'm':
                multiplier = 1_000_000.0
            elif unit == 'mil' or unit == 'k':
                multiplier = 1_000.0
            total = base_num * multiplier
            return (total, format_currency_brl(total))
        except ValueError:
            pass

    # Extração de padrão numérico com separadores
    digits_and_seps = re.search(r'(\d+[\d.,]*)', ascii_clean)
    if not digits_and_seps:
        return None

    raw_num = digits_and_seps.group(1)
    if '.' in raw_num and ',' in raw_num:
        if raw_num.rfind(',') > raw_num.rfind('.'):
            # Formato brasileiro: 10.000.000,00
            clean_num = raw_num.replace('.', '').replace(',', '.')
        else:
            # Formato internacional: 10,000,000.00
            clean_num = raw_num.replace(',', '')
    elif ',' in raw_num:
        parts = raw_num.split(',')
        if len(parts) == 2 and len(parts[1]) in (1, 2):
            clean_num = parts[0] + '.' + parts[1]
        else:
            clean_num = raw_num.replace(',', '')
    elif '.' in raw_num:
        parts = raw_num.split('.')
        if len(parts) > 2:
            clean_num = raw_num.replace('.', '')
        elif len(parts) == 2:
            if len(parts[1]) == 3:  # ex: 50.000
                clean_num = raw_num.replace('.', '')
            else:  # ex: 10.5
                clean_num = raw_num
        else:
            clean_num = raw_num
    else:
        clean_num = raw_num

    try:
        val_float = float(clean_num)
        return (val_float, format_currency_brl(val_float))
    except ValueError:
        return None


def normalize_percentage(value: Optional[str]) -> Optional[Tuple[float, str]]:
    """Extrai e normaliza valores percentuais (ex: '10%', '10,5%')."""
    if not value or not str(value).strip():
        return None
    val_clean = str(value).strip()
    match = re.search(r'(\d+(?:[.,]\d+)?)\s*%', val_clean)
    if not match:
        match = re.search(r'(\d+(?:[.,]\d+)?)', val_clean)
    if not match:
        return None
    try:
        val_float = float(match.group(1).replace(',', '.'))
        return (val_float, f"{val_float:.1f}%")
    except ValueError:
        return None


def normalize_date(value: Optional[str]) -> Optional[Tuple[str, str]]:
    """Normaliza datas para formato canônico ISO (YYYY-MM-DD), preservando original."""
    if not value or not str(value).strip():
        return None
    val_clean = str(value).strip()

    # Formato ISO direto YYYY-MM-DD
    iso_match = re.search(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', val_clean)
    if iso_match:
        y, m, d = iso_match.group(1), int(iso_match.group(2)), int(iso_match.group(3))
        iso_str = f"{y}-{m:02d}-{d:02d}"
        return (iso_str, val_clean)

    # Formato brasileiro DD/MM/YYYY
    br_match = re.search(r'(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})', val_clean)
    if br_match:
        d, m, y = int(br_match.group(1)), int(br_match.group(2)), br_match.group(3)
        iso_str = f"{y}-{m:02d}-{d:02d}"
        return (iso_str, val_clean)

    # Formato textual: 15 de janeiro de 2025
    norm = unicodedata.normalize('NFKD', val_clean)
    ascii_clean = ''.join([c for c in norm if not unicodedata.combining(c)]).lower()
    text_match = re.search(r'(\d{1,2})\s+de\s+([a-z]+)\s+de\s+(\d{4})', ascii_clean)
    if text_match:
        d = int(text_match.group(1))
        month_name = text_match.group(2)
        y = text_match.group(3)
        if month_name in MONTHS_PT:
            m = MONTHS_PT[month_name]
            iso_str = f"{y}-{m}-{d:02d}"
            return (iso_str, val_clean)

    return None


def normalize_list(items: Optional[List[str]]) -> List[str]:
    """Deduplica e limpa lista preservando itens originais sem falso positivo."""
    if not items:
        return []
    seen = set()
    result = []
    for it in items:
        if not it or not str(it).strip():
            continue
        cleaned = str(it).strip()
        norm_key = normalize_text(cleaned)
        if norm_key and norm_key not in seen:
            seen.add(norm_key)
            result.append(cleaned)
    return result


def normalize_boolean_like(value: Optional[str]) -> Optional[bool]:
    """Normaliza valores textuais com semântica booleana."""
    if not value:
        return None
    val_norm = normalize_text(value)
    if val_norm in ("sim", "true", "1", "coberto", "aplicavel", "incluso"):
        return True
    if val_norm in ("nao", "false", "0", "excluido", "nao aplicavel", "isento"):
        return False
    return None


def are_values_equal(
    val_a: Optional[str],
    val_b: Optional[str],
    is_financial: bool = False,
    is_date: bool = False,
    is_percentage: bool = False
) -> bool:
    """Verifica equivalência determinística entre dois valores considerando tipagem e normalização."""
    if val_a is None and val_b is None:
        return True
    if val_a is None or val_b is None:
        return False

    if is_financial:
        norm_a = normalize_money(val_a)
        norm_b = normalize_money(val_b)
        if norm_a and norm_b:
            return abs(norm_a[0] - norm_b[0]) < 0.01
        # Fallback de dígitos puros
        digits_a = re.sub(r'[^\d]', '', val_a)
        digits_b = re.sub(r'[^\d]', '', val_b)
        if digits_a and digits_b:
            return digits_a == digits_b

    if is_date:
        norm_date_a = normalize_date(val_a)
        norm_date_b = normalize_date(val_b)
        if norm_date_a and norm_date_b:
            return norm_date_a[0] == norm_date_b[0]

    if is_percentage:
        norm_pct_a = normalize_percentage(val_a)
        norm_pct_b = normalize_percentage(val_b)
        if norm_pct_a and norm_pct_b:
            return abs(norm_pct_a[0] - norm_pct_b[0]) < 0.01

    return normalize_text(val_a) == normalize_text(val_b)


# =============================================================================
# ETAPA 3, 6, 7 & 8 — COMPARAÇÃO DE ESCALARES COM EVIDÊNCIA, CONFLITOS E EXPLICAÇÃO
# =============================================================================

def compare_scalar_field(
    campo: str,
    rotulo: str,
    val_a: Optional[str],
    val_b: Optional[str],
    categoria: Optional[str] = None,
    is_financial: bool = False,
    is_date: bool = False,
    is_percentage: bool = False,
    evidence_a: Optional[EvidenceItem] = None,
    evidence_b: Optional[EvidenceItem] = None,
    conflito_a: bool = False,
    conflito_b: bool = False,
) -> FieldDiff:
    """Gera um FieldDiff completo e explicável para parâmetros escalares contratuais."""
    cat = categoria or TAXONOMY_CATEGORIES.get(campo, "1. Identificação")

    # 1. Tratamento explícito de conflitos internos (Etapa 7)
    if conflito_a and conflito_b:
        return FieldDiff(
            campo=campo,
            rotulo=rotulo,
            categoria=cat,
            valor_apolice_a=val_a,
            valor_apolice_b=val_b,
            ha_diferenca=True,
            tipo_diferenca="conflito_A_e_B",
            explicacao=f"Divergência interna de extração identificada em ambas as apólices para o parâmetro {rotulo}.",
            confidence=0.5,
            evidence_a=evidence_a,
            evidence_b=evidence_b
        )
    if conflito_a:
        return FieldDiff(
            campo=campo,
            rotulo=rotulo,
            categoria=cat,
            valor_apolice_a=val_a,
            valor_apolice_b=val_b,
            ha_diferenca=True,
            tipo_diferenca="conflito_A",
            explicacao=f"A Apólice A apresenta conflito documental interno para {rotulo}, impedindo determinação unívoca.",
            confidence=0.6,
            evidence_a=evidence_a,
            evidence_b=evidence_b
        )
    if conflito_b:
        return FieldDiff(
            campo=campo,
            rotulo=rotulo,
            categoria=cat,
            valor_apolice_a=val_a,
            valor_apolice_b=val_b,
            ha_diferenca=True,
            tipo_diferenca="conflito_B",
            explicacao=f"A Apólice B apresenta conflito documental interno para {rotulo}, impedindo determinação unívoca.",
            confidence=0.6,
            evidence_a=evidence_a,
            evidence_b=evidence_b
        )

    # 2. Ausência unilateral ou bilateral
    if not val_a and not val_b:
        return FieldDiff(
            campo=campo,
            rotulo=rotulo,
            categoria=cat,
            valor_apolice_a=None,
            valor_apolice_b=None,
            ha_diferenca=False,
            tipo_diferenca="ambos_ausentes",
            explicacao=f"Parâmetro {rotulo} não identificado documentalmente em nenhuma das apólices comparadas.",
            confidence=1.0,
            evidence_a=evidence_a,
            evidence_b=evidence_b
        )
    if val_a and not val_b:
        return FieldDiff(
            campo=campo,
            rotulo=rotulo,
            categoria=cat,
            valor_apolice_a=val_a,
            valor_apolice_b=None,
            ha_diferenca=True,
            tipo_diferenca="ausente_em_B",
            explicacao=f"Parâmetro {rotulo} identificado apenas na Apólice A ({val_a}); ausente na Apólice B.",
            confidence=0.9 if evidence_a else 0.7,
            evidence_a=evidence_a,
            evidence_b=evidence_b
        )
    if not val_a and val_b:
        return FieldDiff(
            campo=campo,
            rotulo=rotulo,
            categoria=cat,
            valor_apolice_a=None,
            valor_apolice_b=val_b,
            ha_diferenca=True,
            tipo_diferenca="ausente_em_A",
            explicacao=f"Parâmetro {rotulo} identificado apenas na Apólice B ({val_b}); ausente na Apólice A.",
            confidence=0.9 if evidence_b else 0.7,
            evidence_a=evidence_a,
            evidence_b=evidence_b
        )

    # 3. Ambos presentes: normalização e comparação
    normalized_a_str: Optional[str] = None
    normalized_b_str: Optional[str] = None
    equals = False

    if is_financial:
        norm_a = normalize_money(val_a)
        norm_b = normalize_money(val_b)
        if norm_a and norm_b:
            normalized_a_str = norm_a[1]
            normalized_b_str = norm_b[1]
            equals = abs(norm_a[0] - norm_b[0]) < 0.01
        else:
            equals = are_values_equal(val_a, val_b, is_financial=True)
            normalized_a_str = val_a.strip()
            normalized_b_str = val_b.strip()
    elif is_date:
        norm_date_a = normalize_date(val_a)
        norm_date_b = normalize_date(val_b)
        if norm_date_a and norm_date_b:
            normalized_a_str = norm_date_a[0]
            normalized_b_str = norm_date_b[0]
            equals = (norm_date_a[0] == norm_date_b[0])
        else:
            equals = are_values_equal(val_a, val_b, is_date=True)
            normalized_a_str = val_a.strip()
            normalized_b_str = val_b.strip()
    elif is_percentage:
        norm_pct_a = normalize_percentage(val_a)
        norm_pct_b = normalize_percentage(val_b)
        if norm_pct_a and norm_pct_b:
            normalized_a_str = norm_pct_a[1]
            normalized_b_str = norm_pct_b[1]
            equals = abs(norm_pct_a[0] - norm_pct_b[0]) < 0.01
        else:
            equals = are_values_equal(val_a, val_b, is_percentage=True)
            normalized_a_str = val_a.strip()
            normalized_b_str = val_b.strip()
    else:
        normalized_a_str = normalize_text(val_a)
        normalized_b_str = normalize_text(val_b)
        equals = (normalized_a_str == normalized_b_str)

    # Confiança baseada na proveniência das evidências
    conf = 1.0
    if not evidence_a or not evidence_b:
        conf = 0.8
    else:
        conf = min(evidence_a.confidence, evidence_b.confidence)

    # Geração de explicação neutra e factual (Etapa 8)
    if equals:
        if str(val_a).strip() == str(val_b).strip():
            explicacao = f"Os valores de {rotulo} são idênticos em ambas as apólices ({val_a.strip()})."
        else:
            explicacao = f"Os valores de {rotulo} são equivalentes após normalização ({normalized_a_str})."
        return FieldDiff(
            campo=campo,
            rotulo=rotulo,
            categoria=cat,
            valor_apolice_a=val_a,
            valor_apolice_b=val_b,
            normalized_a=normalized_a_str,
            normalized_b=normalized_b_str,
            ha_diferenca=False,
            tipo_diferenca="igual",
            explicacao=explicacao,
            confidence=conf,
            evidence_a=evidence_a,
            evidence_b=evidence_b
        )
    else:
        if is_financial:
            explicacao = f"Os valores monetários identificados para {rotulo} são diferentes: {val_a} na Apólice A vs {val_b} na Apólice B."
        elif is_date:
            explicacao = f"As datas registradas para {rotulo} são divergentes: {val_a} na Apólice A vs {val_b} na Apólice B."
        else:
            explicacao = f"Os termos registrados para {rotulo} apresentam redação divergente entre as apólices."

        return FieldDiff(
            campo=campo,
            rotulo=rotulo,
            categoria=cat,
            valor_apolice_a=val_a,
            valor_apolice_b=val_b,
            normalized_a=normalized_a_str,
            normalized_b=normalized_b_str,
            ha_diferenca=True,
            tipo_diferenca="diferente",
            explicacao=explicacao,
            confidence=conf,
            evidence_a=evidence_a,
            evidence_b=evidence_b
        )


# =============================================================================
# ETAPA 4 & 5 — COMPARAÇÃO DE LISTAS E CAMADA SEMÂNTICA (D&O DOMAIN + GEMINI)
# =============================================================================

DO_SEMANTIC_GROUPS: List[Dict[str, Any]] = [
    {
        "concept": "Custos e Despesas de Defesa",
        "keywords": ["custo de defesa", "custos de defesa", "despesas de defesa", "honorarios advocaticios", "honorarios e despesas de defesa", "gastos de defesa"],
        "negative_keywords": ["dic"]
    },
    {
        "concept": "Investigações e Inquéritos Administrativos",
        "keywords": ["investigacao", "investigacoes", "inquerito", "inqueritos", "processo administrativo", "processos administrativos", "procedimento preliminar"],
        "negative_keywords": []
    },
    {
        "concept": "Penalidades, Multas Civis e Administrativas",
        "keywords": ["multas civis", "multas administrativas", "penalidades e multas", "multas regulatorias"],
        "negative_keywords": []
    },
    {
        "concept": "Penhora Online e Bloqueio de Bens",
        "keywords": ["penhora de bens", "penhora online", "bloqueio de bens", "indisponibilidade de bens", "caucao judicial"],
        "negative_keywords": []
    },
    {
        "concept": "Gestão de Crise e Reputação",
        "keywords": ["gestao de crise", "gerenciamento de crise", "crise e imagem", "protecao de imagem", "relacoes publicas"],
        "negative_keywords": []
    },
    {
        "concept": "Extradição e Custos Relacionados",
        "keywords": ["extradicao", "custos de extradicao", "despesas com extradicao"],
        "negative_keywords": []
    },
    {
        "concept": "Responsabilidade por Poluição ou Ambiental",
        "keywords": ["danos ambientais", "poluicao", "reclamacoes ambientais", "custos ambientais"],
        "negative_keywords": []
    },
    {
        "concept": "Side A (Indenização Direta de Administradores)",
        "keywords": ["side a", "cobertura a", "indenizacao individual", "garantia de administradores"],
        "negative_keywords": ["dic", "difference in conditions"]
    },
    {
        "concept": "Side A DIC (Difference in Conditions)",
        "keywords": ["side a dic", "difference in conditions", "dic"],
        "negative_keywords": []
    },
    {
        "concept": "Side B (Reembolso à Sociedade)",
        "keywords": ["side b", "cobertura b", "reembolso a sociedade", "reembolso a empresa"],
        "negative_keywords": ["dic"]
    },
    {
        "concept": "Side C (Reclamações sobre Valores Mobiliários / Empresa)",
        "keywords": ["side c", "cobertura c", "securities claims", "valores mobiliarios"],
        "negative_keywords": []
    },
]

DO_SEMANTIC_SYNONYMS = [
    (r'\b(?:empresa\s+estiver\s+impedida\s+de\s+indenizar|sociedade\s+n[aã]o\s+indenizar|n[aã]o\s+indenizados\s+pela\s+sociedade)\b', 'sem_indenizacao_sociedade'),
    (r'\b(?:prote[cç][aã]o\s+financeira|indeniza[cç][aã]o\s+direta|cobertura\s+direta)\b', 'cobertura_direta'),
    (r'\b(?:administradores|diretores|gestores|membros\s+estatut[aá]rios)\b', 'administradores'),
    (r'\b(?:empresa|sociedade|sociedade\s+estipulante|estipulante|tomadora)\b', 'sociedade'),
    (r'\b(?:honor[aá]rios\s+advocat[ií]cios|despesas\s+de\s+defesa|custos\s+de\s+defesa|honor[aá]rios\s+periciais)\b', 'custos_defesa'),
    (r'\b(?:bloqueio\s+de\s+bens|indisponibilidade\s+de\s+bens|apreens[aã]o\s+de\s+bens|constri[cç][aã]o\s+judicial)\b', 'bloqueio_bens'),
]


def apply_semantic_synonyms(text: str) -> str:
    """Substitui termos sinônimos canônicos de D&O para matching semântico robusto."""
    res = text
    for pattern, repl in DO_SEMANTIC_SYNONYMS:
        res = re.sub(pattern, repl, res, flags=re.IGNORECASE)
    return res


def _match_keyword(text: str, kw: str) -> bool:
    """Verifica presença de termo garantindo limite de palavra (boundary) para siglas e termos curtos."""
    if not text or not kw:
        return False
    if len(kw) <= 4:
        return bool(re.search(r'\b' + re.escape(kw) + r'\b', text))
    return kw in text


def compare_clauses_semantically(
    item_a: str,
    item_b: str,
    llm_client: Optional[Any] = None
) -> Optional[SemanticMatchItem]:
    """Avalia equivalência conceitual entre duas cláusulas contratuais de D&O.

    Utiliza Gemini se disponível e configurado, com fallback determinístico baseado em ontologia D&O.
    """
    norm_a = normalize_text(item_a)
    norm_b = normalize_text(item_b)

    if not norm_a or not norm_b:
        return None

    # Igualdade textual direta
    if norm_a == norm_b:
        return SemanticMatchItem(
            item_a=item_a,
            item_b=item_b,
            equivalence=True,
            relation="semantic_equivalent",
            explanation="Cláusulas com redação substancialmente idêntica.",
            confidence=1.0,
            evidence_a=item_a,
            evidence_b=item_b
        )

    # 1. Tentativa via Gemini estruturado (se client ativo)
    if llm_client and hasattr(llm_client, "is_available") and llm_client.is_available():
        try:
            gemini_res = llm_client.compare_clauses_semantically(item_a, item_b)
            if gemini_res and isinstance(gemini_res, dict) and "equivalence" in gemini_res:
                return SemanticMatchItem(
                    item_a=item_a,
                    item_b=item_b,
                    equivalence=bool(gemini_res.get("equivalence", False)),
                    relation=str(gemini_res.get("relation", "different")),
                    explanation=str(gemini_res.get("explanation", "")),
                    confidence=float(gemini_res.get("confidence", 0.85)),
                    evidence_a=item_a,
                    evidence_b=item_b
                )
        except Exception as e:
            logger.warning(f"Falha na camada semântica Gemini, ativando fallback determinístico: {e}")

    # 2. Distinções estritas de domínio D&O (prevenção de falsos positivos lexicais)
    # A) Side A pura vs Side A DIC
    has_dic_a = "dic" in norm_a.split()
    has_dic_b = "dic" in norm_b.split()
    if (has_dic_a and not has_dic_b) or (has_dic_b and not has_dic_a):
        return SemanticMatchItem(
            item_a=item_a,
            item_b=item_b,
            equivalence=False,
            relation="different",
            explanation="A apólice que inclui 'DIC' (Difference in Conditions) prevê cobertura suplementar de lacunas, distinta de Side A pura.",
            confidence=0.95,
            evidence_a=item_a,
            evidence_b=item_b
        )

    # B) Danos Corporais / Materiais vs Danos Morais (semelhança lexical sem equivalência jurídica)
    has_moral_a = "moral" in norm_a or "morais" in norm_a
    has_moral_b = "moral" in norm_b or "morais" in norm_b
    has_mat_a = any(t in norm_a for t in ("material", "materiais", "corporal", "corporais"))
    has_mat_b = any(t in norm_b for t in ("material", "materiais", "corporal", "corporais"))
    if (has_moral_a and not has_moral_b and has_mat_b) or (has_moral_b and not has_moral_a and has_mat_a):
        return SemanticMatchItem(
            item_a=item_a,
            item_b=item_b,
            equivalence=False,
            relation="different",
            explanation="Divergência jurídica substancial: Danos Morais e Danos Materiais/Corporais representam modalidades distintas de dano indenizável.",
            confidence=0.95,
            evidence_a=item_a,
            evidence_b=item_b
        )

    # C) Escopo Amplo vs Restrito em Penhora (Penhora Ampla vs Penhora Online Bacenjud)
    if "penhora" in norm_a and "penhora" in norm_b:
        is_online_a = any(t in norm_a for t in ("online", "bacenjud", "sisbajud"))
        is_online_b = any(t in norm_b for t in ("online", "bacenjud", "sisbajud"))
        if is_online_a and not is_online_b:
            return SemanticMatchItem(
                item_a=item_a,
                item_b=item_b,
                equivalence=True,
                relation="narrower",
                explanation="A Cláusula A possui escopo restrito a bloqueio eletrônico (Penhora Online/Sisbajud), enquanto a Cláusula B contempla penhora de bens em geral.",
                confidence=0.90,
                evidence_a=item_a,
                evidence_b=item_b
            )
        elif is_online_b and not is_online_a:
            return SemanticMatchItem(
                item_a=item_a,
                item_b=item_b,
                equivalence=True,
                relation="broader",
                explanation="A Cláusula A contempla penhora de bens de forma genérica, enquanto a Cláusula B limita-se à modalidade online (Sisbajud).",
                confidence=0.90,
                evidence_a=item_a,
                evidence_b=item_b
            )

    # 3. Decomposição Título / Corpo para detecção de mudanças substantivas internas
    has_body = (":" in item_a or ":" in item_b or len(item_a) > 60 or len(item_b) > 60)
    if ":" in item_a:
        title_a, _, body_a = item_a.partition(":")
    else:
        title_a, body_a = item_a, item_a

    if ":" in item_b:
        title_b, _, body_b = item_b.partition(":")
    else:
        title_b, body_b = item_b, item_b

    norm_title_a = normalize_text(title_a)
    norm_title_b = normalize_text(title_b)
    norm_body_a = normalize_text(body_a)
    norm_body_b = normalize_text(body_b)

    # Verifica se pertencem ao mesmo conceito contratual
    same_concept = False
    concept_name = title_a.strip()
    if norm_title_a == norm_title_b and norm_title_a:
        same_concept = True
    else:
        for group in DO_SEMANTIC_GROUPS:
            kws = group["keywords"]
            negs = group.get("negative_keywords", [])
            if any(_match_keyword(norm_title_a, n) for n in negs) or any(_match_keyword(norm_title_b, n) for n in negs):
                continue
            if any(_match_keyword(norm_title_a, k) for k in kws) and any(_match_keyword(norm_title_b, k) for k in kws):
                same_concept = True
                concept_name = group["concept"]
                break

    # Se é o mesmo conceito/título:
    if same_concept:
        if not has_body:
            # Ambas são apenas títulos/rótulos do mesmo conceito
            return SemanticMatchItem(
                item_a=item_a,
                item_b=item_b,
                equivalence=True,
                relation="semantic_equivalent",
                explanation=f"Ambas as cláusulas tratam do mesmo conceito securitário D&O: {concept_name}.",
                confidence=0.90,
                evidence_a=item_a,
                evidence_b=item_b
            )

        if norm_body_a == norm_body_b:
            return SemanticMatchItem(
                item_a=item_a,
                item_b=item_b,
                equivalence=True,
                relation="semantic_equivalent",
                explanation=f"Ambas as cláusulas tratam do conceito '{concept_name}' com redação substantivamente idêntica.",
                confidence=1.0,
                evidence_a=item_a,
                evidence_b=item_b
            )

        # A. Limites financeiros / Sub-limites
        money_a = re.findall(r'r\$\s*[\d\.,]+', body_a.lower())
        money_b = re.findall(r'r\$\s*[\d\.,]+', body_b.lower())
        pct_a = re.findall(r'\b\d+(?:[.,]\d+)?\s*%', body_a.lower())
        pct_b = re.findall(r'\b\d+(?:[.,]\d+)?\s*%', body_b.lower())
        has_sub_a = any(t in norm_body_a for t in ("sublimite", "sub limite"))
        has_sub_b = any(t in norm_body_b for t in ("sublimite", "sub limite"))

        if (money_a and money_b and money_a != money_b) or \
           (pct_a and pct_b and pct_a != pct_b) or \
           (has_sub_a != has_sub_b) or \
           ((has_sub_a or has_sub_b) and (money_a != money_b or pct_a != pct_b)):
            diff_desc = []
            if money_a != money_b:
                diff_desc.append(f"{', '.join(money_a)} em A vs {', '.join(money_b)} em B")
            if pct_a != pct_b:
                diff_desc.append(f"{', '.join(pct_a)} em A vs {', '.join(pct_b)} em B")
            if has_sub_a != has_sub_b:
                diff_desc.append("sub-limite específico imposto em uma das apólices")
            return SemanticMatchItem(
                item_a=item_a,
                item_b=item_b,
                equivalence=False,
                relation="changed_limit",
                explanation=f"Mesma cláusula nominal ({concept_name}) com limites/sub-limites divergentes: {'; '.join(diff_desc)}.",
                confidence=0.95,
                evidence_a=item_a,
                evidence_b=item_b
            )

        # B. Condições procedimentais / prévias
        cond_terms = ("mediante consentimento", "previa aprovacao", "previa autorizacao", "aprovacao expressa", "por escrito", "condicionado a", "condicionada a", "prazo decadencial")
        conds_a = [c for c in cond_terms if c in norm_body_a]
        conds_b = [c for c in cond_terms if c in norm_body_b]
        if set(conds_a) != set(conds_b):
            return SemanticMatchItem(
                item_a=item_a,
                item_b=item_b,
                equivalence=False,
                relation="changed_condition",
                explanation=f"Mesma cláusula ({concept_name}) com exigências procedimentais ou condições prévias divergentes: {', '.join(set(conds_a) ^ set(conds_b))}.",
                confidence=0.90,
                evidence_a=item_a,
                evidence_b=item_b
            )

        # C. Alterações de Escopo / Restrições / Exclusões internas
        restr_terms = ("exceto", "salvo", "excluindo", "restricao", "ressalvada", "ressalvadas", "ressalvado", "ressalvados", "nao cobre", "carve back", "enriquecimento ilicito", "compliance", "atos dolosos", "multas penais")
        restrs_a = [r for r in restr_terms if r in norm_body_a]
        restrs_b = [r for r in restr_terms if r in norm_body_b]
        if set(restrs_a) != set(restrs_b):
            return SemanticMatchItem(
                item_a=item_a,
                item_b=item_b,
                equivalence=False,
                relation="changed_scope",
                explanation=f"A cobertura '{concept_name}' apresenta alterações de escopo ou ressalvas contratuais divergentes: {', '.join(set(restrs_a) ^ set(restrs_b))}.",
                confidence=0.90,
                evidence_a=item_a,
                evidence_b=item_b
            )

        # D. Mais Amplo vs Mais Restrito
        broad_terms = ("ampla", "em geral", "qualquer", "todas as", "mundial", "global", "sem restricao")
        narrow_terms = ("restrita", "exclusivamente", "limitada a", "apenas", "nacional", "online", "sisbajud", "bacenjud")
        has_b_a = any(t in norm_body_a for t in broad_terms)
        has_n_a = any(t in norm_body_a for t in narrow_terms)
        has_b_b = any(t in norm_body_b for t in broad_terms)
        has_n_b = any(t in norm_body_b for t in narrow_terms)

        if (has_b_a and has_n_b) or (not has_n_a and has_n_b):
            return SemanticMatchItem(
                item_a=item_a,
                item_b=item_b,
                equivalence=True,
                relation="broader",
                explanation=f"A Cláusula A possui escopo mais amplo ({concept_name}), enquanto a Cláusula B limita-se à modalidade restrita.",
                confidence=0.88,
                evidence_a=item_a,
                evidence_b=item_b
            )
        elif (has_n_a and has_b_b) or (has_n_a and not has_n_b):
            return SemanticMatchItem(
                item_a=item_a,
                item_b=item_b,
                equivalence=True,
                relation="narrower",
                explanation=f"A Cláusula A possui escopo restrito ({concept_name}) comparado à abrangência da Cláusula B.",
                confidence=0.88,
                evidence_a=item_a,
                evidence_b=item_b
            )

        # Se redação mudou substancialmente (após normalização de sinônimos canônicos D&O)
        syn_body_a = apply_semantic_synonyms(norm_body_a)
        syn_body_b = apply_semantic_synonyms(norm_body_b)
        words_a = set(syn_body_a.split())
        words_b = set(syn_body_b.split())
        jaccard = len(words_a & words_b) / max(len(words_a | words_b), 1)
        if jaccard < 0.6:
            return SemanticMatchItem(
                item_a=item_a,
                item_b=item_b,
                equivalence=False,
                relation="changed_scope",
                explanation=f"Mesma cláusula nominal ({concept_name}), porém com redação substancialmente alterada entre as apólices.",
                confidence=0.85,
                evidence_a=item_a,
                evidence_b=item_b
            )
        else:
            return SemanticMatchItem(
                item_a=item_a,
                item_b=item_b,
                equivalence=True,
                relation="semantic_equivalent",
                explanation=f"Ambas as cláusulas tratam do conceito '{concept_name}' com redação equivalente.",
                confidence=0.90,
                evidence_a=item_a,
                evidence_b=item_b
            )


    # 4. Ontologia DO_SEMANTIC_GROUPS para termos gerais
    for group in DO_SEMANTIC_GROUPS:
        keywords = group["keywords"]
        neg_keywords = group.get("negative_keywords", [])

        # Verifica negativos
        if any(_match_keyword(norm_a, neg) for neg in neg_keywords) or any(_match_keyword(norm_b, neg) for neg in neg_keywords):
            continue

        match_a = any(_match_keyword(norm_a, kw) for kw in keywords)
        match_b = any(_match_keyword(norm_b, kw) for kw in keywords)

        if match_a and match_b:
            concept_name = group["concept"]
            return SemanticMatchItem(
                item_a=item_a,
                item_b=item_b,
                equivalence=True,
                relation="semantic_equivalent",
                explanation=f"Ambas as cláusulas tratam do mesmo conceito securitário D&O: {concept_name}.",
                confidence=0.90,
                evidence_a=item_a,
                evidence_b=item_b
            )

    return None


def compare_clause_lists(
    list_a: List[str],
    list_b: List[str],
    llm_client: Optional[Any] = None
) -> Tuple[List[str], List[str], List[str], List[SemanticMatchItem]]:
    """Compara listas de cláusulas sem depender apenas de correspondência literal.

    Retorna:
        Tuple: (exclusivas_a, exclusivas_b, comuns, semantic_matches)
    """
    norm_items_a = normalize_list(list_a)
    norm_items_b = normalize_list(list_b)

    map_a = {normalize_text(item): item for item in norm_items_a}
    map_b = {normalize_text(item): item for item in norm_items_b}

    matched_a = set()
    matched_b = set()
    semantic_matches: List[SemanticMatchItem] = []
    comuns: List[str] = []

    # 1. Casamento literal direto
    for k_a, orig_a in map_a.items():
        if k_a in map_b:
            matched_a.add(k_a)
            matched_b.add(k_a)
            comuns.append(orig_a)
            semantic_matches.append(SemanticMatchItem(
                item_a=orig_a,
                item_b=map_b[k_a],
                equivalence=True,
                relation="semantic_equivalent",
                explanation="Cláusulas com redação idêntica.",
                confidence=1.0,
                evidence_a=orig_a,
                evidence_b=map_b[k_a]
            ))

    # 2. Casamento semântico nas cláusulas remanescentes
    remaining_a = [k for k in map_a.keys() if k not in matched_a]
    remaining_b = [k for k in map_b.keys() if k not in matched_b]

    for k_a in remaining_a:
        orig_a = map_a[k_a]
        title_a = orig_a.split(":")[0].strip()
        norm_t_a = normalize_text(title_a)
        for k_b in list(remaining_b):
            orig_b = map_b[k_b]
            title_b = orig_b.split(":")[0].strip()
            norm_t_b = normalize_text(title_b)

            # Evita chamar LLM remoto para cláusulas completamente desconexas
            if llm_client and hasattr(llm_client, "is_available") and llm_client.is_available():
                same_group = any(
                    any(_match_keyword(k_a, kw) for kw in grp["keywords"]) and
                    any(_match_keyword(k_b, kw) for kw in grp["keywords"])
                    for grp in DO_SEMANTIC_GROUPS
                )
                is_plausible = (norm_t_a == norm_t_b or same_group)
                if not is_plausible:
                    continue

            match_res = compare_clauses_semantically(orig_a, orig_b, llm_client=llm_client)
            if match_res:
                if match_res.relation == "semantic_equivalent":
                    matched_a.add(k_a)
                    matched_b.add(k_b)
                    remaining_b.remove(k_b)
                    comuns.append(orig_a)
                    semantic_matches.append(match_res)
                    break
                elif match_res.relation in ("changed_scope", "changed_condition", "changed_limit", "broader", "narrower"):
                    matched_a.add(k_a)
                    matched_b.add(k_b)
                    remaining_b.remove(k_b)
                    # Cláusulas com o mesmo conceito, porém com alteração substantiva (NÃO são idênticas em comuns)
                    semantic_matches.append(match_res)
                    break
                elif match_res.relation == "different":
                    semantic_matches.append(match_res)

    exclusivas_a = [map_a[k] for k in map_a if k not in matched_a]
    exclusivas_b = [map_b[k] for k in map_b if k not in matched_b]

    return exclusivas_a, exclusivas_b, comuns, semantic_matches


def compare_list_items(list_a: List[str], list_b: List[str]) -> Tuple[List[str], List[str], List[str]]:
    """Função legada mantida para compatibilidade direta de interface."""
    excl_a, excl_b, comuns, _ = compare_clause_lists(list_a, list_b)
    return excl_a, excl_b, comuns


# =============================================================================
# CÁLCULO DE SCORE DE SIMILARIDADE
# =============================================================================

def calculate_similarity_score(
    diffs: List[FieldDiff],
    coberturas_stats: Tuple[int, int, int],
    exclusoes_stats: Tuple[int, int, int],
    semantic_matches: Optional[List[SemanticMatchItem]] = None
) -> float:
    """Calcula score percentual composto auxiliar de similaridade estrutural e textual (0 a 100%).

    Atenção: Ausência bilateral ('ambos_ausentes') não constitui convergência substantiva
    e não pontua positivamente na dimensão escalar. Cláusulas com mesmo título porém com
    alteração substantiva de escopo, limites ou condições pontuam 0.0 na dimensão de
    convergência de cláusulas. O score não substitui a análise detalhada dos FieldDiffs
    e não representa juízo de valor, comercial ou jurídico.
    """
    total_scalar = len(diffs)
    if total_scalar > 0:
        # Apenas campos efetivamente preenchidos e idênticos recebem pontuação substantiva
        equal_scalar = sum(1 for d in diffs if d.tipo_diferenca == "igual")
        scalar_score = (equal_scalar / total_scalar) * 40.0
    else:
        scalar_score = 0.0

    excl_a, excl_b, comuns_cob = coberturas_stats
    total_cob = excl_a + excl_b + comuns_cob

    # Avaliação de correspondências semânticas e penalização de divergências internas
    if semantic_matches:
        equiv_cobs = sum(
            1.0 if m.relation == "semantic_equivalent"
            else 0.5 if m.relation in ("broader", "narrower")
            else 0.0
            for m in semantic_matches
        )
        total_clauses = max(1, len(semantic_matches) + excl_a + excl_b)
        cob_score = (equiv_cobs / total_clauses) * 40.0
    else:
        cob_score = ((comuns_cob / total_cob) * 40.0) if total_cob > 0 else 0.0

    excl_ea, excl_eb, comuns_exc = exclusoes_stats
    total_exc = excl_ea + excl_eb + comuns_exc
    exc_score = ((comuns_exc / total_exc) * 20.0) if total_exc > 0 else 0.0

    total_score = scalar_score + cob_score + exc_score
    return round(max(0.0, min(100.0, total_score)), 1)


# =============================================================================
# ETAPA 9 — COMPARAÇÃO GERAL DE APÓLICES D&O
# =============================================================================

def compare_policies(
    apolice_a: ApoliceDAO,
    apolice_b: ApoliceDAO,
    llm_client: Optional[Any] = None
) -> ComparisonResult:
    """Executa comparação analítica completa entre duas apólices D&O."""
    conflicts_map: Dict[str, Any] = {}

    # Mapeamento de conflitos pré-existentes
    for k, v in (apolice_a.conflitos_extracao or {}).items():
        if v:
            conflicts_map[f"apolice_a_{k}"] = v
    for k, v in (apolice_b.conflitos_extracao or {}).items():
        if v:
            conflicts_map[f"apolice_b_{k}"] = v

    diffs: List[FieldDiff] = [
        compare_scalar_field(
            "seguradora", "Companhia Seguradora",
            apolice_a.seguradora, apolice_b.seguradora,
            categoria=TAXONOMY_CATEGORIES["seguradora"],
            evidence_a=apolice_a.evidencias.get("seguradora"),
            evidence_b=apolice_b.evidencias.get("seguradora"),
            conflito_a="seguradora" in (apolice_a.conflitos_extracao or {}),
            conflito_b="seguradora" in (apolice_b.conflitos_extracao or {})
        ),
        compare_scalar_field(
            "numero_apolice", "Número da Apólice",
            apolice_a.numero_apolice, apolice_b.numero_apolice,
            categoria=TAXONOMY_CATEGORIES["numero_apolice"],
            evidence_a=apolice_a.evidencias.get("numero_apolice"),
            evidence_b=apolice_b.evidencias.get("numero_apolice"),
            conflito_a="numero_apolice" in (apolice_a.conflitos_extracao or {}),
            conflito_b="numero_apolice" in (apolice_b.conflitos_extracao or {})
        ),
        compare_scalar_field(
            "processo_susep", "Processo SUSEP",
            apolice_a.processo_susep, apolice_b.processo_susep,
            categoria=TAXONOMY_CATEGORIES["processo_susep"],
            evidence_a=apolice_a.evidencias.get("processo_susep"),
            evidence_b=apolice_b.evidencias.get("processo_susep"),
            conflito_a="processo_susep" in (apolice_a.conflitos_extracao or {}),
            conflito_b="processo_susep" in (apolice_b.conflitos_extracao or {})
        ),
        compare_scalar_field(
            "segurado", "Empresa Segurada / Tomadora",
            apolice_a.segurado, apolice_b.segurado,
            categoria=TAXONOMY_CATEGORIES["segurado"],
            evidence_a=apolice_a.evidencias.get("segurado"),
            evidence_b=apolice_b.evidencias.get("segurado"),
            conflito_a="segurado" in (apolice_a.conflitos_extracao or {}),
            conflito_b="segurado" in (apolice_b.conflitos_extracao or {})
        ),
        compare_scalar_field(
            "vigencia_inicio", "Início de Vigência",
            apolice_a.vigencia_inicio, apolice_b.vigencia_inicio,
            categoria=TAXONOMY_CATEGORIES["vigencia_inicio"],
            is_date=True,
            evidence_a=apolice_a.evidencias.get("vigencia_inicio"),
            evidence_b=apolice_b.evidencias.get("vigencia_inicio"),
            conflito_a="vigencia_inicio" in (apolice_a.conflitos_extracao or {}),
            conflito_b="vigencia_inicio" in (apolice_b.conflitos_extracao or {})
        ),
        compare_scalar_field(
            "vigencia_fim", "Término de Vigência",
            apolice_a.vigencia_fim, apolice_b.vigencia_fim,
            categoria=TAXONOMY_CATEGORIES["vigencia_fim"],
            is_date=True,
            evidence_a=apolice_a.evidencias.get("vigencia_fim"),
            evidence_b=apolice_b.evidencias.get("vigencia_fim"),
            conflito_a="vigencia_fim" in (apolice_a.conflitos_extracao or {}),
            conflito_b="vigencia_fim" in (apolice_b.conflitos_extracao or {})
        ),
        compare_scalar_field(
            "retroatividade", "Data de Retroatividade",
            apolice_a.retroatividade, apolice_b.retroatividade,
            categoria=TAXONOMY_CATEGORIES["retroatividade"],
            is_date=True,
            evidence_a=apolice_a.evidencias.get("retroatividade"),
            evidence_b=apolice_b.evidencias.get("retroatividade"),
            conflito_a="retroatividade" in (apolice_a.conflitos_extracao or {}),
            conflito_b="retroatividade" in (apolice_b.conflitos_extracao or {})
        ),
        compare_scalar_field(
            "limite_responsabilidade", "Limite Máximo de Garantia (LMG)",
            apolice_a.limite_responsabilidade, apolice_b.limite_responsabilidade,
            categoria=TAXONOMY_CATEGORIES["limite_responsabilidade"],
            is_financial=True,
            evidence_a=apolice_a.evidencias.get("limite_responsabilidade"),
            evidence_b=apolice_b.evidencias.get("limite_responsabilidade"),
            conflito_a="limite_responsabilidade" in (apolice_a.conflitos_extracao or {}),
            conflito_b="limite_responsabilidade" in (apolice_b.conflitos_extracao or {})
        ),
        compare_scalar_field(
            "franquia", "Franquia / Retenção",
            apolice_a.franquia, apolice_b.franquia,
            categoria=TAXONOMY_CATEGORIES["franquia"],
            is_financial=True,
            evidence_a=apolice_a.evidencias.get("franquia"),
            evidence_b=apolice_b.evidencias.get("franquia"),
            conflito_a="franquia" in (apolice_a.conflitos_extracao or {}),
            conflito_b="franquia" in (apolice_b.conflitos_extracao or {})
        ),
        compare_scalar_field(
            "premio_total", "Prêmio Total",
            apolice_a.premio_total, apolice_b.premio_total,
            categoria=TAXONOMY_CATEGORIES["premio_total"],
            is_financial=True,
            evidence_a=apolice_a.evidencias.get("premio_total"),
            evidence_b=apolice_b.evidencias.get("premio_total"),
            conflito_a="premio_total" in (apolice_a.conflitos_extracao or {}),
            conflito_b="premio_total" in (apolice_b.conflitos_extracao or {})
        ),
        compare_scalar_field(
            "territorio", "Âmbito Territorial",
            apolice_a.territorio, apolice_b.territorio,
            categoria=TAXONOMY_CATEGORIES["territorio"],
            evidence_a=apolice_a.evidencias.get("territorio"),
            evidence_b=apolice_b.evidencias.get("territorio"),
            conflito_a="territorio" in (apolice_a.conflitos_extracao or {}),
            conflito_b="territorio" in (apolice_b.conflitos_extracao or {})
        ),
        compare_scalar_field(
            "legislacao_aplicavel", "Legislação e Foro Aplicável",
            apolice_a.legislacao_aplicavel, apolice_b.legislacao_aplicavel,
            categoria=TAXONOMY_CATEGORIES["legislacao_aplicavel"],
            evidence_a=apolice_a.evidencias.get("legislacao_aplicavel"),
            evidence_b=apolice_b.evidencias.get("legislacao_aplicavel"),
            conflito_a="legislacao_aplicavel" in (apolice_a.conflitos_extracao or {}),
            conflito_b="legislacao_aplicavel" in (apolice_b.conflitos_extracao or {})
        ),
        compare_scalar_field(
            "cod_ramo", "Ramo SUSEP",
            f"{apolice_a.cod_ramo} - {apolice_a.ramo_descricao or 'D&O'}" if apolice_a.cod_ramo else None,
            f"{apolice_b.cod_ramo} - {apolice_b.ramo_descricao or 'D&O'}" if apolice_b.cod_ramo else None,
            categoria=TAXONOMY_CATEGORIES["cod_ramo"],
            evidence_a=apolice_a.evidencias.get("cod_ramo"),
            evidence_b=apolice_b.evidencias.get("cod_ramo"),
            conflito_a="cod_ramo" in (apolice_a.conflitos_extracao or {}),
            conflito_b="cod_ramo" in (apolice_b.conflitos_extracao or {})
        ),
        compare_scalar_field(
            "tipo_movimento", "Tipo de Movimento Regulatório",
            f"{apolice_a.tipo_movimento} - {apolice_a.tipo_movimento_descricao or 'Emissão'}" if apolice_a.tipo_movimento else None,
            f"{apolice_b.tipo_movimento} - {apolice_b.tipo_movimento_descricao or 'Emissão'}" if apolice_b.tipo_movimento else None,
            categoria=TAXONOMY_CATEGORIES["tipo_movimento"],
            evidence_a=apolice_a.evidencias.get("tipo_movimento"),
            evidence_b=apolice_b.evidencias.get("tipo_movimento"),
            conflito_a="tipo_movimento" in (apolice_a.conflitos_extracao or {}),
            conflito_b="tipo_movimento" in (apolice_b.conflitos_extracao or {})
        ),
    ]

    # Comparação de listas contratuais (Coberturas, Exclusões e Cláusulas Especiais - Fase 5)
    cob_excl_a, cob_excl_b, cob_comuns, cob_semantic = compare_clause_lists(
        apolice_a.coberturas, apolice_b.coberturas, llm_client=llm_client
    )
    exc_excl_a, exc_excl_b, exc_comuns, exc_semantic = compare_clause_lists(
        apolice_a.exclusoes, apolice_b.exclusoes, llm_client=llm_client
    )
    ce_excl_a, ce_excl_b, ce_comuns, ce_semantic = compare_clause_lists(
        apolice_a.clausulas_especiais, apolice_b.clausulas_especiais, llm_client=llm_client
    )

    all_semantic_matches = cob_semantic + exc_semantic + ce_semantic

    # Enriquecimento de proveniência contratual auditável (página + método) nas evidências A/B
    for match in all_semantic_matches:
        title_a = match.item_a.split(":")[0].strip()
        title_b = match.item_b.split(":")[0].strip()
        ev_a = apolice_a.evidencias.get(title_a)
        if not ev_a:
            for k, v in apolice_a.evidencias.items():
                if title_a.lower() in k.lower() or k.lower() in title_a.lower():
                    ev_a = v
                    break
        if ev_a:
            match.page_a = ev_a.page
            match.method_a = ev_a.method

        ev_b = apolice_b.evidencias.get(title_b)
        if not ev_b:
            for k, v in apolice_b.evidencias.items():
                if title_b.lower() in k.lower() or k.lower() in title_b.lower():
                    ev_b = v
                    break
        if ev_b:
            match.page_b = ev_b.page
            match.method_b = ev_b.method

    # Cálculo do Score de Similaridade
    score = calculate_similarity_score(
        diffs=diffs,
        coberturas_stats=(len(cob_excl_a), len(cob_excl_b), len(cob_comuns)),
        exclusoes_stats=(len(exc_excl_a), len(exc_excl_b), len(exc_comuns)),
        semantic_matches=all_semantic_matches
    )

    # Identificação das categorias únicas cobertas
    cat_list = [d.categoria for d in diffs] + [TAXONOMY_CATEGORIES["coberturas"], TAXONOMY_CATEGORIES["exclusoes"]]
    if apolice_a.clausulas_especiais or apolice_b.clausulas_especiais:
        cat_list.append(TAXONOMY_CATEGORIES["clausulas_especiais"])
    categories_present = sorted(list(set(cat_list)))

    # Resumo objetivo das assimetrias
    divergencias = [d for d in diffs if d.ha_diferenca]
    iguais = [d for d in diffs if d.tipo_diferenca == "igual"]
    ambos_ausentes = [d for d in diffs if d.tipo_diferenca == "ambos_ausentes"]

    summary_text = (
        f"A análise comparativa entre as apólices identificou {len(divergencias)} assimetria(s) em parâmetros contratuais "
        f"escalares, {len(iguais)} parâmetro(s) com convergência substantiva comprovada e {len(ambos_ausentes)} parâmetro(s) não "
        f"identificados documentalmente em ambas as propostas. No escopo de garantias, identificou-se {len(cob_excl_a)} cobertura(s) "
        f"exclusiva(s) na Apólice A, {len(cob_excl_b)} cobertura(s) exclusiva(s) na Apólice B e {len(cob_comuns)} garantia(s) convergente(s). "
        f"O índice de similaridade estrutural ({score}%) possui caráter estritamente técnico e auxiliar, não constituindo parecer de mérito ou juízo de contratação."
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
        exclusoes_comuns=exc_comuns,
        clausulas_especiais_exclusivas_a=ce_excl_a,
        clausulas_especiais_exclusivas_b=ce_excl_b,
        clausulas_especiais_comuns=ce_comuns,
        categories=categories_present,
        semantic_matches=all_semantic_matches,
        conflicts=conflicts_map,
        summary=summary_text,
        metadata={
            "comparison_engine_version": "fase5_v1.0",
            "taxonomy_version": "d_and_o_v1",
            "deterministic_reproducible": True,
            "has_llm_client": bool(llm_client and hasattr(llm_client, "is_available") and llm_client.is_available()),
            "score_nature": "similaridade_tecnica_estrutural_auxiliar",
            "note": "FieldDiffs e SemanticMatches constituem a fonte principal de divergências contratuais."
        }
    )
