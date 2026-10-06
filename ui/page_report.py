"""Página de Relatório de Análise Contratual D&O — Insurance Intelligence v1.0.
Síntese Profissional e Rastreável: "Como apresento os resultados desta análise de forma clara, objetiva e rastreável?".
Estrutura corporativa com cabeçalho editorial, resumo executivo factual, principais alterações,
confronto resumido, evidências auditáveis, interpretação assistida com avisos de governança e exportação.
"""
from typing import Optional, List, Dict, Any, Tuple
import streamlit as st
import pandas as pd

from core.database import db
from core.schemas import ApoliceDAO, ComparisonResult, SemanticMatchItem, FieldDiff, EvidenceItem
from ui.navigation import navigate_to
from ui.persona.profiles import get_active_profile
from ui.tokens import COLORS, TYPOGRAPHY, RADIUS, SHADOWS
from ui.styles import render_html
from ui.components.badges import (
    SEMANTIC_RELATION_CONFIG,
    render_semantic_badge
)
from ui.components.cards import render_metric_card
from ui.components.evidence import render_evidence_panel
from ui.components.states import render_empty_state, render_alert, render_error_state
from ui.page_detail import _get_item_category, _get_profile_review_note

# Aviso Legal Obrigatório (Preservado para conformidade com Requisito 10 e suíte de testes)
MANDATORY_DISCLAIMER = "A análise é assistida por IA e não substitui a avaliação jurídica, técnica ou de subscrição."


def _get_active_or_latest_analysis() -> Tuple[Optional[ComparisonResult], Optional[str], Optional[ApoliceDAO], Optional[ApoliceDAO]]:
    """Recupera a análise ativa na sessão ou a comparação mais recente persistida no banco SQLite."""
    comp_result: Optional[ComparisonResult] = st.session_state.get("active_comparison_result", None)
    report_md: Optional[str] = st.session_state.get("active_executive_report", None)
    selected_pols: List[ApoliceDAO] = st.session_state.get("selected_for_compare", [])

    pol_a: Optional[ApoliceDAO] = selected_pols[0] if len(selected_pols) > 0 else None
    pol_b: Optional[ApoliceDAO] = selected_pols[1] if len(selected_pols) > 1 else None

    # Se já houver comp_result e pol_a e pol_b completos na sessão, retorna diretamente
    if comp_result and pol_a and pol_b:
        return comp_result, report_md, pol_a, pol_b

    # Caso contrário, recupera a comparação mais recente persistida no banco relacional
    try:
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT apolice_a_id, apolice_b_id, score_similaridade, data_comparacao, resultado_json, relatorio_markdown
                FROM comparacoes
                ORDER BY created_at DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                comp_loaded = ComparisonResult.model_validate_json(row["resultado_json"])
                md_loaded = row["relatorio_markdown"] or ""
                pa_loaded = db.get_apolice_by_id(row["apolice_a_id"])
                pb_loaded = db.get_apolice_by_id(row["apolice_b_id"])
                return comp_loaded, md_loaded, pa_loaded, pb_loaded
    except Exception:
        pass

    return None, None, None, None


def _format_doc_type(doc_type: Optional[str]) -> str:
    """Normaliza o tipo documental para nomenclatura técnica padrão."""
    mapping = {
        "condicoes_gerais": "Condições Gerais",
        "apolice_individual": "Apólice Individual",
        "endosso": "Endosso",
        "proposta": "Proposta de Seguro",
        "unknown": "Não especificado"
    }
    return mapping.get(str(doc_type).lower(), "Condições Gerais")


