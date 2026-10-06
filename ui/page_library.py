"""Página de Biblioteca Documental — Insurance Intelligence v1.0.
Gestão Documental Operacional: "Quais documentos existem, qual é o contexto deles e como continuo a análise?".
Permite localizar, auditar e reutilizar apólices D&O e retomar comparações existentes
sem competir com a experiência de Comparação ou de Nova Análise.
"""
import re
from typing import Optional, List, Dict, Any, Tuple
import streamlit as st

from core.database import db
from core.schemas import ApoliceDAO, ComparisonResult
from ui.navigation import navigate_to
from ui.persona.profiles import get_active_profile
from ui.tokens import COLORS, TYPOGRAPHY, RADIUS, SHADOWS
from ui.styles import render_html
from ui.components.states import render_empty_state, render_alert, render_error_state
from ui.components.cards import render_metric_card

# Aviso Legal Obrigatório (Preservado para conformidade com Requisito 10 e suíte de testes)
MANDATORY_DISCLAIMER = "A análise é assistida por IA e não substitui a avaliação jurídica, técnica ou de subscrição."


def _get_saved_comparisons(apolice_map: Dict[str, ApoliceDAO]) -> List[Dict[str, Any]]:
    """Recupera comparações salvas no banco de dados e correlaciona com as apólices em memória."""
    try:
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, apolice_a_id, apolice_b_id, score_similaridade, data_comparacao, relatorio_markdown
                FROM comparacoes
                ORDER BY created_at DESC
            """)
            rows = cursor.fetchall()

            comparisons = []
            for r in rows:
                pol_a = apolice_map.get(r["apolice_a_id"])
                pol_b = apolice_map.get(r["apolice_b_id"])
                comparisons.append({
                    "id": r["id"],
                    "apolice_a_id": r["apolice_a_id"],
                    "apolice_b_id": r["apolice_b_id"],
                    "pol_a": pol_a,
                    "pol_b": pol_b,
                    "score_similaridade": float(r["score_similaridade"]),
                    "data_comparacao": r["data_comparacao"] or "",
                    "has_report": bool(r["relatorio_markdown"])
                })
            return comparisons
    except Exception as e:
        return []


def _extract_year(apolice: ApoliceDAO) -> str:
    """Extrai o ano contratual a partir do nome do arquivo ou da vigência."""
    match = re.search(r"(202[0-9])", apolice.nome_arquivo)
    if match:
        return match.group(1)
    if apolice.vigencia_inicio:
        m_vig = re.search(r"(202[0-9])", apolice.vigencia_inicio)
        if m_vig:
            return m_vig.group(1)
    return "N/D"


def _extract_pages_estimate(apolice: ApoliceDAO) -> str:
    """Calcula a maior página auditada disponível nas evidências."""
    if apolice.evidencias:
        pages = [ev.page for ev in apolice.evidencias.values() if ev and ev.page]
        if pages:
            return f"~{max(pages)} págs"
    return "Consolidado"


def _format_doc_type(doc_type: Optional[str]) -> str:
    """Normaliza o tipo documental para rótulos formais do mercado securitário."""
    mapping = {
        "condicoes_gerais": "Condições Gerais",
        "apolice_individual": "Apólice Individual",
        "endosso": "Endosso",
        "proposta": "Proposta de Seguro",
        "outros": "Documento Suplementar",
        "unknown": "Não especificado"
    }
    return mapping.get(str(doc_type).lower(), "Condições Gerais")


def _get_comparison_for_policy(
    apolice_id: str,
    saved_comparisons: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Identifica se o documento já participou de alguma comparação registrada."""
    for comp in saved_comparisons:
        if comp["apolice_a_id"] == apolice_id or comp["apolice_b_id"] == apolice_id:
            return comp
    return None


