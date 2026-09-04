"""Design System & Harmonização de Cores para o Mercado Segurador e Ressegurador.
Inspirado nos padrões visuais de líderes globais (Swiss Re, Munich Re, Lloyd's of London, Allianz e Chubb).
Prioriza alta credibilidade, contraste executivo, sofisticação tipográfica e experiência do usuário (UX).
"""
import streamlit as st


def apply_custom_styles():
    """Injeta o ecossistema visual de alta fidelidade para o InsurMinds Apólice Analyzer."""
    st.markdown("""
        <style>
        /* ====================================================================
           1. TIPOGRAFIA & BASE GLOBAL (Inter & Plus Jakarta Sans)
           ==================================================================== */
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
            color: #0F172A;
            background-color: #F8FAFC;
        }

        /* Redução de espaçamentos superiores excessivos do Streamlit */
        .block-container {
            padding-top: 1.8rem !important;
            padding-bottom: 3.5rem !important;
            max-width: 1280px !important;
        }

        /* ====================================================================
           2. BANNER EXECUTIVO INSTITUCIONAL (Mercado Segurador & Ressegurador)
           ==================================================================== */
        .insurminds-header {
            background: linear-gradient(135deg, #0A192F 0%, #0F253E 50%, #16325B 100%);
            border-bottom: 3px solid #C5A059; /* Dourado nobre de resseguro */
            color: #FFFFFF;
            padding: 26px 32px;
            border-radius: 14px;
            margin-bottom: 28px;
            box-shadow: 0 10px 30px -5px rgba(10, 25, 47, 0.25), 0 4px 6px -2px rgba(10, 25, 47, 0.1);
            position: relative;
            overflow: hidden;
        }

        .insurminds-header::after {
            content: "";
            position: absolute;
            top: -40px;
            right: -40px;
            width: 180px;
            height: 180px;
            background: radial-gradient(circle, rgba(2, 132, 199, 0.2) 0%, rgba(2, 132, 199, 0) 70%);
            pointer-events: none;
        }

        .insurminds-header .badge-tag {
            display: inline-block;
            background: rgba(197, 160, 89, 0.18);
            color: #F3E8C8;
            border: 1px solid rgba(197, 160, 89, 0.4);
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 3px 10px;
            border-radius: 20px;
            margin-bottom: 8px;
        }

        .insurminds-header h1 {
            color: #FFFFFF !important;
            font-size: 26px !important;
            font-weight: 800 !important;
            margin: 0 !important;
            letter-spacing: -0.5px;
            line-height: 1.2;
        }

        .insurminds-header p {
            color: #CBD5E1 !important;
            font-size: 14px !important;
            margin: 8px 0 0 0 !important;
            font-weight: 400;
            max-width: 800px;
        }

        /* ====================================================================
           3. BARRA LATERAL CORPORATIVA (Deep Midnight Slate)
           ==================================================================== */
        [data-testid="stSidebar"] {
            background: #0A192F !important;
            border-right: 1px solid #1E293B !important;
        }

        [data-testid="stSidebar"] * {
            color: #F1F5F9 !important;
        }

        [data-testid="stSidebar"] hr {
            border-color: #1E293B !important;
        }

        [data-testid="stSidebar"] .stRadio label {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.06);
            padding: 8px 14px;
            border-radius: 8px;
            margin-bottom: 6px;
            transition: all 0.2s ease;
            cursor: pointer;
        }

        [data-testid="stSidebar"] .stRadio label:hover {
            background: rgba(2, 132, 199, 0.15) !important;
            border-color: rgba(2, 132, 199, 0.4) !important;
        }

        /* ====================================================================
           4. CARTÕES DE MÉTRICAS & KPIS EXECUTIVOS
           ==================================================================== */
        div[data-testid="stMetric"] {
            background: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 12px !important;
            padding: 16px 20px !important;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04) !important;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        div[data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08) !important;
            border-color: #CBD5E1 !important;
        }

        div[data-testid="stMetricLabel"] {
            font-size: 13px !important;
            font-weight: 600 !important;
            color: #64748B !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
        }

        div[data-testid="stMetricValue"] {
            font-size: 28px !important;
            font-weight: 800 !important;
            color: #0A192F !important;
        }

        /* ====================================================================
           5. BOTÕES & INTERATIVIDADE
           ==================================================================== */
        /* Botão Primário (Azul Institucional / Royal Azure) */
        button[kind="primary"], .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #0284C7 0%, #0369A1 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            padding: 10px 22px !important;
            font-weight: 600 !important;
            font-size: 14px !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 12px rgba(2, 132, 199, 0.25) !important;
            transition: all 0.2s ease-in-out !important;
        }

        button[kind="primary"]:hover, .stButton > button[kind="primary"]:hover {
            background: linear-gradient(135deg, #0369A1 0%, #075985 100%) !important;
            box-shadow: 0 6px 18px rgba(2, 132, 199, 0.35) !important;
            transform: translateY(-1px);
        }

        /* Botão Secundário / Padrão */
        .stButton > button:not([kind="primary"]) {
            background-color: #FFFFFF !important;
            color: #0F172A !important;
            border: 1px solid #CBD5E1 !important;
            padding: 9px 18px !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
            transition: all 0.15s ease-in-out !important;
        }

        .stButton > button:not([kind="primary"]):hover {
            border-color: #0284C7 !important;
            color: #0284C7 !important;
            background-color: #F8FAFC !important;
            transform: translateY(-1px);
        }

        /* Botão de Download */
        .stDownloadButton > button {
            background-color: #FFFFFF !important;
            color: #0F253E !important;
            border: 1.5px solid #0F253E !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
        }

        .stDownloadButton > button:hover {
            background-color: #0F253E !important;
            color: #FFFFFF !important;
        }

        /* ====================================================================
           6. CAIXAS DE COBERTURA, EXCLUSÃO E RISCO (Harmonização Semântica)
           ==================================================================== */
        /* Cobertura Exclusiva / Vantajosa (Emerald / Teal) */
        .coverage-box {
            background: #F0FDF4;
            border: 1px solid #BBF7D0;
            border-left: 4px solid #10B981;
            padding: 12px 16px;
            margin-bottom: 10px;
            border-radius: 8px;
            font-size: 13.5px;
            color: #065F46;
            line-height: 1.4;
            box-shadow: 0 1px 3px rgba(16, 185, 129, 0.05);
        }

        /* Cobertura Neutra / Em Comum */
        .common-box {
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-left: 4px solid #64748B;
            padding: 10px 14px;
            margin-bottom: 8px;
            border-radius: 8px;
            font-size: 13px;
            color: #334155;
        }

        /* Exclusão / Risco Crítico (Crimson / Ruby) */
        .exclusion-box {
            background: #FEF2F2;
            border: 1px solid #FECACA;
            border-left: 4px solid #EF4444;
            padding: 12px 16px;
            margin-bottom: 10px;
            border-radius: 8px;
            font-size: 13.5px;
            color: #991B1B;
            line-height: 1.4;
            box-shadow: 0 1px 3px rgba(239, 68, 68, 0.05);
        }

        /* Alerta de Divergência Financeira (Amber Gold) */
        .divergence-box {
            background: #FFFBEB;
            border: 1px solid #FDE68A;
            border-left: 4px solid #F59E0B;
            padding: 12px 16px;
            margin-bottom: 10px;
            border-radius: 8px;
            font-size: 13.5px;
            color: #92400E;
        }

        /* ====================================================================
           7. BADGES DE CONFORMIDADE & STATUS
           ==================================================================== */
        .badge-equal {
            background: #ECFDF5;
            color: #065F46;
            border: 1px solid #A7F3D0;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }

        .badge-diff {
            background: #FFFBEB;
            color: #B45309;
            border: 1px solid #FDE68A;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }

        .badge-missing {
            background: #FEF2F2;
            color: #B91C1C;
            border: 1px solid #FECACA;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }

        /* ====================================================================
           8. TABELAS & DATAFRAMES
           ==================================================================== */
        div[data-testid="stDataFrame"] {
            border: 1px solid #E2E8F0 !important;
            border-radius: 10px !important;
            overflow: hidden !important;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04) !important;
        }

        /* Expanders elegantes */
        .streamlit-expanderHeader {
            background-color: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            color: #0F253E !important;
            font-size: 14.5px !important;
        }

        /* Barra de Progresso elegante */
        div[data-testid="stProgressBar"] > div > div {
            background: linear-gradient(90deg, #0284C7 0%, #10B981 100%) !important;
            border-radius: 10px !important;
        }
        </style>
    """, unsafe_allow_html=True)
