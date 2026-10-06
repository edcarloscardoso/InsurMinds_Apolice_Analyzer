"""Componente Assistente Contextual — Insurance Intelligence v1.0.
Copiloto de leitura e interpretação documental D&O contextual à análise ativa.
Opera exclusivamente sobre os dados e objetos contratuais já carregados:
ComparisonResult, FieldDiff, SemanticMatchItem, EvidenceItem, ApoliceDAO e Relatório.
Não cria segunda camada analítica, não recalcula score e não inventa evidências.
Princípio: "O assistente explica o contexto disponível; o documento continua sendo a fonte."
"""
from typing import Optional, List, Dict, Any, Tuple
import re
import streamlit as st

from core.database import db
from core.schemas import ApoliceDAO, ComparisonResult, SemanticMatchItem, FieldDiff, EvidenceItem
from ui.tokens import COLORS, TYPOGRAPHY, RADIUS, SHADOWS
from ui.styles import render_html
from ui.navigation import navigate_to
from ui.persona.profiles import get_active_profile


# Aviso Obrigatório de Governança de IA
AI_ASSISTANT_GOVERNANCE_NOTICE = (
    "Respostas são geradas a partir do contexto documental disponível e devem ser revisadas "
    "pelo profissional responsável. O texto contratual permanece sendo a fonte primária."
)

NO_EVIDENCE_AVAILABLE_MESSAGE = "Não há evidência documental disponível para sustentar esta resposta."
EMPTY_CONTEXT_MESSAGE = "Abra uma comparação ou uma diferença para ativar a assistência contextual."
ERROR_CONTEXT_MESSAGE = "A assistência contextual não pôde ser carregada."


def get_assistant_context(current_page: str) -> Dict[str, Any]:
    """Recupera o contexto completo da tela ativa, documentos selecionados e comparação em memória/banco."""
    profile = get_active_profile()

    # Detecção da tela e sub-tela
    screen_key = "comparacoes"
    item_idx: Optional[int] = None

    if current_page == "Comparações":
        viewing_diff_idx = st.session_state.get("viewing_diff_idx")
        if viewing_diff_idx is not None:
            screen_key = "detalhe"
            try:
                item_idx = int(viewing_diff_idx)
            except (ValueError, TypeError):
                item_idx = 0
        else:
            screen_key = "comparacao"
    elif current_page == "Relatórios":
        screen_key = "relatorio"
    elif current_page == "Documentos":
        screen_key = "biblioteca"
    elif current_page in ("Início", "Nova análise"):
        screen_key = "workspace"
    else:
        screen_key = "configuracoes"

    # Recuperação da análise ativa ou mais recente
    from ui.page_report import _get_active_or_latest_analysis
    comp_result, report_md, pol_a, pol_b = _get_active_or_latest_analysis()

    # Recuperação do item específico se estiver no Detalhe
    match_item: Optional[SemanticMatchItem] = None
    if screen_key == "detalhe" and comp_result and item_idx is not None:
        if 0 <= item_idx < len(comp_result.semantic_matches):
            match_item = comp_result.semantic_matches[item_idx]

    return {
        "screen_key": screen_key,
        "current_page": current_page,
        "item_idx": item_idx,
        "match_item": match_item,
        "comp_result": comp_result,
        "report_md": report_md,
        "pol_a": pol_a,
        "pol_b": pol_b,
        "profile": profile
    }


# =============================================================================
# FORMATADORES FACTUAIS DE RESPOSTA CONTEXTUAL
# =============================================================================

def _extract_match_details(item: SemanticMatchItem) -> Dict[str, Any]:
    """Extrai com segurança título, resumo, páginas e evidências de SemanticMatchItem."""
    if hasattr(item, "clause_title") and item.clause_title:
        title = item.clause_title
    elif hasattr(item, "item_a") and item.item_a:
        title_a = item.item_a.split(":")[0].strip()
        title_b = item.item_b.split(":")[0].strip() if hasattr(item, "item_b") and item.item_b else title_a
        title = title_a if title_a == title_b else f"{title_a} ⟷ {title_b}"
    else:
        title = "Cláusula Contratual"

    summary = getattr(item, "summary", "") or getattr(item, "explanation", "")

    page_b = getattr(item, "page_b", None)
    page_a = getattr(item, "page_a", None)
    sec_title = "Cláusulas Gerais"
    met_info = "pdf_text"
    conf_score = getattr(item, "confidence", 1.0)

    snippet_a = getattr(item, "clause_text_a", None) or getattr(item, "evidence_a", None)
    snippet_b = getattr(item, "clause_text_b", None) or getattr(item, "evidence_b", None)

    if hasattr(item, "evidence") and item.evidence:
        page_b = getattr(item.evidence, "page_num", None) or getattr(item.evidence, "page", page_b)
        page_a = getattr(item.evidence, "page_num", None) or getattr(item.evidence, "page", page_a)
        sec_title = getattr(item.evidence, "section_title", None) or getattr(item.evidence, "section", sec_title)
        met_info = getattr(item.evidence, "extraction_method", None) or getattr(item.evidence, "method", met_info)
        conf_score = getattr(item.evidence, "confidence_score", None) or getattr(item.evidence, "confidence", conf_score)
        snippet_a = getattr(item.evidence, "snippet_a", None) or getattr(item.evidence, "snippet", snippet_a)
        snippet_b = getattr(item.evidence, "snippet_b", None) or getattr(item.evidence, "snippet", snippet_b)

    return {
        "title": title,
        "summary": summary,
        "page_a": page_a,
        "page_b": page_b,
        "section": sec_title,
        "method": met_info,
        "confidence": conf_score,
        "snippet_a": snippet_a,
        "snippet_b": snippet_b,
        "relation": getattr(item, "relation", "equivalent")
    }