def render_library_page() -> None:
    """Renderiza a experiência completa da Biblioteca Documental Operacional."""

    # 1. CABEÇALHO EDITORIAL
    render_html(f"""
        <div style="margin-bottom: 16px;">
            <h2 style="color:{COLORS.PRIMARY_NAVY}; font-size:24px; font-weight:700; margin:0 0 6px 0; font-family:{TYPOGRAPHY.FONT_UI};">
                BIBLIOTECA
            </h2>
            <p style="color:{COLORS.TEXT_MUTED}; font-size:14px; margin:0; font-family:{TYPOGRAPHY.FONT_UI}; line-height:1.5;">
                Consulte documentos analisados e retome comparações existentes.
            </p>
        </div>
    """)

    # Aviso Legal Obrigatório
    render_html(f"""
        <div class="disclaimer-banner">
            🛡️ <strong>Aviso Legal Obrigatório:</strong> {MANDATORY_DISCLAIMER}
        </div>
    """)

    active_profile = get_active_profile()
    apolices = db.list_apolices()

    # 11. ESTADO: Biblioteca Vazia
    if not apolices:
        render_empty_state(
            title="Nenhum documento cadastrado na biblioteca",
            description="Processe apólices individuais ou condições gerais no fluxo de análise para consultar documentos e comparações.",
            action_label="Iniciar Nova Análise ➔",
            action_callback=lambda: navigate_to("Nova análise")
        )
        return

    apolice_map = {a.id: a for a in apolices}
    saved_comparisons = _get_saved_comparisons(apolice_map)

    # 2. CONTEXTO DO WORKSPACE (Métricas Factuais Sóbrias)
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    with col_kpi1:
        render_metric_card(
            label="Total de Documentos",
            value=f"{len(apolices)}",
            delta="Cadastrados no repositório",
            delta_type="neutral"
        )
    with col_kpi2:
        seguradoras_unicas = sorted(list(set(a.seguradora for a in apolices if a.seguradora)))
        render_metric_card(
            label="Seguradoras Presentes",
            value=f"{len(seguradoras_unicas)}",
            delta="Companhias emissoras",
            delta_type="neutral"
        )
    with col_kpi3:
        render_metric_card(
            label="Comparações Realizadas",
            value=f"{len(saved_comparisons)}",
            delta="Confrontos A × B salvos",
            delta_type="positive" if saved_comparisons else "neutral"
        )
    with col_kpi4:
        data_recente = apolices[0].data_processamento[:10] if apolices[0].data_processamento else "Recente"
        render_metric_card(
            label="Última Ingestão",
            value=data_recente,
            delta="Data de processamento",
            delta_type="neutral"
        )

    render_html(f"<div style='margin-top:20px;'></div>")

    # =========================================================================
    # 7. SEÇÃO DE COMPARAÇÕES EXISTENTES
    # =========================================================================
    if saved_comparisons:
        render_html(f"""
            <div style="background:{COLORS.SURFACE}; border:1px solid {COLORS.BORDER}; border-radius:{RADIUS.MD}; padding:18px 20px; margin-bottom:24px; box-shadow:{SHADOWS.SM};">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <div>
                        <h3 style="margin:0; font-size:15px; font-weight:700; color:{COLORS.PRIMARY_NAVY};">
                            📊 Comparações Registradas no Workspace ({len(saved_comparisons)})
                        </h3>
                        <p style="margin:2px 0 0 0; font-size:12.5px; color:{COLORS.TEXT_MUTED};">
                            Retome confrontos analíticos previamente executados com preservação integral de metadados:
                        </p>
                    </div>
                </div>
        """)

        for c_idx, comp_data in enumerate(saved_comparisons[:4]):
            pa = comp_data["pol_a"]
            pb = comp_data["pol_b"]
            if not pa or not pb:
                continue

            name_a = pa.nome_arquivo
            name_b = pb.nome_arquivo
            seg_a = pa.seguradora or "Documento A"
            seg_b = pb.seguradora or "Documento B"
            dt_comp = comp_data["data_comparacao"][:10] if comp_data["data_comparacao"] else "Data N/D"
            score = comp_data["score_similaridade"]

            col_c_info, col_c_btn = st.columns([3.5, 1.2])
            with col_c_info:
                render_html(f"""
                    <div style="background:#F8FAFC; border:1px solid {COLORS.BORDER}; border-radius:{RADIUS.SM}; padding:10px 14px; margin-bottom:8px; font-size:12.5px;">
                        <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                            <b style="color:{COLORS.PRIMARY_NAVY};">{seg_a}</b>
                            <span style="color:{COLORS.PRIMARY_BLUE}; font-weight:700;">⟷</span>
                            <b style="color:{COLORS.PRIMARY_NAVY};">{seg_b}</b>
                            <span style="color:#D1D5DB;">·</span>
                            <span style="color:{COLORS.TEXT_MUTED}; font-size:11.5px;">Similaridade Auxiliar: <b>{score:.1f}%</b></span>
                            <span style="color:#D1D5DB;">·</span>
                            <span style="color:{COLORS.TEXT_MUTED}; font-size:11.5px;">{dt_comp}</span>
                        </div>
                        <div style="font-size:11.5px; color:{COLORS.TEXT_MUTED};">
                            <code>{name_a}</code> × <code>{name_b}</code>
                        </div>
                    </div>
                """)
            with col_c_btn:
                if st.button("▶ Retomar Comparação", key=f"btn_resume_comp_{c_idx}", help=f"Carregar confronto entre {seg_a} e {seg_b}"):
                    st.session_state["selected_for_compare"] = [pa, pb]
                    st.session_state["viewing_diff_idx"] = None
                    navigate_to("Comparações")
                    st.rerun()

        render_html("</div>")

    # =========================================================================
    # 3. BARRA DE BUSCA & 4. FILTROS
    # =========================================================================
    render_html(f"""
        <div style="margin-bottom: 12px;">
            <h3 style="margin:0 0 4px 0; font-size:16px; font-weight:700; color:{COLORS.PRIMARY_NAVY};">
                📑 Acervo Documental de Apólices & Condições Gerais
            </h3>
            <p style="margin:0; font-size:12.5px; color:{COLORS.TEXT_MUTED};">
                Filtre por seguradora, modalidade ou pesquise termos contratuais para gerenciar o acervo:
            </p>
        </div>
    """)

    col_search, col_f_seg, col_f_tipo, col_f_status = st.columns([2.5, 1.8, 1.8, 1.8])

    with col_search:
        search_query = st.text_input(
            "Buscar no acervo:",
            placeholder="Nome do arquivo, seguradora, SUSEP...",
            key="library_search"
        ).strip().lower()

    with col_f_seg:
        filtro_seg = st.selectbox(
            "Seguradora:",
            options=["Todas"] + seguradoras_unicas,
            key="lib_f_seg"
        )

    with col_f_tipo:
        tipos_disponiveis = sorted(list(set(_format_doc_type(a.document_type) for a in apolices)))
        filtro_tipo = st.selectbox(
            "Tipo Documental:",
            options=["Todos"] + tipos_disponiveis,
            key="lib_f_tipo"
        )

    with col_f_status:
        filtro_status = st.selectbox(
            "Status de Comparação:",
            options=["Todos", "Com comparação", "Sem comparação"],
            key="lib_f_status"
        )

    # Aplicação de Filtros em Memória
    apolices_filtradas = []
    for a in apolices:
        # 1. Filtro Textual
        if search_query:
            termos = f"{a.nome_arquivo} {a.seguradora or ''} {a.processo_susep or ''} {a.numero_apolice or ''} {a.segurado or ''}".lower()
            if search_query not in termos:
                continue

        # 2. Filtro Seguradora
        if filtro_seg != "Todas" and a.seguradora != filtro_seg:
            continue

        # 3. Filtro Tipo Documental
        if filtro_tipo != "Todos" and _format_doc_type(a.document_type) != filtro_tipo:
            continue

        # 4. Filtro Status
        comp_existente = _get_comparison_for_policy(a.id, saved_comparisons)
        if filtro_status == "Com comparação" and not comp_existente:
            continue
        if filtro_status == "Sem comparação" and comp_existente:
            continue

        apolices_filtradas.append(a)

    # 11. ESTADO: Nenhum Resultado de Busca
    if not apolices_filtradas:
        render_alert(
            message=f"Nenhum documento encontrado para os filtros selecionados. Tente ajustar os termos de busca ou limpar os filtros.",
            level="info"
        )
        if st.button("Limpar Filtros e Busca", key="btn_clear_filters"):
            st.session_state["library_search"] = ""
            st.session_state["lib_f_seg"] = "Todas"
            st.session_state["lib_f_tipo"] = "Todos"
            st.session_state["lib_f_status"] = "Todos"
            st.rerun()
        return

    render_html(f"""
        <div style="font-size:12px; color:{COLORS.TEXT_MUTED}; margin:8px 0 16px 0;">
            Exibindo <b>{len(apolices_filtradas)}</b> de <b>{len(apolices)}</b> documentos cadastrados.
        </div>
    """)

    # =========================================================================
    # 5. LISTAGEM PRINCIPAL DE DOCUMENTOS (Biblioteca Corporativa)
    # =========================================================================
    for idx, apolice in enumerate(apolices_filtradas):
        ano_str = _extract_year(apolice)
        tipo_str = _format_doc_type(apolice.document_type)
        pags_str = _extract_pages_estimate(apolice)
        comp_assoc = _get_comparison_for_policy(apolice.id, saved_comparisons)

        # 8 & 9. Indicação Objetiva de Uso em Comparação
        if comp_assoc:
            other_pol = comp_assoc["pol_b"] if comp_assoc["apolice_a_id"] == apolice.id else comp_assoc["pol_a"]
            other_name = other_pol.seguradora if other_pol else "Outro Documento"
            status_badge = f"""
                <span style="background:#E6F4EA; color:#197B5C; border:1px solid #A3D9B5; padding:3px 8px; border-radius:{RADIUS.SM}; font-size:11px; font-weight:700;">
                    ✓ Comparação disponível ({other_name})
                </span>
            """
        else:
            status_badge = f"""
                <span style="background:#F1F5F9; color:#475569; border:1px solid #CBD5E1; padding:3px 8px; border-radius:{RADIUS.SM}; font-size:11px; font-weight:600;">
                    ⚪ Disponível para análise
                </span>
            """

        # Linha/Cartão do Documento
        render_html(f"""
            <div style="background:{COLORS.SURFACE}; border:1px solid {COLORS.BORDER}; border-radius:{RADIUS.MD}; padding:14px 18px; margin-bottom:12px; box-shadow:{SHADOWS.SM};">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:8px;">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <span style="font-size:16px;">📄</span>
                        <div>
                            <span style="font-weight:700; color:{COLORS.PRIMARY_NAVY}; font-size:14px;">
                                {apolice.seguradora or 'Seguradora não informada'}
                            </span>
                            <span style="color:#D1D5DB; margin:0 6px;">·</span>
                            <span style="font-size:13px; color:{COLORS.TEXT_MAIN}; font-weight:500;">
                                {apolice.nome_arquivo}
                            </span>
                        </div>
                    </div>
                    <div>
                        {status_badge}
                    </div>
                </div>

                <div style="display:flex; gap:16px; font-size:12px; color:{COLORS.TEXT_MUTED}; flex-wrap:wrap; margin-bottom:10px;">
                    <span><b>Tipo:</b> {tipo_str}</span>
                    <span>·</span>
                    <span><b>Ano/Versão:</b> {ano_str}</span>
                    <span>·</span>
                    <span><b>Páginas:</b> {pags_str}</span>
                    <span>·</span>
                    <span><b>SUSEP:</b> {apolice.processo_susep or 'Não informado'}</span>
                    <span>·</span>
                    <span><b>LMG:</b> {apolice.limite_responsabilidade or 'Não informado'}</span>
                </div>
            </div>
        """)

        # Ações e Gaveta de Detalhamento
        col_act1, col_act2, col_act_space = st.columns([1.8, 1.8, 2.5])

        with col_act1:
            # 6. Ação: Usar em Nova Análise
            if st.button("⚖️ Usar em Nova Análise", key=f"btn_use_new_{apolice.id}"):
                st.session_state["selected_for_compare"] = [apolice]
                navigate_to("Nova análise")
                st.rerun()

        with col_act2:
            # 6 & 9. Ação: Retomar Comparação
            if comp_assoc:
                other_pol = comp_assoc["pol_b"] if comp_assoc["apolice_a_id"] == apolice.id else comp_assoc["pol_a"]
                if other_pol:
                    if st.button("▶ Retomar Comparação", key=f"btn_resume_{apolice.id}"):
                        st.session_state["selected_for_compare"] = [apolice, other_pol]
                        st.session_state["viewing_diff_idx"] = None
                        navigate_to("Comparações")
                        st.rerun()

        # Detalhes e Estrutura Contratual (Expander Compacto)
        with st.expander(f"🔍 Detalhes Contratuais e Evidências ({apolice.nome_arquivo})", expanded=False):
            c_meta1, c_meta2, c_meta3 = st.columns(3)
            with c_meta1:
                render_html(f"""
                    <div style="font-size:12px; line-height:1.6;">
                        <b>Dados Cadastrais:</b><br/>
                        • Seguradora: {apolice.seguradora or 'N/A'}<br/>
                        • Segurado: {apolice.segurado or 'N/A (Condições Gerais)'}<br/>
                        • Apólice nº: {apolice.numero_apolice or 'N/A'}<br/>
                        • Processo SUSEP: {apolice.processo_susep or 'N/A'}<br/>
                        • Ramo SUSEP: {apolice.cod_ramo or '0378'} ({apolice.ramo_descricao or 'D&O'})
                    </div>
                """)
            with c_meta2:
                render_html(f"""
                    <div style="font-size:12px; line-height:1.6;">
                        <b>Condições Econômicas:</b><br/>
                        • LMG: {apolice.limite_responsabilidade or 'N/A'}<br/>
                        • Franquia: {apolice.franquia or 'N/A'}<br/>
                        • Prêmio Total: {apolice.premio_total or 'N/A'}<br/>
                        • Vigência: {apolice.vigencia_inicio or '?'} até {apolice.vigencia_fim or '?'}<br/>
                        • Território: {apolice.territorio or 'N/A'}
                    </div>
                """)
            with c_meta3:
                render_html(f"""
                    <div style="font-size:12px; line-height:1.6;">
                        <b>Auditoria de Extração:</b><br/>
                        • Método: {apolice.metodo_extracao}<br/>
                        • Confiança: {apolice.confianca_extracao * 100:.0f}%<br/>
                        • Evidências Auditáveis: {len(apolice.evidencias)} registradas<br/>
                        • Cláusulas Especiais: {len(apolice.clausulas_especiais)} itens<br/>
                        • Data Ingestão: {apolice.data_processamento[:19]}
                    </div>
                """)

            # Coberturas e Exclusões Resumidas
            if apolice.coberturas or apolice.exclusoes:
                render_html(f"<div style='margin-top:10px;'></div>")
                col_cobs, col_excs = st.columns(2)
                with col_cobs:
                    st.caption(f"🛡️ **Coberturas Extraídas ({len(apolice.coberturas)}):**")
                    for c in apolice.coberturas[:5]:
                        render_html(f"<div style='font-size:11.5px; color:#166534; margin-bottom:3px;'>✓ {c[:60]}...</div>")
                with col_excs:
                    st.caption(f"⛔ **Exclusões Contratuais ({len(apolice.exclusoes)}):**")
                    for e in apolice.exclusoes[:5]:
                        render_html(f"<div style='font-size:11.5px; color:#991B1B; margin-bottom:3px;'>✕ {e[:60]}...</div>")

        render_html(f"<hr style='border:none; border-top:1px solid #E2E8F0; margin:8px 0 16px 0;'/>")

    # =========================================================================
    # 6. SELEÇÃO DIRETA PARA CONFRONTO
    # =========================================================================
    render_html(f"""
        <div style="background:{COLORS.SURFACE}; border:1px solid {COLORS.BORDER}; border-radius:{RADIUS.MD}; padding:18px 20px; margin-top:20px;">
            <div style="font-size:14px; font-weight:700; color:{COLORS.PRIMARY_NAVY}; margin-bottom:4px;">
                ⚖️ Confronto Rápido de Documentos Existentes
            </div>
            <p style="font-size:12.5px; color:{COLORS.TEXT_MUTED}; margin:0 0 12px 0;">
                Selecione exatamente dois documentos do acervo acima para abrir imediatamente a tela de Comparação:
            </p>
        </div>
    """)

    opcoes_confronto = {
        f"{a.seguradora or 'Seguradora'} — {a.nome_arquivo} ({_format_doc_type(a.document_type)})": a
        for a in apolices
    }

    selecionadas_chaves = st.multiselect(
        "Selecione dois documentos para comparar:",
        options=list(opcoes_confronto.keys()),
        default=list(opcoes_confronto.keys())[:2] if len(opcoes_confronto) >= 2 else list(opcoes_confronto.keys()),
        max_selections=2,
        key="ms_quick_compare"
    )

    col_q_btn, col_q_info = st.columns([1.8, 3])
    with col_q_btn:
        if len(selecionadas_chaves) == 2:
            if st.button("⚖️ Iniciar Comparação Analítica ➔", type="primary", key="btn_quick_comp"):
                st.session_state["selected_for_compare"] = [
                    opcoes_confronto[selecionadas_chaves[0]],
                    opcoes_confronto[selecionadas_chaves[1]]
                ]
                st.session_state["viewing_diff_idx"] = None
                navigate_to("Comparações")
                st.rerun()
        else:
            st.button("⚖️ Selecione 2 Apólices para Comparar", disabled=True, key="btn_quick_comp_dis")

    with col_q_info:
        if len(selecionadas_chaves) != 2:
            st.caption("ℹ️ Marque exatamente dois contratos para habilitar o acionamento do motor comparativo.")
