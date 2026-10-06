"""Página de Comparação Analítica de Apólices D&O — Insurance Intelligence v1.0.
Signature Screen do Produto: "O que mudou? → Como mudou? → Onde está a prova?".
Apresenta o confronto estruturado A ⟷ B com progressive disclosure em 3 níveis:
- Nível 1: Resumo da alteração e classificação semântica
- Nível 2: Comparação A/B lado a lado
- Nível 3: Evidência contratual completa com metadados e rastreabilidade documental.
"""
from typing import List, Dict, Any, Optional
import streamlit as st
import pandas as pd

from core.database import db
from core.schemas import ApoliceDAO, ComparisonResult, SemanticMatchItem, FieldDiff, EvidenceItem
from core.config import GEMINI_MODEL
from core.llm_client import llm_client
from agents.graph import run_comparison_pipeline_with_progress
from ui.navigation import navigate_to
from ui.persona.profiles import get_active_profile
from ui.tokens import COLORS, TYPOGRAPHY, RADIUS, SHADOWS
from ui.styles import render_html
from ui.components.badges import (
    SEMANTIC_RELATION_CONFIG,
    render_semantic_badge,
    render_status_badge
)
from ui.components.cards import render_metric_card
from ui.components.evidence import render_evidence_panel, render_evidence_snippet_html
from ui.components.states import (
    render_alert,
    render_empty_state,
    render_success_state,
    render_error_state,
    render_fallback_state
)
from ui.page_upload import render_structured_doc_card
from ui.page_detail import render_detail_page

# Aviso Legal Obrigatório (Preservado para conformidade com Requisito 10 e suíte de testes)
MANDATORY_DISCLAIMER = "A análise é assistida por IA e não substitui a avaliação jurídica, técnica ou de subscrição."


