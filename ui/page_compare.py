"""Página 3: Comparação Analítica de Apólices.
Apresenta a matriz comparativa de campos, scorecard de similaridade global e detecção de assimetrias de cobertura.
Padrão executivo de subscrição de riscos e resseguro.
"""
import streamlit as st
import pandas as pd
from core.database import db
from agents.graph import run_comparison_pipeline_with_progress


def render_compare_page():
    """Renderiza o painel analítico de confronto e o score de similaridade."""
    st.markdown("### ⚖️ Matriz Analítica de Confronto Contratual D&O")
    st.write(
        "Auditoria comparativa campo a campo, detecção de assimetrias em limites, franquias, "
        "retroatividade e identificação de lacunas de cobertura (Gap Analysis)."
    )

    # Recupera apólices selecionadas na sessão
    selected = st.session_state.get("selected_for_compare", [])
    if len(selected) < 2:
        todas = db.list_apolices()
        if len(todas) >= 2:
            selected = todas[:2]
            st.session_state["selected_for_compare"] = selected
        else:
            st.warning("⚠️ Selecione pelo menos 2 apólices na Biblioteca para realizar o confronto.")
            if st.button("Ir para a Biblioteca", type="primary"):
                st.session_state["nav_page"] = "Biblioteca"
                st.rerun()
            return

    pol_a, pol_b = selected[0], selected[1]

    # Executa ou recupera a comparação
    cached_comp = db.get_comparison(pol_a.id, pol_b.id)
    if cached_comp and "resultado" in cached_comp:
        comp_result = cached_comp["resultado"]
        report_md = cached_comp.get("relatorio_markdown", "")
    else:
        with st.spinner("Executando Agente 5 (Comparator) e Agente 6 (Reporter)..."):
            comp_state = run_comparison_pipeline_with_progress(pol_a, pol_b)
            comp_result = comp_state.diff_result
            report_md = comp_state.report_markdown

    st.session_state["active_report_markdown"] = report_md
    st.session_state["active_comparison_result"] = comp_result

    # 1. Header do Confronto e Scorecards Executivos
    st.markdown(f"#### Confrontando: **{pol_a.seguradora}** × **{pol_b.seguradora}**")

    score = comp_result.score_similaridade
    total_campos = len(comp_result.diffs)
    campos_iguais = sum(1 for d in comp_result.diffs if not d.ha_diferenca)
    campos_divergentes = total_campos - campos_iguais

    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    with col_kpi1:
        st.metric(
            label="Índice de Similaridade",
            value=f"{score:.1f}%",
            delta="Alta Aderência" if score >= 75 else ("Aderência Média" if score >= 50 else "Divergência Crítica"),
            delta_color="normal" if score >= 75 else "off"
        )
    with col_kpi2:
        st.metric(
            label="Convergência Contratual",
            value=f"{campos_iguais} / {total_campos}",
            delta=f"{campos_divergentes} divergência(s)",
            delta_color="off" if campos_divergentes > 0 else "normal"
        )
    with col_kpi3:
        total_exclusivas = len(comp_result.coberturas_exclusivas_a) + len(comp_result.coberturas_exclusivas_b)
        st.metric(
            label="Assimetrias de Cobertura",
            value=f"{total_exclusivas} cláusula(s)",
            delta="Lacunas detectadas" if total_exclusivas > 0 else "Coberturas simétricas",
            delta_color="off" if total_exclusivas > 0 else "normal"
        )

    st.progress(score / 100.0)
    st.markdown("---")

    # 2. Matriz Comparativa Campo a Campo
    st.markdown("#### 📊 Matriz Comparativa de Condições Gerais")

    dados_tabela = []
    for d in comp_result.diffs:
        status_tag = "🟢 EQUIVALENTE" if not d.ha_diferenca else "🟡 DIVERGENTE"
        dados_tabela.append({
            "Parâmetro Analisado": d.rotulo,
            f"Proposta 1: {pol_a.seguradora or 'Apólice A'}": d.valor_apolice_a or "Não informado",
            f"Proposta 2: {pol_b.seguradora or 'Apólice B'}": d.valor_apolice_b or "Não informado",
            "Classificação": status_tag
        })

    df_diffs = pd.DataFrame(dados_tabela)
    st.dataframe(df_diffs, use_container_width=True, hide_index=True)

    st.markdown("---")

    # 3. Análise Diferencial de Coberturas (Gap Analysis)
    st.markdown("#### 🛡️ Análise Diferencial de Coberturas (Gap Analysis)")
    st.caption("Identificação de cláusulas oferecidas exclusivamente por uma das companhias seguradoras.")
    col_cob_a, col_cob_b = st.columns(2)

    with col_cob_a:
        st.markdown(f"**Garantias Exclusivas — {pol_a.seguradora}:**")
        if comp_result.coberturas_exclusivas_a:
            for c in comp_result.coberturas_exclusivas_a:
                st.markdown(f"""<div class="coverage-box"><b>+ {c}</b></div>""", unsafe_allow_html=True)
        else:
            st.info("Nenhuma cobertura exclusiva identificada nesta proposta.")

    with col_cob_b:
        st.markdown(f"**Garantias Exclusivas — {pol_b.seguradora}:**")
        if comp_result.coberturas_exclusivas_b:
            for c in comp_result.coberturas_exclusivas_b:
                st.markdown(f"""<div class="coverage-box"><b>+ {c}</b></div>""", unsafe_allow_html=True)
        else:
            st.info("Nenhuma cobertura exclusiva identificada nesta proposta.")

    with st.expander(f"🤝 Ver Coberturas em Comum Contratadas por Ambas ({len(comp_result.coberturas_comuns)})"):
        for c in comp_result.coberturas_comuns:
            st.caption(f"• {c}")

    # 4. Análise Diferencial de Exclusões
    st.markdown("---")
    st.markdown("#### ⛔ Exclusões Assimétricas & Riscos Restritivos")
    st.caption("Atenção para cláusulas que retiram direitos de indenização de administradores em uma apólice mas não na outra.")
    col_exc_a, col_exc_b = st.columns(2)

    with col_exc_a:
        st.markdown(f"**Exclusões Particulares ({pol_a.seguradora}):**")
        if comp_result.exclusoes_exclusivas_a:
            for e in comp_result.exclusoes_exclusivas_a:
                st.markdown(f"""<div class="exclusion-box"><b>⚠️ {e}</b></div>""", unsafe_allow_html=True)
        else:
            st.caption("_Sem exclusões assimétricas adicionais._")

    with col_exc_b:
        st.markdown(f"**Exclusões Particulares ({pol_b.seguradora}):**")
        if comp_result.exclusoes_exclusivas_b:
            for e in comp_result.exclusoes_exclusivas_b:
                st.markdown(f"""<div class="exclusion-box"><b>⚠️ {e}</b></div>""", unsafe_allow_html=True)
        else:
            st.caption("_Sem exclusões assimétricas adicionais._")

    # Botão de Ação para o Relatório
    st.markdown("---")
    col_act1, col_act2 = st.columns([2.5, 1.5])
    with col_act1:
        st.markdown("Deseja visualizar o **parecer executivo narrativo** estruturado para apresentação à diretoria?")
    with col_act2:
        if st.button("📄 Acessar Parecer Executivo do Gemini ➔", type="primary"):
            st.session_state["nav_page"] = "Relatório"
            st.rerun()
