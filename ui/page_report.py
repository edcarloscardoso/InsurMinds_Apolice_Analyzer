"""Página 4: Parecer Executivo Narrativo (Gemini).
Apresenta o relatório narrativo em Linguagem Natural formatado no padrão de memorando de resseguro e consultoria de riscos.
"""
import streamlit as st
import json
from core.database import db
from ui.navigation import navigate_to


def render_report_page():
    """Renderiza a visualização do parecer executivo narrativo e ferramentas de exportação."""
    st.markdown("### 📄 Parecer Executivo Narrativo (D&O)")
    st.write("Análise comparativa aprofundada gerada por Inteligência Artificial Generativa para subsidiar a tomada de decisão da diretoria.")

    report_md = st.session_state.get("active_executive_report", None)
    comp_result = st.session_state.get("active_comparison_result", None)

    # Se não houver relatório ativo na sessão, tenta recuperar a comparação mais recente do banco
    if not report_md:
        todas = db.list_apolices()
        if len(todas) >= 2:
            cached = db.get_comparison(todas[0].id, todas[1].id)
            if cached and cached.get("relatorio_markdown"):
                report_md = cached["relatorio_markdown"]
                comp_result = cached.get("resultado")

    if not report_md:
        st.info("Nenhum parecer comparativo ativo no momento.")
        st.markdown("👉 Selecione 2 apólices na **Biblioteca** ou acesse a tela de **Comparação** para gerar o parecer.")
        st.button("Ir para a Comparação", type="primary", on_click=navigate_to, args=("Comparação",))
        return

    # Barra de Ferramentas de Exportação Executiva
    col_exp1, col_exp2, col_info = st.columns([1.3, 1.3, 2.4])
    with col_exp1:
        st.download_button(
            label="💾 Exportar Parecer (Markdown)",
            data=report_md,
            file_name="parecer_executivo_do_insurminds.md",
            mime="text/markdown"
        )
    with col_exp2:
        if comp_result:
            json_data = comp_result.model_dump_json(indent=2)
            st.download_button(
                label="💾 Exportar Dados (JSON)",
                data=json_data,
                file_name="comparacao_apolices.json",
                mime="application/json"
            )
    with col_info:
        st.caption("✅ Documento formatado para anexação em atas de conselho ou dossiês de corretagem.")

    st.markdown("---")

    # Renderização do Relatório em Caixa de Memorando de Resseguro
    st.markdown("""
        <div style="
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-top: 4px solid #0A192F;
            border-radius: 12px;
            padding: 36px 40px;
            box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.05);
            margin-bottom: 24px;
        ">
    """, unsafe_allow_html=True)

    st.markdown(report_md)

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    with st.expander("🔍 Ver Código-Fonte do Relatório / Copiar Texto"):
        st.text_area("Texto Formatado (Markdown)", value=report_md, height=220)