def render_compare_page():
    """Renderiza a experiência central de Comparação Contratual D&O."""
    viewing_diff_idx = st.session_state.get("viewing_diff_idx")
    is_detail_view = viewing_diff_idx is not None
    title_text = "DETALHE DA DIFERENÇA" if is_detail_view else "COMPARAÇÃO"
    subtitle_text = (
        "Auditoria minuciosa de cláusula contratual: Como mudou? → Onde está a prova?"
        if is_detail_view else
        "Visualize o que mudou entre os documentos e consulte a evidência correspondente."
    )

    # 1. CABEÇALHO EDITORIAL
    render_html(f"""
        <div style="margin-bottom: 16px;">
            <h2 style="color:{COLORS.PRIMARY_NAVY}; font-size:24px; font-weight:700; margin:0 0 6px 0; font-family:{TYPOGRAPHY.FONT_UI};">
                {title_text}
            </h2>
            <p style="color:{COLORS.TEXT_MUTED}; font-size:14px; margin:0; font-family:{TYPOGRAPHY.FONT_UI}; line-height:1.5;">
                {subtitle_text}
            </p>
        </div>
    """)

    # Aviso Legal Obrigatório
    render_html(f"""
        <div class="disclaimer-banner">
            🛡️ <strong>Aviso Legal Obrigatório:</strong> {MANDATORY_DISCLAIMER}
        </div>
    """)

    # Status do Motor Analítico / Fallback
    if llm_client.is_available():
        render_html(f"""
            <div style="display:inline-flex; align-items:center; gap:8px; background:#EFF6FF; border:1px solid #BFDBFE; padding:5px 14px; border-radius:20px; font-size:12px; color:#1E40AF; margin-bottom:16px;">
                <span style="width:7px; height:7px; border-radius:50%; background:#2563EB;"></span>
                <b>Motor de IA Ativo:</b> Google Gemini (<code>{GEMINI_MODEL}</code>) · Análise semântica e Structured Output em tempo real.
            </div>
        """)
    else:
        render_fallback_state("Modo de contingência ativo — análise utilizando regras determinísticas regulatórias da SUSEP.")

    # 12. ESTADO VAZIO: Validação de Apólices Disponíveis no Repositório
    todas_apolices = db.list_apolices()
    if len(todas_apolices) < 2:
        render_empty_state(
            title="Não há documentos suficientes para comparação.",
            description="São necessárias pelo menos duas apólices D&O cadastradas no repositório para iniciar o confronto contratual.",
            action_label="Iniciar Nova Análise ➔",
            action_callback=lambda: navigate_to("Nova análise")
        )
        return

    # Recuperação ou Seleção Ativa dos Documentos A e B
    selected = st.session_state.get("selected_for_compare", [])
    if len(selected) != 2:
        selected = todas_apolices[:2]
        st.session_state["selected_for_compare"] = selected

    pol_a = selected[0]
    pol_b = selected[1]

    # Identificação Compacta dos Documentos A e B
    _render_compact_document_header(pol_a, pol_b, todas_apolices)

    if pol_a.id == pol_b.id:
        render_html(f"""
            <div style="background:#FEF3C7; border:1px solid #FCD34D; border-radius:6px; padding:10px 14px; font-size:13px; color:#92400E; margin-bottom:16px;">
                ⚠️ <b>Atenção:</b> O mesmo documento foi selecionado para A e B. Escolha contratos distintos para avaliar alterações reais.
            </div>
        """)

    # Execução ou Recuperação da Comparação
    comp_result, report_md = _get_or_run_comparison(pol_a, pol_b)
    if comp_result:
        st.session_state["active_comparison_result"] = comp_result
        st.session_state["active_executive_report"] = report_md

    if not comp_result:
        # 11. ESTADO DE ERRO
        render_error_state(
            title="O processamento não pôde ser concluído.",
            error_message="Não foi possível gerar a matriz comparativa entre os dois documentos selecionados."
        )
        with st.expander("Ver detalhes técnicos do erro", expanded=False):
            st.code("Falha ao recuperar ComparisonResult no pipeline de comparação.")
        return

    active_profile = get_active_profile()

    # Roteamento Dedicado: Detalhe da Diferença (Fase 7.6)
    viewing_diff_idx = st.session_state.get("viewing_diff_idx")
    if viewing_diff_idx is None and "diff" in st.query_params:
        try:
            viewing_diff_idx = int(st.query_params.get("diff", 0))
        except (ValueError, TypeError):
            viewing_diff_idx = 0

    if viewing_diff_idx is not None:
        render_detail_page(comp_result, pol_a, pol_b, active_profile, item_idx=int(viewing_diff_idx))
        return

    # 2. RESUMO EXECUTIVO (Faixa Superior com Indicadores Factuais)
    _render_executive_summary_strip(comp_result)

    # 9. PERFIL DE TRABALHO & 3. BARRA DE CONTROLE (Filtros e Ordenação)
    selected_filter, selected_sort = _render_control_bar(comp_result, active_profile)

    # 4 & 6. ÁREA DE COMPARAÇÃO COM PRIORIZAÇÃO E PROGRESSIVE DISCLOSURE
    _render_comparison_content(comp_result, pol_a, pol_b, selected_filter, selected_sort, active_profile)

    # 15. NOTA METODOLÓGICA DO SCORE AUXILIAR
    _render_score_auxiliary_notice(comp_result.score_similaridade)

    # Navegação de Saída para o Relatório Narrativo
    st.markdown("---")
    col_rep_text, col_rep_btn = st.columns([3, 1.2])
    with col_rep_text:
        render_html(f"""
            <div style="font-size:13px; color:{COLORS.TEXT_MAIN};">
                <b>Deseja formalizar esta análise contratual?</b><br/>
                <span style="color:{COLORS.TEXT_MUTED};">Acesse o parecer executivo estruturado com cadeia de custódia e notas técnicas de subscrição.</span>
            </div>
        """)
    with col_rep_btn:
        st.button(
            "📄 Visualizar Relatório Completo ➔",
            type="primary",
            key="btn_go_to_report",
            on_click=navigate_to,
            args=("Relatórios",)
        )


