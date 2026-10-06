"""Página 1: Workspace / Início — Insurance Intelligence v1.0.
Implementa a tela central de trabalho corporativo respondendo rapidamente:
- onde estou;
- o que já foi analisado;
- o que posso fazer agora;
- qual análise posso continuar.
Apresenta dados 100% reais persistidos no SQLite, com adaptação de prioridade e apresentação conforme o Perfil de Trabalho ativo.
"""
from typing import List, Dict, Any, Optional
import streamlit as st
import datetime

from core.database import db
from core.schemas import ApoliceDAO, ComparisonResult, SemanticMatchItem
from core.llm_client import llm_client
from ui.navigation import navigate_to
from ui.persona.profiles import get_active_profile, ProfileConfig
from ui.tokens import COLORS
from ui.components.badges import render_status_badge, render_semantic_badge
from ui.components.cards import render_card_start, render_card_end, render_metric_card
from ui.components.states import render_empty_state, render_alert


# Aviso legal obrigatório mantido para conformidade regulatória
MANDATORY_DISCLAIMER = "A análise é assistida por IA e não substitui a avaliação jurídica, técnica ou de subscrição."


def _get_recent_comparisons_from_db(limit: int = 10) -> List[Dict[str, Any]]:
    """Recupera comparações reais persistidas no banco SQLite ordenadas pela mais recente."""
    comparisons = []
    try:
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, apolice_a_id, apolice_b_id, score_similaridade,
                       data_comparacao, resultado_json, relatorio_markdown, created_at
                FROM comparacoes
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()

            for row in rows:
                pol_a = db.get_apolice_by_id(row["apolice_a_id"])
                pol_b = db.get_apolice_by_id(row["apolice_b_id"])

                try:
                    comp_res = ComparisonResult.model_validate_json(row["resultado_json"])
                except Exception:
                    comp_res = None

                # Cálculo de diferenças e substantivas
                substantive_count = 0
                total_diffs = 0
                if comp_res:
                    semantic_matches = comp_res.semantic_matches or []
                    substantive_count = sum(
                        1 for m in semantic_matches
                        if m.relation in ("changed_scope", "changed_condition", "changed_limit", "different")
                    ) + len(comp_res.coberturas_exclusivas_a or []) + len(comp_res.coberturas_exclusivas_b or [])
                    total_diffs = len(comp_res.diffs or []) + len(semantic_matches)

                # Formatação amigável da data
                created_str = str(row["created_at"])
                try:
                    dt = datetime.datetime.fromisoformat(created_str.replace("Z", ""))
                    data_formatada = dt.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    data_formatada = created_str[:16]

                comparisons.append({
                    "id": row["id"],
                    "data": data_formatada,
                    "score": row["score_similaridade"],
                    "apolice_a": pol_a,
                    "apolice_b": pol_b,
                    "resultado": comp_res,
                    "relatorio_markdown": row["relatorio_markdown"] or "",
                    "total_diffs": total_diffs,
                    "substantive_count": substantive_count
                })
    except Exception as e:
        # Modo resiliente de consulta
        pass

    return comparisons