def format_difference_summary(comp: ComparisonResult, pol_a: ApoliceDAO, pol_b: ApoliceDAO, profile) -> Dict[str, Any]:
    """Gera síntese factual das principais diferenças contratuais identificadas."""
    if not comp or not comp.semantic_matches:
        return {"text": "Nenhuma alteração registrada nesta análise.", "citations": []}

    divergent_items = [
        m for m in comp.semantic_matches
        if m.relation in ("changed_scope", "different", "changed_condition", "changed_limit")
    ]

    total_items = len(comp.semantic_matches)
    total_div = len(divergent_items)

    intro = (
        f"Foram avaliadas <b>{total_items} cláusulas contratuais</b> no confronto entre "
        f"<b>{pol_a.nome_arquivo}</b> (Doc A) e <b>{pol_b.nome_arquivo}</b> (Doc B). "
        f"Identificaram-se <b>{total_div} itens com divergência substancial ou alteração de redação</b>."
    )

    items_summary = []
    citations = []

    for idx, item in enumerate(divergent_items[:6], 1):
        details = _extract_match_details(item)
        rel_label = {
            "changed_scope": "Alteração de Escopo",
            "different": "Redação Divergente",
            "changed_condition": "Condição Alterada",
            "changed_limit": "Parâmetro Financeiro Alterado"
        }.get(details["relation"], details["relation"])

        pag_info = f"pág. {details['page_b']}" if details["page_b"] else "pág. não informada"
        sec_info = f"seção '{details['section']}'" if details["section"] else "cláusula contratual"

        items_summary.append(
            f"<b>{idx}. {details['title']}</b> [{rel_label}]: "
            f"<i>{details['summary']}</i> (Doc B, {pag_info}, {sec_info})."
        )
        if details["snippet_b"] or details["snippet_a"]:
            citations.append({
                "clause_title": details["title"],
                "doc": "Doc B",
                "page": details["page_b"],
                "section": details["section"],
                "snippet": details["snippet_b"] or details["snippet_a"]
            })

    body = "<br/><br/>".join(items_summary)

    # Nota de foco por perfil
    persona_notes = {
        "analista": "Foco prioritário: conferir os prazos e condições precedentes das cláusulas divergentes.",
        "subscritor": "Foco prioritário: avaliar o impacto técnico das alterações sobre o risco agregado e condições de acionamento.",
        "corretor": "Foco prioritário: verificar obrigações adicionais estabelecidas na apólice mais recente para comunicação ao cliente.",
        "juridico": "Foco prioritário: validar a clareza e conformidade das cláusulas de perda de direitos perante a Circular SUSEP.",
        "visitante": "Foco prioritário: entender onde as regras do contrato mais recente diferem do contrato anterior."
    }
    pers_note = persona_notes.get(profile.id, persona_notes["visitante"])

    full_text = f"{intro}<br/><br/>{body}<br/><br/>💡 <b>Orientação de leitura ({profile.label}):</b> {pers_note}"
    return {"text": full_text, "citations": citations}


def format_scope_changes(comp: ComparisonResult, pol_a: ApoliceDAO, pol_b: ApoliceDAO, profile) -> Dict[str, Any]:
    """Explica detalhadamente as alterações de escopo contratual (mais restrito / mais amplo)."""
    from ui.page_detail import _get_item_category
    if not comp or not comp.semantic_matches:
        return {"text": "Nenhuma alteração de escopo registrada.", "citations": []}

    scope_items = [
        m for m in comp.semantic_matches
        if m.relation in ("changed_scope", "different")
    ]

    if not scope_items:
        return {
            "text": "Não foram detectadas cláusulas com alteração material de escopo de cobertura ou exclusões. As garantias mantêm simetria técnica.",
            "citations": []
        }

    lines = [
        f"A análise identificou <b>{len(scope_items)} cláusula(s)</b> com alteração no perímetro de cobertura ou exclusões contratuais:"
    ]
    citations = []

    for idx, item in enumerate(scope_items, 1):
        details = _extract_match_details(item)
        category = _get_item_category(details["title"])
        pag = f"pág. {details['page_b']}" if details["page_b"] else "pág. sob auditoria"
        lines.append(
            f"<b>{idx}. {details['title']}</b> (Categoria: {category})<br/>"
            f"• <b>Impacto no Escopo:</b> {details['summary']}<br/>"
            f"• <b>Referência documental:</b> {pol_b.nome_arquivo}, {pag}."
        )
        if details["snippet_b"]:
            citations.append({
                "clause_title": details["title"],
                "doc": "Doc B",
                "page": details["page_b"],
                "section": details["section"],
                "snippet": details["snippet_b"]
            })

    lines.append(
        f"<br/>🛡️ <i>Nota metodológica: Toda alteração de escopo deve ser lida em conjunto com as Condições Gerais e Particulares de cada seguradora.</i>"
    )
    return {"text": "<br/><br/>".join(lines), "citations": citations}