def _render_compact_document_header(pol_a: ApoliceDAO, pol_b: ApoliceDAO, todas_apolices: List[ApoliceDAO]):
    """Exibe o cabeçalho compacto de identificação A ⟷ B com metadados e seletor recolhido."""
    render_html(f"""
        <div style="background:{COLORS.SURFACE}; border:1px solid {COLORS.BORDER}; border-radius:{RADIUS.MD}; padding:16px 20px; margin-bottom:18px; box-shadow:{SHADOWS.SM};">
            <div style="display:grid; grid-template-columns: 1fr auto 1fr; gap:20px; align-items:center;">
                <div style="border-right:1px solid #EDF2F7; padding-right:16px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                        <span style="font-size:11px; font-weight:700; text-transform:uppercase; color:{COLORS.PRIMARY_BLUE}; letter-spacing:0.5px;">Documento A · Referência</span>
                        <span style="font-size:11px; background:#EFF6FF; color:{COLORS.PRIMARY_BLUE}; padding:2px 8px; border-radius:4px; font-weight:600;">Base</span>
                    </div>
                    <div style="font-size:15px; font-weight:700; color:{COLORS.PRIMARY_NAVY}; margin-bottom:4px; word-break:break-all;">
                        {pol_a.nome_arquivo}
                    </div>
                    <div style="font-size:12px; color:{COLORS.TEXT_MUTED}; line-height:1.4;">
                        <b>Seguradora:</b> <span style="color:{COLORS.PRIMARY_BLUE}; font-weight:600;">{pol_a.seguradora or 'Não identificada'}</span> &nbsp;·&nbsp;
                        <b>SUSEP:</b> <span style="font-family:{TYPOGRAPHY.FONT_CODE};">{pol_a.processo_susep or 'N/A'}</span>
                    </div>
                </div>

                <div style="text-align:center; padding:0 8px;">
                    <span style="font-size:20px; color:{COLORS.PRIMARY_BLUE}; font-weight:800;">⟷</span>
                    <div style="font-size:10px; color:{COLORS.TEXT_MUTED}; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">Cotejo</div>
                </div>

                <div style="padding-left:16px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                        <span style="font-size:11px; font-weight:700; text-transform:uppercase; color:{COLORS.SECONDARY_TEAL}; letter-spacing:0.5px;">Documento B · Comparação</span>
                        <span style="font-size:11px; background:#F0FDFA; color:{COLORS.SECONDARY_TEAL}; padding:2px 8px; border-radius:4px; font-weight:600;">Confronto</span>
                    </div>
                    <div style="font-size:15px; font-weight:700; color:{COLORS.PRIMARY_NAVY}; margin-bottom:4px; word-break:break-all;">
                        {pol_b.nome_arquivo}
                    </div>
                    <div style="font-size:12px; color:{COLORS.TEXT_MUTED}; line-height:1.4;">
                        <b>Seguradora:</b> <span style="color:{COLORS.SECONDARY_TEAL}; font-weight:600;">{pol_b.seguradora or 'Não identificada'}</span> &nbsp;·&nbsp;
                        <b>SUSEP:</b> <span style="font-family:{TYPOGRAPHY.FONT_CODE};">{pol_b.processo_susep or 'N/A'}</span>
                    </div>
                </div>
            </div>
        </div>
    """)

    with st.expander("🔄 Alterar documentos sob confronto", expanded=False):
        opcoes = {f"{p.seguradora or 'Seguradora'} — {p.nome_arquivo}": p for p in todas_apolices}
        labels = list(opcoes.keys())

        idx_a = next((i for i, k in enumerate(labels) if opcoes[k].id == pol_a.id), 0)
        idx_b = next((i for i, k in enumerate(labels) if opcoes[k].id == pol_b.id), 1 if len(labels) > 1 else 0)

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            novo_a = st.selectbox("Documento de referência (A):", options=labels, index=idx_a, key="sel_comp_doc_a")
        with col_c2:
            novo_b = st.selectbox("Documento para comparação (B):", options=labels, index=idx_b, key="sel_comp_doc_b")

        if opcoes[novo_a].id != pol_a.id or opcoes[novo_b].id != pol_b.id:
            st.session_state["selected_for_compare"] = [opcoes[novo_a], opcoes[novo_b]]
            st.rerun()


def _get_or_run_comparison(pol_a: ApoliceDAO, pol_b: ApoliceDAO):
    """Recupera comparação em cache no banco ou executa o pipeline dos Agentes 5 e 6."""
    cached = db.get_comparison(pol_a.id, pol_b.id)
    if cached and "resultado" in cached:
        return cached["resultado"], cached.get("relatorio_markdown", "")

    with st.spinner("Confrontando cláusulas, calculando similaridade e estruturando evidências..."):
        comp_state = run_comparison_pipeline_with_progress(pol_a, pol_b)
        if comp_state and comp_state.diff_result:
            return comp_state.diff_result, comp_state.report_markdown
    return None, ""


def _render_executive_summary_strip(comp: ComparisonResult):
    """Renderiza a faixa superior com indicadores derivados APENAS dos dados existentes."""
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

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        render_metric_card(
            label="Diferenças Totais",
            value=f"{total_diferencas}",
            delta=f"{len(substantive_matches)} substantiva(s)",
            delta_type="attention" if len(substantive_matches) > 0 else "neutral",
            help_text="Total de alterações semânticas, divergências escalares e cláusulas exclusivas identificadas."
        )

    with col2:
        render_metric_card(
            label="Merecem Avaliação",
            value=f"{len(substantive_matches)}",
            delta="Revisão prioritária" if len(substantive_matches) > 0 else "Nenhuma crítica",
            delta_type="negative" if len(substantive_matches) > 0 else "positive",
            help_text="Cláusulas com alteração de escopo, condição de acionamento ou limites substanciais."
        )

    with col3:
        render_metric_card(
            label="Equivalências",
            value=f"{total_equivalencias}",
            delta="Efeitos convergentes",
            delta_type="positive",
            help_text="Cláusulas e parâmetros com redação ou efeitos substancialmente equivalentes em ambas as partes."
        )

    with col4:
        render_metric_card(
            label="Alterações de Escopo",
            value=f"{len(scope_matches)}",
            delta="Abrangência relativa",
            delta_type="neutral",
            help_text="Cláusulas onde o escopo de cobertura foi ampliado, reduzido ou modificado."
        )

    with col5:
        render_metric_card(
            label="Condições & Limites",
            value=f"{len(condition_matches) + len(limit_matches)}",
            delta="Prazos / Sublimites",
            delta_type="neutral",
            help_text="Modificações procedimentais, franquias, prazos ou sublimites financeiros alterados."
        )


