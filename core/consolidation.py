"""Motor de consolidação determinística e resolução de divergências entre fragmentos.

Elimina a estratégia ingênua de primeiro valor encontrado, aplicando normalização estrita,
detecção de concordância, resolução objetiva por completude, preservação de proveniência
e registro auditável de evidências e conflitos.
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from core.schemas import EvidenceItem


def normalize_scalar(field_name: str, val: Any) -> Optional[str]:
    """Normaliza deterministamente um valor escalar, eliminando strings espúrias."""
    if val is None:
        return None

    s = " ".join(str(val).split()).strip()
    if not s or s.lower() in ("none", "null", "n/a", "undefined", "não informado", "nao informado"):
        return None

    # Filtro de ruídos: linhas de sumário/índice com pontilhado (dot leaders)
    if re.search(r'\.{3,}|_{3,}|-{3,}', s):
        return None

    # Filtro de ruídos: fragmentos de pontuação ou conectivos sem conteúdo léxico mínimo
    alnum = re.sub(r'[^\w]', '', s)
    if len(alnum) < 4 and field_name not in ("tipo_movimento", "cod_ramo"):
        return None

    # Filtro de definições genéricas de glossário ou cláusulas atribuídas como segurado/seguradora
    if field_name == "segurado":
        lower = s.lower()
        if any(term in lower for term in (
            "objeto garantido", "pessoa física", "pessoa jurídica", "pessoa que contrata", "termo que define",
            "durante a vigência", "no exercício", "administradores", "diretores", "conselheiros",
            "sociedade e suas", "qualquer pessoa", "na qualidade de", "conforme definido"
        )) or re.match(r'^\d+[\.\)]', s):
            return None
        if len(alnum) < 4:
            return None
    elif field_name == "seguradora":
        lower = s.lower()
        if any(term in lower for term in (
            "cabeçalho", "cabecalho", "objeto garantido", "pessoa física", "pessoa fisica",
            "pessoa jurídica", "pessoa juridica", "pessoa física ou jurídica contratante",
            "pessoa que contrata", "termo que define", "conforme definido", "sociedade seguradora"
        )):
            return None
        if len(alnum) < 3:
            return None
        from core.domain_detector import resolve_seguradora
        canonical = resolve_seguradora(extracted_val=s)
        if canonical:
            return canonical
        if any(w in lower for w in ("pessoa", "cabeçalho", "cabecalho", "definido", "glossário", "glossario")):
            return None

    # Normalização de datas (DD/MM/AAAA)
    if "vigencia" in field_name or "data" in field_name or field_name == "retroatividade":
        date_match = re.search(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b', s)
        if date_match:
            d, m, y = date_match.groups()
            formatted_date = f"{int(d):02d}/{int(m):02d}/{y}"
            # Se for retroatividade com texto explicativo adicional, preserva o contexto
            if field_name == "retroatividade" and len(s) > 10:
                return f"{formatted_date} ({s.replace(date_match.group(0), '').strip(' ,()-')})"
            return formatted_date

    # Normalização de valores monetários
    if field_name in ("limite_responsabilidade", "premio_total", "franquia"):
        # Se contiver texto explicativo entre parênteses, isenção ou percentual, preserva a íntegra
        if "(" in s or "isento" in s.lower() or "sem franquia" in s.lower() or "%" in s:
            return s
        match_money = re.search(r'(?:r\$\s*)?([\d\.,]+)', s, re.IGNORECASE)
        if match_money:
            digits = match_money.group(1).strip()
            return f"R$ {digits}"

    # Normalização de identificadores regulatórios e contratuais
    if field_name == "numero_apolice":
        # Rejeita expressamente processos SUSEP atribuídos erroneamente a número de apólice
        if re.search(r'\b(?:processo\s+susep|proc\.?\s*susep|susep\s*n[ºo\.]?)\b', s, re.IGNORECASE):
            return None

    if field_name == "processo_susep":
        match_proc = re.search(r'([0-9\.\-/]{8,35})', s)
        if match_proc:
            return f"Proc. SUSEP {match_proc.group(1).strip()}"
        return s

    if field_name == "cod_ramo":
        match_digits = re.search(r'\b\d{4}\b', s)
        if match_digits:
            return match_digits.group(0)

    if field_name == "tipo_movimento":
        match_mov = re.search(r'\b10[1-8]\b', s)
        if match_mov:
            return match_mov.group(0)

    if field_name == "document_type":
        low = s.lower()
        if "condi" in low:
            return "condicoes_gerais"
        elif "endoss" in low:
            return "endosso"
        elif "propost" in low:
            return "proposta"
        elif "apolic" in low or "front" in low:
            return "apolice_individual"
        return low

    return s


def consolidate_scalar_field(
    field_name: str,
    candidates: List[Any]
) -> Tuple[Optional[str], Optional[List[str]]]:
    """Consolida candidatos de múltiplos chunks para um campo escalar (compatibilidade legada)."""
    val, confs, _, _ = consolidate_scalar_field_with_evidence(
        field_name,
        [(c, None) for c in candidates]
    )
    return val, confs


def consolidate_scalar_field_with_evidence(
    field_name: str,
    candidate_tuples: List[Tuple[Any, Optional[EvidenceItem]]]
) -> Tuple[Optional[str], Optional[List[str]], Optional[EvidenceItem], List[EvidenceItem]]:
    """Consolida candidatos associando cada valor à sua evidência contratual auditável.

    Retorna:
        Tuple: (valor_resolvido, lista_de_conflitos, evidencia_resolvida, lista_evidencias_conflito)
    """
    norm_to_evidences: Dict[str, List[EvidenceItem]] = {}
    normalized_values: List[str] = []

    for val, ev in candidate_tuples:
        norm = normalize_scalar(field_name, val)
        if norm is not None:
            if norm not in norm_to_evidences:
                norm_to_evidences[norm] = []
                normalized_values.append(norm)
            if ev is not None:
                norm_to_evidences[norm].append(ev)

    if not normalized_values:
        return None, None, None, []

    # Caso 1: Todos os fragmentos concordam
    if len(normalized_values) == 1:
        resolved = normalized_values[0]
        ev_list = norm_to_evidences.get(resolved, [])
        best_ev = max(ev_list, key=lambda e: e.confidence) if ev_list else None
        return resolved, None, best_ev, []

    # Caso 2: Um candidato é uma extensão/completude de outro
    # Exemplo: "Allianz" vs "Allianz Global Corporate & Specialty"
    # Exemplo: "Isento" vs "R$ 50.000,00 (Isento para Side A)"
    sorted_by_len = sorted(normalized_values, key=len, reverse=True)
    longest = sorted_by_len[0]

    all_subsumed = True
    for item in sorted_by_len[1:]:
        if item.lower() not in longest.lower():
            all_subsumed = False
            break

    if all_subsumed:
        ev_list = norm_to_evidences.get(longest, [])
        best_ev = max(ev_list, key=lambda e: e.confidence) if ev_list else None
        return longest, None, best_ev, []

    # Caso 3: Conflito genuíno irreconciliável entre fragmentos (ex: R$ 10M vs R$ 25M)
    # Regra estrita: valor = None e preserva todas as evidências conflitantes
    conflict_evs = [
        ev for ev_list in norm_to_evidences.values() for ev in ev_list if ev is not None
    ]
    return None, normalized_values, None, conflict_evs


def consolidate_list_field(lists_of_items: List[List[Any]]) -> List[str]:
    """Consolida e deduplica listas (compatibilidade legada)."""
    items, _ = consolidate_list_field_with_evidence([
        [(item, None) for item in l] for l in lists_of_items
    ])
    return items


def consolidate_list_field_with_evidence(
    lists_of_tuples: List[List[Tuple[Any, Optional[EvidenceItem]]]]
) -> Tuple[List[str], Dict[str, EvidenceItem]]:
    """Consolida listas preservando a evidência de cada item distinto."""
    seen_keys = set()
    result: List[str] = []
    item_evidences: Dict[str, EvidenceItem] = {}

    for item_list in lists_of_tuples:
        if not isinstance(item_list, list):
            continue
        for item_data in item_list:
            if isinstance(item_data, tuple):
                item_val, item_ev = item_data
            else:
                item_val, item_ev = item_data, None

            if item_val is None:
                continue
            text = " ".join(str(item_val).split()).strip()
            if not text or text.lower() in ("none", "null", "n/a"):
                continue

            norm_key = re.sub(r'[^\w\s]', '', text.lower()).strip()
            if norm_key and norm_key not in seen_keys:
                seen_keys.add(norm_key)
                result.append(text)
                if item_ev is not None:
                    item_evidences[norm_key] = item_ev

    return result, item_evidences


def consolidate_extracted_chunks(
    partials: List[Dict[str, Any]],
    scalar_fields: List[str],
    list_fields: List[str]
) -> Tuple[Dict[str, Any], Dict[str, EvidenceItem], Dict[str, List[str]], Dict[str, List[EvidenceItem]]]:
    """Executa a consolidação de dados e evidências de múltiplos fragmentos.

    Retorna:
        Tuple: (dados_consolidados, evidencias_resolvidas, dicionario_conflitos, evidencias_conflito)
    """
    consolidated: Dict[str, Any] = {}
    field_evidences: Dict[str, EvidenceItem] = {}
    conflicts: Dict[str, List[str]] = {}
    conflict_evidences: Dict[str, List[EvidenceItem]] = {}

    for field in scalar_fields:
        candidates_with_ev: List[Tuple[Any, Optional[EvidenceItem]]] = []
        for p in partials:
            if field in p:
                raw_v = p.get(field)
                ev_obj: Optional[EvidenceItem] = None

                # Suporte a formatos estruturados com evidência acoplada
                if isinstance(raw_v, dict) and ("valor" in raw_v or "value" in raw_v):
                    val = raw_v.get("valor", raw_v.get("value"))
                    ev_data = raw_v.get("evidencia", raw_v.get("evidence"))
                    if isinstance(ev_data, EvidenceItem):
                        ev_obj = ev_data
                    elif isinstance(ev_data, dict):
                        try:
                            ev_obj = EvidenceItem(**ev_data)
                        except Exception:
                            ev_obj = None
                else:
                    val = raw_v
                    # Verifica metadado no dicionário parcial
                    p_evs = p.get("__evidencias__", {})
                    if field in p_evs:
                        ev_obj = p_evs[field]

                candidates_with_ev.append((val, ev_obj))

        res_val, conf_vals, res_ev, conf_evs = consolidate_scalar_field_with_evidence(
            field, candidates_with_ev
        )
        consolidated[field] = res_val
        if res_ev is not None:
            field_evidences[field] = res_ev
        if conf_vals:
            conflicts[field] = conf_vals
        if conf_evs:
            conflict_evidences[field] = conf_evs

    for field in list_fields:
        candidates_lists: List[List[Tuple[Any, Optional[EvidenceItem]]]] = []
        for p in partials:
            raw_list = p.get(field)
            if isinstance(raw_list, list):
                p_evs = p.get("__evidencias__", {})
                default_ev = p_evs.get(field)
                candidates_lists.append([(item, default_ev) for item in raw_list])

        items, _ = consolidate_list_field_with_evidence(candidates_lists)
        consolidated[field] = items

    return consolidated, field_evidences, conflicts, conflict_evidences
