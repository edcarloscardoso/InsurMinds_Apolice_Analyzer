"""Particionamento estruturado e rastreável de documentos contratuais longos.

Garante que 100% das páginas do documento sejam cobertas sem qualquer descarte silencioso,
preservando o número da página, o contexto de continuidade e os limites de caracteres.
"""
import re
from typing import List, Tuple, Optional, Dict, Any
from core.schemas import DocumentChunk, EvidenceItem


def _find_page_intervals(text: str) -> List[Tuple[int, int, int]]:
    """Mapeia os intervalos de caracteres para cada página detectada no texto.

    Retorna lista de tuplas: (numero_pagina, pos_inicio, pos_fim).
    """
    matches = list(re.finditer(r'--- PÁGINA (\d+) ---', text))
    if not matches:
        return [(1, 0, len(text))]

    intervals: List[Tuple[int, int, int]] = []
    for idx, match in enumerate(matches):
        page_num = int(match.group(1))
        start_pos = match.start()
        end_pos = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        intervals.append((page_num, start_pos, end_pos))

    return intervals


def _get_page_range_for_span(intervals: List[Tuple[int, int, int]], start: int, end: int) -> Tuple[int, int]:
    """Determina a página inicial e final para uma janela de caracteres."""
    if not intervals:
        return (1, 1)

    start_page = intervals[0][0]
    end_page = intervals[-1][0]

    for p_num, p_start, p_end in intervals:
        if p_start <= start < p_end:
            start_page = p_num
            break

    for p_num, p_start, p_end in intervals:
        if p_start < end <= p_end or (p_start <= start and end <= p_end):
            end_page = p_num
            break

    return (start_page, max(start_page, end_page))