def _render_control_bar(comp: ComparisonResult, active_profile):
    """Renderiza a barra de controle com filtros temáticos e ordenação respeitando o perfil ativo."""
    render_html("<div style='margin-top:20px;'></div>")

    default_filter_map = {
        "analista": "Todas",
        "subscritor": "Alterações que merecem avaliação",
        "corretor": "Garantias exclusivas",
        "juridico": "Alterações que merecem avaliação",
        "visitante": "Todas"
    }
    default_filter_choice = default_filter_map.get(active_profile.id, "Todas")

    filter_options = [
        "Todas",
        "Alterações que merecem avaliação",
        "Equivalentes",
        "Alterações de escopo",
        "Condições alteradas",
        "Limites alterados",
        "Garantias exclusivas",
        "Parâmetros gerais"
    ]

    col_flt, col_sort = st.columns([3, 1.2])

    with col_flt:
        initial_idx = filter_options.index(default_filter_choice) if default_filter_choice in filter_options else 0
        selected_filter = st.selectbox(
            "Filtro de Análise:",
            options=filter_options,
            index=initial_idx,
            key=f"comp_filter_select_{active_profile.id}",
            help="Filtre os itens comparativos por categoria semântica ou prioridade analítica."
        )

    with col_sort:
        sort_options = [
            "Relevância documental",
            "Categoria contratual",
            "Localização (Página)"
        ]
        selected_sort = st.selectbox(
            "Ordenar por:",
            options=sort_options,
            index=0,
            key="comp_sort_select",
            help="Ordenação visual dos itens comparados."
        )

    persona_notes = {
        "analista": "Visualização detalhada com foco em granularidade de cláusulas, rastreabilidade integral e equivalência técnica.",
        "subscritor": "Foco prioritário em alterações de escopo, condições prévias, sublimites e restrições contratuais.",
        "corretor": "Foco em confronto A/B, garantias exclusivas de cada documento e síntese executiva para tomada de decisão.",
        "juridico": "Foco em redação contratual literal, localização e circulares SUSEP, com cadeia de custódia auditada.",
        "visitante": "Visão panorâmica equilibrada para exploração institucional das diferenças contratuais D&O."
    }
    render_html(f"""
        <div style="font-size:12px; color:{COLORS.TEXT_MUTED}; margin:-6px 0 16px 2px;">
            <b>Perfil Ativo ({active_profile.label}):</b> {persona_notes.get(active_profile.id, '')}
        </div>
    """)

    return selected_filter, selected_sort


