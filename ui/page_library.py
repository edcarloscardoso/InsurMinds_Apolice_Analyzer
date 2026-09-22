"""Página 2: Biblioteca de Apólices.
Exibe as apólices armazenadas no banco SQLite, detalhes contratuais e seleção de documentos para comparação.
Harmonizada para o padrão institucional do mercado de seguros e resseguros corporativos.
"""
import streamlit as st
from core.database import db
from ui.navigation import navigate_to


def render_library_page():
    """Renderiza a biblioteca de apólices e o seletor para análise comparativa."""
    st.markdown("### 📚 Repositório de Apólices & Catálogo de Riscos")
    st.write("Consulte os contratos de seguro estruturados no repositório local e selecione propostas para confrontação analítica.")

    apolices = db.list_apolices()

    if not apolices:
        st.info("Nenhuma apólice cadastrada ainda na base de dados.")
        st.markdown("👉 Vá para a aba **Upload** para processar contratos do Google Drive ou amostras D&O:")
        st.button("Ir para Ingestão e Upload", type="primary", on_click=navigate_to, args=("Upload",))
        return

    # Painel de Métricas do Portfólio (Resseguro / Gestão de Riscos)
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    with col_kpi1:
        st.metric("Contratos em Carteira", f"{len(apolices)} apólices")
    with col_kpi2:
        seguradoras_unicas = len(set(a.seguradora for a in apolices if a.seguradora))
        st.metric("Seguradoras Analisadas", f"{seguradoras_unicas} emissoras")
    with col_kpi3:
        ramos_unicos = len(set(a.cod_ramo for a in apolices if a.cod_ramo))
        st.metric("Ramos SUSEP Presentes", f"{ramos_unicos} ramos")

    st.markdown("---")

    # Filtros e Ferramentas de Manutenção
    col_filter_ramo, col_reset = st.columns([3, 1.2])
    with col_filter_ramo:
        ramos_disponiveis = ["Todos os Ramos"] + sorted(list(set(a.cod_ramo for a in apolices if a.cod_ramo)))
        filtro_ramo = st.selectbox(
            "🔍 Filtrar exibição por Ramo SUSEP:",
            options=ramos_disponiveis,
            format_func=lambda x: "🌐 Todos os Ramos" if x == "Todos os Ramos" else f"🏷️ Ramo {x} ({'Automóvel' if x == '0531' else 'D&O' if x == '0378' else 'Patrimonial'})"
        )
    with col_reset:
        st.write("")
        st.write("")
        if st.button("🗑️ Limpar Repositório (Zerar)", help="Remove todas as apólices do banco local para recomeçar os testes com base limpa"):
            db.clear_database()
            st.session_state["selected_for_compare"] = []
            st.success("Repositório limpo com sucesso! Nenhuma apólice armazenada.")
            st.rerun()

    apolices_exibidas = [a for a in apolices if a.cod_ramo == filtro_ramo] if filtro_ramo != "Todos os Ramos" else apolices

    st.markdown("---")

    # Mecanismo de Seleção para Comparação
    st.markdown("#### ⚖️ Seleção para Confronto de Condições Particulares")
    st.caption("Selecione exatamente **2 apólices** do mesmo ramo ou ramos concorrentes para acionar a matriz comparativa.")

    opcoes = {
        f"🏢 {a.seguradora or 'Seguradora'} · Ramo {a.cod_ramo or '0378'} · Mov {a.tipo_movimento or '101'} · LMG: {a.limite_responsabilidade or 'N/A'} ({a.nome_arquivo})": a
        for a in apolices_exibidas
    }

    selecionadas_chaves = st.multiselect(
        "Escolha as duas propostas concorrentes para confronto:",
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
                navigate_to("Comparação")
                st.rerun()
        else:
            st.button("⚖️ Selecione 2 Apólices para Comparar", disabled=True)
    with col_count:
        if len(selecionadas_chaves) != 2:
            st.caption("⚠️ É necessário marcar exatamente 2 apólices para prosseguir.")

    st.markdown("---")

    # Listagem em Cartões Corporativos Detalhados
    st.markdown("#### 📑 Detalhamento dos Contratos Ingeridos")
    for apolice in apolices_exibidas:
        tipo_badge = f"📄 Mov {apolice.tipo_movimento or '101'}"
        with st.expander(f"🏢 **{apolice.seguradora or 'Seguradora'}** — {apolice.nome_arquivo} | Ramo: {apolice.cod_ramo or '0378'} | {tipo_badge} | LMG: {apolice.limite_responsabilidade or 'N/A'}"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Empresa Segurada:**\n{apolice.segurado or 'N/A'}")
                st.markdown(f"**Nº de Registro da Apólice:**\n`{apolice.numero_apolice or 'N/A'}`")
                st.markdown(f"**Ramo SUSEP:**\n`{apolice.cod_ramo or '0378'}` — {apolice.ramo_descricao or 'Responsabilidade Civil D&O'}")
                st.markdown(f"**Tipo de Movimento:**\n`{apolice.tipo_movimento or '101'}` — {apolice.tipo_movimento_descricao or 'Emissão de Apólice'}")
            with col2:
                st.markdown(f"**Limite Máximo de Garantia (LMG):**\n<span style='color:#0F253E; font-weight:700; font-size:16px;'>{apolice.limite_responsabilidade or 'N/A'}</span>", unsafe_allow_html=True)
                st.markdown(f"**Franquia / Retenção:**\n{apolice.franquia or 'N/A'}")
                st.markdown(f"**Prêmio Comercial:**\n{apolice.premio_total or 'N/A'}")
                st.markdown(f"**Vigência Contratual:**\n{apolice.vigencia_inicio or '?'} até {apolice.vigencia_fim or '?'}")
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
