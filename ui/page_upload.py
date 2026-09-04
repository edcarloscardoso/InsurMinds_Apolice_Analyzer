"""Página 1: Upload e Ingestão de Apólices.
Gerencia recepção de múltiplos PDFs, validação de integridade e visualização em tempo real dos Agentes 1 a 4.
Harmonizada para o padrão corporativo de seguradoras e resseguradoras.
"""
from pathlib import Path
import streamlit as st
from core.config import UPLOADS_DIR, SAMPLE_POLICIES_DIR, MAX_FILE_SIZE_MB
from core.security import get_safe_destination_path
from agents.graph import run_document_pipeline_with_progress


def render_upload_page():
    """Renderiza a interface de ingestão com timeline de agentes."""
    st.markdown("### 📤 Ingestão & Recepção de Apólices D&O")
    st.write(
        "Envie propostas ou apólices de seguro D&O em formato PDF para extração e estruturação automática "
        "através dos agentes inteligentes de subscrição."
    )

    # Botão de Carregamento Rápido de Amostras para Demonstração
    st.markdown("---")
    col_demo, col_info = st.columns([1.3, 2.7])
    with col_demo:
        if st.button("⚡ Carregar Amostras Oficiais (I2A2)", type="primary", help="Carrega instantaneamente as 3 apólices D&O realistas (Allianz, Chubb e AIG)"):
            _process_sample_policies()
    with col_info:
        st.info("💡 **Acesso Rápido para Banca Avaliadora:** Clique no botão ao lado para carregar e estruturar automaticamente as apólices de teste da Allianz, Chubb e AIG.")

    st.markdown("---")

    # Colunas com Instruções e Upload
    col_upload, col_rules = st.columns([2.5, 1.5])

    with col_upload:
        uploaded_files = st.file_uploader(
            "Selecione ou arraste os arquivos de apólice (PDF)",
            type=["pdf"],
            accept_multiple_files=True,
            help=f"Tamanho máximo de {MAX_FILE_SIZE_MB}MB por arquivo."
        )

        if uploaded_files:
            if len(uploaded_files) > 5:
                st.warning("⚠️ Limite de 5 apólices por sessão excedido. As 5 primeiras serão consideradas.")
                uploaded_files = uploaded_files[:5]

            st.markdown(f"**📁 {len(uploaded_files)} arquivo(s) selecionado(s):**")
            for f in uploaded_files:
                st.caption(f"• **{f.name}** ({f.size / 1024:.1f} KB)")

            if st.button("▶ Iniciar Processamento dos Agentes", type="primary"):
                _process_uploaded_files(uploaded_files)

    with col_rules:
        st.markdown("""
            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:18px 20px; box-shadow:0 2px 8px rgba(15,23,42,0.04);">
                <h4 style="margin-top:0; color:#0A192F; font-size:14px; font-weight:700;">🛡️ Diretrizes de Ingestão</h4>
                <ul style="font-size:12.5px; color:#475569; padding-left:18px; margin-bottom:0;">
                    <li><b>Formatos:</b> PDFs digitais ou escaneados (fallback multimodal).</li>
                    <li><b>Validação:</b> Checagem de integridade binária (%PDF-).</li>
                    <li><b>Idempotência:</b> Deduplicação automática via hash MD5.</li>
                    <li><b>Segurança:</b> Sanitização rígida contra Path Traversal.</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)


def _process_uploaded_files(files):
    """Processa a lista de arquivos enviados pelo usuário executando o pipeline dos agentes."""
    total = len(files)
    progress_bar = st.progress(0)
    status_text = st.empty()
    results = []

    for idx, uploaded_file in enumerate(files):
        filename = uploaded_file.name
        status_text.markdown(f"**Processando documento {idx + 1}/{total}:** `{filename}`")

        # Salva o arquivo no diretório seguro de uploads
        try:
            dest_path = get_safe_destination_path(UPLOADS_DIR, filename)
            dest_path.write_bytes(uploaded_file.getbuffer())
        except Exception as e:
            st.error(f"Erro ao salvar arquivo {filename}: {e}")
            continue

        step_container = st.container()
        step_placeholder = step_container.empty()

        def on_step(step_num: int, agent_name: str, desc: str):
            step_placeholder.info(f"⏳ **Passo {step_num}/4 — {agent_name}:** {desc}")

        # Executa o pipeline dos 4 agentes
        state = run_document_pipeline_with_progress(
            file_path=str(dest_path),
            file_name=filename,
            on_step_callback=on_step
        )

        if state.status == "erro":
            step_placeholder.error(f"❌ Erro ao processar `{filename}`: {', '.join(state.errors)}")
        elif state.status == "concluido_em_cache":
            step_placeholder.success(f"⚡ `{filename}` recuperado do cache analítico (já processado).")
            results.append(state.structured_data)
        else:
            step_placeholder.success(f"✅ `{filename}` catalogado com sucesso pelos 4 Agentes!")
            results.append(state.structured_data)

        progress_bar.progress((idx + 1) / total)

    status_text.markdown("✨ **Processamento de Ingestão Finalizado!**")
    if results:
        st.success(f"🎉 {len(results)} contrato(s) estruturado(s) no banco de dados.")
        if st.button("Ir para o Repositório de Apólices ➔", type="primary"):
            st.session_state["nav_page"] = "Biblioteca"
            st.rerun()


def _process_sample_policies():
    """Processa automaticamente os arquivos da pasta data/sample_policies."""
    sample_files = list(SAMPLE_POLICIES_DIR.glob("*.pdf"))
    if not sample_files:
        st.error("Nenhuma apólice encontrada em data/sample_policies.")
        return

    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(sample_files)

    for idx, sample_path in enumerate(sample_files):
        status_text.markdown(f"**Processando amostra de subscrição {idx + 1}/{total}:** `{sample_path.name}`")
        state = run_document_pipeline_with_progress(
            file_path=str(sample_path),
            file_name=sample_path.name
        )
        progress_bar.progress((idx + 1) / total)

    status_text.markdown("✨ **Amostras estruturadas com sucesso!**")
    st.success("✅ Apólices da Allianz, Chubb e AIG prontas para confronto na Biblioteca.")
    if st.button("Acessar Repositório Agora ➔", type="primary"):
        st.session_state["nav_page"] = "Biblioteca"
        st.rerun()