def _render_comparison_content(
    comp: ComparisonResult,
    pol_a: ApoliceDAO,
    pol_b: ApoliceDAO,
    selected_filter: str,
    selected_sort: str,
    active_profile
):
    """Renderiza os blocos comparativos organizados e com progressive disclosure em 3 níveis."""
    semantic_matches = comp.semantic_matches or []

    substantive_matches = [m for m in semantic_matches if m.relation in ("changed_scope", "changed_condition", "changed_limit", "different")]
    scope_matches = [m for m in semantic_matches if m.relation in ("broader", "narrower")]
    equivalent_matches = [m for m in semantic_matches if m.relation == "semantic_equivalent"]

    has_exclusives = bool(
        comp.coberturas_exclusivas_a or comp.coberturas_exclusivas_b or
        comp.clausulas_especiais_exclusivas_a or comp.clausulas_especiais_exclusivas_b or
        comp.exclusoes_exclusivas_a or comp.exclusoes_exclusivas_b
    )

    items_to_render = []

    if selected_filter == "Todas":
        items_to_render = substantive_matches + scope_matches + equivalent_matches
    elif selected_filter == "Alterações que merecem avaliação":
        items_to_render = substantive_matches
    elif selected_filter == "Equivalentes":
        items_to_render = equivalent_matches
    elif selected_filter == "Alterações de escopo":
        items_to_render = [m for m in semantic_matches if m.relation in ("broader", "narrower", "changed_scope")]
    elif selected_filter == "Condições alteradas":
        items_to_render = [m for m in semantic_matches if m.relation == "changed_condition"]
    elif selected_filter == "Limites alterados":
        items_to_render = [m for m in semantic_matches if m.relation == "changed_limit"]
    elif selected_filter in ("Garantias exclusivas", "Parâmetros gerais"):
        items_to_render = []

    if selected_sort == "Relevância documental":
        relation_weight = {
            "changed_condition": 1,
            "changed_scope": 2,
            "changed_limit": 3,
            "different": 4,
            "broader": 5,
            "narrower": 6,
            "semantic_equivalent": 7
        }
        items_to_render.sort(key=lambda m: relation_weight.get(m.relation, 9))
    elif selected_sort == "Localização (Página)":
        items_to_render.sort(key=lambda m: (m.page_a or 999, m.page_b or 999))
    elif selected_sort == "Categoria contratual":
        items_to_render.sort(key=lambda m: m.item_a.split(":")[0])

    # 6. SEÇÃO PRINCIPAL: ALTERAÇÕES QUE MERECEM AVALIAÇÃO
    if selected_filter in ("Todas", "Alterações que merecem avaliação") and substantive_matches:
        render_html(f"""
            <div style="display:flex; align-items:center; gap:8px; margin:24px 0 8px 0;">
                <h3 style="margin:0; font-size:16px; font-weight:700; color:{COLORS.PRIMARY_NAVY};">
                    🚨 Alterações que Merecem Avaliação
                </h3>
                <span style="font-size:11px; background:#FEF2F2; color:{COLORS.CRITICAL}; border:1px solid #FECACA; padding:2px 8px; border-radius:12px; font-weight:700;">
                    {len(substantive_matches)} item(ns)
                </span>
            </div>
            <p style="margin:0 0 14px 0; font-size:12.5px; color:{COLORS.TEXT_MUTED};">
                Cláusulas com o mesmo conceito securitário que apresentam modificações substanciais em obrigações, prazos, limites ou escopo de indenização:
            </p>
        """)

        for idx, match in enumerate(substantive_matches):
            m_idx = comp.semantic_matches.index(match) if match in comp.semantic_matches else idx
            _render_comparative_item_card(match, idx, pol_a, pol_b, is_substantive=True, match_index=m_idx)

    # SEÇÃO: OUTRAS ALTERAÇÕES OU ITENS FILTRADOS
    if selected_filter not in ("Todas", "Alterações que merecem avaliação", "Garantias exclusivas", "Parâmetros gerais"):
        if items_to_render:
            render_html(f"""
                <div style="margin:20px 0 12px 0;">
                    <h3 style="margin:0; font-size:15px; font-weight:700; color:{COLORS.PRIMARY_NAVY};">
                        Resultados do Filtro: {selected_filter} ({len(items_to_render)} itens)
                    </h3>
                </div>
            """)
            for idx, match in enumerate(items_to_render):
                m_idx = comp.semantic_matches.index(match) if match in comp.semantic_matches else idx
                _render_comparative_item_card(match, 100 + idx, pol_a, pol_b, match_index=m_idx)
        else:
            # 10. ESTADO SEM DIFERENÇAS NO FILTRO
            render_html(f"""
                <div style="background:#F8FAFC; border:1px solid {COLORS.BORDER}; border-radius:{RADIUS.MD}; padding:24px; text-align:center; margin:16px 0;">
                    <div style="font-size:22px; color:{COLORS.TEXT_MUTED}; margin-bottom:6px;">✓</div>
                    <div style="font-size:14px; font-weight:600; color:{COLORS.PRIMARY_NAVY};">
                        Não foram identificadas diferenças relevantes nos itens analisados para o filtro "{selected_filter}".
                    </div>
                    <div style="font-size:12.5px; color:{COLORS.TEXT_MUTED}; margin-top:4px;">
                        Alterne para outro filtro na barra de controle acima para visualizar outras cláusulas.
                    </div>
                </div>
            """)

    elif selected_filter == "Todas":
        # Seção de Escopo Relativo
        if scope_matches:
            render_html(f"""
                <div style="display:flex; align-items:center; gap:8px; margin:28px 0 8px 0;">
                    <h3 style="margin:0; font-size:15px; font-weight:700; color:{COLORS.PRIMARY_NAVY};">
                        ⚖️ Diferenças de Abrangência e Escopo Relativo
                    </h3>
                    <span style="font-size:11px; background:#EFF6FF; color:{COLORS.PRIMARY_BLUE}; padding:2px 8px; border-radius:12px; font-weight:600;">
                        {len(scope_matches)} item(ns)
                    </span>
                </div>
                <p style="margin:0 0 14px 0; font-size:12.5px; color:{COLORS.TEXT_MUTED};">
                    Cláusulas onde uma das partes prevê redação abrangente e a outra adota modalidade restrita ou qualificada:
                </p>
            """)
            for idx, match in enumerate(scope_matches):
                m_idx = comp.semantic_matches.index(match) if match in comp.semantic_matches else idx
                _render_comparative_item_card(match, 200 + idx, pol_a, pol_b, match_index=m_idx)

        # Seção de Equivalências
        if equivalent_matches:
            render_html(f"""
                <div style="display:flex; align-items:center; gap:8px; margin:28px 0 8px 0;">
                    <h3 style="margin:0; font-size:15px; font-weight:700; color:{COLORS.PRIMARY_NAVY};">
                        🟢 Cláusulas com Efeitos Contratuais Equivalentes
                    </h3>
                    <span style="font-size:11px; background:#E6F4EA; color:{COLORS.SUCCESS}; padding:2px 8px; border-radius:12px; font-weight:600;">
                        {len(equivalent_matches)} item(ns)
                    </span>
                </div>
                <p style="margin:0 0 14px 0; font-size:12.5px; color:{COLORS.TEXT_MUTED};">
                    Garantias com redação e amplitude substancialmente equivalentes em ambos os documentos:
                </p>
            """)
            for idx, match in enumerate(equivalent_matches):
                m_idx = comp.semantic_matches.index(match) if match in comp.semantic_matches else idx
                _render_comparative_item_card(match, 300 + idx, pol_a, pol_b, match_index=m_idx)

    # SEÇÃO: GARANTIAS E CLÁUSULAS EXCLUSIVAS (Se selecionada ou no modo Geral)
    if selected_filter in ("Todas", "Garantias exclusivas") and has_exclusives:
        _render_exclusive_items_section(comp, pol_a, pol_b)

    # SEÇÃO: MATRIZ DE PARÂMETROS ESCALARES
    if selected_filter in ("Todas", "Parâmetros gerais"):
        _render_scalar_parameters_matrix(comp, pol_a, pol_b)


