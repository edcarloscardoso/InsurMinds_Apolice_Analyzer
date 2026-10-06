"""Design System & Harmonização Visual — Insurance Intelligence v1.0.
Implementa o ecossistema visual corporativo para a plataforma InsurMinds Apólice Analyzer.
Fundo claro (#F5F7FA), superfícies brancas (#FFFFFF), azul marinho (#12304A), azul primário (#2864C7),
tipografia Inter (UI) e IBM Plex Mono (Evidências literais), com hierarquia editorial e foco documental.
"""
import streamlit as st
from ui.tokens import COLORS, TYPOGRAPHY, SPACING, RADIUS, SHADOWS


def render_html(html_str: str) -> None:
    """Renderiza HTML corporativo no Streamlit removendo qualquer indentação inicial de linhas
    para evitar que o parser CommonMark do Streamlit trate tags como blocos de código preformatado (<pre><code>).
    """
    clean_html = "\n".join(line.strip() for line in html_str.strip().splitlines())
    st.markdown(clean_html, unsafe_allow_html=True)


def apply_custom_styles():
    """Injeta a folha de estilos corporativa do Design System Insurance Intelligence v1.0."""
    render_html(f"""
        <style>
        /* ====================================================================
           1. TIPOGRAFIA & BASE GLOBAL (Inter & IBM Plex Mono)
           ==================================================================== */
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700;800&display=swap');

        /* Canvas Global Claro Institucional */
        html, body, .stApp, [data-testid="stApp"], [data-testid="stAppViewContainer"],
        section.main, [data-testid="stMain"], .main, .block-container, [data-testid="stAppViewBlockContainer"] {{
            font-family: {TYPOGRAPHY.FONT_UI} !important;
            color: {COLORS.TEXT_MAIN} !important;
            background-color: {COLORS.BACKGROUND} !important;
            background: {COLORS.BACKGROUND} !important;
        }}

        header[data-testid="stHeader"] {{
            background-color: rgba(245, 247, 250, 0.92) !important;
            backdrop-filter: blur(8px) !important;
            border-bottom: 1px solid {COLORS.BORDER} !important;
        }}

        /* Tipografia de Títulos e Parágrafos */
        .stMarkdown, .stMarkdown p, .stMarkdown span, .stMarkdown div,
        [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] span {{
            color: {COLORS.TEXT_MAIN} !important;
            font-family: {TYPOGRAPHY.FONT_UI} !important;
        }}

        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6,
        h1, h2, h3, h4, h5, h6 {{
            font-family: {TYPOGRAPHY.FONT_UI} !important;
            color: {COLORS.PRIMARY_NAVY} !important;
            letter-spacing: -0.3px !important;
            font-weight: 600 !important;
        }}

        h1 {{ font-size: 24px !important; line-height: 32px !important; }}
        h2 {{ font-size: 20px !important; line-height: 28px !important; }}
        h3 {{ font-size: 16px !important; line-height: 24px !important; }}

        /* Container Principal com Alinhamento Executivo */
        .block-container {{
            padding-top: 1.25rem !important;
            padding-bottom: 3.5rem !important;
            max-width: 1380px !important;
        }}

        /* ====================================================================
           2. TOPBAR CORPORATIVA & IDENTIDADE
           ==================================================================== */
        .im-topbar-brand {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 4px;
        }}

        .im-topbar-badge {{
            display: inline-block;
            background-color: #E2E8F0;
            color: {COLORS.PRIMARY_NAVY};
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 2px 8px;
            border-radius: {RADIUS.SM};
            margin-bottom: 4px;
        }}

        .im-topbar-title {{
            font-size: 18px !important;
            font-weight: 700 !important;
            color: {COLORS.PRIMARY_NAVY} !important;
            margin: 0 !important;
            line-height: 1.3 !important;
        }}

        .im-topbar-divider {{
            border: none;
            border-top: 1px solid {COLORS.BORDER};
            margin: 12px 0 20px 0;
        }}

        .im-profile-tagline {{
            font-size: 12px;
            color: {COLORS.TEXT_MUTED};
            font-weight: 500;
        }}

        /* Breadcrumb Corporativo */
        .im-breadcrumb {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 12.5px;
            color: {COLORS.TEXT_MUTED};
            margin-top: 4px;
        }}
        .im-breadcrumb-item {{
            color: {COLORS.TEXT_MUTED};
        }}
        .im-breadcrumb-sep {{
            color: #94A3B8;
        }}
        .im-breadcrumb-current {{
            color: {COLORS.PRIMARY_BLUE};
            font-weight: 600;
        }}

        /* ====================================================================
           3. BARRA LATERAL (SIDEBAR) CORPORATIVA COMPACTA
           ==================================================================== */
        [data-testid="stSidebar"] {{
            background-color: {COLORS.SURFACE} !important;
            background: {COLORS.SURFACE} !important;
            border-right: 1px solid {COLORS.BORDER} !important;
        }}

        [data-testid="stSidebar"] * {{
            color: {COLORS.TEXT_MAIN} !important;
        }}

        .im-sidebar-header {{
            text-align: center;
            padding: 12px 0 16px 0;
            border-bottom: 1px solid {COLORS.BORDER};
            margin-bottom: 16px;
        }}

        .im-logo-icon {{
            font-size: 32px;
            line-height: 1;
            margin-bottom: 4px;
        }}

        .im-logo-title {{
            font-size: 18px;
            font-weight: 800;
            color: {COLORS.PRIMARY_NAVY} !important;
            letter-spacing: -0.3px;
        }}

        .im-logo-sub {{
            font-size: 11px;
            color: {COLORS.PRIMARY_BLUE} !important;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.8px;
        }}

        .im-nav-section-label {{
            font-size: 11px;
            font-weight: 700;
            color: {COLORS.TEXT_MUTED} !important;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            margin: 12px 0 6px 0;
        }}

        /* Botões de Seleção Lateral Estilizados */
        [data-testid="stSidebar"] .stRadio label {{
            background: {COLORS.SURFACE} !important;
            border: 1px solid transparent !important;
            padding: 8px 12px !important;
            border-radius: {RADIUS.MD} !important;
            margin-bottom: 4px !important;
            transition: all 0.15s ease !important;
            cursor: pointer !important;
            display: flex !important;
            align-items: center !important;
            font-size: 13.5px !important;
            font-weight: 500 !important;
            color: {COLORS.TEXT_MAIN} !important;
        }}

        [data-testid="stSidebar"] .stRadio label:hover {{
            background: {COLORS.SURFACE_HOVER} !important;
            border-color: {COLORS.BORDER} !important;
            color: {COLORS.PRIMARY_NAVY} !important;
        }}

        .im-sidebar-divider {{
            border: none;
            border-top: 1px solid {COLORS.BORDER};
            margin: 16px 0;
        }}

        .im-system-status {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 12px;
            border-radius: {RADIUS.MD};
            margin-bottom: 10px;
            font-size: 12px;
        }}

        .im-status-online {{
            background-color: #E6F4EA;
            border: 1px solid #A3D9B5;
            color: {COLORS.SUCCESS};
        }}

        .im-status-fallback {{
            background-color: #EFF6FF;
            border: 1px solid #BFDBFE;
            color: {COLORS.PRIMARY_BLUE};
        }}

        .im-status-dot-green {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: {COLORS.SUCCESS};
            display: inline-block;
        }}

        .im-status-dot-blue {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: {COLORS.PRIMARY_BLUE};
            display: inline-block;
        }}

        .im-status-name {{
            font-weight: 600;
            font-size: 12px;
        }}

        .im-status-model {{
            font-family: {TYPOGRAPHY.FONT_CODE};
            font-size: 11px;
            color: {COLORS.TEXT_MUTED};
        }}

        .im-sidebar-meta {{
            font-size: 11.5px;
            color: {COLORS.TEXT_MUTED};
            line-height: 1.6;
        }}

        /* ====================================================================
           4. CARTÕES INSTITUCIONAIS & METRICCARDS
           ==================================================================== */
        .im-card {{
            background-color: {COLORS.SURFACE};
            border: 1px solid {COLORS.BORDER};
            border-radius: {RADIUS.LG};
            padding: 20px 24px;
            margin-bottom: 16px;
            box-shadow: {SHADOWS.SM};
            transition: border-color 0.15s ease;
        }}

        .im-card:hover {{
            border-color: #B0C0D0;
        }}

        .im-card-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 14px;
        }}

        .im-card-title {{
            font-size: 16px !important;
            font-weight: 600 !important;
            color: {COLORS.PRIMARY_NAVY} !important;
            margin: 0 !important;
        }}

        .im-card-subtitle {{
            font-size: 13px !important;
            color: {COLORS.TEXT_MUTED} !important;
            margin: 2px 0 0 0 !important;
        }}

        /* MetricCards */
        .im-metric-card {{
            background-color: {COLORS.SURFACE};
            border: 1px solid {COLORS.BORDER};
            border-radius: {RADIUS.MD};
            padding: 14px 18px;
            box-shadow: {SHADOWS.SM};
        }}

        .im-metric-label {{
            font-size: 12px;
            font-weight: 600;
            color: {COLORS.TEXT_MUTED};
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }}

        .im-metric-value {{
            font-size: 24px;
            font-weight: 700;
            color: {COLORS.PRIMARY_NAVY};
            line-height: 1.2;
        }}

        .im-metric-delta {{
            font-size: 12px;
            font-weight: 600;
            margin-top: 4px;
        }}

        /* Streamlit native metric overrides */
        div[data-testid="stMetric"] {{
            background-color: {COLORS.SURFACE} !important;
            border: 1px solid {COLORS.BORDER} !important;
            border-radius: {RADIUS.MD} !important;
            padding: 14px 18px !important;
            box-shadow: {SHADOWS.SM} !important;
        }}

        div[data-testid="stMetricLabel"] {{
            font-size: 12px !important;
            font-weight: 600 !important;
            color: {COLORS.TEXT_MUTED} !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
        }}

        div[data-testid="stMetricValue"] {{
            font-size: 24px !important;
            font-weight: 700 !important;
            color: {COLORS.PRIMARY_NAVY} !important;
        }}

        /* ====================================================================
           5. BADGES SEMÂNTICOS & STATUS BADGES
           ==================================================================== */
        .im-badge {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            font-size: 12px;
            font-weight: 600;
            padding: 3px 10px;
            border-radius: {RADIUS.PILL};
            border: 1px solid transparent;
            line-height: 1.3;
        }}

        .badge-icon {{
            font-size: 11px;
            font-weight: 700;
        }}

        .im-status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            font-size: 11.5px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: {RADIUS.SM};
            border: 1px solid transparent;
        }}

        /* Classes semânticas oficiais */
        .badge-sem-equiv {{
            background-color: #E6F4EA !important;
            color: #197B5C !important;
            border-color: #A3D9B5 !important;
        }}

        .badge-sem-diff {{
            background-color: #FDE8E8 !important;
            color: #D94A4A !important;
            border-color: #F8B4B4 !important;
        }}

        .badge-sem-broader {{
            background-color: #E0F2F1 !important;
            color: #0B8A84 !important;
            border-color: #80CBC4 !important;
        }}

        .badge-sem-narrower {{
            background-color: #EFF6FF !important;
            color: #2864C7 !important;
            border-color: #BFDBFE !important;
        }}

        .badge-sem-scope {{
            background-color: #FEF3C7 !important;
            color: #B45309 !important;
            border-color: #FCD34D !important;
        }}

        .badge-sem-cond {{
            background-color: #F3E8FF !important;
            color: #7E22CE !important;
            border-color: #D8B4FE !important;
        }}

        .badge-sem-limit {{
            background-color: #E0E7FF !important;
            color: #3730A3 !important;
            border-color: #C7D2FE !important;
        }}

        /* ====================================================================
           6. DIFFERENCE CARD & EVIDÊNCIAS AUDITÁVEIS
           ==================================================================== */
        .im-difference-card {{
            background-color: {COLORS.SURFACE};
            border: 1px solid {COLORS.BORDER};
            border-radius: {RADIUS.MD};
            padding: 16px 20px;
            margin-bottom: 12px;
            box-shadow: {SHADOWS.SM};
        }}

        .im-diff-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}

        .im-diff-confidence {{
            font-size: 11.5px;
            color: {COLORS.TEXT_MUTED};
            font-weight: 500;
        }}

        .im-diff-title {{
            font-size: 15px;
            font-weight: 600;
            color: {COLORS.PRIMARY_NAVY};
            margin-bottom: 6px;
        }}

        .im-diff-pages {{
            font-size: 12.5px;
            color: {COLORS.TEXT_MUTED};
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .im-page-tag {{
            background-color: {COLORS.BACKGROUND};
            padding: 2px 6px;
            border-radius: {RADIUS.SM};
            border: 1px solid {COLORS.BORDER};
            font-family: {TYPOGRAPHY.FONT_CODE};
            font-size: 11.5px;
        }}

        .im-diff-explanation {{
            font-size: 13.5px;
            color: {COLORS.TEXT_MAIN};
            line-height: 1.5;
            background-color: {COLORS.SURFACE_MUTED};
            padding: 10px 14px;
            border-radius: {RADIUS.SM};
            border-left: 3px solid {COLORS.PRIMARY_BLUE};
        }}

        /* Painel e Snippet de Evidência */
        .im-evidence-panel {{
            background-color: {COLORS.SURFACE};
            border: 1px solid {COLORS.BORDER};
            border-radius: {RADIUS.MD};
            padding: 16px;
            margin-top: 10px;
            box-shadow: {SHADOWS.SM};
        }}

        .im-evidence-panel-title {{
            font-size: 13px;
            font-weight: 600;
            color: {COLORS.PRIMARY_NAVY};
            margin-bottom: 12px;
        }}

        .im-evidence-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }}

        .im-evidence-snippet {{
            background-color: {COLORS.SURFACE_MUTED};
            border: 1px solid {COLORS.BORDER};
            border-radius: {RADIUS.SM};
            padding: 12px 14px;
        }}

        .im-evidence-header {{
            display: flex;
            justify-content: space-between;
            font-size: 11.5px;
            color: {COLORS.TEXT_MUTED};
            margin-bottom: 8px;
            border-bottom: 1px solid {COLORS.BORDER};
            padding-bottom: 4px;
        }}

        .evidence-page {{
            color: {COLORS.PRIMARY_BLUE};
            font-weight: 600;
        }}

        .evidence-method {{
            font-family: {TYPOGRAPHY.FONT_CODE};
            font-size: 10.5px;
            background-color: #E2E8F0;
            padding: 1px 4px;
            border-radius: 2px;
        }}

        .im-evidence-content {{
            font-family: {TYPOGRAPHY.FONT_CODE};
            font-size: 12px;
            line-height: 1.6;
            color: {COLORS.TEXT_MAIN};
            white-space: pre-wrap;
            word-break: break-word;
        }}

        /* ====================================================================
           7. ESTADOS DO SISTEMA (Empty, Loading, Error, etc.)
           ==================================================================== */
        .im-state-box {{
            background-color: {COLORS.SURFACE};
            border: 1px solid {COLORS.BORDER};
            border-radius: {RADIUS.LG};
            padding: 32px 24px;
            text-align: center;
            margin: 16px 0;
            box-shadow: {SHADOWS.SM};
        }}

        .im-state-icon {{
            font-size: 32px;
            margin-bottom: 10px;
        }}

        .im-state-title {{
            font-size: 16px !important;
            font-weight: 600 !important;
            color: {COLORS.PRIMARY_NAVY} !important;
            margin: 0 0 6px 0 !important;
        }}

        .im-state-desc {{
            font-size: 13.5px !important;
            color: {COLORS.TEXT_MUTED} !important;
            max-width: 520px;
            margin: 0 auto !important;
            line-height: 1.5;
        }}

        /* Spinner corporativo discreto */
        .im-spinner {{
            width: 28px;
            height: 28px;
            border: 3px solid {COLORS.BORDER};
            border-top: 3px solid {COLORS.PRIMARY_BLUE};
            border-radius: 50%;
            animation: im-spin 0.8s linear infinite;
            margin: 0 auto 12px auto;
        }}

        @keyframes im-spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}

        /* Alertas Corporativos */
        .im-alert {{
            display: flex;
            align-items: flex-start;
            gap: 12px;
            padding: 12px 16px;
            border-radius: {RADIUS.MD};
            font-size: 13px;
            line-height: 1.5;
            margin-bottom: 14px;
            border: 1px solid transparent;
        }}

        .im-alert-icon {{
            font-size: 16px;
            line-height: 1;
            margin-top: 2px;
        }}

        .im-alert-info {{
            background-color: #EFF6FF;
            border-color: #BFDBFE;
            color: #1E40AF;
        }}

        .im-alert-success {{
            background-color: #E6F4EA;
            border-color: #A3D9B5;
            color: #166534;
        }}

        .im-alert-attention {{
            background-color: #FEF3C7;
            border-color: #FCD34D;
            color: #92400E;
        }}

        .im-alert-critical {{
            background-color: #FDE8E8;
            border-color: #F8B4B4;
            color: #991B1B;
        }}

        .im-alert-legal {{
            background-color: #F8FAFC;
            border-color: {COLORS.BORDER};
            border-left: 4px solid {COLORS.PRIMARY_NAVY};
            color: {COLORS.PRIMARY_NAVY};
        }}

        /* ====================================================================
           8. BOTÕES & CONTROLES STREAMLIT PADRÃO CORPORATIVO
           ==================================================================== */
        /* Botão Primário */
        button[kind="primary"], .stButton > button[kind="primary"] {{
            background-color: {COLORS.PRIMARY_BLUE} !important;
            color: #FFFFFF !important;
            border: 1px solid {COLORS.PRIMARY_BLUE} !important;
            padding: 8px 18px !important;
            font-weight: 600 !important;
            font-size: 13.5px !important;
            border-radius: {RADIUS.MD} !important;
            box-shadow: {SHADOWS.SM} !important;
            transition: all 0.15s ease !important;
        }}

        button[kind="primary"]:hover, .stButton > button[kind="primary"]:hover {{
            background-color: #1F4FA0 !important;
            border-color: #1F4FA0 !important;
            color: #FFFFFF !important;
        }}

        /* Botão Secundário */
        .stButton > button:not([kind="primary"]) {{
            background-color: {COLORS.SURFACE} !important;
            color: {COLORS.TEXT_MAIN} !important;
            border: 1px solid {COLORS.BORDER} !important;
            padding: 8px 16px !important;
            font-weight: 500 !important;
            font-size: 13.5px !important;
            border-radius: {RADIUS.MD} !important;
            box-shadow: {SHADOWS.SM} !important;
            transition: all 0.15s ease !important;
        }}

        .stButton > button:not([kind="primary"]):hover {{
            background-color: {COLORS.SURFACE_HOVER} !important;
            border-color: #B0C0D0 !important;
            color: {COLORS.PRIMARY_NAVY} !important;
        }}

        /* Botão de Download */
        .stDownloadButton > button {{
            background-color: {COLORS.SURFACE} !important;
            color: {COLORS.PRIMARY_BLUE} !important;
            border: 1px solid {COLORS.BORDER} !important;
            border-radius: {RADIUS.MD} !important;
            font-weight: 600 !important;
            font-size: 13px !important;
        }}

        .stDownloadButton > button:hover {{
            background-color: #EFF6FF !important;
            border-color: {COLORS.PRIMARY_BLUE} !important;
            color: {COLORS.PRIMARY_BLUE} !important;
        }}

        /* Inputs e Selects */
        div[data-baseweb="select"] > div {{
            background-color: {COLORS.SURFACE} !important;
            border: 1px solid {COLORS.BORDER} !important;
            border-radius: {RADIUS.MD} !important;
            color: {COLORS.TEXT_MAIN} !important;
        }}

        input {{
            color: {COLORS.TEXT_MAIN} !important;
            background-color: {COLORS.SURFACE} !important;
        }}

        /* Abas Streamlit Corporativas */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 4px !important;
            background-color: transparent !important;
            border-bottom: 2px solid {COLORS.BORDER} !important;
            padding: 0 !important;
        }}

        .stTabs [data-baseweb="tab"] {{
            background-color: transparent !important;
            border: none !important;
            color: {COLORS.TEXT_MUTED} !important;
            font-weight: 600 !important;
            font-size: 13.5px !important;
            padding: 10px 16px !important;
            border-bottom: 2px solid transparent !important;
            margin-bottom: -2px !important;
            transition: all 0.15s ease !important;
        }}

        .stTabs [data-baseweb="tab"]:hover {{
            color: {COLORS.PRIMARY_NAVY} !important;
            background-color: {COLORS.SURFACE_HOVER} !important;
        }}

        .stTabs [aria-selected="true"] {{
            color: {COLORS.PRIMARY_BLUE} !important;
            border-bottom: 2px solid {COLORS.PRIMARY_BLUE} !important;
            background-color: transparent !important;
        }}

        .stTabs [data-baseweb="tab-highlight"] {{
            display: none !important;
        }}

        /* Expanders */
        div[data-testid="stExpander"] {{
            background-color: {COLORS.SURFACE} !important;
            border: 1px solid {COLORS.BORDER} !important;
            border-radius: {RADIUS.MD} !important;
            box-shadow: {SHADOWS.SM} !important;
            margin-bottom: 10px !important;
        }}

        summary[data-testid="stExpanderToggle"] {{
            color: {COLORS.PRIMARY_NAVY} !important;
            font-weight: 600 !important;
            font-size: 13.5px !important;
        }}

        summary[data-testid="stExpanderToggle"]:hover {{
            color: {COLORS.PRIMARY_BLUE} !important;
        }}

        /* Tabelas e Dataframes */
        [data-testid="stDataFrame"] {{
            border: 1px solid {COLORS.BORDER} !important;
            border-radius: {RADIUS.MD} !important;
            background-color: {COLORS.SURFACE} !important;
        }}

        /* Barra de Progresso */
        div[data-testid="stProgressBar"] > div > div {{
            background: linear-gradient(90deg, {COLORS.PRIMARY_BLUE} 0%, {COLORS.SECONDARY_TEAL} 100%) !important;
            border-radius: {RADIUS.PILL} !important;
        }}

        /* ====================================================================
           9. CLASSES DE RETROCOMPATIBILIDADE PARA TELAS EXISTENTES
           ==================================================================== */
        .disclaimer-banner {{
            background-color: #F8FAFC;
            border: 1px solid {COLORS.BORDER};
            border-left: 4px solid {COLORS.PRIMARY_NAVY};
            padding: 12px 18px;
            border-radius: {RADIUS.MD};
            margin: 12px 0 20px 0;
            font-size: 13px;
            color: {COLORS.PRIMARY_NAVY};
        }}

        .doc-summary-card {{
            background-color: {COLORS.SURFACE};
            border: 1px solid {COLORS.BORDER};
            border-top: 3px solid {COLORS.PRIMARY_BLUE};
            border-radius: {RADIUS.MD};
            padding: 18px 22px;
            margin-bottom: 16px;
            box-shadow: {SHADOWS.SM};
        }}

        .substantive-card {{
            background-color: {COLORS.SURFACE};
            border: 1px solid {COLORS.BORDER};
            border-left: 4px solid {COLORS.CRITICAL};
            border-radius: {RADIUS.MD};
            padding: 16px 20px;
            margin-bottom: 14px;
            box-shadow: {SHADOWS.SM};
        }}

        .evidence-box {{
            background-color: {COLORS.SURFACE_MUTED};
            border: 1px solid {COLORS.BORDER};
            border-left: 3px solid {COLORS.PRIMARY_BLUE};
            border-radius: {RADIUS.SM};
            padding: 12px 16px;
            font-size: 12px;
            color: {COLORS.TEXT_MAIN};
            margin-top: 8px;
            font-family: {TYPOGRAPHY.FONT_CODE};
            line-height: 1.6;
        }}

        .coverage-box {{
            background-color: #E6F4EA;
            border: 1px solid #A3D9B5;
            border-left: 3px solid {COLORS.SUCCESS};
            padding: 10px 14px;
            margin-bottom: 8px;
            border-radius: {RADIUS.SM};
            font-size: 13px;
            color: #166534;
        }}

        .exclusion-box {{
            background-color: #FDE8E8;
            border: 1px solid #F8B4B4;
            border-left: 3px solid {COLORS.CRITICAL};
            padding: 10px 14px;
            margin-bottom: 8px;
            border-radius: {RADIUS.SM};
            font-size: 13px;
            color: #991B1B;
        }}

        .badge-tag {{
            display: inline-block;
            background-color: #E2E8F0;
            color: {COLORS.PRIMARY_NAVY};
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            padding: 2px 8px;
            border-radius: {RADIUS.SM};
            margin-bottom: 6px;
        }}

        /* ====================================================================
           10. ASSISTENTE CONTEXTUAL — COPILOTO DE LEITURA (FASE 7.9)
           ==================================================================== */
        .im-assistant-panel {{
            background-color: {COLORS.SURFACE};
            border: 1px solid #CBD5E1;
            border-top: 4px solid {COLORS.PRIMARY_BLUE};
            border-radius: {RADIUS.MD};
            padding: 18px 22px;
            margin-bottom: 20px;
            box-shadow: {SHADOWS.MD};
        }}

        .im-assistant-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }}

        .im-assistant-context-bar {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            align-items: center;
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            padding: 8px 14px;
            border-radius: {RADIUS.SM};
            margin: 10px 0 16px 0;
            font-size: 12px;
            color: {COLORS.TEXT_MAIN};
        }}

        .im-assistant-box {{
            background-color: {COLORS.SURFACE};
            border: 1px solid #D9E1E8;
            border-radius: {RADIUS.SM};
            padding: 16px 18px;
            margin-top: 14px;
            font-size: 13px;
            line-height: 1.6;
            color: {COLORS.TEXT_MAIN};
        }}

        .im-assistant-gov-box {{
            background-color: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: {RADIUS.SM};
            padding: 8px 12px;
            font-size: 11px;
            color: #475569;
            margin-top: 14px;
            line-height: 1.4;
        }}
        </style>
    """)