def render_report_page() -> None:
    """Renderiza a experiência completa do Relatório Profissional e Rastreável."""

    # 1. CABEÇALHO EDITORIAL
    render_html(f"""
        <div style="margin-bottom: 16px;">
            <h2 style="color:{COLORS.PRIMARY_NAVY}; font-size:24px; font-weight:700; margin:0 0 6px 0; font-family:{TYPOGRAPHY.FONT_UI};">
                RELATÓRIO
            </h2>
            <p style="color:{COLORS.TEXT_MUTED}; font-size:14px; margin:0; font-family:{TYPOGRAPHY.FONT_UI}; line-height:1.5;">
                Sintetize os resultados da comparação preservando a rastreabilidade documental.
            </p>
        </div>
    """)

    # Aviso Legal Obrigatório
    render_html(f"""
        <div class="disclaimer-banner">
            🛡️ <strong>Aviso Legal Obrigatório:</strong> {MANDATORY_DISCLAIMER}
        </div>
    """)

    comp, report_md, pol_a, pol_b = _get_active_or_latest_analysis()

    # 15. ESTADO: Nenhuma análise selecionada / Comparação inexistente
    if not comp or not pol_a or not pol_b:
        render_empty_state(
            title="Nenhum relatório comparativo disponível",
            description="Selecione duas apólices na Biblioteca ou execute uma análise na tela de Comparação para gerar a síntese executiva.",
            action_label="Ir para a Biblioteca de Documentos ➔",
            action_callback=lambda: navigate_to("Documentos")
        )
        return

    active_profile = get_active_profile()

    # Metadados de identificação
    seg_a = pol_a.seguradora or "Documento A"
    seg_b = pol_b.seguradora or "Documento B"
    tipo_a = _format_doc_type(pol_a.document_type)
    tipo_b = _format_doc_type(pol_b.document_type)
    susep_a = pol_a.processo_susep or "Não informado"
    susep_b = pol_b.processo_susep or "Não informado"
    dt_analise = comp.data_comparacao[:10] if comp.data_comparacao else "Data não indicada"

    # =========================================================================
    # 16. BARRA DE NAVEGAÇÃO DE TOPO
    # =========================================================================
    col_nav1, col_nav2, col_nav3 = st.columns([2.5, 2.5, 2.5])
    with col_nav1:
        if st.button("⬅ Retornar à Comparação", key="rep_top_back_comp", help="Voltar para a matriz comparativa completa"):
            st.session_state["selected_for_compare"] = [pol_a, pol_b]
            st.session_state["viewing_diff_idx"] = None
            navigate_to("Comparações")
            st.rerun()
    with col_nav2:
        if st.button("📚 Consultar Biblioteca", key="rep_top_go_lib"):
            navigate_to("Documentos")
            st.rerun()
    with col_nav3:
        if st.button("🏠 Início / Workspace", key="rep_top_go_home"):
            navigate_to("Início")
            st.rerun()

    render_html(f"<div style='margin-top:16px;'></div>")

    # =========================================================================
    # 2. IDENTIFICAÇÃO DA ANÁLISE (Factual e Sem Invencionismos)
    # =========================================================================
    render_html(f"""
        <div style="background:{COLORS.SURFACE}; border:1px solid {COLORS.BORDER}; border-radius:{RADIUS.MD}; padding:18px 22px; margin-bottom:20px; box-shadow:{SHADOWS.SM};">
            <div style="font-size:11px; font-weight:700; text-transform:uppercase; color:{COLORS.PRIMARY_BLUE}; letter-spacing:0.5px; margin-bottom:8px;">
                IDENTIFICAÇÃO DA ANÁLISE CONTRATUAL D&O
            </div>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px; font-size:12.5px;">
                <div style="border-right:1px solid #EDF2F7; padding-right:16px;">
                    <div style="font-weight:700; color:{COLORS.PRIMARY_NAVY}; font-size:14px; margin-bottom:4px;">
                        Documento A (Referência): {seg_a}
                    </div>
                    <div style="color:{COLORS.TEXT_MUTED}; line-height:1.5;">
                        • Arquivo: <code>{pol_a.nome_arquivo}</code><br/>
                        • Tipo Documental: {tipo_a}<br/>
                        • Processo SUSEP: {susep_a}<br/>
                        • Vigência: {pol_a.vigencia_inicio or '?'} até {pol_a.vigencia_fim or '?'}
                    </div>
                </div>

                <div style="padding-left:8px;">
                    <div style="font-weight:700; color:{COLORS.PRIMARY_NAVY}; font-size:14px; margin-bottom:4px;">
                        Documento B (Comparação): {seg_b}
                    </div>
                    <div style="color:{COLORS.TEXT_MUTED}; line-height:1.5;">
                        • Arquivo: <code>{pol_b.nome_arquivo}</code><br/>
                        • Tipo Documental: {tipo_b}<br/>
                        • Processo SUSEP: {susep_b}<br/>
                        • Vigência: {pol_b.vigencia_inicio or '?'} até {pol_b.vigencia_fim or '?'}
                    </div>
                </div>
            </div>
            <div style="border-top:1px solid #F1F5F9; margin-top:12px; padding-top:8px; font-size:11.5px; color:{COLORS.TEXT_MUTED}; display:flex; justify-content:space-between;">
                <span>Data do Processamento Analítico: <b>{dt_analise}</b></span>
                <span>Perfil de Apresentação: <b>{active_profile.label}</b></span>
            </div>
        </div>
    """)

    # =========================================================================
    # 3. RESUMO EXECUTIVO (Derivado Estritamente de ComparisonResult)
    # =========================================================================
    semantic_matches = comp.semantic_matches or []
    substantive_matches = [m for m in semantic_matches if m.relation in ("changed_scope", "changed_condition", "changed_limit", "different")]
    scope_matches = [m for m in semantic_matches if m.relation in ("broader", "narrower", "changed_scope")]
    condition_matches = [m for m in semantic_matches if m.relation == "changed_condition"]
    limit_matches = [m for m in semantic_matches if m.relation == "changed_limit"]
    equivalent_matches = [m for m in semantic_matches if m.relation == "semantic_equivalent"]

    scalar_diffs = [d for d in comp.diffs if d.ha_diferenca]
    scalar_equals = [d for d in comp.diffs if not d.ha_diferenca]

    total_exclusivas = (
        len(comp.coberturas_exclusivas_a) + len(comp.coberturas_exclusivas_b) +
        len(comp.clausulas_especiais_exclusivas_a) + len(comp.clausulas_especiais_exclusivas_b)
    )
    total_diferencas = len(substantive_matches) + len(scalar_diffs) + total_exclusivas
    total_equivalencias = len(equivalent_matches) + len(scalar_equals)

    render_html(f"""
        <div style="margin-bottom: 12px;">
            <h3 style="margin:0 0 4px 0; font-size:16px; font-weight:700; color:{COLORS.PRIMARY_NAVY};">
                📋 Resumo Executivo Factual
            </h3>
            <p style="margin:0; font-size:12.5px; color:{COLORS.TEXT_MUTED};">
                Indicadores derivados exclusivamente da análise analítica estruturada:
            </p>
        </div>
    """)

    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
    with col_m1:
        render_metric_card("Diferenças Totais", f"{total_diferencas}", "Identificadas no cotejo", "neutral")
    with col_m2:
        render_metric_card("Merecem Avaliação", f"{len(substantive_matches)}", "Substantivas", "attention" if substantive_matches else "neutral")
    with col_m3:
        render_metric_card("Equivalências", f"{total_equivalencias}", "Redações simétricas", "positive" if total_equivalencias else "neutral")
    with col_m4:
        render_metric_card("Escopo Alterado", f"{len(scope_matches)}", "Abrangência distinta", "neutral")
    with col_m5:
        render_metric_card("Condições & Prazos", f"{len(condition_matches) + len(limit_matches)}", "Exigências e limites", "neutral")

    render_html(f"<div style='margin-top:20px;'></div>")

    # =========================================================================
    # 11. BARRA DE EXPORTAÇÃO REAL (Reutilizando Mecanismo Existente)
    # =========================================================================
    col_exp_info, col_btn_md, col_btn_json = st.columns([3, 1.8, 1.8])
    with col_exp_info:
        render_html(f"""
            <div style="font-size:12.5px; color:{COLORS.TEXT_MUTED}; padding-top:6px;">
                💾 <b>Exportação Documental Auditável:</b> Disponibilize a síntese para dossiês técnicos ou integração externa.
            </div>
        """)
    with col_btn_md:
        md_export_content = report_md if report_md else f"# Relatório de Comparação D&O\n\n{seg_a} × {seg_b}\n\nSimilaridade Técnica: {comp.score_similaridade:.1f}%\n"
        st.download_button(
            label="💾 Exportar Relatório (MD)",
            data=md_export_content,
            file_name=f"relatorio_insurminds_{seg_a[:10]}_{seg_b[:10]}.md".replace(" ", "_"),
            mime="text/markdown",
            key="btn_download_report_md"
        )
    with col_btn_json:
        json_export_content = comp.model_dump_json(indent=2)
        st.download_button(
            label="💾 Exportar Dados (JSON)",
            data=json_export_content,
            file_name=f"dados_comparacao_{seg_a[:10]}_{seg_b[:10]}.json".replace(" ", "_"),
            mime="application/json",
            key="btn_download_report_json"
        )

    render_html(f"<hr style='border:none; border-top:1px solid {COLORS.BORDER}; margin:16px 0 24px 0;'/>")

    # =========================================================================
    # 4. PRINCIPAIS ALTERAÇÕES (Diferenças Substantivas com Auditoria)
    # =========================================================================
    render_html(f"""
        <div style="margin-bottom: 14px;">
            <h3 style="margin:0 0 4px 0; font-size:16px; font-weight:700; color:{COLORS.PRIMARY_NAVY};">
                ⚖️ Principais Alterações Contratuais ({len(substantive_matches)} cláusulas)
            </h3>
            <p style="margin:0; font-size:12.5px; color:{COLORS.TEXT_MUTED};">
                Cláusulas com o mesmo conceito securitário que apresentam modificações substantivas em redação, obrigações ou escopo:
            </p>
        </div>
    """)

    if substantive_matches:
        for idx, match in enumerate(substantive_matches):
            title_a = match.item_a.split(":")[0].strip()
            title_b = match.item_b.split(":")[0].strip()
            item_title = title_a if title_a == title_b else f"{title_a} ⟷ {title_b}"
            cat = _get_item_category(item_title)
            badge_html = render_semantic_badge(match.relation)
            page_a_str = f"Pág. {match.page_a}" if match.page_a else "Pág. não indicada"
            page_b_str = f"Pág. {match.page_b}" if match.page_b else "Pág. não indicada"

            true_idx = comp.semantic_matches.index(match) if match in comp.semantic_matches else idx

            render_html(f"""
                <div style="background:{COLORS.SURFACE}; border:1px solid {COLORS.BORDER}; border-left:4px solid {COLORS.CRITICAL}; border-radius:{RADIUS.MD}; padding:14px 18px; margin-bottom:12px; box-shadow:{SHADOWS.SM};">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; flex-wrap:wrap; gap:8px;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span style="font-size:10px; font-weight:700; text-transform:uppercase; color:{COLORS.PRIMARY_BLUE}; background:#EFF6FF; padding:2px 6px; border-radius:4px;">
                                {cat}
                            </span>
                            <span style="color:#D1D5DB;">·</span>
                            {badge_html}
                        </div>
                        <div style="font-size:11.5px; color:{COLORS.TEXT_MUTED};">
                            {page_a_str} (Doc A) &nbsp;·&nbsp; {page_b_str} (Doc B)
                        </div>
                    </div>
                    <div style="font-weight:700; font-size:14.5px; color:{COLORS.PRIMARY_NAVY}; margin-bottom:4px;">
                        {item_title}
                    </div>
                    <div style="font-size:12.5px; color:{COLORS.TEXT_MAIN}; line-height:1.5;">
                        <b>Síntese factual:</b> {match.explanation}
                    </div>
                </div>
            """)

            # 6. Evidência Expansível + Ação de Detalhe
            col_ev_exp, col_ev_btn = st.columns([3.2, 1.2])
            with col_ev_exp:
                with st.expander(f"🔍 Ver Evidência Auditável: {title_a} × {title_b}", expanded=False):
                    ev_a_obj = pol_a.evidencias.get(title_a) if pol_a.evidencias else None
                    ev_b_obj = pol_b.evidencias.get(title_b) if pol_b.evidencias else None
                    render_evidence_panel(
                        item_title=item_title,
                        evidence_a=ev_a_obj,
                        evidence_b=ev_b_obj,
                        doc_a_name=seg_a,
                        doc_b_name=seg_b,
                        raw_text_a=match.evidence_a or match.item_a,
                        raw_text_b=match.evidence_b or match.item_b,
                        page_a=match.page_a,
                        page_b=match.page_b
                    )
            with col_ev_btn:
                if st.button("🔍 Auditar Detalhe ➔", key=f"btn_rep_detail_{idx}", help="Abrir tela dedicada de auditoria para esta alteração"):
                    st.session_state["selected_for_compare"] = [pol_a, pol_b]
                    st.session_state["viewing_diff_idx"] = true_idx
                    navigate_to("Comparações")
                    st.rerun()

            render_html(f"<div style='margin-bottom:8px;'></div>")
    else:
        render_alert("Não foram identificadas alterações substantivas nas cláusulas analisadas.", alert_type="info")

    render_html(f"<div style='margin-top:20px;'></div>")

    # =========================================================================
    # 5. CONFRONTO RESUMIDO (Matriz Compacta)
    # =========================================================================
    render_html(f"""
        <div style="margin-bottom: 12px;">
            <h3 style="margin:0 0 4px 0; font-size:16px; font-weight:700; color:{COLORS.PRIMARY_NAVY};">
                📊 Matriz de Confronto Resumido
            </h3>
            <p style="margin:0; font-size:12.5px; color:{COLORS.TEXT_MUTED};">
                Visão sintética das correspondências semânticas e parâmetros escalares identificados:
            </p>
        </div>
    """)

    dados_matriz = []
    for m in semantic_matches:
        t_a = m.item_a.split(":")[0].strip()
        t_b = m.item_b.split(":")[0].strip()
        label_rel = SEMANTIC_RELATION_CONFIG.get(m.relation, {}).get("label", m.relation)
        dados_matriz.append({
            "Cláusula / Item": t_a if t_a == t_b else f"{t_a} ⟷ {t_b}",
            f"Doc A ({seg_a})": f"{t_a} (Pág. {m.page_a or 'N/D'})",
            f"Doc B ({seg_b})": f"{t_b} (Pág. {m.page_b or 'N/D'})",
            "Relação Semântica": label_rel
        })

    if dados_matriz:
        df_matriz = pd.DataFrame(dados_matriz)
        st.dataframe(df_matriz, use_container_width=True, hide_index=True)

    render_html(f"<div style='margin-top:24px;'></div>")

    # =========================================================================
    # 7. INTERPRETAÇÃO ASSISTIDA & 8. PONTOS PARA REVISÃO PROFISSIONAL
    # =========================================================================
    col_assist, col_review = st.columns(2)

    with col_assist:
        render_html(f"""
            <div style="background:#F8FAFC; border:1px solid {COLORS.BORDER}; border-radius:{RADIUS.MD}; padding:16px 18px; height:100%; box-shadow:{SHADOWS.SM};">
                <div style="font-size:11px; font-weight:700; text-transform:uppercase; color:{COLORS.TEXT_MUTED}; letter-spacing:0.5px; margin-bottom:6px;">
                    🤖 INTERPRETAÇÃO ASSISTIDA
                </div>
                <div style="font-size:13px; color:{COLORS.TEXT_MAIN}; line-height:1.5; margin-bottom:12px;">
                    {comp.summary or 'Análise comparativa assistida estruturada sobre o teor contratual extraído.'}
                </div>
                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:4px; padding:10px 12px; font-size:11.5px; color:{COLORS.TEXT_MUTED}; line-height:1.4;">
                    ℹ️ <b>Aviso de Governança Obrigatório:</b> O texto contratual é a fonte primária.
                    A interpretação apresentada é assistida por IA e deve ser obrigatoriamente revisada pelo profissional responsável.
                </div>
            </div>
        """)

    with col_review:
        top_diff_relation = substantive_matches[0].relation if substantive_matches else "semantic_equivalent"
        note_profile = _get_profile_review_note(active_profile.id, top_diff_relation)

        render_html(f"""
            <div style="background:#F8FAFC; border:1px solid {COLORS.BORDER}; border-left:4px solid {COLORS.ATTENTION}; border-radius:{RADIUS.MD}; padding:16px 18px; height:100%; box-shadow:{SHADOWS.SM};">
                <div style="font-size:11px; font-weight:700; text-transform:uppercase; color:{COLORS.ATTENTION}; letter-spacing:0.5px; margin-bottom:6px;">
                    🔍 PONTOS PARA REVISÃO PROFISSIONAL ({active_profile.label.upper()})
                </div>
                <div style="font-size:13px; color:{COLORS.TEXT_MAIN}; line-height:1.5; margin-bottom:12px;">
                    {note_profile}
                </div>
                <div style="font-size:11.5px; color:{COLORS.TEXT_MUTED}; line-height:1.4;">
                    <i>A interface indica que as alterações merecem avaliação técnica humana especializada, não determinando decisão jurídica ou risco crítico automático.</i>
                </div>
            </div>
        """)

    render_html(f"<div style='margin-top:24px;'></div>")

    # =========================================================================
    # 9. SCORE AUXILIAR & 10. DECLARAÇÃO DE LIMITAÇÕES
    # =========================================================================
    render_html(f"""
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px; margin-bottom:28px;">
            <div style="background:{COLORS.SURFACE}; border:1px solid {COLORS.BORDER}; border-radius:{RADIUS.MD}; padding:14px 18px; box-shadow:{SHADOWS.SM};">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <div style="font-size:12px; font-weight:700; color:{COLORS.PRIMARY_NAVY};">
                        📐 Similaridade Estrutural (Indicador Técnico Auxiliar)
                    </div>
                    <div style="font-size:16px; font-weight:800; color:{COLORS.PRIMARY_BLUE}; font-family:{TYPOGRAPHY.FONT_CODE};">
                        {comp.score_similaridade:.1f}%
                    </div>
                </div>
                <div style="font-size:11.5px; color:{COLORS.TEXT_MUTED}; line-height:1.4;">
                    Este indicador mede a proximidade léxica e taxonômica entre as minutas contratuais.
                    <b>Não representa nota de qualidade, recomendação de compra ou superioridade</b> entre os documentos.
                </div>
            </div>

            <div style="background:{COLORS.SURFACE}; border:1px solid {COLORS.BORDER}; border-radius:{RADIUS.MD}; padding:14px 18px; box-shadow:{SHADOWS.SM};">
                <div style="font-size:12px; font-weight:700; color:{COLORS.PRIMARY_NAVY}; margin-bottom:6px;">
                    🛡️ Declaração de Limitações Metodológicas
                </div>
                <div style="font-size:11.5px; color:{COLORS.TEXT_MUTED}; line-height:1.4;">
                    A análise depende estritamente dos documentos fornecidos e da legibilidade digital dos arquivos PDF.
                    Não substitui a revisão jurídica ou de subscrição e pode conter limitações de extração caso trechos não constem do texto digital.
                </div>
            </div>
        </div>
    """)

    # =========================================================================
    # CÓDIGO-FONTE DO RELATÓRIO NARRATIVO (Se persistido)
    # =========================================================================
    if report_md:
        with st.expander("📄 Ver Parecer Narrativo Completo Gerado (Markdown)", expanded=False):
            st.markdown(report_md)

    # =========================================================================
    # 16. RODAPÉ DE NAVEGAÇÃO
    # =========================================================================
    render_html(f"<hr style='border:none; border-top:1px solid {COLORS.BORDER}; margin:16px 0 20px 0;'/>")
    col_b1, col_b2, col_b3 = st.columns([2.5, 2.5, 2.5])
    with col_b1:
        if st.button("⬅ Retornar à Comparação Geral", key="rep_bot_back_comp"):
            st.session_state["selected_for_compare"] = [pol_a, pol_b]
            st.session_state["viewing_diff_idx"] = None
            navigate_to("Comparações")
            st.rerun()
    with col_b2:
        if st.button("📚 Ir para Biblioteca de Documentos", key="rep_bot_go_lib"):
            navigate_to("Documentos")
            st.rerun()
    with col_b3:
        if st.button("🏠 Ir para Início / Workspace", key="rep_bot_go_home"):
            navigate_to("Início")
            st.rerun()