def render_workspace_page():
    """Renderiza a interface do Workspace / Início conforme o Wireframe 01 e os requisitos da Fase 7.3."""
    active_profile: ProfileConfig = get_active_profile()

    # -------------------------------------------------------------------------
    # 1. CABEÇALHO DO WORKSPACE
    # -------------------------------------------------------------------------
    col_hdr_title, col_hdr_badge = st.columns([3.2, 1.8])
    with col_hdr_title:
        st.markdown(f"""
            <div style="margin-bottom: 8px;">
                <span style="font-size: 11px; font-weight: 700; color: #0B8A84; text-transform: uppercase; letter-spacing: 0.8px;">
                    SEU WORKSPACE
                </span>
                <h2 style="margin: 2px 0 0 0; color: #12304A; font-size: 22px; font-weight: 700; letter-spacing: -0.3px;">
                    Visão Geral do Trabalho Analítico
                </h2>
                <p style="margin: 4px 0 0 0; color: #6B7785; font-size: 13.5px;">
                    Acompanhe documentos ingeridos, continue comparações ativas e acesse alterações relevantes de apólices D&O.
                </p>
            </div>
        """, unsafe_allow_html=True)
    with col_hdr_badge:
        st.markdown(f"""
            <div style="text-align: right; background-color: #FFFFFF; border: 1px solid #D9E1E8; border-radius: 8px; padding: 10px 14px; box-shadow: 0 1px 2px rgba(18, 48, 74, 0.04);">
                <span style="font-size: 11px; color: #6B7785; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
                    Perfil em Uso:
                </span>
                <div style="font-size: 13.5px; font-weight: 700; color: #12304A; margin-top: 2px;">
                    {active_profile.icon} {active_profile.label}
                </div>
                <div style="font-size: 11px; color: #0B8A84; margin-top: 2px;">
                    {active_profile.focus_summary.split('→')[0].strip()} em destaque
                </div>
            </div>
        """, unsafe_allow_html=True)

    # Aviso Legal Obrigatório
    st.markdown(f"""
        <div class="disclaimer-banner" style="margin: 12px 0 14px 0;">
            🛡️ <b>Aviso Legal Obrigatório:</b> {MANDATORY_DISCLAIMER}
        </div>
    """, unsafe_allow_html=True)

    # Banner de Onboarding da IA (Requisito 5)
    if not llm_client.is_available():
        col_ban_txt, col_ban_btn = st.columns([3.8, 1.2])
        with col_ban_txt:
            st.markdown("""
                <div style="background:#FFFBEB; border:1px solid #FDE68A; border-left:4px solid #D97706; border-radius:6px; padding:10px 14px; margin-bottom:12px;">
                    <div style="font-weight:700; font-size:12.5px; color:#92400E;">⚠️ IA Generativa não configurada</div>
                    <div style="font-size:12px; color:#B45309; margin-top:2px;">
                        Para executar a análise com Gemini, configure sua chave do Google AI Studio.
                    </div>
                </div>
            """, unsafe_allow_html=True)
        with col_ban_btn:
            st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
            if st.button("⚙️ Configurar IA", key="btn_cfg_ai_workspace", use_container_width=True):
                navigate_to("Configurações")
                st.rerun()

    # -------------------------------------------------------------------------
    # 2. CARREGAMENTO DOS DADOS REAIS DO REPOSITÓRIO
    # -------------------------------------------------------------------------
    apolices = db.list_apolices()
    recent_comparisons = _get_recent_comparisons_from_db(limit=10)

    total_apolices = len(apolices)
    total_comparacoes = len(recent_comparisons)
    total_evidencias = sum(len(a.evidencias or {}) for a in apolices)
    total_diferencas = sum(c["total_diffs"] for c in recent_comparisons)

    # Identificação Transparente do Workspace de Demonstração (Requisito 6)
    if total_comparacoes > 0 or total_apolices > 0:
        st.markdown("""
            <div style="background:#F8FAFC; border:1px solid #D9E1E8; border-left:3px solid #0B8A84; border-radius:6px; padding:10px 14px; margin-bottom:14px; display:flex; justify-content:space-between; align-items:center;">
                <div style="font-size:12.5px; color:#12304A;">
                    <span style="font-weight:700; color:#0B8A84; text-transform:uppercase; font-size:11px; letter-spacing:0.5px; margin-right:8px;">🏛️ Workspace de demonstração</span>
                    Este ambiente contém documentos e comparações previamente processados para demonstração.
                </div>
                <span style="font-size:11px; background:#EDF2F7; color:#4A5568; padding:2px 8px; border-radius:4px; font-weight:600;">Base Local Homologada</span>
            </div>
        """, unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # 3. KPIS SECUNDÁRIOS DO WORKSPACE
    # -------------------------------------------------------------------------
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    with col_kpi1:
        render_metric_card(
            label="Análises Realizadas",
            value=f"{total_comparacoes}",
            delta="Confrontos A × B" if total_comparacoes > 0 else "Nenhum confronto",
            delta_type="positive" if total_comparacoes > 0 else "neutral",
            help_text="Número total de comparações processadas e salvas no banco relacional."
        )
    with col_kpi2:
        render_metric_card(
            label="Documentos no Repositório",
            value=f"{total_apolices}",
            delta="Contratos D&O" if total_apolices > 0 else "Repositório vazio",
            delta_type="positive" if total_apolices > 0 else "neutral",
            help_text="Apólices e condições gerais cadastradas na base analítica local."
        )
    with col_kpi3:
        render_metric_card(
            label="Diferenças Catalogadas",
            value=f"{total_diferencas}",
            delta="Itens identificados" if total_diferencas > 0 else "Aguardando análise",
            delta_type="attention" if total_diferencas > 0 else "neutral",
            help_text="Total de divergências semânticas e escalares mapeadas pelo ComparatorAgent."
        )
    with col_kpi4:
        render_metric_card(
            label="Evidências Auditáveis",
            value=f"{total_evidencias}",
            delta="Páginas e snippets" if total_evidencias > 0 else "Nenhuma evidência",
            delta_type="positive" if total_evidencias > 0 else "neutral",
            help_text="Trechos contratuais literais extraídos com rastreabilidade de página."
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # 4. CTA PRINCIPAL + BLOCO DE CONTINUIDADE
    # -------------------------------------------------------------------------
    col_cta_box, col_cont_box = st.columns([1.6, 2.4])

    with col_cta_box:
        # CTA Principal (Wireframe 01 - Requisito 2)
        st.markdown("""
            <div style="background-color: #FFFFFF; border: 1px solid #D9E1E8; border-top: 3px solid #2864C7; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(18, 48, 74, 0.05); height: 100%;">
                <span style="font-size: 11px; font-weight: 700; color: #2864C7; text-transform: uppercase; letter-spacing: 0.8px;">
                    NOVA CONFRONTAÇÃO
                </span>
                <h3 style="margin: 6px 0 8px 0; color: #12304A; font-size: 17px; font-weight: 700;">
                    + Nova análise
                </h3>
                <p style="color: #475569; font-size: 13px; line-height: 1.5; margin-bottom: 16px;">
                    Compare documentos de seguros e encontre alterações relevantes entre versões contratuais ou minutas concorrentes.
                </p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("＋ Iniciar Nova Análise (Upload A × B)", type="primary", key="btn_cta_new_analysis", use_container_width=True):
            navigate_to("Nova análise")
            st.rerun()

    with col_cont_box:
        # Bloco de Continuidade da Análise Mais Recente (Requisito 3)
        if recent_comparisons:
            latest = recent_comparisons[0]
            doc_a = latest["apolice_a"]
            doc_b = latest["apolice_b"]

            nome_a = doc_a.nome_arquivo if doc_a else "Documento A"
            seg_a = doc_a.seguradora if doc_a else "Seguradora A"
            nome_b = doc_b.nome_arquivo if doc_b else "Documento B"
            seg_b = doc_b.seguradora if doc_b else "Seguradora B"

            diffs_total = latest["total_diffs"]
            diffs_relevantes = latest["substantive_count"]
            score_sim = latest["score"]
            data_exec = latest["data"]

            st.markdown(f"""
                <div style="background-color: #FFFFFF; border: 1px solid #D9E1E8; border-left: 4px solid #0B8A84; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(18, 48, 74, 0.05);">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        <span style="font-size: 11px; font-weight: 700; color: #0B8A84; text-transform: uppercase; letter-spacing: 0.8px;">
                            CONTINUIDADE · ANÁLISE RECENTE
                        </span>
                        <span style="font-size: 11.5px; color: #64748B;">{data_exec}</span>
                    </div>
                    <h4 style="margin: 4px 0 8px 0; color: #12304A; font-size: 16px; font-weight: 700;">
                        {seg_a} ⟷ {seg_b}
                    </h4>
                    <div style="font-size: 12px; color: #64748B; margin-bottom: 12px; line-height: 1.4;">
                        <b>A:</b> <code style="font-size: 11px;">{nome_a}</code><br/>
                        <b>B:</b> <code style="font-size: 11px;">{nome_b}</code>
                    </div>
                    <div style="display:flex; gap: 12px; margin-bottom: 14px;">
                        <div style="background-color: #F8FAFC; border: 1px solid #D9E1E8; border-radius: 6px; padding: 6px 12px; font-size: 12px;">
                            Diferenças: <b style="color: #12304A;">{diffs_total}</b>
                        </div>
                        <div style="background-color: #FDE8E8; border: 1px solid #F8B4B4; border-radius: 6px; padding: 6px 12px; font-size: 12px; color: #D94A4A;">
                            Relevantes: <b>{diffs_relevantes}</b>
                        </div>
                        <div style="background-color: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 6px; padding: 6px 12px; font-size: 12px; color: #2864C7;">
                            Similaridade Auxiliar: <b>{score_sim:.1f}%</b>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            if st.button("▶ Continuar Esta Análise (Abrir Confronto)", key="btn_continue_latest", type="primary", use_container_width=True):
                if doc_a and doc_b:
                    st.session_state["selected_for_compare"] = [doc_a, doc_b]
                    st.session_state["active_doc_a"] = doc_a
                    st.session_state["active_doc_b"] = doc_b
                if latest["resultado"]:
                    st.session_state["active_comparison_result"] = latest["resultado"]
                if latest["relatorio_markdown"]:
                    st.session_state["active_executive_report"] = latest["relatorio_markdown"]
                st.session_state["viewing_diff_idx"] = None
                navigate_to("Comparações")
                st.rerun()
        else:
            render_empty_state(
                title="Nenhuma análise recente encontrada",
                description="Seu workspace está pronto para a primeira comparação de apólices D&O.",
                action_label="＋ Iniciar Primeira Análise",
                action_callback=lambda: navigate_to("Nova análise")
            )

    st.markdown("---")

    # -------------------------------------------------------------------------
    # 5. PERSONALIZAÇÃO POR PERFIL DE TRABALHO (PERSONAS - Requisito 6)
    # -------------------------------------------------------------------------
    # Reorganiza o foco da tela conforme a persona ativa
    _render_profile_specific_section(active_profile, recent_comparisons, apolices)

    st.markdown("---")

    # -------------------------------------------------------------------------
    # 6. HISTÓRICO DE ANÁLISES RECENTES (Requisito 5)
    # -------------------------------------------------------------------------
    st.markdown("### 📑 Análises Recentes no Repositório")
    st.caption("Confrontos analíticos já executados e persistidos localmente no banco de dados:")

    if recent_comparisons:
        for idx, comp_item in enumerate(recent_comparisons):
            p_a = comp_item["apolice_a"]
            p_b = comp_item["apolice_b"]
            seg_a = p_a.seguradora if p_a else "Doc A"
            seg_b = p_b.seguradora if p_b else "Doc B"
            file_a = p_a.nome_arquivo if p_a else "doc_a.pdf"
            file_b = p_b.nome_arquivo if p_b else "doc_b.pdf"
            diffs = comp_item["total_diffs"]
            subst = comp_item["substantive_count"]
            dt_exec = comp_item["data"]
            score_val = comp_item["score"]

            col_row1, col_row2, col_row3, col_row4 = st.columns([2.5, 1.2, 1.2, 1.1])
            with col_row1:
                st.markdown(f"""
                    <div style="font-size: 13.5px; font-weight: 600; color: #12304A;">
                        🏢 {seg_a} &nbsp;⟷&nbsp; 🏢 {seg_b}
                    </div>
                    <div style="font-size: 11.5px; color: #64748B;">
                        <code>{file_a}</code> vs <code>{file_b}</code>
                    </div>
                """, unsafe_allow_html=True)
            with col_row2:
                st.markdown(f"""
                    <div style="font-size: 12.5px; color: #1F2A35;">
                        <b>{diffs}</b> diferenças
                    </div>
                    <div style="font-size: 11.5px; color: #D94A4A; font-weight: 600;">
                        {subst} alteração(ões) relevante(s)
                    </div>
                """, unsafe_allow_html=True)
            with col_row3:
                st.markdown(f"""
                    <div style="font-size: 12px; color: #64748B;">
                        Data: <b>{dt_exec}</b>
                    </div>
                    <div style="font-size: 11.5px; color: #2864C7;">
                        Similaridade Auxiliar: <b>{score_val:.1f}%</b>
                    </div>
                """, unsafe_allow_html=True)
            with col_row4:
                btn_key = f"btn_open_rec_{idx}"
                if st.button("Abrir ➔", key=btn_key, use_container_width=True):
                    if p_a and p_b:
                        st.session_state["selected_for_compare"] = [p_a, p_b]
                        st.session_state["active_doc_a"] = p_a
                        st.session_state["active_doc_b"] = p_b
                    if comp_item["resultado"]:
                        st.session_state["active_comparison_result"] = comp_item["resultado"]
                    if comp_item["relatorio_markdown"]:
                        st.session_state["active_executive_report"] = comp_item["relatorio_markdown"]
                    st.session_state["viewing_diff_idx"] = None
                    navigate_to("Comparações")
                    st.rerun()
            st.markdown("<hr style='border:none; border-top:1px solid #E2E8F0; margin:8px 0;'/>", unsafe_allow_html=True)
    else:
        render_empty_state(
            title="Nenhum histórico de análise disponível",
            description="Quando você processar e confrontar documentos, o registro de análises aparecerá aqui."
        )


def _render_profile_specific_section(
    profile: ProfileConfig,
    recent_comparisons: List[Dict[str, Any]],
    apolices: List[ApoliceDAO]
) -> None:
    """Renderiza uma seção adaptada ao perfil profissional selecionado (Requisito 6).

    A mesma informação analítica é reorganizada e priorizada conforme as necessidades do cargo.
    """
    pid = profile.id

    if pid == "analista":
        st.markdown("#### 🔍 Visão do Analista Técnico: Granularidade & Evidências")
        st.caption("Priorização de cláusulas divergentes, redação integral e parâmetros escalares:")

        col_an1, col_an2 = st.columns(2)
        with col_an1:
            st.markdown("""
                <div style="background:#FFFFFF; border:1px solid #D9E1E8; border-radius:8px; padding:14px; font-size:12.5px;">
                    <b style="color:#12304A;">Critérios de Alta Prioridade:</b>
                    <ul style="margin:6px 0 0 16px; padding:0; color:#475569;">
                        <li>Alterações de Condição Prévia (prazos e requisitos de aviso)</li>
                        <li>Alterações de Escopo e Sublimites Financeiros</li>
                        <li>Confronto literal página a página via IBM Plex Mono</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)
        with col_an2:
            st.markdown("""
                <div style="background:#FFFFFF; border:1px solid #D9E1E8; border-radius:8px; padding:14px; font-size:12.5px;">
                    <b style="color:#12304A;">Ações Recomendadas para Analistas:</b>
                    <ul style="margin:6px 0 0 16px; padding:0; color:#475569;">
                        <li>Confrontar trechos literais no painel de evidências auditáveis</li>
                        <li>Verificar integridade do número de processo SUSEP e LMG</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)

    elif pid == "subscritor":
        st.markdown("#### ⚖️ Visão do Subscritor / Underwriter: Exposição & Risco Contratual")
        st.caption("Foco imediato nas restrições de garantias, exclusões particulares e alterações de escopo:")

        col_sub1, col_sub2 = st.columns(2)
        with col_sub1:
            st.markdown("""
                <div style="background:#FFFFFF; border:1px solid #D9E1E8; border-left:4px solid #D94A4A; border-radius:8px; padding:14px; font-size:12.5px;">
                    <b style="color:#D94A4A;">Pontos Críticos de Subscrição:</b>
                    <ul style="margin:6px 0 0 16px; padding:0; color:#475569;">
                        <li>Cláusula 18.6.1 — Agravamento do Risco (Sompo v1.5)</li>
                        <li>Custos de Defesa — Adiantamento vs Reembolso prévio</li>
                        <li>Despesas de Contenção e Salvamento (Chubb 2025)</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)
        with col_sub2:
            st.markdown("""
                <div style="background:#FFFFFF; border:1px solid #D9E1E8; border-radius:8px; padding:14px; font-size:12.5px;">
                    <b style="color:#12304A;">Monitoramento de Limites:</b>
                    <ul style="margin:6px 0 0 16px; padding:0; color:#475569;">
                        <li>LMG máximo contratado vs Retenção / Franquia</li>
                        <li>Âmbito Territorial e Extensão Jurisdicional</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)

    elif pid == "corretor":
        st.markdown("#### 🤝 Visão do Corretor de Seguros: Confronto Contratual e Coberturas Exclusivas")
        st.caption("Destaque para garantias exclusivas, coberturas ampliadas e diferenciais técnicos para apresentação ao cliente:")

        col_cor1, col_cor2 = st.columns(2)
        with col_cor1:
            st.markdown("""
                <div style="background:#FFFFFF; border:1px solid #D9E1E8; border-left:4px solid #197B5C; border-radius:8px; padding:14px; font-size:12.5px;">
                    <b style="color:#197B5C;">Diferenciais Técnicos e Coberturas (Documento B):</b>
                    <ul style="margin:6px 0 0 16px; padding:0; color:#475569;">
                        <li>Coberturas adicionadas sem contrapartida de franquia</li>
                        <li>Escopo de garantia ampliado em termos de indenização</li>
                        <li>Parecer executivo estruturado para apresentação técnica ao cliente</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)
        with col_cor2:
            st.markdown("""
                <div style="background:#FFFFFF; border:1px solid #D9E1E8; border-radius:8px; padding:14px; font-size:12.5px;">
                    <b style="color:#12304A;">Dossiê Executivo:</b>
                    <p style="margin:6px 0 0 0; color:#475569;">
                        Exporte relatórios narrativos formatados para reuniões com administradores e conselhos fiscais.
                    </p>
                </div>
            """, unsafe_allow_html=True)

    elif pid == "juridico":
        st.markdown("#### 🏛️ Visão do Jurídico & Compliance: Aderência Regulatória SUSEP")
        st.caption("Confronto normativo com foco em litígios potenciais, boa-fé e validade das cláusulas restritivas:")

        col_jur1, col_jur2 = st.columns(2)
        with col_jur1:
            st.markdown("""
                <div style="background:#FFFFFF; border:1px solid #D9E1E8; border-left:4px solid #7E22CE; border-radius:8px; padding:14px; font-size:12.5px;">
                    <b style="color:#7E22CE;">Aderência a Circulares SUSEP:</b>
                    <ul style="margin:6px 0 0 16px; padding:0; color:#475569;">
                        <li>Validade de cláusula resolutiva expressa por inadimplemento (16.10)</li>
                        <li>Prazos de prescrição e decadência na regulação de sinistros</li>
                        <li>Rastreabilidade de metadados das evidências textuais</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)
        with col_jur2:
            st.markdown("""
                <div style="background:#FFFFFF; border:1px solid #D9E1E8; border-radius:8px; padding:14px; font-size:12.5px;">
                    <b style="color:#12304A;">Cadeia de Custódia Auditável:</b>
                    <p style="margin:6px 0 0 0; color:#475569;">
                        Cada diferença semântica possui hash criptográfico do documento de origem e indicação exata da página.
                    </p>
                </div>
            """, unsafe_allow_html=True)

    else:  # visitante
        st.markdown("#### 🌐 Guia de Primeiros Passos no InsurMinds")
        st.caption("Visão panorâmica para explorar a plataforma analítica de apólices D&O:")

        col_vis1, col_vis2 = st.columns(2)
        with col_vis1:
            st.markdown("""
                <div style="background:#FFFFFF; border:1px solid #D9E1E8; border-radius:8px; padding:14px; font-size:12.5px;">
                    <b style="color:#12304A;">Como Funciona o Analisador:</b>
                    <ol style="margin:6px 0 0 16px; padding:0; color:#475569;">
                        <li>Envie dois documentos PDF na aba <b>Nova análise</b></li>
                        <li>Aguarde a extração canônica estruturada (Agentes 1 a 4)</li>
                        <li>Explore a matriz de confronto A × B com evidências literais</li>
                    </ol>
                </div>
            """, unsafe_allow_html=True)
        with col_vis2:
            st.markdown("""
                <div style="background:#FFFFFF; border:1px solid #D9E1E8; border-radius:8px; padding:14px; font-size:12.5px;">
                    <b style="color:#12304A;">Casos Prontos para Teste:</b>
                    <p style="margin:6px 0 0 0; color:#475569;">
                        Você pode carregar em 1 clique os pares oficiais da <b>Sompo Seguros</b> ou <b>Chubb Seguros</b> através do menu <b>Nova análise</b>.
                    </p>
                </div>
            """, unsafe_allow_html=True)