def build_document_chunks(
    raw_text: str,
    max_chars: int = 45000,
    overlap: int = 3000
) -> List[DocumentChunk]:
    """Particiona o documento em objetos DocumentChunk estruturados com preservação de páginas.

    Args:
        raw_text: Texto completo extraído do documento.
        max_chars: Tamanho máximo aproximado de cada fragmento em caracteres.
        overlap: Sobreposição entre blocos consecutivos para continuidade de contexto.

    Returns:
        Lista de DocumentChunk com indexação sequencial e rastreabilidade de páginas.
    """
    text = raw_text or ""
    if not text.strip():
        return [
            DocumentChunk(
                index=1,
                page_start=1,
                page_end=1,
                text="",
                char_start=0,
                char_end=0
            )
        ]

    if max_chars <= overlap:
        raise ValueError(f"max_chars ({max_chars}) deve ser maior que overlap ({overlap})")

    intervals = _find_page_intervals(text)
    chunks: List[DocumentChunk] = []
    start = 0
    text_len = len(text)
    chunk_index = 1

    while start < text_len:
        hard_end = min(start + max_chars, text_len)
        end = hard_end

        # Tenta quebrar em marcador de página natural na segunda metade da janela
        if hard_end < text_len:
            page_break = text.rfind("\n--- PÁGINA ", start + max_chars // 2, hard_end)
            if page_break > start:
                end = page_break
            else:
                # Alternativa: quebrar em quebra de parágrafo duplo
                para_break = text.rfind("\n\n", start + max_chars // 2, hard_end)
                if para_break > start:
                    end = para_break + 2

        chunk_content = text[start:end].strip()
        page_start, page_end = _get_page_range_for_span(intervals, start, end)

        # Se o bloco começou no meio de uma página longa, preservar o cabeçalho
        # da página ativa para que o LLM e analisadores conheçam o contexto
        if not chunk_content.startswith("--- PÁGINA "):
            chunk_content = f"--- PÁGINA {page_start} ---\n{chunk_content}"

        if chunk_content:
            chunks.append(
                DocumentChunk(
                    index=chunk_index,
                    page_start=page_start,
                    page_end=page_end,
                    text=chunk_content,
                    char_start=start,
                    char_end=end
                )
            )
            chunk_index += 1

        if end >= text_len:
            break

        next_start = max(end - overlap, start + 1)
        start = next_start

    return chunks or [
        DocumentChunk(
            index=1,
            page_start=1,
            page_end=1,
            text="",
            char_start=0,
            char_end=0
        )
    ]


def chunk_text(
    raw_text: str,
    max_chars: int = 45000,
    overlap: int = 3000
) -> List[str]:
    """Retorna os conteúdos textuais dos chunks para compatibilidade com APIs anteriores."""
    return [chunk.text for chunk in build_document_chunks(raw_text, max_chars, overlap)]


def find_evidence_in_text(
    raw_text: str,
    target: str,
    method: str = "pdf_text",
    confidence: float = 0.95,
    chunk_index: Optional[int] = None,
    snippet_window: int = 140
) -> Optional[EvidenceItem]:
    """Localiza deterministicamente a página e o trecho literal de sustentação para um termo no documento."""
    if not raw_text or not target or len(target.strip()) < 3:
        return None

    intervals = _find_page_intervals(raw_text)

    # 1. Procura exata
    idx = raw_text.find(target)

    # 2. Se não encontrou exato, tenta ignorando maiúsculas/minúsculas
    if idx == -1:
        match_ci = re.search(re.escape(target), raw_text, re.IGNORECASE)
        if match_ci:
            idx = match_ci.start()
            target_len = match_ci.end() - match_ci.start()
        else:
            # 3. Tenta tokens principais (ex: primeiras 3 palavras significativas)
            words = [w for w in target.split() if len(w) > 3]
            if len(words) >= 2:
                subphrase = " ".join(words[:2])
                match_sub = re.search(re.escape(subphrase), raw_text, re.IGNORECASE)
                if match_sub:
                    idx = match_sub.start()
                    target_len = len(subphrase)
                else:
                    return None
            else:
                return None
    else:
        target_len = len(target)

    char_start = idx
    char_end = idx + target_len
    page_start, page_end = _get_page_range_for_span(intervals, char_start, char_end)

    # Extrai o contexto ao redor (linha inteira ou janela de caracteres) para formar o snippet
    line_start = raw_text.rfind("\n", 0, char_start)
    line_start = 0 if line_start == -1 else line_start + 1

    line_end = raw_text.find("\n", char_end)
    line_end = len(raw_text) if line_end == -1 else line_end

    raw_snippet = raw_text[line_start:line_end].strip()
    if not raw_snippet or len(raw_snippet) < len(target):
        snippet_start = max(0, char_start - 30)
        snippet_end = min(len(raw_text), char_end + snippet_window)
        raw_snippet = raw_text[snippet_start:snippet_end].strip()

    # Identifica cláusula/seção contratual precedente mais próxima
    section = None
    preceding_text = raw_text[max(0, char_start - 500):char_start]
    sec_match = re.findall(r'(?:cl[áa]usula|se[çc][ãa]o|artigo|item)\s*[\d\.]+[^\n\r]*', preceding_text, re.IGNORECASE)
    if sec_match:
        section = sec_match[-1].strip()

    return EvidenceItem(
        page=page_start,
        page_end=page_end if page_end != page_start else None,
        section=section,
        snippet=raw_snippet,
        method=method,
        confidence=confidence,
        chunk_index=chunk_index,
        char_start=char_start,
        char_end=char_end
    )


# =============================================================================
# ESPECIFICAÇÕES DE CLÁUSULAS CONTRATUAIS D&O (FASE 5)
# =============================================================================

DO_CONTRACT_CLAUSE_SPECS = [
    # Coberturas & Garantias
    {
        "name": "Defesa e Acordos",
        "category": "coberturas",
        "patterns": [
            r"19\.3\.1\.\s+Cada Segurado poderá escolher",
            r"DEFESA E ACORDOS REFERENTES A RECLAMAÇÕES",
            r"defesa e acordos"
        ]
    },
    {
        "name": "Garantias Pessoais (Aval e Fiança)",
        "category": "coberturas",
        "patterns": [
            r"4\.1\.10\.\s+Garantias Pessoais",
            r"Garantias Pessoais\s*\([^\)]*Aval",
            r"garantias pessoais"
        ]
    },
    {
        "name": "Custos de Defesa",
        "category": "coberturas",
        "patterns": [
            r"COBERTURA ADICIONAL DE CUSTOS DE DEFESA\s*\n\s*1\.",
            r"30\.1\.\s+Desde que não se vislumbre",
            r"30\.\s+ADIANTAMENTO DE CUSTOS DE DEFESA",
            r"adiantamento de custos de defesa",
            r"custos de defesa e honor[aá]rios"
        ]
    },
    {
        "name": "Cobertura Side A",
        "category": "coberturas",
        "patterns": [
            r"cobertura\s+(?:b[aá]sica\s+)?side\s+a\b",
            r"cobertura\s+a\b",
            r"side\s+a\s*\(indiv[ií]duos"
        ]
    },
    {
        "name": "Cobertura Side B",
        "category": "coberturas",
        "patterns": [
            r"COBERTURA B - A Seguradora pagará ao Tomador",
            r"cobertura\s+(?:b[aá]sica\s+)?side\s+b\b",
            r"cobertura\s+b\b",
            r"side\s+b\s*\(reembolso"
        ]
    },
    {
        "name": "Cobertura Side C",
        "category": "coberturas",
        "patterns": [
            r"COBERTURA ADICIONAL DE RECLAMAÇÕES CONTRA O TOMADOR[^\n]*SIDE C",
            r"cobertura\s+(?:adicional\s+)?side\s+c\b",
            r"side\s+c\s*\(sociedade"
        ]
    },
    {
        "name": "Multas e Penalidades",
        "category": "coberturas",
        "patterns": [
            r"COBERTURA ADICIONAL DE MULTAS E PENALIDADES",
            r"multas\s+e\s+penalidades\s+civis"
        ]
    },
    {
        "name": "Despesas de Contenção e Salvamento",
        "category": "coberturas",
        "patterns": [
            r"COBERTURA ADICIONAL DE DESPESAS DE CONTENÇÃO E SALVAMENTO",
            r"despesas de contenção e salvamento de sinistro"
        ]
    },
    {
        "name": "Herdeiros e Representantes Legais",
        "category": "coberturas",
        "patterns": [
            r"COBERTURA ADICIONAL PARA HERDEIROS,\s*REPRESENTANTES LEGAIS E\s*ESPÓLIO",
            r"herdeiros,\s*representantes legais e espólio"
        ]
    },
    {
        "name": "Penhora Online e Bloqueio de Bens",
        "category": "coberturas",
        "patterns": [
            r"penhora\s+online",
            r"bloqueio\s+de\s+bens",
            r"indisponibilidade\s+de\s+bens"
        ]
    },
    {
        "name": "Gestão de Crise e Imagem",
        "category": "coberturas",
        "patterns": [
            r"gest[aã]o\s+de\s+crise",
            r"despesas\s+de\s+publicidade\s+e\s+gest[aã]o\s+de\s+crise",
            r"prote[cç][aã]o\s+de\s+imagem"
        ]
    },
    {
        "name": "Investigações Regulatórias e Administrativas",
        "category": "coberturas",
        "patterns": [
            r"investiga[cç][oõ]es\s+regulatórias",
            r"custos\s+de\s+investiga[cç][aã]o",
            r"inquérito\s+administrativo"
        ]
    },
    # Exclusões
    {
        "name": "Poluição",
        "category": "exclusoes",
        "patterns": [
            r"POLUIÇÃO\s*\n\s*Descarga,\s*dispensa",
            r"poluição e contaminação ambiental",
            r"poluição\b"
        ]
    },
    {
        "name": "Atos Dolosos e Fraude",
        "category": "exclusoes",
        "patterns": [
            r"atos dolosos,\s*fraude",
            r"conduta dolosa ou \(ii\) de decisão judicial transitada em julgado",
            r"atos fraudulentos"
        ]
    },
    {
        "name": "Obtenção de Lucro ou Vantagem Indevida",
        "category": "exclusoes",
        "patterns": [
            r"obtenção de lucro ou vantagem",
            r"vantagem financeira indevida"
        ]
    },
    {
        "name": "Danos Corporais e Materiais",
        "category": "exclusoes",
        "patterns": [
            r"danos corporais,\s*morte\s+e\s+danos materiais",
            r"danos materiais e corporais"
        ]
    },
    # Cláusulas Especiais e Condições Contratuais
    {
        "name": "Inadimplemento do Prêmio",
        "category": "clausulas_especiais",
        "patterns": [
            r"16\.10\.\s+Nas hipóteses de fracionamento do Prêmio",
            r"inadimplemento do prêmio",
            r"falta de pagamento do prêmio"
        ]
    },
    {
        "name": "Agravamento do Risco",
        "category": "clausulas_especiais",
        "patterns": [
            r"18\.6\.1\.\s+NA HIPÓTESE EM QUE A OMISSÃO",
            r"18\.6\.1\.\s+Na hipótese em que a omissão quanto ao agravamento"
        ]
    }
]


def discover_contract_clauses(
    raw_text: str,
    document_domain: str = "do"
) -> Tuple[List[str], List[str], List[str], Dict[str, EvidenceItem]]:
    """Descobre e extrai cláusulas contratuais reais diretamente das páginas do documento.

    Retorna:
        Tuple: (coberturas, exclusoes, clausulas_especiais, evidencias)
        onde cada lista contém strings no formato canônico 'Título: Snippet do corpo'
        e evidencias mapeia o título da cláusula para o respectivo EvidenceItem com página e offset.
    """
    if not raw_text or document_domain != "do":
        return [], [], [], {}

    pages = raw_text.split("--- PÁGINA ")
    coberturas: List[str] = []
    exclusoes: List[str] = []
    clausulas_especiais: List[str] = []
    evidencias: Dict[str, EvidenceItem] = {}

    for spec in DO_CONTRACT_CLAUSE_SPECS:
        name = spec["name"]
        cat = spec["category"]
        found = False

        for p_str in pages:
            if not p_str.strip():
                continue
            try:
                p_num = int(p_str.split(" ---")[0])
            except ValueError:
                continue

            for pat in spec["patterns"]:
                match = re.search(pat, p_str, re.IGNORECASE)
                if match:
                    # Filtra falsos positivos de sumário / índice com pontilhados
                    line = p_str[max(0, match.start() - 50):min(len(p_str), match.end() + 100)]
                    if p_num <= 5 and re.search(r'\.{3,}\s*\d+', line):
                        continue

                    # Extrai trecho substancial da cláusula
                    start = match.start()
                    raw_snip = p_str[start:start + 300].replace("\n", " ")
                    clean_snip = " ".join(raw_snip.split())
                    formatted_entry = f"{name}: {clean_snip}"

                    ev = EvidenceItem(
                        page=p_num,
                        snippet=clean_snip[:180],
                        section=name,
                        method="pdf_text",
                        confidence=0.95
                    )
                    evidencias[name] = ev

                    if cat == "coberturas":
                        coberturas.append(formatted_entry)
                    elif cat == "exclusoes":
                        exclusoes.append(formatted_entry)
                    else:
                        clausulas_especiais.append(formatted_entry)

                    found = True
                    break
            if found:
                break

    return coberturas, exclusoes, clausulas_especiais, evidencias