def format_review_items(comp: ComparisonResult, pol_a: ApoliceDAO, pol_b: ApoliceDAO, profile) -> Dict[str, Any]:
    """Lista pontos contratuais que demandam revisão profissional pelo perfil ativo."""
    from ui.page_detail import _get_profile_review_note
    if not comp or not comp.semantic_matches:
        return {"text": "Nenhum item pendente de revisão.", "citations": []}

    divergent_items = [
        m for m in comp.semantic_matches
        if m.relation in ("changed_scope", "different", "changed_condition", "changed_limit")
    ]

    lines = [
        f"<b>Itens Prioritários para Revisão Profissional · Perfil: {profile.label}</b><br/>"
        f"Recomenda-se exame detalhado das cláusulas abaixo em função da sua classificação de divergência:"
    ]
    citations = []

    for idx, item in enumerate(divergent_items[:5], 1):
        details = _extract_match_details(item)
        note = _get_profile_review_note(profile.id, details["relation"])
        pag = f"pág. {details['page_b']}" if details["page_b"] else "pág. documental"
        lines.append(
            f"<b>Item #{idx} · {details['title']}</b> ({details['relation']})<br/>"
            f"• <b>Achado:</b> {details['summary']}<br/>"
            f"• <b>Recomendação de revisão:</b> {note}<br/>"
            f"• <b>Localização:</b> {pol_b.nome_arquivo}, {pag}."
        )
        if details["snippet_b"]:
            citations.append({
                "clause_title": details["title"],
                "doc": "Doc B",
                "page": details["page_b"],
                "section": details["section"],
                "snippet": details["snippet_b"]
            })

    return {"text": "<br/><br/>".join(lines), "citations": citations}


def format_clause_explanation(match: SemanticMatchItem, pol_a: ApoliceDAO, pol_b: ApoliceDAO, profile) -> Dict[str, Any]:
    """Explica factual e minuciosamente a cláusula atualmente aberta no Detalhe da Diferença."""
    from ui.page_detail import _get_item_category, _get_profile_review_note
    if not match:
        return {"text": "Nenhuma cláusula selecionada para detalhamento.", "citations": []}

    details = _extract_match_details(match)

    rel_pt = {
        "equivalent": "Equivalência Material Plena",
        "equivalent_different_text": "Equivalência Semântica com Redação Distinta",
        "changed_scope": "Alteração no Escopo de Cobertura / Exclusão",
        "changed_condition": "Alteração de Condição Operacional ou Procedimental",
        "changed_limit": "Parâmetro Financeiro ou Limite Substantivo Alterado",
        "different": "Redação Contratual Divergente",
        "exclusive_a": "Cláusula Presente Exclusivamente no Documento A",
        "exclusive_b": "Cláusula Presente Exclusivamente no Documento B"
    }.get(details["relation"], details["relation"])

    category = _get_item_category(details["title"])
    review_note = _get_profile_review_note(profile.id, details["relation"])

    text = (
        f"<b>Cláusula sob Auditoria:</b> {details['title']}<br/>"
        f"• <b>Categoria Documental:</b> {category}<br/>"
        f"• <b>Relação Semântica Identificada:</b> <code>{rel_pt}</code><br/>"
        f"• <b>Síntese da Alteração:</b> {details['summary']}<br/><br/>"
        f"🔍 <b>Interpretação para o Perfil ({profile.label}):</b><br/>"
        f"{review_note}"
    )

    citations = []
    if details["snippet_b"] or details["snippet_a"]:
        citations.append({
            "clause_title": details["title"],
            "doc": "Confronto A/B",
            "page": details["page_b"],
            "section": details["section"],
            "snippet": details["snippet_b"] or details["snippet_a"]
        })

    return {"text": text, "citations": citations}