def _render_comparative_item_card(
    match: SemanticMatchItem,
    idx: int,
    pol_a: ApoliceDAO,
    pol_b: ApoliceDAO,
    is_substantive: bool = False,
    match_index: Optional[int] = None
):
    """Renderiza um item comparativo com os 3 níveis de Progressive Disclosure (Wireframe 03 e 04)."""
    title_a = match.item_a.split(":")[0].strip()
    title_b = match.item_b.split(":")[0].strip()
    display_title = title_a if title_a == title_b else f"{title_a} ⟷ {title_b}"

    ev_a_obj = pol_a.evidencias.get(title_a) if pol_a.evidencias else None
    ev_b_obj = pol_b.evidencias.get(title_b) if pol_b.evidencias else None

    page_a = match.page_a or (ev_a_obj.page if ev_a_obj else None)
    page_b = match.page_b or (ev_b_obj.page if ev_b_obj else None)

    page_a_str = f"Pág. {page_a}" if page_a else "Pág. não indicada"
    page_b_str = f"Pág. {page_b}" if page_b else "Pág. não indicada"

    badge_html = render_semantic_badge(match.relation)
    conf_pct = int(match.confidence * 100)

    category = "COBERTURAS & GARANTIAS D&O"
    if "exclus" in title_a.lower() or "polui" in title_a.lower() or "dolo" in title_a.lower():
        category = "EXCLUSÕES CONTRATUAIS"
    elif "prêmio" in title_a.lower() or "vigência" in title_a.lower() or "franquia" in title_a.lower():
        category = "CONDIÇÕES GERAIS E OPERACIONAIS"

    border_color = COLORS.CRITICAL if is_substantive else (
        COLORS.PRIMARY_BLUE if match.relation in ("narrower", "broader") else (
            COLORS.SUCCESS if match.relation == "semantic_equivalent" else COLORS.BORDER
        )
    )

    # NÍVEL 1 & NÍVEL 2: Resumo + Comparação A/B
    render_html(f"""
        <div class="im-difference-card" style="border-left:4px solid {border_color}; margin-bottom:12px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:10px; font-weight:700; text-transform:uppercase; color:{COLORS.TEXT_MUTED}; letter-spacing:0.5px;">
                        {category}
                    </span>
                    <span style="color:#D1D5DB;">·</span>
                    {badge_html}
                </div>
                <div style="font-size:11.5px; color:{COLORS.TEXT_MUTED};">
                    Confiança analítica: <b style="color:{COLORS.PRIMARY_NAVY};">{conf_pct}%</b>
                </div>
            </div>

            <h4 style="margin:2px 0 6px 0; font-size:15px; font-weight:700; color:{COLORS.PRIMARY_NAVY};">
                {display_title}
            </h4>

            <div class="im-diff-explanation" style="margin-bottom:12px;">
                <b>Interpretação assistida:</b> {match.explanation}
            </div>

            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; background:#F8FAFC; border:1px solid {COLORS.BORDER}; border-radius:6px; padding:12px 14px; font-size:12.5px;">
                <div>
                    <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                        <span style="font-weight:700; color:{COLORS.PRIMARY_BLUE}; font-size:11px; text-transform:uppercase;">
                            Documento A ({pol_a.seguradora or 'Referência'})
                        </span>
                        <span class="im-page-tag">{page_a_str}</span>
                    </div>
                    <div style="font-weight:600; color:{COLORS.PRIMARY_NAVY}; margin-bottom:4px;">{title_a}</div>
                    <div style="font-size:12px; color:{COLORS.TEXT_MAIN}; line-height:1.4;">
                        "{match.item_a[:140]}..."
                    </div>
                </div>

                <div style="border-left:1px solid #E2E8F0; padding-left:12px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                        <span style="font-weight:700; color:{COLORS.SECONDARY_TEAL}; font-size:11px; text-transform:uppercase;">
                            Documento B ({pol_b.seguradora or 'Comparação'})
                        </span>
                        <span class="im-page-tag">{page_b_str}</span>
                    </div>
                    <div style="font-weight:600; color:{COLORS.PRIMARY_NAVY}; margin-bottom:4px;">{title_b}</div>
                    <div style="font-size:12px; color:{COLORS.TEXT_MAIN}; line-height:1.4;">
                        "{match.item_b[:140]}..."
                    </div>
                </div>
            </div>
        </div>
    """)

    # NÍVEL 3: Evidência Completa com Metadados (Auditável e Rastreável) + Ação de Detalhe
    snippet_a = match.evidence_a or (ev_a_obj.snippet if ev_a_obj else None) or match.item_a
    snippet_b = match.evidence_b or (ev_b_obj.snippet if ev_b_obj else None) or match.item_b

    col_card_exp, col_card_btn = st.columns([3.2, 1.2])
    with col_card_exp:
        with st.expander(f"🔍 Ver Evidência Contratual Completa: {title_a} × {title_b}", expanded=False):
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
            st.caption(
                "ℹ️ **Cadeia de Custódia Documental:** Trechos extraídos literalmente do conteúdo binário digital dos arquivos PDF. "
                "A interpretação é assistida pelo modelo e deve ser revisada pelo profissional habilitado."
            )
    with col_card_btn:
        target_idx = match_index if match_index is not None else (idx % 100)
        if st.button("🔍 Auditar Detalhe ➔", key=f"btn_go_detail_{idx}", help="Acessar tela completa de auditoria com confronto literal e notas técnicas"):
            st.session_state["viewing_diff_idx"] = target_idx
            st.rerun()


