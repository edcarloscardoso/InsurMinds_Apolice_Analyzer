"""Ponto de entrada principal da aplicação Streamlit InsurMinds Apólice Analyzer.
Configura layout institucional, AppShell corporativo (TopBar com Perfil de Trabalho e Sidebar de 6 itens),
injeção de estilos Insurance Intelligence v1.0 e roteamento oficial.
"""
import streamlit as st

from core.config import GEMINI_MODEL, DB_PATH, get_secret_or_env
from core.database import db
from core.llm_client import llm_client
from ui.styles import apply_custom_styles
from ui.navigation import normalize_page_name, navigate_to
from ui.persona.profiles import get_active_profile, DEFAULT_PROFILE_ID
from ui.components.app_shell import render_app_shell, OFFICIAL_NAVIGATION

# Páginas analíticas do sistema
from ui.page_workspace import render_workspace_page
from ui.page_upload import render_upload_page
from ui.page_library import render_library_page
from ui.page_compare import render_compare_page
from ui.page_report import render_report_page
from ui.page_accounting import render_accounting_page


# Configuração inicial do Streamlit
st.set_page_config(
    page_title="InsurMinds Apólice Analyzer",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Injeção de Estilos Corporativos — Insurance Intelligence v1.0
apply_custom_styles()

# Inicialização do estado da sessão
if "user_profile" not in st.session_state:
    st.session_state["user_profile"] = DEFAULT_PROFILE_ID

if "nav_version" not in st.session_state:
    st.session_state["nav_version"] = 0

if "page" in st.query_params:
    raw_param = str(st.query_params.get("page", "")).lower()
    st.session_state["nav_page"] = normalize_page_name(raw_param)

if "diff" in st.query_params:
    try:
        st.session_state["viewing_diff_idx"] = int(st.query_params.get("diff", 0))
    except Exception:
        pass

if "doc_a" in st.query_params and "doc_b" in st.query_params:
    da_name = st.query_params.get("doc_a")
    db_name = st.query_params.get("doc_b")
    pol_a = db.get_apolice_by_id(da_name) or next((p for p in db.list_apolices() if p.nome_arquivo == da_name), None)
    pol_b = db.get_apolice_by_id(db_name) or next((p for p in db.list_apolices() if p.nome_arquivo == db_name), None)
    if pol_a and pol_b:
        st.session_state["active_doc_a"] = pol_a
        st.session_state["active_doc_b"] = pol_b
        st.session_state["selected_for_compare"] = [pol_a, pol_b]

if "nav_page" not in st.session_state:
    st.session_state["nav_page"] = "Início"


# Callback centralizado de navegação
def handle_navigation(target_page: str):
    navigate_to(target_page)


# Renderização do AppShell Institucional (Sidebar + TopBar + ProfileSelector)
active_page = render_app_shell(
    current_page=st.session_state.get("nav_page", "Início"),
    on_navigate=handle_navigation
)

# Assistente Contextual D&O (Drawer Retrátil — FASE 7.9)
if st.session_state.get("context_assistant_open", False):
    from ui.components.context_assistant import render_context_assistant
    render_context_assistant(current_page=active_page)


# =============================================================================
# PÁGINA DE CONFIGURAÇÕES & INFRAESTRUTURA
# =============================================================================

def _render_settings_page():
    """Renderiza a página de IA e Integrações (Configurações do Sistema)."""
    st.markdown("### ⚙️ IA e Integrações")
    st.caption("Gerenciamento de conectividade do Google Gemini, chaves de API do Google AI Studio e infraestrutura analítica do sistema.")

    col_cfg1, col_cfg2 = st.columns([1.6, 1.4])
    with col_cfg1:
        st.markdown("#### Status da IA Generativa")
        if llm_client.is_available():
            st.markdown(f"""
                <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-left:4px solid #16A34A; border-radius:8px; padding:14px 18px; margin-bottom:16px;">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="font-size:16px;">🟢</span>
                        <span style="font-weight:700; color:#15803D; font-size:14px;">IA Generativa ativa</span>
                    </div>
                    <div style="font-size:12.5px; color:#166534; margin-top:4px;">
                        Google Gemini Conectado: Modelo <code>{GEMINI_MODEL}</code> operacional com Structured Output nativo.
                    </div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div style="background:#FFFBEB; border:1px solid #FDE68A; border-left:4px solid #D97706; border-radius:8px; padding:14px 18px; margin-bottom:16px;">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="font-size:16px;">🟡</span>
                        <span style="font-weight:700; color:#B45309; font-size:14px;">Modo de contingência ativo</span>
                    </div>
                    <div style="font-size:12.5px; color:#92400E; margin-top:4px;">
                        Gemini não configurado: Análise utilizando regras determinísticas regulatórias da SUSEP.
                    </div>
                </div>
            """, unsafe_allow_html=True)

        current_key = llm_client.api_key or get_secret_or_env("GOOGLE_API_KEY") or get_secret_or_env("GEMINI_API_KEY")
        if not llm_client.is_available() and current_key:
            llm_client.api_key = current_key
            llm_client._initialize_client()

        api_key_input = st.text_input(
            "Google AI Studio API Key:",
            type="password",
            value=current_key,
            help="Insira sua chave de API do Google AI Studio para ativar o processamento com Gemini.",
            placeholder="AIzaSy..."
        )

        st.markdown("""
            <div style="font-size:12px; color:#6B7785; margin:6px 0 16px 0; line-height:1.5;">
                <b>Como obter sua chave do Google AI Studio:</b><br/>
                1. Acesse o <a href="https://aistudio.google.com/app/apikey" target="_blank" style="color:#2864C7; font-weight:600; text-decoration:underline;">Google AI Studio (aistudio.google.com/app/apikey)</a>.<br/>
                2. Faça login com sua conta Google e clique em <b>Create API Key</b>.<br/>
                3. Cole a chave gerada no campo acima e clique em <b>Salvar Chave na Sessão</b>.
            </div>
        """, unsafe_allow_html=True)

        col_btn1, col_btn2 = st.columns([1, 1.3])
        with col_btn1:
            if st.button("💾 Salvar Chave", key="btn_save_gemini_key", use_container_width=True):
                if api_key_input and api_key_input.strip() != current_key:
                    llm_client.api_key = api_key_input.strip()
                    llm_client._initialize_client()
                    st.success("Chave atualizada na sessão.")
                    st.rerun()
                elif api_key_input and api_key_input.strip() == current_key:
                    st.info("Chave já configurada na sessão.")
                else:
                    st.warning("Insira uma chave válida.")
        with col_btn2:
            if st.button("⚡ Testar Conexão com IA", key="btn_test_gemini_key", use_container_width=True):
                if not llm_client.is_available():
                    st.error("Gemini não configurado. Forneça uma chave de API antes de testar a conexão.")
                else:
                    with st.spinner("Testando chamada remota com o Google Gemini..."):
                        try:
                            # Teste rápido consumindo o cliente GenAI nativo existente
                            test_resp = llm_client.client.models.generate_content(
                                model="gemini-2.5-flash",
                                contents="Responda estritamente: OK"
                            )
                            st.success(f"✅ Conexão validada com sucesso! Resposta: {test_resp.text.strip()}")
                        except Exception as e_test:
                            st.error(f"Falha na conexão com a API do Gemini: {e_test}")

    with col_cfg2:
        st.markdown("#### Estado do Repositório Local")
        total_apolices = len(db.list_apolices())
        st.markdown(f"""
            <div style="background:#FFFFFF; border:1px solid #D9E1E8; padding:16px 20px; border-radius:8px; font-size:13px; color:#1F2A35; line-height:1.8; box-shadow:0 1px 3px rgba(18, 48, 74, 0.05);">
                <div>• <b>Documentos Ingeridos:</b> {total_apolices}</div>
                <div>• <b>Banco SQLite:</b> <code>{DB_PATH.name}</code></div>
                <div>• <b>Orquestrador:</b> LangGraph Multi-Agente (Agentes 1 a 6)</div>
                <div>• <b>Modelo IA Principal:</b> <code>{GEMINI_MODEL}</code></div>
                <div>• <b>Filtros SUSEP:</b> Ramo 0378 (D&O) e Ramo 0531 (Auto)</div>
                <div>• <b>Armazenamento de Segredos:</b> Em memória na sessão (Zero gravação em banco)</div>
            </div>
        """, unsafe_allow_html=True)



# =============================================================================
# DESPACHO CONFORME A PÁGINA ATIVA
# =============================================================================
if active_page == "Início":
    render_workspace_page()
elif active_page == "Nova análise":
    render_upload_page()
elif active_page == "Comparações":
    render_compare_page()
elif active_page == "Documentos":
    render_library_page()
elif active_page == "Relatórios":
    render_report_page()
elif active_page == "Configurações":
    _render_settings_page()

# Rodapé Executivo Global
st.markdown("""
    <div style="text-align:center; color:#6B7785; font-size:12px; margin-top:48px; padding-top:18px; border-top:1px solid #D9E1E8;">
        🛡️ <b>InsurMinds Apólice Analyzer</b> · Insurance Intelligence v1.0 · I2A2 (2026)<br/>
        <i>Aviso: A análise é assistida por IA e não substitui a avaliação jurídica, técnica ou de subscrição.</i>
    </div>
""", unsafe_allow_html=True)