def format_clause_diff_ab(match: SemanticMatchItem, pol_a: ApoliceDAO, pol_b: ApoliceDAO, profile) -> Dict[str, Any]:
    """Apresenta o resumo estruturado da alteração redação A → redação B."""
    if not match:
        return {"text": "Cláusula não disponível.", "citations": []}

    details = _extract_match_details(match)

    has_text_a = bool(details["snippet_a"] and details["snippet_a"].strip())
    has_text_b = bool(details["snippet_b"] and details["snippet_b"].strip())

    text_a_preview = details["snippet_a"].strip() if has_text_a else "Texto não extraído isoladamente no Documento A."
    text_b_preview = details["snippet_b"].strip() if has_text_b else "Texto não extraído isoladamente no Documento B."

    text = (
        f"<b>Confronto Redacional Direto: {details['title']}</b><br/><br/>"
        f"📄 <b>Documento A ({pol_a.nome_arquivo}):</b><br/>"
        f"<i>\"{text_a_preview[:300]}{'...' if len(text_a_preview) > 300 else ''}\"</i><br/><br/>"
        f"📄 <b>Documento B ({pol_b.nome_arquivo}):</b><br/>"
        f"<i>\"{text_b_preview[:300]}{'...' if len(text_b_preview) > 300 else ''}\"</i><br/><br/>"
        f"⚖️ <b>Distinção Identificada pelo Motor Analítico:</b><br/>"
        f"{details['summary']}"
    )

    citations = []
    if has_text_a or has_text_b:
        citations.append({
            "clause_title": details["title"],
            "doc": "Doc A / Doc B",
            "page": details["page_b"],
            "section": details["section"],
            "snippet": f"A: {text_a_preview}\n\nB: {text_b_preview}"
        })

    return {"text": text, "citations": citations}


def format_clause_evidence(match: SemanticMatchItem, pol_a: ApoliceDAO, pol_b: ApoliceDAO) -> Dict[str, Any]:
    """Exibe a evidência literal documental da cláusula ou a mensagem obrigatória de ausência."""
    if not match:
        return {
            "text": f"<b>{NO_EVIDENCE_AVAILABLE_MESSAGE}</b>",
            "citations": [],
            "has_evidence": False
        }

    details = _extract_match_details(match)
    has_evidence = bool(details["snippet_a"] or details["snippet_b"])

    if not has_evidence:
        return {
            "text": f"<b>{NO_EVIDENCE_AVAILABLE_MESSAGE}</b>",
            "citations": [],
            "has_evidence": False
        }

    pag_info = f"Página: {details['page_b']}" if details['page_b'] is not None else "Página: Não informada"
    sec_info = f"Seção: {details['section']}" if details['section'] else "Seção: Cláusulas Gerais"
    met_info = f"Método de extração: {details['method'] or 'pdf_text'}"
    conf_info = f"Confiança: {int(details['confidence'] * 100)}%" if details['confidence'] else "Confiança: 100%"

    text = (
        f"<b>Evidência Documental Auditável: {details['title']}</b><br/>"
        f"• <b>{pag_info}</b> · <b>{sec_info}</b><br/>"
        f"• <b>{met_info}</b> · <b>{conf_info}</b><br/><br/>"
        f"<b>Trecho Literal Documento A ({pol_a.nome_arquivo}):</b><br/>"
        f"<pre style='background:#F1F5F9; border:1px solid #CBD5E1; padding:10px; border-radius:4px; font-family:{TYPOGRAPHY.FONT_CODE}; font-size:12px; white-space:pre-wrap; color:{COLORS.TEXT_MAIN};'>"
        f"{details['snippet_a'] or 'Snippet literal não disponível para Doc A.'}</pre><br/>"
        f"<b>Trecho Literal Documento B ({pol_b.nome_arquivo}):</b><br/>"
        f"<pre style='background:#F1F5F9; border:1px solid #CBD5E1; padding:10px; border-radius:4px; font-family:{TYPOGRAPHY.FONT_CODE}; font-size:12px; white-space:pre-wrap; color:{COLORS.TEXT_MAIN};'>"
        f"{details['snippet_b'] or 'Snippet literal não disponível para Doc B.'}</pre>"
    )

    return {
        "text": text,
        "citations": [{
            "clause_title": details["title"],
            "doc": "Evidência A/B",
            "page": details["page_b"],
            "section": details["section"],
            "snippet": details["snippet_b"] or details["snippet_a"]
        }],
        "has_evidence": True
    }