def _render_exclusive_items_section(comp: ComparisonResult, pol_a: ApoliceDAO, pol_b: ApoliceDAO):
    """Exibe itens e garantias presentes exclusivamente no Documento A ou no Documento B."""
    render_html(f"""
        <div style="margin:28px 0 10px 0;">
            <h3 style="margin:0 0 4px 0; font-size:16px; font-weight:700; color:{COLORS.PRIMARY_NAVY};">
                📋 Cláusulas & Garantias Exclusivas de Cada Documento
            </h3>
            <p style="margin:0; font-size:12.5px; color:{COLORS.TEXT_MUTED};">
                Garantias e cláusulas identificadas em apenas um dos documentos contratados:
            </p>
        </div>
    """)

    all_excl_a = comp.coberturas_exclusivas_a + comp.clausulas_especiais_exclusivas_a
    all_excl_b = comp.coberturas_exclusivas_b + comp.clausulas_especiais_exclusivas_b

    col_a_box, col_b_box = st.columns(2)

    with col_a_box:
        render_html(f"""
            <div style="background:{COLORS.SURFACE}; border:1px solid {COLORS.BORDER}; border-top:3px solid {COLORS.PRIMARY_BLUE}; border-radius:{RADIUS.MD}; padding:14px 16px; height:100%;">
                <div style="font-size:12px; font-weight:700; color:{COLORS.PRIMARY_BLUE}; text-transform:uppercase; margin-bottom:8px;">
                    Exclusivas em {pol_a.seguradora or 'Documento A'} ({len(all_excl_a)} itens)
                </div>
        """)

        if all_excl_a:
            for item in all_excl_a:
                ev = pol_a.evidencias.get(item.split(":")[0].strip()) if pol_a.evidencias else None
                page_info = f" · Pág. {ev.page}" if ev and ev.page else ""
                render_html(f"""
                    <div style="background:#F8FAFC; border:1px solid {COLORS.BORDER}; border-radius:4px; padding:8px 10px; margin-bottom:6px; font-size:12px;">
                        <b style="color:{COLORS.PRIMARY_NAVY};">+ {item.split(':')[0]}</b>
                        <span style="color:{COLORS.TEXT_MUTED}; font-size:11px;">{page_info}</span>
                    </div>
                """)
        else:
            render_html(f"<div style='font-size:12px; color:{COLORS.TEXT_MUTED};'>_Nenhuma cobertura exclusiva identificada nesta apólice._</div>")

        render_html("</div>")

    with col_b_box:
        render_html(f"""
            <div style="background:{COLORS.SURFACE}; border:1px solid {COLORS.BORDER}; border-top:3px solid {COLORS.SECONDARY_TEAL}; border-radius:{RADIUS.MD}; padding:14px 16px; height:100%;">
                <div style="font-size:12px; font-weight:700; color:{COLORS.SECONDARY_TEAL}; text-transform:uppercase; margin-bottom:8px;">
                    Exclusivas em {pol_b.seguradora or 'Documento B'} ({len(all_excl_b)} itens)
                </div>
        """)

        if all_excl_b:
            for item in all_excl_b:
                ev = pol_b.evidencias.get(item.split(":")[0].strip()) if pol_b.evidencias else None
                page_info = f" · Pág. {ev.page}" if ev and ev.page else ""
                render_html(f"""
                    <div style="background:#F8FAFC; border:1px solid {COLORS.BORDER}; border-radius:4px; padding:8px 10px; margin-bottom:6px; font-size:12px;">
                        <b style="color:{COLORS.PRIMARY_NAVY};">+ {item.split(':')[0]}</b>
                        <span style="color:{COLORS.TEXT_MUTED}; font-size:11px;">{page_info}</span>
                    </div>
                """)
        else:
            render_html(f"<div style='font-size:12px; color:{COLORS.TEXT_MUTED};'>_Nenhuma cobertura exclusiva identificada nesta apólice._</div>")

        render_html("</div>")


