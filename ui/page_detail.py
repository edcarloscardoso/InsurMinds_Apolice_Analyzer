"""Página de Detalhe da Diferença — Insurance Intelligence v1.0.
Signature Screen de Auditoria Contratual: "Como mudou? → Onde está a prova?".
Permite ao analista, subscritor, corretor ou advogado auditar minuciosamente cada alteração
ou correspondência entre o Documento A e o Documento B com proveniência literal.
"""
from typing import Optional, List, Dict, Any
import streamlit as st

from core.schemas import ApoliceDAO, ComparisonResult, SemanticMatchItem, FieldDiff, EvidenceItem
from ui.tokens import COLORS, TYPOGRAPHY, RADIUS, SHADOWS
from ui.styles import render_html
from ui.components.badges import (
    SEMANTIC_RELATION_CONFIG,
    render_semantic_badge
)
from ui.components.evidence import render_evidence_panel, render_evidence_snippet_html
from ui.components.states import render_empty_state, render_error_state, render_alert


def _get_item_category(title: str) -> str:
    """Classifica a categoria documental a partir do título da cláusula."""
    t_lower = title.lower()
    if any(k in t_lower for k in ["exclus", "polui", "dolo", "fraude", "sanco"]):
        return "EXCLUSÕES CONTRATUAIS"
    elif any(k in t_lower for k in ["prêmio", "vigência", "franquia", "cancelamento", "inadimplemento"]):
        return "CONDIÇÕES GERAIS E OPERACIONAIS"
    elif any(k in t_lower for k in ["limite", "lmg", "sublimite", "franquia"]):
        return "PARÂMETROS FINANCEIROS"
    return "COBERTURAS & GARANTIAS D&O"


def _get_profile_review_note(profile_id: str, relation: str) -> str:
    """Retorna microcopy neutro e orientativo de ponto para revisão profissional por perfil."""
    is_divergent = relation in ("different", "changed_condition", "changed_scope", "changed_limit")

    notes = {
        "analista": (
            "Recomenda-se confrontar os prazos, condições precedentes e eventuais restrições procedimentais "
            "entre as redações contratuais antes da emissão da nota técnica."
            if is_divergent else
            "Cláusulas estruturalmente equivalentes. Recomenda-se confirmar a manutenção das referências normativas."
        ),
        "subscritor": (
            "Recomenda-se avaliar o impacto técnico da alteração sobre a gradação do risco, limites agregados "
            "e condições de acionamento da garantia."
            if is_divergent else
            "Redações equivalentes com parâmetros técnicos simétricos entre as minutas."
        ),
        "corretor": (
            "Recomenda-se esclarecer ao segurado eventuais exigências procedimentais ou obrigações adicionais "
            "estabelecidas na redação do documento mais recente."
            if is_divergent else
            "Garantias equivalentes em termos de proteção ao patrimônio dos administradores segurados."
        ),
        "juridico": (
            "Recomenda-se validar a conformidade da redação com a Circular SUSEP aplicável, bem como "
            "a clareza das hipóteses de perda de direitos e foro estipulado."
            if is_divergent else
            "Equivalência material verificada. Recomenda-se validação da cadeia de custódia documental."
        ),
        "visitante": (
            "Alteração identificada pelo motor analítico. A validação definitiva requer análise técnica "
            "por profissional devidamente habilitado."
            if is_divergent else
            "Correspondência semântica identificada entre os documentos comparados."
        )
    }
    return notes.get(profile_id, notes["visitante"])