def format_report_summary(comp: ComparisonResult, report_md: Optional[str], pol_a: ApoliceDAO, pol_b: ApoliceDAO, profile) -> Dict[str, Any]:
    """Sintetiza a estrutura e conclusões do relatório executivo ativo."""
    if not comp:
        return {"text": EMPTY_CONTEXT_MESSAGE, "citations": []}

    score_pct = int(comp.score_similaridade * 100) if comp.score_similaridade <= 1.0 else int(comp.score_similaridade)
    score_aux = f"{score_pct}%"
    total_matches = len(comp.semantic_matches)
    total_diffs = len([m for m in comp.semantic_matches if m.relation in ("changed_scope", "different", "changed_condition", "changed_limit")])

    text = (
        f"<b>Estrutura e Síntese do Parecer Executivo D&O</b><br/><br/>"
        f"• <b>Documentos Analisados:</b> {pol_a.nome_arquivo} ⟷ {pol_b.nome_arquivo}<br/>"
        f"• <b>Total de Cláusulas no Confronto:</b> {total_matches}<br/>"
        f"• <b>Divergências Substantivas Identificadas:</b> {total_diffs}<br/>"
        f"• <b>Índice de Similaridade Estrutural (Auxiliar):</b> <code>{score_aux}</code><br/><br/>"
        f"<b>Seções do Relatório:</b><br/>"
        f"1. Cabeçalho Institucional e Metadados Regulatórios (SUSEP Ramo 0378)<br/>"
        f"2. Resumo Executivo Factual com Indicadores de Conformidade<br/>"
        f"3. Matriz de Alterações Substantivas Ordenada por Relevância<br/>"
        f"4. Confronto Integral de Cláusulas com Relações Semânticas<br/>"
        f"5. Cadeia de Custódia e Evidências Literais com Número de Página<br/>"
        f"6. Parecer Técnico com Notas Específicas por Perfil ({profile.label})<br/><br/>"
        f"💡 <i>Utilize os botões de exportação (Markdown / Impressão) na tela de Relatório para emissão formal.</i>"
    )
    return {"text": text, "citations": []}


def format_report_findings(comp: ComparisonResult, report_md: Optional[str], profile) -> Dict[str, Any]:
    """Exibe os principais achados factuais contidos no relatório executivo."""
    if not comp:
        return {"text": EMPTY_CONTEXT_MESSAGE, "citations": []}

    divergent = [m for m in comp.semantic_matches if m.relation in ("changed_scope", "different", "changed_condition", "changed_limit")]

    findings = [
        f"<b>Principais Achados Técnicos Consolidados no Relatório:</b><br/>"
    ]
    for idx, item in enumerate(divergent[:4], 1):
        details = _extract_match_details(item)
        findings.append(
            f"<b>{idx}. {details['title']}:</b> {details['summary']}"
        )

    findings.append(
        f"<br/><b>Nota de Governança ({profile.label}):</b> Todas as divergências foram rastreadas até as páginas originais dos arquivos PDF."
    )
    return {"text": "<br/><br/>".join(findings), "citations": []}


def format_library_summary(todas_apolices: List[ApoliceDAO], profile) -> Dict[str, Any]:
    """Resume as apólices disponíveis no acervo documental da biblioteca."""
    if not todas_apolices:
        return {
            "text": "Nenhum documento cadastrado na biblioteca. Utilize a tela 'Nova análise' para carregar arquivos PDF.",
            "citations": []
        }

    seguradoras = {}
    for pol in todas_apolices:
        seg = pol.seguradora or "Não Identificada"
        seguradoras[seg] = seguradoras.get(seg, 0) + 1

    lines = [
        f"<b>Acervo Documental da Biblioteca InsurMinds</b><br/>"
        f"• <b>Total de Documentos Ingeridos:</b> {len(todas_apolices)} apólices D&O (Ramo 0378)<br/>"
        f"• <b>Distribuição por Seguradora:</b>"
    ]
    for seg, count in seguradoras.items():
        lines.append(f"  - <b>{seg}:</b> {count} documento(s)")

    lines.append(
        f"<br/><b>Ação recomendada ({profile.label}):</b> Selecione dois documentos do mesmo emissor (ex: Sompo 2024 × 2025 ou Chubb 2024 × 2025) "
        f"para analisar a evolução temporal das condições contratuais."
    )
    return {"text": "<br/>".join(lines), "citations": []}


def format_library_comparisons(comparisons: List[Dict[str, Any]], profile) -> Dict[str, Any]:
    """Lista as comparações salvas e disponíveis no repositório."""
    if not comparisons:
        return {
            "text": "Não há comparações persistidas no banco. Inicie uma nova análise na tela de Comparações.",
            "citations": []
        }

    lines = [
        f"<b>Comparações Salvas no Repositório ({len(comparisons)} disponíveis):</b>"
    ]
    for idx, c in enumerate(comparisons[:5], 1):
        pa_name = c["pol_a"].nome_arquivo if c.get("pol_a") else c["apolice_a_id"][:12]
        raw_score = float(c.get('score_similaridade', 0.0))
        score_pct = f"{int(raw_score * 100)}%" if raw_score <= 1.0 else f"{int(raw_score)}%"
        lines.append(
            f"<b>{idx}. {pa_name} ⟷ {pb_name}</b><br/>"
            f"• Data: {c['data_comparacao'][:10] if c.get('data_comparacao') else 'Data recente'} · Similaridade Auxiliar: <code>{score_pct}</code>"
        )

    return {"text": "<br/><br/>".join(lines), "citations": []}


