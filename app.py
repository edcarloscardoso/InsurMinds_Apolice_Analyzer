"""Ponto de entrada principal da aplicação Streamlit InsurMinds Apólice Analyzer.
Configura layout, navegação centralizada, barra lateral executiva e injeção de estilos.
"""
import streamlit as st
from core.config import GEMINI_MODEL, DB_PATH
from core.database import db
from core.llm_client import llm_client
from ui.styles import apply_custom_styles
from ui.page_upload import render_upload_page
from ui.page_library import render_library_page
from ui.page_compare import render_compare_page
from ui.page_report import render_report_page
from ui.page_accounting import render_accounting_page

# Configuração da página Streamlit
st.set_page_config(
    page_title="InsurMinds Apólice Analyzer",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Injeção de Estilos Executivos Customizados
apply_custom_styles()

# Inicialização de estado da sessão
if "nav_page" not in st.session_state:
    st.session_state["nav_page"] = "Upload"
if "nav_version" not in st.session_state:
    st.session_state["nav_version"] = 0

# Banner Superior Corporativo InsurMinds (Padrão Seguros & Resseguros)
st.markdown("""
    <div class="insurminds-header">
        <span class="badge-tag">Plataforma Analítica D&O · Seguros & Resseguros Corporativos</span>
        <h1>🛡️ InsurMinds Apólice Analyzer</h1>
        <p>Inteligência Artificial Generativa para Extração Canônica, Confronto de Coberturas e Auditoria de Riscos Executivos · I2A2 (2026)</p>
    </div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Barra Lateral (Navegação e Status do Sistema)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/shield.png", width=64)
    st.markdown("### Navegação")
    
    paginas = ["Upload", "Biblioteca", "Comparação", "Relatório", "Auditoria Contábil"]
    icones = {"Upload": "📤", "Biblioteca": "📚", "Comparação": "⚖️", "Relatório": "📄", "Auditoria Contábil": "📊"}

    current_page = st.session_state.get("nav_page", "Upload")
    current_index = paginas.index(current_page) if current_page in paginas else 0
    radio_key = f"nav_radio_{st.session_state.get('nav_version', 0)}"

    escolha = st.radio(
        "Selecione o módulo:",
        options=paginas,
        index=current_index,
        key=radio_key,
        format_func=lambda x: f"{icones[x]} {x}"
    )
    if escolha != st.session_state["nav_page"]:
        st.session_state["nav_page"] = escolha
        st.rerun()

    st.markdown("---")
    st.markdown("### ⚙️ Configurações & IA")

    # Status da Conexão Gemini
    if llm_client.is_available():
        st.success(f"🟢 **Gemini Conectado**\n`{GEMINI_MODEL}`")
    else:
        st.info("🟡 **Modo Contingência / Offline**\nMotor de regras D&O ativo.")

    # Campo de chave de API opcional para teste ao vivo
    api_key_input = st.text_input(
        "Google API Key (Opcional):",
        type="password",
        value=llm_client.api_key if llm_client.api_key else "",
        help="Insira sua chave do Google AI Studio para ativar o Gemini ao vivo."
    )
    if api_key_input and api_key_input != llm_client.api_key:
        llm_client.api_key = api_key_input
        llm_client._initialize_client()
        st.rerun()

    st.markdown("---")
    st.markdown("### 📊 Status da Infraestrutura")
    total_apolices = len(db.list_apolices())
    st.caption(f"• **Apólices Armazenadas:** {total_apolices}")
    st.caption(f"• **Banco:** SQLite (`{DB_PATH.name}`)")
    st.caption("• **Orquestração:** LangGraph Multi-Agente")

    st.markdown("---")
    st.caption("InsurMinds · I2A2 — Instituto de Inteligência Artificial Aplicada · 2026")

# -----------------------------------------------------------------------------
# Roteamento de Páginas
# -----------------------------------------------------------------------------
active_page = st.session_state["nav_page"]

if active_page == "Upload":
    render_upload_page()
elif active_page == "Biblioteca":
    render_library_page()
elif active_page == "Comparação":
    render_compare_page()
elif active_page == "Relatório":
    render_report_page()
elif active_page == "Auditoria Contábil":
    render_accounting_page()
