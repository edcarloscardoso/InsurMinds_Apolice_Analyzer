"""Página 5: Auditoria Contábil & Análise de Sinistros (SUSEP).
Monitoramento de variações de provisões técnicas (PSL / Sinistros a Liquidar),
identificação do Maior Ofensor por Ramo SUSEP e geração de justificativas com IA.
"""
import streamlit as st
import pandas as pd
from core.schemas import SinistroItem, AuditoriaVarianceReport
from core.variance_engine import (
    calculate_claims_variance,
    generate_sample_accounting_data,
    RAMOS_SUSEP,
    TIPOS_MOVIMENTO_SUSEP,
    get_ramo_name,
    get_tipo_mov_name
)
from core.llm_client import llm_client


def render_accounting_page():
    """Renderiza a página de Auditoria Contábil e Análise de Variação de Sinistros."""
    st.markdown("### 📊 Auditoria Contábil & Análise de Sinistros (SUSEP)")
    st.write(
        "Conciliação de Provisões Técnicas (PSL), atribuição de variações contábeis e identificação "
        "do **Maior Ofensor e Ramo** para notas explicativas da SUSEP e auditorias externas."
    )

    # -------------------------------------------------------------------------
    # 1. Gerenciamento da Base de Dados de Sinistros
    # -------------------------------------------------------------------------
    if "accounting_sinistros" not in st.session_state:
        st.session_state["accounting_sinistros"] = generate_sample_accounting_data()

    col_actions1, col_actions2, col_actions3 = st.columns([1.8, 2.2, 1.2])
    with col_actions1:
        if st.button("🔄 Recarregar Base Demonstrativa SUSEP (08/2026)"):
            st.session_state["accounting_sinistros"] = generate_sample_accounting_data()
            st.session_state.pop("active_audit_report", None)
            st.rerun()

    with col_actions2:
        periodo_selecionado = st.selectbox(
            "Período de Referência Contábil:",
            options=["08/2026 (Fechamento Mensal FIP)", "07/2026 (Fechamento Mensal FIP)", "2T/2026 (Demonstração Trimestral)"],
            index=0
        )

    with col_actions3:
        uploaded_file = st.file_uploader("Subir CSV de Sinistros:", type=["csv"], label_visibility="collapsed")
        if uploaded_file is not None:
            try:
                df_upload = pd.read_csv(uploaded_file)
                # Conversão simples se as colunas essenciais existirem
                items = []
                for _, row in df_upload.iterrows():
                    items.append(SinistroItem(
                        numero_sinistro=str(row.get("numero_sinistro", f"SIN-{len(items)+1}")),
                        numero_apolice=str(row.get("numero_apolice", "01.000.000")),
                        segurado=str(row.get("segurado", "Empresa Segurada")),
                        seguradora=str(row.get("seguradora", "Seguradora")),
                        cod_ramo=str(row.get("cod_ramo", "0378")).zfill(4),
                        ramo_nome=str(row.get("ramo_nome", get_ramo_name(str(row.get("cod_ramo", "0378"))))),
                        tipo_mov=str(row.get("tipo_mov", "101")),
                        saldo_anterior=float(row.get("saldo_anterior", 0.0)),
                        saldo_atual=float(row.get("saldo_atual", 0.0)),
                        delta_variacao=float(row.get("saldo_atual", 0.0)) - float(row.get("saldo_anterior", 0.0)),
                        status_sinistro=str(row.get("status_sinistro", "Avisado")),
                        causa_sinistro=str(row.get("causa_sinistro", "Fato gerador do sinistro"))
                    ))
                if items:
                    st.session_state["accounting_sinistros"] = items
                    st.success(f"Base de {len(items)} sinistros carregada com sucesso!")
            except Exception as e:
                st.error(f"Erro ao processar arquivo CSV: {e}")

    sinistros = st.session_state["accounting_sinistros"]
    periodo_cod = periodo_selecionado.split(" ")[0]
    report: AuditoriaVarianceReport = calculate_claims_variance(sinistros, periodo_referencia=periodo_cod)

    st.markdown("---")

    # -------------------------------------------------------------------------
    # 2. Painel Executivo de Indicadores de Fechamento Contábil
    # -------------------------------------------------------------------------
    st.markdown("#### 📈 Síntese Executiva de Variação de Provisão")

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric(
            label="Provisão Anterior (PSL)",
            value=f"R$ {report.total_anterior_geral:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
    with kpi2:
        st.metric(
            label="Provisão Atualizada",
            value=f"R$ {report.total_atual_geral:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
    with kpi3:
        delta_val = report.delta_global
        delta_str = f"{'+' if delta_val >= 0 else ''}R$ {delta_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        st.metric(
            label="Variação Global (Δ)",
            value=delta_str,
            delta=f"{report.delta_global_percentual:+.2f}%",
            delta_color="off" if delta_val > 0 else "normal"
        )
    with kpi4:
        if report.ramo_maior_ofensor:
            st.metric(
                label="🚨 Ramo Maior Ofensor",
                value=f"Ramo {report.ramo_maior_ofensor.cod_ramo}",
                delta=f"{report.ramo_maior_ofensor.share_na_variacao_total:.1f}% da variação",
                delta_color="off"
            )
        else:
            st.metric(label="Ramo Maior Ofensor", value="Nenhum")

    st.markdown("---")

    # -------------------------------------------------------------------------
    # 3. Matriz de Variação por Ramo SUSEP (Bridge de Auditoria)
    # -------------------------------------------------------------------------
    st.markdown("#### 🏢 Matriz de Variação Agregada por Ramo SUSEP")
    st.caption("Visão contábil requerida pela SUSEP para demonstrar quais carteiras impulsionaram o saldo técnico.")

    tabela_ramos = []
    for r in report.variacao_por_ramo:
        status_tag = "🚨 MAIOR OFENSOR" if r.is_maior_ofensor else "Normal"
        tabela_ramos.append({
            "Código": r.cod_ramo,
            "Ramo SUSEP": r.ramo_nome,
            "Qtd Sinistros": r.qtd_sinistros,
            "Saldo Anterior (R$)": f"{r.total_anterior:,.2f}",
            "Saldo Atual (R$)": f"{r.total_atual:,.2f}",
            "Variação Líquida (R$)": f"{'+' if r.delta_absoluto >= 0 else ''}{r.delta_absoluto:,.2f}",
            "Variação (%)": f"{r.delta_percentual:+.2f}%",
            "Share da Oscilação": f"{r.share_na_variacao_total:.1f}%",
            "Classificação": status_tag
        })

    df_ramos = pd.DataFrame(tabela_ramos)
    st.dataframe(df_ramos, use_container_width=True, hide_index=True)

    st.markdown("---")

    # -------------------------------------------------------------------------
    # 4. Detalhamento de Sinistros e Identificação do Ofensor Individual
    # -------------------------------------------------------------------------
    st.markdown("#### 📑 Detalhamento Analítico dos Sinistros & Movimentos")
    st.caption("Investigação no nível da apólice para fundamentar questionamentos de auditoria e circulares da SUSEP.")

    col_filtro_ramo, col_filtro_mov = st.columns(2)
    with col_filtro_ramo:
        ramos_opcoes = ["Todos os Ramos"] + [f"{r.cod_ramo} - {r.ramo_nome}" for r in report.variacao_por_ramo]
        filtro_ramo = st.selectbox("Filtrar por Ramo:", options=ramos_opcoes, index=0)

    with col_filtro_mov:
        mov_opcoes = ["Todos os Movimentos"] + [f"{k} - {v}" for k, v in TIPOS_MOVIMENTO_SUSEP.items()]
        filtro_mov = st.selectbox("Filtrar por Tipo de Movimento:", options=mov_opcoes, index=0)

    sinistros_filtrados = sinistros
    if filtro_ramo != "Todos os Ramos":
        cod_escolhido = filtro_ramo.split(" - ")[0].strip()
        sinistros_filtrados = [s for s in sinistros_filtrados if s.cod_ramo == cod_escolhido]
    if filtro_mov != "Todos os Movimentos":
        mov_escolhido = filtro_mov.split(" - ")[0].strip()
        sinistros_filtrados = [s for s in sinistros_filtrados if s.tipo_mov == mov_escolhido]

    tabela_sinistros = []
    for s in sinistros_filtrados:
        tabela_sinistros.append({
            "Sinistro Nº": s.numero_sinistro,
            "Apólice Nº": s.numero_apolice,
            "Segurado": s.segurado,
            "Ramo SUSEP": f"{s.cod_ramo} - {s.ramo_nome}",
            "Tipo Movimento": get_tipo_mov_name(s.tipo_mov),
            "Saldo Anterior (R$)": f"{s.saldo_anterior:,.2f}",
            "Saldo Atual (R$)": f"{s.saldo_atual:,.2f}",
            "Delta (R$)": f"{'+' if s.delta_variacao >= 0 else ''}{s.delta_variacao:,.2f}",
            "Status": s.status_sinistro,
            "Causa / Justificativa": s.causa_sinistro
        })

    df_sinistros = pd.DataFrame(tabela_sinistros)
    st.dataframe(df_sinistros, use_container_width=True, hide_index=True)

    st.markdown("---")

    # -------------------------------------------------------------------------
    # 5. Síntese de Justificativa para SUSEP e Auditoria Externa (IA)
    # -------------------------------------------------------------------------
    st.markdown("#### 🤖 Síntese de Justificativa Contábil (SUSEP & Auditoria)")
    st.write(
        "Gere automaticamente a **Nota Explicativa Oficial** pronta para ser anexada ao FIP SUSEP "
        "ou enviada à equipe de auditoria independente, detalhando a variação e justificando o maior ofensor."
    )

    col_gerar, col_info = st.columns([2, 3])
    with col_gerar:
        if st.button("✨ Gerar Justificativa Oficial com Gemini 2.0 Flash", type="primary"):
            with st.spinner("Sintetizando nota técnica atuarial/contábil..."):
                texto_justificativa = llm_client.generate_audit_variance_justification(report)
                st.session_state["active_audit_justification"] = texto_justificativa
                st.session_state["active_audit_periodo"] = report.periodo_referencia
    with col_info:
        st.caption("A nota sintetiza a evolução do saldo, a aderência às provisões técnicas e o histórico do evento ofensor.")

    justificativa_atual = st.session_state.get("active_audit_justification", report.justificativa_auditoria_markdown)

    st.markdown("### 📄 Parecer Técnico Estruturado")
    st.markdown(f"""
        <div style="background-color: #FFFFFF; border: 1px solid #D6E0EA; border-left: 5px solid #0F2B48; padding: 24px; border-radius: 8px; margin-top: 12px; box-shadow: 0 4px 12px rgba(15, 43, 72, 0.05);">
            {justificativa_atual}
        </div>
    """, unsafe_allow_html=True)

    st.download_button(
        label="📥 Baixar Nota Explicativa (Markdown)",
        data=justificativa_atual,
        file_name=f"justificativa_auditoria_susep_{periodo_cod.replace('/', '_')}.md",
        mime="text/markdown"
    )