def format_workspace_guide(profile) -> Dict[str, Any]:
    """Guia de início e orientação operacional para as telas de Workspace e Nova Análise."""
    text = (
        f"<b>Guia Operacional InsurMinds · Perfil: {profile.label}</b><br/><br/>"
        f"Para iniciar uma análise comparativa rigorosa:<br/>"
        f"1. Acesse <b>'Nova análise'</b> no menu lateral para enviar duas apólices D&O (PDF) ou selecione documentos do acervo.<br/>"
        f"2. Utilize pares consolidados de benchmark como <b>Sompo 2024 × Sompo 2025</b> ou <b>Chubb 2024 × Chubb 2025</b>.<br/>"
        f"3. O sistema executará a ingestão, segmentação de cláusulas e confronto semântico auditável.<br/>"
        f"4. Na tela <b>'Comparações'</b>, você poderá auditar o que mudou, como mudou e onde está a evidência documental.<br/><br/>"
        f"🛡️ <i>Aviso: O Assistente Contextual acompanha cada etapa fornecendo leituras orientadas por evidência sem alterar dados ou regras contratuais.</i>"
    )
    return {"text": text, "citations": []}


# =============================================================================
# RENDERIZADOR PRINCIPAL DO ASSISTENTE CONTEXTUAL
# =============================================================================