def _render_scalar_parameters_matrix(comp: ComparisonResult, pol_a: ApoliceDAO, pol_b: ApoliceDAO):
    """Renderiza a matriz comparativa de parâmetros escalares (LMG, franquia, vigência, etc.)."""
    render_html(f"""
        <div style="margin:28px 0 10px 0;">
            <h3 style="margin:0 0 4px 0; font-size:16px; font-weight:700; color:{COLORS.PRIMARY_NAVY};">
                📊 Parâmetros Contratuais Escalares
            </h3>
            <p style="margin:0; font-size:12.5px; color:{COLORS.TEXT_MUTED};">
                Confronto objetivo de limites financeiros, franquias, prazos de vigência e âmbitos territoriais:
            </p>
        </div>
    """)

    dados_tabela = []
    for d in comp.diffs:
        status_rotulo = "🟢 Equivalente" if not d.ha_diferenca else (
            "🟡 Divergente" if d.tipo_diferenca == "diferente" else (
                "⚪ Ausente em ambas" if d.tipo_diferenca == "ambos_ausentes" else "⚠️ Ausente em uma"
            )
        )
        dados_tabela.append({
            "Parâmetro": d.rotulo,
            "Categoria": d.categoria,
            f"Doc A: {pol_a.seguradora or 'Referência'}": d.valor_apolice_a or "Não informado",
            f"Doc B: {pol_b.seguradora or 'Comparação'}": d.valor_apolice_b or "Não informado",
            "Status": status_rotulo,
            "Explicação": d.explicacao
        })

    df_diffs = pd.DataFrame(dados_tabela)
    st.dataframe(df_diffs, use_container_width=True, hide_index=True)


def _render_score_auxiliary_notice(score: float):
    """Renderiza o indicador de similaridade com disclaimer estritamente factual e neutro."""
    render_html(f"""
        <div style="background:{COLORS.SURFACE}; border:1px solid {COLORS.BORDER}; border-radius:{RADIUS.MD}; padding:14px 18px; margin:24px 0 10px 0; box-shadow:{SHADOWS.SM};">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <div style="font-size:13px; font-weight:700; color:{COLORS.PRIMARY_NAVY};">
                    📐 Índice de Similaridade Estrutural (Indicador Técnico Auxiliar)
                </div>
                <div style="font-size:15px; font-weight:800; color:{COLORS.PRIMARY_BLUE}; font-family:{TYPOGRAPHY.FONT_CODE};">
                    {score:.1f}%
                </div>
            </div>
            <div style="font-size:12px; color:{COLORS.TEXT_MUTED}; line-height:1.5;">
                <b>Nota Metodológica Obrigatória:</b> O índice de similaridade é calculado por distância de Jaccard e similaridade semântica entre tokens contratuais.
                Reflete unicamente o grau de aderência léxica e taxonômica entre as redações. <b>Não constitui recomendação de contratação</b>, nota de mérito, aprovação jurídica ou atribuição de benefício unilateral.
            </div>
        </div>
    """)