def render_detail_page(
    comp: ComparisonResult,
    pol_a: ApoliceDAO,
    pol_b: ApoliceDAO,
    active_profile,
    item_idx: int = 0
) -> None:
    """Renderiza a experiência completa de Detalhe da Diferença orientada por evidência."""

    # 10. ESTADO: Comparação Ausente
    if not comp or not pol_a or not pol_b:
        render_empty_state(
            title="Comparação não disponível",
            description="Não foi encontrada uma comparação ativa para exibir o detalhamento da diferença.",
            action_label="Voltar ao Início",
            action_callback=lambda: st.session_state.update({"nav_page": "Início", "viewing_diff_idx": None})
        )
        return

    items_list = comp.semantic_matches
    total_items = len(items_list)

    # 10. ESTADO: Navegação Inválida / Detalhe não encontrado
    if total_items == 0:
        render_empty_state(
            title="Nenhuma correspondência disponível",
            description="Não há itens comparativos registrados para este par de documentos.",
            action_label="⬅ Voltar à Comparação",
            action_callback=lambda: st.session_state.update({"viewing_diff_idx": None})
        )
        return

    # Garante que o índice esteja dentro dos limites
    if item_idx < 0 or item_idx >= total_items:
        render_error_state(
            title="Item comparativo não encontrado",
            error_message=f"O índice solicitado ({item_idx}) não existe na lista de correspondências (total: {total_items})."
        )
        if st.button("⬅ Retornar à Comparação Principal", key="btn_err_back_compare"):
            st.session_state["viewing_diff_idx"] = None
            st.rerun()
        return

    match: SemanticMatchItem = items_list[item_idx]

    # Extrai metadados do item
    title_a = match.item_a.split(":")[0].strip()
    title_b = match.item_b.split(":")[0].strip()
    display_title = title_a if title_a == title_b else f"{title_a} ⟷ {title_b}"
    category = _get_item_category(display_title)

    ev_a_obj = pol_a.evidencias.get(title_a) if pol_a.evidencias else None
    ev_b_obj = pol_b.evidencias.get(title_b) if pol_b.evidencias else None

    page_a = match.page_a or (ev_a_obj.page if ev_a_obj else None)
    page_b = match.page_b or (ev_b_obj.page if ev_b_obj else None)
    page_a_str = f"Pág. {page_a}" if page_a else "Pág. não indicada"
    page_b_str = f"Pág. {page_b}" if page_b else "Pág. não indicada"

    snippet_a = match.evidence_a or (ev_a_obj.snippet if ev_a_obj else None) or match.item_a
    snippet_b = match.evidence_b or (ev_b_obj.snippet if ev_b_obj else None) or match.item_b

    badge_html = render_semantic_badge(match.relation)
    relation_cfg = SEMANTIC_RELATION_CONFIG.get(match.relation, {})
    conf_pct = int(match.confidence * 100)

    # =========================================================================
    # 8. BARRA DE NAVEGAÇÃO SUPERIOR (Voltar + Anterior / Próximo)
    # =========================================================================
    col_nav_back, col_nav_counter, col_nav_arrows = st.columns([2.5, 2, 2.5])

    with col_nav_back:
        if st.button("⬅ Voltar à Comparação", key="btn_back_to_compare", help="Retorna à visualização geral da comparação"):
            st.session_state["viewing_diff_idx"] = None
            st.rerun()

    with col_nav_counter:
        render_html(f"""
            <div style="text-align:center; font-size:12.5px; color:{COLORS.TEXT_MUTED}; font-weight:600; padding-top:6px;">
                Diferença <b>{item_idx + 1}</b> de <b>{total_items}</b>
            </div>
        """)

    with col_nav_arrows:
        col_prev, col_next = st.columns(2)
        with col_prev:
            if st.button("⬅ Anterior", key="btn_prev_diff", disabled=(item_idx == 0)):
                st.session_state["viewing_diff_idx"] = item_idx - 1
                st.rerun()
        with col_next:
            if st.button("Próximo ➔", key="btn_next_diff", disabled=(item_idx >= total_items - 1)):
                st.session_state["viewing_diff_idx"] = item_idx + 1
                st.rerun()

    render_html(f"<hr style='border:none; border-top:1px solid {COLORS.BORDER}; margin:12px 0 20px 0;'/>")

    # =========================================================================
    # 1. CABEÇALHO DA DIFERENÇA
    # =========================================================================
    render_html(f"""
        <div style="margin-bottom: 20px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; flex-wrap:wrap; gap:8px;">
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="font-size:11px; font-weight:700; text-transform:uppercase; color:{COLORS.PRIMARY_BLUE}; letter-spacing:0.5px; background:#EFF6FF; border:1px solid #BFDBFE; padding:3px 8px; border-radius:{RADIUS.SM};">
                        {category}
                    </span>
                    <span style="color:#D1D5DB;">·</span>
                    {badge_html}
                </div>
                <div style="font-size:12px; color:{COLORS.TEXT_MUTED};">
                    Confiança analítica do motor: <b style="color:{COLORS.PRIMARY_NAVY};">{conf_pct}%</b>
                </div>
            </div>

            <h2 style="color:{COLORS.PRIMARY_NAVY}; font-size:22px; font-weight:700; margin:0 0 8px 0; font-family:{TYPOGRAPHY.FONT_UI};">
                {display_title}
            </h2>

            <div style="display:flex; gap:16px; font-size:12.5px; color:{COLORS.TEXT_MUTED}; flex-wrap:wrap;">
                <span><b>Doc A:</b> {pol_a.seguradora or 'Referência'} ({page_a_str})</span>
                <span>·</span>
                <span><b>Doc B:</b> {pol_b.seguradora or 'Comparação'} ({page_b_str})</span>
            </div>
        </div>
    """)

    # =========================================================================
    # 2. RESUMO DA ALTERAÇÃO ("O que mudou?")
    # =========================================================================
    render_html(f"""
        <div style="background:{COLORS.SURFACE}; border:1px solid {COLORS.BORDER}; border-left:4px solid {COLORS.PRIMARY_BLUE}; border-radius:{RADIUS.MD}; padding:16px 20px; margin-bottom:20px; box-shadow:{SHADOWS.SM};">
            <div style="font-size:11px; font-weight:700; text-transform:uppercase; color:{COLORS.PRIMARY_BLUE}; letter-spacing:0.5px; margin-bottom:6px;">
                O QUE MUDOU?
            </div>
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px; font-size:13px; font-weight:600; color:{COLORS.PRIMARY_NAVY}; flex-wrap:wrap;">
                <span>Documento A ({pol_a.seguradora or 'Referência'})</span>
                <span style="color:{COLORS.PRIMARY_BLUE};">➔</span>
                <span>Documento B ({pol_b.seguradora or 'Comparação'})</span>
                <span>·</span>
                {badge_html}
            </div>
            <div style="font-size:13px; color:{COLORS.TEXT_MAIN}; line-height:1.5;">
                {match.explanation or 'Correspondência identificada entre as cláusulas sem divergências substantivas informadas.'}
            </div>
        </div>
    """)

    # =========================================================================
    # 3. INTERPRETAÇÃO ASSISTIDA
    # =========================================================================
    render_html(f"""
        <div style="background:#F8FAFC; border:1px solid {COLORS.BORDER}; border-radius:{RADIUS.MD}; padding:16px 20px; margin-bottom:24px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <div style="font-size:11px; font-weight:700; text-transform:uppercase; color:{COLORS.TEXT_MUTED}; letter-spacing:0.5px;">
                    🤖 INTERPRETAÇÃO ASSISTIDA
                </div>
                <div style="font-size:11px; color:#6B7280; font-style:italic;">
                    Fonte: Texto Contratual Original · Interpretação assistida por IA
                </div>
            </div>
            <div style="font-size:13px; color:{COLORS.TEXT_MAIN}; line-height:1.6; margin-bottom:10px;">
                {match.explanation}
            </div>
            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:4px; padding:8px 12px; font-size:11.5px; color:{COLORS.TEXT_MUTED}; line-height:1.4;">
                ℹ️ <b>Ressalva de Governança:</b> O texto contratual original é a fonte primária e irredutível da obrigação.
                A síntese acima é assistida pelo modelo e <b>deve ser obrigatoriamente revisada pelo profissional habilitado</b> (subscritor, corretor ou advogado).
            </div>
        </div>
    """)

    # =========================================================================
    # 4. CONFRONTO A/B (Lado a Lado em IBM Plex Mono)
    # =========================================================================
    render_html(f"""
        <div style="margin-bottom: 24px;">
            <div style="font-size:14px; font-weight:700; color:{COLORS.PRIMARY_NAVY}; margin-bottom:12px;">
                ⚖️ Confronto Contratual A ⟷ B (Trechos Originais Intactos)
            </div>
        </div>
    """)

    col_doc_a, col_doc_b = st.columns(2)

    with col_doc_a:
        render_html(f"""
            <div style="background:{COLORS.SURFACE}; border:1px solid {COLORS.BORDER}; border-top:3px solid {COLORS.PRIMARY_BLUE}; border-radius:{RADIUS.MD}; padding:16px; height:100%; box-shadow:{SHADOWS.SM};">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <div>
                        <span style="font-weight:700; color:{COLORS.PRIMARY_BLUE}; font-size:11px; text-transform:uppercase;">
                            DOCUMENTO A
                        </span>
                        <div style="font-weight:700; color:{COLORS.PRIMARY_NAVY}; font-size:13.5px;">
                            {pol_a.seguradora or 'Referência'}
                        </div>
                    </div>
                    <span class="im-page-tag">{page_a_str}</span>
                </div>
                <div style="font-size:11.5px; color:{COLORS.TEXT_MUTED}; margin-bottom:8px;">
                    <b>Cláusula identificada:</b> {title_a}
                </div>
                <div style="font-family:{TYPOGRAPHY.FONT_CODE}; font-size:12px; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:4px; padding:12px; color:{COLORS.TEXT_MAIN}; line-height:1.5; white-space:pre-wrap; max-height:360px; overflow-y:auto;">
{snippet_a}
                </div>
                <div style="margin-top:10px; font-size:11px; color:{COLORS.TEXT_MUTED}; display:flex; justify-content:space-between;">
                    <span>Origem: {pol_a.nome_arquivo}</span>
                    <span>Método: {match.method_a or 'pdf_text'}</span>
                </div>
            </div>
        """)

    with col_doc_b:
        render_html(f"""
            <div style="background:{COLORS.SURFACE}; border:1px solid {COLORS.BORDER}; border-top:3px solid {COLORS.SECONDARY_TEAL}; border-radius:{RADIUS.MD}; padding:16px; height:100%; box-shadow:{SHADOWS.SM};">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <div>
                        <span style="font-weight:700; color:{COLORS.SECONDARY_TEAL}; font-size:11px; text-transform:uppercase;">
                            DOCUMENTO B
                        </span>
                        <div style="font-weight:700; color:{COLORS.PRIMARY_NAVY}; font-size:13.5px;">
                            {pol_b.seguradora or 'Comparação'}
                        </div>
                    </div>
                    <span class="im-page-tag">{page_b_str}</span>
                </div>
                <div style="font-size:11.5px; color:{COLORS.TEXT_MUTED}; margin-bottom:8px;">
                    <b>Cláusula identificada:</b> {title_b}
                </div>
                <div style="font-family:{TYPOGRAPHY.FONT_CODE}; font-size:12px; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:4px; padding:12px; color:{COLORS.TEXT_MAIN}; line-height:1.5; white-space:pre-wrap; max-height:360px; overflow-y:auto;">
{snippet_b}
                </div>
                <div style="margin-top:10px; font-size:11px; color:{COLORS.TEXT_MUTED}; display:flex; justify-content:space-between;">
                    <span>Origem: {pol_b.nome_arquivo}</span>
                    <span>Método: {match.method_b or 'pdf_text'}</span>
                </div>
            </div>
        """)

    render_html(f"<div style='margin-top:24px;'></div>")

    # =========================================================================
    # 5. EVIDÊNCIA CONTRATUAL AUDITÁVEL (EvidencePanel Integrado)
    # =========================================================================
    render_html(f"""
        <div style="margin-bottom: 12px;">
            <div style="font-size:14px; font-weight:700; color:{COLORS.PRIMARY_NAVY}; margin-bottom:4px;">
                🔍 Evidência Contratual Auditável & Cadeia de Custódia
            </div>
            <div style="font-size:12px; color:{COLORS.TEXT_MUTED};">
                Comprovação física dos trechos extraídos com rastreabilidade de página e hash documental:
            </div>
        </div>
    """)

    render_evidence_panel(
        item_title=display_title,
        evidence_a=ev_a_obj,
        evidence_b=ev_b_obj,
        doc_a_name=pol_a.seguradora or "Documento A",
        doc_b_name=pol_b.seguradora or "Documento B",
        raw_text_a=snippet_a,
        raw_text_b=snippet_b,
        page_a=page_a,
        page_b=page_b
    )

    # 10. ESTADO: Tratamento explícito quando faltar evidência
    has_evidence_a = bool(snippet_a and snippet_a != "Evidência documental não disponível para este item.")
    has_evidence_b = bool(snippet_b and snippet_b != "Evidência documental não disponível para este item.")
    if not has_evidence_a or not has_evidence_b:
        render_alert(
            message="Evidência documental não disponível para este item em um dos documentos. O trecho não pôde ser localizado nas páginas extraídas.",
            level="warning"
        )

    # =========================================================================
    # 6. RELAÇÃO SEMÂNTICA & 7. PONTO PARA REVISÃO PROFISSIONAL
    # =========================================================================
    review_note = _get_profile_review_note(active_profile.id, match.relation)
    relation_desc = relation_cfg.get("desc", "Relação contratual analisada pelo motor semântico.")

    render_html(f"""
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px; margin:24px 0 28px 0;">
            <div style="background:{COLORS.SURFACE}; border:1px solid {COLORS.BORDER}; border-radius:{RADIUS.MD}; padding:16px; box-shadow:{SHADOWS.SM};">
                <div style="font-size:11px; font-weight:700; text-transform:uppercase; color:{COLORS.TEXT_MUTED}; letter-spacing:0.5px; margin-bottom:6px;">
                    CLASSIFICAÇÃO SEMÂNTICA CANÔNICA
                </div>
                <div style="margin-bottom:8px;">
                    {badge_html}
                </div>
                <div style="font-size:12.5px; color:{COLORS.TEXT_MAIN}; line-height:1.4;">
                    {relation_desc}
                </div>
            </div>

            <div style="background:{COLORS.SURFACE}; border:1px solid {COLORS.BORDER}; border-left:4px solid {COLORS.ATTENTION}; border-radius:{RADIUS.MD}; padding:16px; box-shadow:{SHADOWS.SM};">
                <div style="font-size:11px; font-weight:700; text-transform:uppercase; color:{COLORS.ATTENTION}; letter-spacing:0.5px; margin-bottom:6px;">
                    PONTO PARA REVISÃO PROFISSIONAL ({active_profile.label.upper()})
                </div>
                <div style="font-size:12.5px; color:{COLORS.TEXT_MAIN}; line-height:1.5;">
                    {review_note}
                </div>
                <div style="margin-top:8px; font-size:11px; color:{COLORS.TEXT_MUTED};">
                    <i>A interface indica que a alteração merece análise humana, sem determinar o resultado decisório.</i>
                </div>
            </div>
        </div>
    """)

    # =========================================================================
    # 8. RODAPÉ DE NAVEGAÇÃO
    # =========================================================================
    col_bot_back, col_bot_space, col_bot_next = st.columns([2.5, 3, 2.5])
    with col_bot_back:
        if st.button("⬅ Voltar à Comparação Geral", key="btn_bot_back_compare"):
            st.session_state["viewing_diff_idx"] = None
            st.rerun()

    with col_bot_next:
        if item_idx < total_items - 1:
            if st.button("Próxima Diferença ➔", key="btn_bot_next_diff"):
                st.session_state["viewing_diff_idx"] = item_idx + 1
                st.rerun()
        else:
            st.caption("Você está no último item comparativo.")