def render_context_assistant(current_page: str) -> None:
    """Renderiza o drawer / painel retrátil contextual corporativo do Assistente Contextual."""
    ctx = get_assistant_context(current_page)
    screen_key = ctx["screen_key"]
    comp_result: Optional[ComparisonResult] = ctx["comp_result"]
    pol_a: Optional[ApoliceDAO] = ctx["pol_a"]
    pol_b: Optional[ApoliceDAO] = ctx["pol_b"]
    match_item: Optional[SemanticMatchItem] = ctx["match_item"]
    item_idx: Optional[int] = ctx["item_idx"]
    profile = ctx["profile"]

    # 1. CABEÇALHO DO PAINEL & BOTÃO DE FECHAMENTO
    col_hdr_text, col_close_btn = st.columns([5.2, 1.3])
    with col_hdr_text:
        render_html(f"""
            <div style="background:{COLORS.SURFACE}; border:1px solid #CBD5E1; border-top:4px solid {COLORS.PRIMARY_BLUE}; border-radius:{RADIUS.MD}; padding:14px 18px; margin-bottom:8px; box-shadow:{SHADOWS.SM};">
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                    <span style="font-size:18px;">🧠</span>
                    <h3 style="margin:0; font-size:17px; font-weight:700; color:{COLORS.PRIMARY_NAVY}; font-family:{TYPOGRAPHY.FONT_UI};">
                        ASSISTENTE CONTEXTUAL
                    </h3>
                    <span style="background:#EFF6FF; color:{COLORS.PRIMARY_BLUE}; font-size:11px; font-weight:700; padding:2px 8px; border-radius:4px;">
                        COPILOTO DE LEITURA
                    </span>
                </div>
                <p style="margin:0; font-size:13px; color:{COLORS.TEXT_MUTED}; font-family:{TYPOGRAPHY.FONT_UI};">
                    Ajuda para interpretar a análise atualmente aberta. O assistente explica o contexto disponível; o documento continua sendo a fonte.
                </p>
            </div>
        """)
    with col_close_btn:
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        if st.button("✕ Fechar Assistente", key="assistant_close_btn", help="Fechar o painel contextual"):
            st.session_state["context_assistant_open"] = False
            st.rerun()

    # 2. BARRA DE CONTEXTO ATIVO (Documento A × B, Tela, Item, Perfil)
    doc_pair_str = (
        f"{pol_a.nome_arquivo} ⟷ {pol_b.nome_arquivo}"
        if pol_a and pol_b
        else "Nenhum documento em confronto direto"
    )

    screen_desc_map = {
        "comparacao": "Comparação Estruturada",
        "detalhe": f"Detalhe da Diferença (Cláusula #{item_idx + 1 if item_idx is not None else 1})",
        "relatorio": "Relatório Executivo",
        "biblioteca": "Biblioteca Documental",
        "workspace": "Espaço de Trabalho / Início",
        "configuracoes": "Configurações & Infraestrutura"
    }
    screen_label = screen_desc_map.get(screen_key, current_page)

    item_pill = ""
    if screen_key == "detalhe" and match_item:
        match_title = _extract_match_details(match_item)["title"]
        item_pill = f"<span style='background:#F1F5F9; border:1px solid #CBD5E1; color:{COLORS.PRIMARY_NAVY}; padding:3px 8px; border-radius:4px; font-size:11px;'>Cláusula: <b>{match_title}</b></span>"

    render_html(f"""
        <div style="display:flex; flex-wrap:wrap; gap:8px; align-items:center; background:#F8FAFC; border:1px solid #E2E8F0; padding:8px 14px; border-radius:6px; margin:10px 0 16px 0; font-size:12px; color:{COLORS.TEXT_MAIN};">
            <span>📍 <b>Tela:</b> {screen_label}</span>
            <span style="color:#CBD5E1;">|</span>
            <span>📑 <b>Contexto Documental:</b> {doc_pair_str}</span>
            <span style="color:#CBD5E1;">|</span>
            <span>👤 <b>Perfil:</b> {profile.icon} {profile.label}</span>
            {item_pill}
        </div>
    """)

    # 3. VERIFICAÇÃO DE ESTADO VAZIO OU ERRO
    if screen_key in ("comparacao", "detalhe", "relatorio") and not comp_result:
        render_html(f"""
            <div style="background:#FFFBEB; border:1px solid #FCD34D; border-radius:6px; padding:12px 16px; font-size:13px; color:#92400E; margin-bottom:14px;">
                ⚠️ <b>Contexto Indisponível:</b> {EMPTY_CONTEXT_MESSAGE}
            </div>
        """)
        col_act1, col_act2 = st.columns([1.5, 3])
        with col_act1:
            if st.button("⚖️ Ir para Comparações ➔", key="asst_nav_comp"):
                navigate_to("Comparações")
        return

    # 4. BOTÕES DE AÇÃO SUGERIDA (PRIMEIRAS AÇÕES POR TELA)
    st.markdown("<div style='font-size:12px; font-weight:700; color:#475569; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px;'>AÇÕES DE LEITURA RECOMENDADAS:</div>", unsafe_allow_html=True)

    # Inicialização da ação selecionada
    if "assistant_action_selected" not in st.session_state:
        # Default action de acordo com a tela
        default_map = {
            "comparacao": "resumo_diferencas",
            "detalhe": "explicar_diferenca",
            "relatorio": "resumo_relatorio",
            "biblioteca": "resumo_biblioteca",
            "workspace": "guia_inicio"
        }
        st.session_state["assistant_action_selected"] = default_map.get(screen_key, "resumo_diferencas")

    active_action = st.session_state.get("assistant_action_selected")

    # Renderização de botões conforme a tela
    if screen_key == "comparacao":
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("📌 Resumir as principais diferenças", key="act_cmp_resumo", use_container_width=True):
                st.session_state["assistant_action_selected"] = "resumo_diferencas"
                st.rerun()
        with c2:
            if st.button("🔍 Explicar alterações de escopo", key="act_cmp_escopo", use_container_width=True):
                st.session_state["assistant_action_selected"] = "alteracoes_escopo"
                st.rerun()
        with c3:
            if st.button("⚖️ Mostrar itens para revisão profissional", key="act_cmp_revisao", use_container_width=True):
                st.session_state["assistant_action_selected"] = "itens_revisao"
                st.rerun()

    elif screen_key == "detalhe":
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("📖 Explicar esta diferença", key="act_dtl_explicar", use_container_width=True):
                st.session_state["assistant_action_selected"] = "explicar_diferenca"
                st.rerun()
        with c2:
            if st.button("🔄 Resumir a alteração A → B", key="act_dtl_resumir_ab", use_container_width=True):
                st.session_state["assistant_action_selected"] = "resumir_ab"
                st.rerun()
        with c3:
            if st.button("🔎 Mostrar a evidência relacionada", key="act_dtl_evidencia", use_container_width=True):
                st.session_state["assistant_action_selected"] = "mostrar_evidencia"
                st.rerun()

    elif screen_key == "relatorio":
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("📑 Resumir o relatório", key="act_rep_resumo", use_container_width=True):
                st.session_state["assistant_action_selected"] = "resumo_relatorio"
                st.rerun()
        with c2:
            if st.button("💡 Explicar os principais achados", key="act_rep_achados", use_container_width=True):
                st.session_state["assistant_action_selected"] = "principais_achados"
                st.rerun()
        with c3:
            if st.button("📋 Listar pontos para revisão", key="act_rep_revisao", use_container_width=True):
                st.session_state["assistant_action_selected"] = "pontos_revisao_relatorio"
                st.rerun()

    elif screen_key == "biblioteca":
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📚 Resumir apólices disponíveis", key="act_lib_resumo", use_container_width=True):
                st.session_state["assistant_action_selected"] = "resumo_biblioteca"
                st.rerun()
        with c2:
            if st.button("⚖️ Mostrar comparações disponíveis", key="act_lib_comps", use_container_width=True):
                st.session_state["assistant_action_selected"] = "comparacoes_disponiveis"
                st.rerun()

    else:  # workspace ou configuracoes
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🚀 Como iniciar uma análise D&O?", key="act_wsp_guia", use_container_width=True):
                st.session_state["assistant_action_selected"] = "guia_inicio"
                st.rerun()
        with c2:
            if st.button("📑 Ver pares de teste recomendados", key="act_wsp_pares", use_container_width=True):
                st.session_state["assistant_action_selected"] = "pares_teste"
                st.rerun()

    # 5. ÁREA DE RESPOSTA FACTUAL BASEADA NO CONTEXTO
    response_data: Dict[str, Any] = {"text": "", "citations": []}

    if active_action == "resumo_diferencas":
        if comp_result and pol_a and pol_b:
            response_data = format_difference_summary(comp_result, pol_a, pol_b, profile)
    elif active_action == "alteracoes_escopo":
        if comp_result and pol_a and pol_b:
            response_data = format_scope_changes(comp_result, pol_a, pol_b, profile)
    elif active_action == "itens_revisao":
        if comp_result and pol_a and pol_b:
            response_data = format_review_items(comp_result, pol_a, pol_b, profile)
    elif active_action == "explicar_diferenca":
        if match_item and pol_a and pol_b:
            response_data = format_clause_explanation(match_item, pol_a, pol_b, profile)
        elif comp_result and pol_a and pol_b and comp_result.semantic_matches:
            response_data = format_clause_explanation(comp_result.semantic_matches[0], pol_a, pol_b, profile)
    elif active_action == "resumir_ab":
        if match_item and pol_a and pol_b:
            response_data = format_clause_diff_ab(match_item, pol_a, pol_b, profile)
        elif comp_result and pol_a and pol_b and comp_result.semantic_matches:
            response_data = format_clause_diff_ab(comp_result.semantic_matches[0], pol_a, pol_b, profile)
    elif active_action == "mostrar_evidencia":
        if match_item and pol_a and pol_b:
            response_data = format_clause_evidence(match_item, pol_a, pol_b)
        elif comp_result and pol_a and pol_b and comp_result.semantic_matches:
            response_data = format_clause_evidence(comp_result.semantic_matches[0], pol_a, pol_b)
        else:
            response_data = {"text": f"<b>{NO_EVIDENCE_AVAILABLE_MESSAGE}</b>", "citations": []}
    elif active_action == "resumo_relatorio":
        if comp_result and pol_a and pol_b:
            response_data = format_report_summary(comp_result, ctx["report_md"], pol_a, pol_b, profile)
    elif active_action == "principais_achados":
        if comp_result:
            response_data = format_report_findings(comp_result, ctx["report_md"], profile)
    elif active_action == "pontos_revisao_relatorio":
        if comp_result and pol_a and pol_b:
            response_data = format_review_items(comp_result, pol_a, pol_b, profile)
    elif active_action == "resumo_biblioteca":
        todas_apolices = db.list_apolices()
        response_data = format_library_summary(todas_apolices, profile)
    elif active_action == "comparacoes_disponiveis":
        from ui.page_library import _get_saved_comparisons
        todas_apolices = db.list_apolices()
        ap_map = {p.id: p for p in todas_apolices}
        comps = _get_saved_comparisons(ap_map)
        response_data = format_library_comparisons(comps, profile)
    elif active_action == "pares_teste":
        response_data = {
            "text": (
                "<b>Pares de Teste Homologados D&O (Repositório Local):</b><br/><br/>"
                "• <b>Sompo 2024 × Sompo 2025:</b> Comparação temporal de condições gerais de D&O (DO_010 × DO_012).<br/>"
                "• <b>Chubb 2024 × Chubb 2025:</b> Comparação de evolução contratual com apólice emitida (DO_005 × DO_014).<br/>"
                "• <b>Allianz × Chubb:</b> Confronto cruzado entre seguradoras líderes de mercado D&O.<br/><br/>"
                "💡 <i>Acesse a tela 'Documentos' ou 'Comparações' para carregar qualquer um desses pares instantaneamente.</i>"
            ),
            "citations": []
        }
    else:  # guia_inicio
        response_data = format_workspace_guide(profile)

    # Renderização da Caixa de Resposta
    render_html(f"""
        <div style="background:#FFFFFF; border:1px solid #D9E1E8; border-radius:6px; padding:16px 18px; margin-top:14px; font-size:13px; line-height:1.6; color:{COLORS.TEXT_MAIN};">
            <div style="font-size:11px; font-weight:700; color:{COLORS.PRIMARY_BLUE}; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:8px;">
                LEITURA CONTEXTUAL ASSISTIDA
            </div>
            {response_data.get('text', '')}
        </div>
    """)

    # 6. EVIDÊNCIAS E NAVEGAÇÃO INTEGRADA (SE HOUVER DIFERENÇA OU CLÁUSULA)
    col_nav1, col_nav2, col_nav3 = st.columns([1.5, 1.5, 2])

    with col_nav1:
        if screen_key == "detalhe":
            if st.button("⚖️ Voltar à Comparação", key="asst_back_to_cmp"):
                st.session_state["viewing_diff_idx"] = None
                st.rerun()
        elif screen_key == "comparacao" and comp_result and comp_result.semantic_matches:
            if st.button("🔍 Auditar Cláusula #1 ➔", key="asst_go_to_diff1"):
                st.session_state["viewing_diff_idx"] = 0
                st.rerun()

    with col_nav2:
        if screen_key != "relatorio" and comp_result:
            if st.button("📄 Abrir Relatório Executivo ➔", key="asst_go_to_rep"):
                navigate_to("Relatórios")

    # 7. GOVERNANÇA DE IA DISCRETA
    render_html(f"""
        <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:8px 12px; font-size:11px; color:#475569; margin-top:14px; line-height:1.4;">
            <span style="font-weight:700; color:{COLORS.PRIMARY_NAVY};">🛡️ Assistência por IA:</span>
            {AI_ASSISTANT_GOVERNANCE_NOTICE}
        </div>
    """)
