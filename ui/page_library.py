"""Página 2: Biblioteca de Apólices.
Exibe as apólices armazenadas no banco SQLite, detalhes contratuais e seleção de documentos para comparação.
Harmonizada para o padrão institucional do mercado de seguros e resseguros corporativos.
"""
import streamlit as st
from core.database import db


def render_library_page():
    """Renderiza a biblioteca de apólices e o seletor para análise comparativa."""
    st.markdown("### 📚 Repositório de Apólices & Catálogo de Riscos")
    st.write("Consulte os contratos de D&O estruturados no repositório local e selecione propostas para confrontação analítica.")

    apolices = db.list_apolices()

    if not apolices:
        st.info("Nenhuma apólice cadastrada ainda na base de dados.")
        st.markdown("👉 Vá para a aba **Upload** ou clique abaixo para carregar as amostras do I2A2:")
        if st.button("Carregar Apólices de Amostra", type="primary"):
            st.session_state["nav_page"] = "Upload"
            st.rerun()
        return

    # Painel de Métricas do Portfólio (Resseguro / Gestão de Riscos)
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    with col_kpi1:
        st.metric("Contratos em Carteira", f"{len(apolices)} apólices")
    with col_kpi2:
        seguradoras_unicas = len(set(a.seguradora for a in apolices if a.seguradora))
        st.metric("Seguradoras Analisadas", f"{seguradoras_unicas} emissoras")
    with col_kpi3:
        st.metric("Padrão Contratual", "D&O Circular SUSEP")

    st.markdown("---")

    # Mecanismo de Seleção para Comparação
    st.markdown("#### ⚖️ Seleção para Confronto de Condições Particulares")
    st.caption("Selecione exatamente **2 apólices** para acionar os Agentes 5 e 6 de análise comparativa.")

    opcoes = {
        f"🏢 {a.seguradora or 'Seguradora'} · LMG: {a.limite_responsabilidade or 'N/A'} ({a.nome_arquivo})": a
        for a in apolices
    }

    selecionadas_chaves = st.multiselect(
        "Escolha as duas propostas concorrentes:",
        options=list(opcoes.keys()),
        default=list(opcoes.keys())[:2] if len(opcoes) >= 2 else list(opcoes.keys()),
        max_selections=2
    )

    col_btn, col_count = st.columns([1.6, 3])
    with col_btn:
        if len(selecionadas_chaves) == 2:
            if st.button("⚖️ Executar Comparação Analítica", type="primary"):
                st.session_state["selected_for_compare"] = [
                    opcoes[selecionadas_chaves[0]],
                    opcoes[selecionadas_chaves[1]]
                ]
                st.session_state["nav_page"] = "Comparação"
                st.rerun()
        else:
            st.button("⚖️ Selecione 2 Apólices para Comparar", disabled=True)
    with col_count:
        if len(selecionadas_chaves) != 2:
            st.caption("⚠️ É necessário marcar exatamente 2 apólices para prosseguir.")

    st.markdown("---")

    # Listagem em Cartões Corporativos Detalhados
    st.markdown("#### 📑 Detalhamento dos Contratos Ingeridos")
    for apolice in apolices:
        with st.expander(f"🏢 **{apolice.seguradora or 'Seguradora'}** — {apolice.nome_arquivo} | LMG: {apolice.limite_responsabilidade or 'N/A'}"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Empresa Segurada:**\n{apolice.segurado or 'N/A'}")
                st.markdown(f"**Nº de Registro da Apólice:**\n`{apolice.numero_apolice or 'N/A'}`")
                st.markdown(f"**Vigência Contratual:**\n{apolice.vigencia_inicio or '?'} até {apolice.vigencia_fim or '?'}")
            with col2:
                st.markdown(f"**Limite Máximo de Garantia (LMG):**\n<span style='color:#0F253E; font-weight:700; font-size:16px;'>{apolice.limite_responsabilidade or 'N/A'}</span>", unsafe_allow_html=True)
                st.markdown(f"**Franquia / Retenção:**\n{apolice.franquia or 'N/A'}")
                st.markdown(f"**Prêmio Comercial:**\n{apolice.premio_total or 'N/A'}")
            with col3:
                st.markdown(f"**Data de Retroatividade:**\n{apolice.retroatividade or 'N/A'}")
                st.markdown(f"**Jurisdição / Território:**\n{apolice.territorio or 'N/A'}")
                st.markdown(f"**Auditoria de Extração:**\n`{apolice.metodo_extracao}` ({apolice.confianca_extracao * 100:.0f}% confiança)")

            st.markdown("---")
            col_cob, col_exc = st.columns(2)
            with col_cob:
                st.markdown(f"**🛡️ Coberturas Contratadas ({len(apolice.coberturas)}):**")
                for c in apolice.coberturas[:6]:
                    st.markdown(f"""<div class="coverage-box"><b>✓ {c}</b></div>""", unsafe_allow_html=True)
                if len(apolice.coberturas) > 6:
                    st.caption(f"_... e mais {len(apolice.coberturas) - 6} cláusulas de cobertura_")
            with col_exc:
                st.markdown(f"**⛔ Riscos Excluídos ({len(apolice.exclusoes)}):**")
                for e in apolice.exclusoes[:5]:
                    st.markdown(f"""<div class="exclusion-box"><b>✕ {e}</b></div>""", unsafe_allow_html=True)
                if len(apolice.exclusoes) > 5:
                    st.caption(f"_... e mais {len(apolice.exclusoes) - 5} exclusões_")

            st.markdown(" ")
            col_del, _ = st.columns([1.2, 4])
            with col_del:
                if st.button("🗑️ Excluir do Repositório", key=f"del_{apolice.id}"):
                    if db.delete_apolice(apolice.id):
                        st.success(f"Apólice {apolice.seguradora} removida com sucesso!")
                        st.rerun()
