"""Página de Início de Análise Contratual D&O — Insurance Intelligence v1.0.
Gerencia a recepção e confronto inicial de documentos contratuais D&O (Documento A de referência
e Documento B para comparação), validação de integridade, telemetria por tarefas e atalhos aos benchmarks oficiais.
"""
import io
from pathlib import Path
from typing import Optional, List, Tuple
import streamlit as st
import pdfplumber

from core.config import UPLOADS_DIR, DATASET_DO_DIR, SAMPLE_POLICIES_DIR, MAX_FILE_SIZE_MB, GEMINI_MODEL, IMAGE_EXTENSIONS
from core.security import get_safe_destination_path, validate_pdf_content, validate_document_content
from core.database import db
from core.schemas import ApoliceDAO
from core.llm_client import llm_client
from ui.navigation import navigate_to
from ui.persona.profiles import get_active_profile
from ui.tokens import COLORS, TYPOGRAPHY, RADIUS, SHADOWS
from ui.components.states import (
    render_alert,
    render_empty_state,
    render_loading_state,
    render_success_state,
    render_partial_state,
    render_error_state,
    render_fallback_state
)
from agents.graph import run_document_pipeline_with_progress

# Aviso Legal Obrigatório (Preservado para conformidade com Requisito 10 e suíte de testes)
MANDATORY_DISCLAIMER = "A análise é assistida por IA e não substitui a avaliação jurídica, técnica ou de subscrição."


def render_upload_page():
    """Renderiza a experiência profissional de Nova Análise D&O."""
    # 1. TÍTULO E SUBTÍTULO OFICIAIS
    st.markdown(f"""
        <div style="margin-bottom: 16px;">
            <h2 style="color:{COLORS.PRIMARY_NAVY}; font-size:24px; font-weight:700; margin:0 0 6px 0; font-family:{TYPOGRAPHY.FONT_UI};">
                NOVA ANÁLISE
            </h2>
            <p style="color:{COLORS.TEXT_MUTED}; font-size:14px; margin:0; font-family:{TYPOGRAPHY.FONT_UI}; line-height:1.5;">
                Compare documentos D&O e identifique alterações relevantes com evidências rastreáveis.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Aviso Legal Obrigatório
    st.markdown(f"""
        <div class="disclaimer-banner">
            🛡️ <strong>Aviso Legal Obrigatório:</strong> {MANDATORY_DISCLAIMER}
        </div>
    """, unsafe_allow_html=True)

    # Status do Motor Analítico / Fallback
    if llm_client.is_available():
        st.markdown(f"""
            <div style="display:inline-flex; align-items:center; gap:8px; background:#EFF6FF; border:1px solid #BFDBFE; padding:5px 14px; border-radius:20px; font-size:12px; color:#1E40AF; margin-bottom:18px;">
                <span style="width:7px; height:7px; border-radius:50%; background:#2563EB;"></span>
                <b>Motor de IA Ativo:</b> Google Gemini (<code>{GEMINI_MODEL}</code>) com Structured Output em tempo real.
            </div>
        """, unsafe_allow_html=True)
    else:
        col_ban_up_txt, col_ban_up_btn = st.columns([3.8, 1.2])
        with col_ban_up_txt:
            st.markdown("""
                <div style="background:#FFFBEB; border:1px solid #FDE68A; border-left:4px solid #D97706; border-radius:6px; padding:10px 14px; margin-bottom:14px;">
                    <div style="font-weight:700; font-size:12.5px; color:#92400E;">⚠️ IA Generativa não configurada</div>
                    <div style="font-size:12px; color:#B45309; margin-top:2px;">
                        Para executar a análise com Gemini, configure sua chave do Google AI Studio.
                    </div>
                </div>
            """, unsafe_allow_html=True)
        with col_ban_up_btn:
            st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
            if st.button("⚙️ Configurar IA", key="btn_cfg_ai_upload", use_container_width=True):
                navigate_to("Configurações")
                st.rerun()

        render_fallback_state("Modo de contingência ativo — análise utilizando regras determinísticas regulatórias da SUSEP.")

    # 5. TIPO DOCUMENTAL (D&O no MVP — Fixo e sem fricção)
    st.markdown(f"""
        <div style="display:inline-flex; align-items:center; gap:8px; background:#F8FAFC; border:1px solid {COLORS.BORDER}; padding:6px 14px; border-radius:6px; font-size:12.5px; color:{COLORS.PRIMARY_NAVY}; margin-bottom:20px;">
            <span style="font-weight:700;">📋 Tipo documental:</span>
            <span style="color:{COLORS.PRIMARY_BLUE}; font-weight:600;">D&O · Responsabilidade Civil de Administradores</span>
            <span style="color:{COLORS.TEXT_MUTED}; font-size:12px;">(Ramo SUSEP 0378 · Identificação automática no backend)</span>
        </div>
    """, unsafe_allow_html=True)

    # Se já existirem documentos ativos e estruturados na sessão
    doc_a = st.session_state.get("active_doc_a")
    doc_b = st.session_state.get("active_doc_b")

    if doc_a and doc_b:
        _render_structured_success_view(doc_a, doc_b)
        st.markdown("---")
        st.markdown(f"""
            <div style="margin: 20px 0 10px 0;">
                <h4 style="font-size:16px; font-weight:700; color:{COLORS.PRIMARY_NAVY}; margin:0 0 4px 0;">
                    Iniciar Nova Comparação Contratual
                </h4>
                <p style="font-size:13px; color:{COLORS.TEXT_MUTED}; margin:0;">
                    Substitua os arquivos abaixo ou escolha um benchmark para analisar outro par de apólices D&O.
                </p>
            </div>
        """, unsafe_allow_html=True)

    # Indicação de Documento Pré-selecionado da Biblioteca (Fase 7.10)
    selected_pre = st.session_state.get("selected_for_compare", [])
    if len(selected_pre) == 1 and isinstance(selected_pre[0], ApoliceDAO):
        pre_doc = selected_pre[0]
        st.markdown(f"""
            <div style="background:#EFF6FF; border:1px solid #BFDBFE; border-left:4px solid {COLORS.PRIMARY_BLUE}; border-radius:{RADIUS.MD}; padding:12px 16px; margin-bottom:18px; font-size:13px; color:{COLORS.PRIMARY_NAVY};">
                📑 <b>Documento pré-selecionado da Biblioteca:</b> <b>{pre_doc.seguradora or 'Seguradora'}</b> — <code>{pre_doc.nome_arquivo}</code>.<br/>
                <span style="font-size:12px; color:{COLORS.TEXT_MUTED};">Você pode carregar o Documento B para confronto direto ou utilizar os atalhos de benchmark abaixo.</span>
            </div>
        """, unsafe_allow_html=True)

    # 4. INDICADOR VISUAL A ↔ B
    st.markdown(f"""
        <div style="display:flex; justify-content:center; align-items:center; margin:10px 0 20px 0;">
            <div style="display:inline-flex; align-items:center; gap:12px; background:{COLORS.SURFACE}; border:1px solid {COLORS.BORDER}; padding:8px 22px; border-radius:30px; box-shadow:{SHADOWS.SM};">
                <span style="font-weight:700; color:{COLORS.PRIMARY_NAVY}; font-size:13px;">Documento de referência (A)</span>
                <span style="color:{COLORS.PRIMARY_BLUE}; font-weight:800; font-size:16px;">⟷</span>
                <span style="font-weight:700; color:{COLORS.PRIMARY_NAVY}; font-size:13px;">Documento para comparação (B)</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 2 & 3. ÁREAS DE INGESTÃO DOCUMENTO A E DOCUMENTO B
    col_up_a, col_up_b = st.columns(2)

    with col_up_a:
        st.markdown(f"""
            <div style="background:{COLORS.SURFACE}; border:1px solid {COLORS.BORDER}; border-top:3px solid {COLORS.PRIMARY_BLUE}; border-radius:{RADIUS.MD}; padding:14px 18px; margin-bottom:12px; box-shadow:{SHADOWS.SM};">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <span style="font-size:11px; font-weight:700; text-transform:uppercase; color:{COLORS.PRIMARY_BLUE}; letter-spacing:0.5px;">Documento A</span>
                    <span style="font-size:11.5px; background:#EFF6FF; color:{COLORS.PRIMARY_BLUE}; padding:2px 8px; border-radius:4px; font-weight:600;">Base / Referência</span>
                </div>
                <h4 style="margin:0 0 4px 0; font-size:15px; font-weight:700; color:{COLORS.PRIMARY_NAVY};">Documento de referência</h4>
                <p style="margin:0; font-size:12.5px; color:{COLORS.TEXT_MUTED};">Apólice base, versão anterior ou contrato vigente para cotejo.</p>
            </div>
        """, unsafe_allow_html=True)

        file_a = st.file_uploader(
            "Selecione o Documento de referência (A) — PDF ou imagem (PNG, JPG, JPEG)",
            type=["pdf", "png", "jpg", "jpeg"],
            key="uploader_doc_a",
            help="Documento contratual de referência em formato PDF ou imagem (PNG, JPG, JPEG)."
        )

        valid_a, info_a = _inspect_and_validate_file(file_a, "Documento A")

        if file_a is None and len(selected_pre) == 1 and isinstance(selected_pre[0], ApoliceDAO):
            pre_a = selected_pre[0]
            st.markdown(f"""
                <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:{RADIUS.MD}; padding:12px 14px; margin-top:8px;">
                    <div style="font-size:11px; font-weight:700; color:{COLORS.SUCCESS}; text-transform:uppercase;">✓ Acervo Vinculado (Doc A)</div>
                    <div style="font-size:13px; font-weight:700; color:{COLORS.PRIMARY_NAVY}; margin:2px 0;">{pre_a.seguradora or 'Seguradora'} · {pre_a.nome_arquivo}</div>
                    <div style="font-size:11.5px; color:{COLORS.TEXT_MUTED};">LMG: {pre_a.limite_responsabilidade or 'N/A'} · Processo SUSEP: {pre_a.processo_susep or 'N/A'}</div>
                </div>
            """, unsafe_allow_html=True)

    with col_up_b:
        st.markdown(f"""
            <div style="background:{COLORS.SURFACE}; border:1px solid {COLORS.BORDER}; border-top:3px solid {COLORS.SECONDARY_TEAL}; border-radius:{RADIUS.MD}; padding:14px 18px; margin-bottom:12px; box-shadow:{SHADOWS.SM};">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <span style="font-size:11px; font-weight:700; text-transform:uppercase; color:{COLORS.SECONDARY_TEAL}; letter-spacing:0.5px;">Documento B</span>
                    <span style="font-size:11.5px; background:#F0FDFA; color:{COLORS.SECONDARY_TEAL}; padding:2px 8px; border-radius:4px; font-weight:600;">Comparação</span>
                </div>
                <h4 style="margin:0 0 4px 0; font-size:15px; font-weight:700; color:{COLORS.PRIMARY_NAVY};">Documento para comparação</h4>
                <p style="margin:0; font-size:12.5px; color:{COLORS.TEXT_MUTED};">Documento para comparação, renovação ou apólice concorrente.</p>
            </div>
        """, unsafe_allow_html=True)

        file_b = st.file_uploader(
            "Selecione o Documento para comparação (B) — PDF ou imagem (PNG, JPG, JPEG)",
            type=["pdf", "png", "jpg", "jpeg"],
            key="uploader_doc_b",
            help="Documento a ser confrontado contra o Documento de referência em formato PDF ou imagem (PNG, JPG, JPEG)."
        )

        valid_b, info_b = _inspect_and_validate_file(file_b, "Documento B")

    # 6. CTA PRINCIPAL COM ADAPTAÇÃO DE PERSONA (Requisitos 6 e 9)
    profile = get_active_profile()
    cta_label, persona_microcopy = _get_persona_cta(profile.id)

    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)

    col_cta_btn, col_cta_msg = st.columns([1.5, 2.5])

    both_valid = valid_a and valid_b

    with col_cta_btn:
        start_clicked = st.button(
            f"▶ {cta_label}",
            type="primary",
            disabled=not both_valid,
            key="btn_run_analysis_cta",
            help="Inicia o pipeline multi-agente de extração e confronto estruturado." if both_valid else "Selecione dois documentos válidos (PDF ou imagem PNG/JPG/JPEG) para habilitar a análise."
        )

    with col_cta_msg:
        if both_valid:
            st.markdown(f"""
                <div style="display:flex; align-items:center; gap:8px; height:100%; font-size:13px; color:{COLORS.SUCCESS}; font-weight:600;">
                    <span>✓</span> Ambos os documentos foram validados e estão prontos para análise contratual.
                </div>
                <div style="font-size:11.5px; color:{COLORS.TEXT_MUTED}; margin-top:2px;">
                    {persona_microcopy}
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div style="display:flex; align-items:center; gap:8px; height:100%; font-size:13px; color:{COLORS.TEXT_MUTED};">
                    <span>ℹ</span> Selecione dois documentos (PDF ou imagem PNG/JPG/JPEG) para continuar.
                </div>
                <div style="font-size:11.5px; color:{COLORS.TEXT_MUTED}; margin-top:2px;">
                    {persona_microcopy}
                </div>
            """, unsafe_allow_html=True)

    if start_clicked and both_valid:
        _process_uploaded_pair(file_a, file_b)

    # 7. ATALHOS OFICIAIS DO CORPUS (Sompo v1.2 x v1.5 e Chubb 2024 x 2025)
    _render_official_benchmarks()


def _inspect_and_validate_file(uploaded_file, label: str) -> Tuple[bool, dict]:
    """Inspeciona arquivo carregado e exibe metadados prévios e status de validação."""
    if uploaded_file is None:
        # Estado: Empty
        st.markdown(f"""
            <div style="border:1px dashed {COLORS.BORDER}; border-radius:{RADIUS.MD}; padding:16px; text-align:center; background:#FAFCFE; margin-top:8px;">
                <div style="font-size:20px; color:{COLORS.TEXT_MUTED}; margin-bottom:4px;">📄</div>
                <div style="font-size:12.5px; color:{COLORS.TEXT_MUTED};">Nenhum arquivo selecionado.</div>
                <div style="font-size:11px; color:#94A3B8;">Arraste o documento (PDF ou imagem PNG/JPG/JPEG) ou utilize o seletor acima.</div>
            </div>
        """, unsafe_allow_html=True)
        return False, {}

    # Estado: File Selected
    file_bytes = uploaded_file.getvalue()
    filename = uploaded_file.name
    size_kb = len(file_bytes) / 1024
    size_str = f"{size_kb / 1024:.2f} MB" if size_kb > 1024 else f"{size_kb:.1f} KB"

    ext = Path(filename).suffix.lower()
    is_image = ext in IMAGE_EXTENSIONS

    # Validação rigorosa do conteúdo binário (magic bytes)
    is_valid, validation_msg, _ = validate_document_content(file_bytes, filename)

    if not is_valid:
        # Estado: Validation Error
        header_err = "Não foi possível ler esta imagem." if is_image else "Não foi possível validar este arquivo."
        st.markdown(f"""
            <div style="background:#FDE8E8; border:1px solid #F8B4B4; border-radius:{RADIUS.MD}; padding:14px; margin-top:8px;">
                <div style="display:flex; align-items:center; gap:8px; color:{COLORS.CRITICAL}; font-weight:700; font-size:13px;">
                    <span>✕</span> {header_err}
                </div>
                <div style="font-size:12px; color:{COLORS.CRITICAL}; margin-top:4px;">{validation_msg}</div>
            </div>
        """, unsafe_allow_html=True)
        return False, {"error": validation_msg}

    # Estado: Validation Success
    if is_image:
        fmt_str = f"Imagem ({ext[1:].upper()})"
        badge_text = f"✓ Imagem válida ({ext[1:].upper()})"
        pages_count = 1
        pages_str = "1 página (Imagem / OCR)"
    else:
        fmt_str = "PDF"
        badge_text = "✓ Arquivo PDF válido"
        pages_count = _get_pdf_page_count(file_bytes)
        pages_str = f"{pages_count} página(s)" if pages_count else "Não determinado"

    # Verifica se já está catalogado no banco de dados para recuperar seguradora/tipo prévio
    cached_dao = _find_cached_apolice_by_filename(filename)
    seguradora_str = cached_dao.seguradora if cached_dao and cached_dao.seguradora else "Identificada na análise"
    tipo_str = "Condições Gerais D&O" if cached_dao and cached_dao.document_type == "condicoes_gerais" else (cached_dao.document_type if cached_dao else "D&O (Identificação automática)")

    st.markdown(f"""
        <div style="background:{COLORS.SURFACE}; border:1px solid {COLORS.BORDER}; border-radius:{RADIUS.MD}; padding:14px 16px; margin-top:8px; box-shadow:{SHADOWS.SM};">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-size:11px; background:#E6F4EA; color:{COLORS.SUCCESS}; border:1px solid #A3D9B5; padding:2px 8px; border-radius:4px; font-weight:700;">
                    {badge_text}
                </span>
                <span style="font-size:11px; color:{COLORS.TEXT_MUTED}; font-family:{TYPOGRAPHY.FONT_CODE};">
                    {size_str}
                </span>
            </div>
            <div style="font-weight:700; font-size:13px; color:{COLORS.PRIMARY_NAVY}; margin-bottom:6px; word-break:break-all;">
                {filename}
            </div>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:6px; font-size:12px; color:{COLORS.TEXT_MAIN}; background:#F8FAFC; padding:8px 10px; border-radius:6px;">
                <div><b>Formato:</b> <span style="color:{COLORS.PRIMARY_BLUE}; font-weight:600;">{fmt_str}</span></div>
                <div><b>Páginas:</b> {pages_str}</div>
                <div><b>Seguradora:</b> <span style="color:{COLORS.PRIMARY_BLUE};">{seguradora_str}</span></div>
                <div><b>Status:</b> <span style="color:{COLORS.SUCCESS}; font-weight:600;">Pronto para análise</span></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    return True, {
        "filename": filename,
        "format": fmt_str,
        "size_str": size_str,
        "pages": pages_count,
        "seguradora": seguradora_str,
        "tipo": tipo_str
    }


def _get_pdf_page_count(file_bytes: bytes) -> Optional[int]:
    """Obtém a contagem de páginas do PDF com segurança."""
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            return len(pdf.pages)
    except Exception:
        return None


def _find_cached_apolice_by_filename(filename: str) -> Optional[ApoliceDAO]:
    """Verifica se o documento já está persistido no repositório SQLite."""
    try:
        existing = db.get_apolice_by_id(filename)
        if existing:
            return existing
        for pol in db.list_apolices():
            if pol.nome_arquivo == filename:
                return pol
    except Exception:
        pass
    return None


def _get_persona_cta(profile_id: str) -> Tuple[str, str]:
    """Retorna o rótulo do CTA e o microcopy contextual conforme o perfil ativo (Requisito 9)."""
    configs = {
        "analista": (
            "Comparar documentos",
            "Prioridade: granularidade de cláusulas, rastreabilidade e equivalência técnica."
        ),
        "subscritor": (
            "Avaliar alterações contratuais",
            "Prioridade: alterações de escopo, limites de garantia e exposição de risco."
        ),
        "corretor": (
            "Comparar alternativas",
            "Prioridade: confronto de cláusulas, diferenciais e síntese executiva."
        ),
        "juridico": (
            "Revisar alterações e evidências",
            "Prioridade: redação literal, circulares SUSEP e evidências auditadas."
        ),
        "visitante": (
            "Iniciar análise D&O",
            "Modo de exploração: visão panorâmica das apólices corporativas D&O."
        )
    }
    return configs.get(profile_id, ("Iniciar análise", "Confronto estruturado e rastreável de apólices D&O."))


def _render_official_benchmarks():
    """Renderiza a seção de atalhos discretos para os benchmarks oficiais do corpus (Requisito 7)."""
    st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
    st.markdown(f"""
        <div style="background:{COLORS.SURFACE}; border:1px solid {COLORS.BORDER}; border-radius:{RADIUS.MD}; padding:18px 20px; box-shadow:{SHADOWS.SM};">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
                <div>
                    <h4 style="margin:0 0 4px 0; font-size:15px; font-weight:700; color:{COLORS.PRIMARY_NAVY};">
                        ⚡ Benchmarks Oficiais do Corpus D&O
                    </h4>
                    <p style="margin:0; font-size:12.5px; color:{COLORS.TEXT_MUTED};">
                        Pares contratuais auditados do dataset oficial para validação imediata sem upload externo:
                    </p>
                </div>
                <span style="font-size:11px; background:#F1F5F9; color:{COLORS.PRIMARY_NAVY}; padding:3px 8px; border-radius:4px; font-weight:600;">
                    Corpus Auditado D&O
                </span>
            </div>
    """, unsafe_allow_html=True)

    has_ext_sompo = (DATASET_DO_DIR / "DO_SOMPO_CONDICOES_GERAIS_V1_2_2024_010.pdf").exists()
    has_samples = (SAMPLE_POLICIES_DIR / "apolice_do_allianz.pdf").exists() and (SAMPLE_POLICIES_DIR / "apolice_do_chubb.pdf").exists()

    col_bm1, col_bm2 = st.columns(2)

    if has_ext_sompo:
        with col_bm1:
            st.markdown(f"""
                <div style="background:#F8FAFC; border:1px solid {COLORS.BORDER}; border-radius:6px; padding:14px; height:100%; display:flex; flex-direction:column; justify-content:space-between;">
                    <div>
                        <div style="font-size:11px; font-weight:700; color:{COLORS.PRIMARY_BLUE}; text-transform:uppercase; margin-bottom:4px;">Par 1 · Sompo Seguros</div>
                        <div style="font-weight:700; font-size:14px; color:{COLORS.PRIMARY_NAVY}; margin-bottom:6px;">Sompo v1.2 (2024) × Sompo v1.5 (2025)</div>
                        <p style="font-size:12px; color:{COLORS.TEXT_MUTED}; line-height:1.4; margin-bottom:12px;">
                            Avalia a evolução contratual: introdução da <b>Cláusula 18.6.1</b> (Agravamento do Risco) e alteração substantiva na <b>Cláusula 16.10</b> (Inadimplemento do Prêmio).
                        </p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Carregar Benchmark Sompo (DO010 × DO012)", key="btn_bm_sompo", type="secondary"):
                _process_preset_pair(
                    "DO_SOMPO_CONDICOES_GERAIS_V1_2_2024_010.pdf",
                    "DO_SOMPO_CONDICOES_GERAIS_V1_5_2025_012.pdf"
                )

        with col_bm2:
            st.markdown(f"""
                <div style="background:#F8FAFC; border:1px solid {COLORS.BORDER}; border-radius:6px; padding:14px; height:100%; display:flex; flex-direction:column; justify-content:space-between;">
                    <div>
                        <div style="font-size:11px; font-weight:700; color:{COLORS.SECONDARY_TEAL}; text-transform:uppercase; margin-bottom:4px;">Par 2 · Chubb Seguros</div>
                        <div style="font-weight:700; font-size:14px; color:{COLORS.PRIMARY_NAVY}; margin-bottom:6px;">Chubb Oferta Pública 2024 × 2025</div>
                        <p style="font-size:12px; color:{COLORS.TEXT_MUTED}; line-height:1.4; margin-bottom:12px;">
                            Avalia a reestruturação contratual: inclusão de <b>Despesas de Contenção e Salvamento</b> e modificação substantiva nos <b>Custos de Defesa</b>.
                        </p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Carregar Benchmark Chubb (DO005 × DO014)", key="btn_bm_chubb", type="secondary"):
                _process_preset_pair(
                    "DO_CHUBB_CONDICOES_GERAIS_OFERTA_PUBLICA_2024_005.pdf",
                    "DO_CHUBB_CONDICOES_GERAIS_OFERTA_PUBLICA_2025_014.pdf"
                )
    else:
        with col_bm1:
            st.markdown(f"""
                <div style="background:#F8FAFC; border:1px solid {COLORS.BORDER}; border-radius:6px; padding:14px; height:100%; display:flex; flex-direction:column; justify-content:space-between;">
                    <div>
                        <div style="font-size:11px; font-weight:700; color:{COLORS.PRIMARY_BLUE}; text-transform:uppercase; margin-bottom:4px;">Par 1 · Confronto Concorrencial</div>
                        <div style="font-weight:700; font-size:14px; color:{COLORS.PRIMARY_NAVY}; margin-bottom:6px;">Allianz D&O × Chubb D&O</div>
                        <p style="font-size:12px; color:{COLORS.TEXT_MUTED}; line-height:1.4; margin-bottom:12px;">
                            Avalia a divergência entre seguradoras: confronto de <b>Limites Máximos de Garantia</b>, franquias e escopo de coberturas de custos de defesa.
                        </p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Carregar Benchmark Allianz × Chubb", key="btn_bm_allianz_chubb", type="secondary"):
                _process_preset_pair(
                    "apolice_do_allianz.pdf",
                    "apolice_do_chubb.pdf"
                )

        with col_bm2:
            st.markdown(f"""
                <div style="background:#F8FAFC; border:1px solid {COLORS.BORDER}; border-radius:6px; padding:14px; height:100%; display:flex; flex-direction:column; justify-content:space-between;">
                    <div>
                        <div style="font-size:11px; font-weight:700; color:{COLORS.SECONDARY_TEAL}; text-transform:uppercase; margin-bottom:4px;">Par 2 · Evolução Contratual</div>
                        <div style="font-weight:700; font-size:14px; color:{COLORS.PRIMARY_NAVY}; margin-bottom:6px;">Allianz D&O × Endosso de Alteração</div>
                        <p style="font-size:12px; color:{COLORS.TEXT_MUTED}; line-height:1.4; margin-bottom:12px;">
                            Avalia alteração de apólice por endosso: aumento de LMG para <b>R$ 30.000.000,00</b> e extensão do período de retroatividade.
                        </p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Carregar Benchmark Allianz × Endosso", key="btn_bm_allianz_endosso", type="secondary"):
                _process_preset_pair(
                    "apolice_do_allianz.pdf",
                    "apolice_do_allianz_endosso.pdf"
                )

    st.markdown("</div>", unsafe_allow_html=True)


def _render_task_checklist(current_stage: int, current_desc: str = "", is_image: bool = False) -> str:
    """Renderiza a lista de verificação com linguagem de tarefa profissional (Requisitos 8 e 12)."""
    if is_image:
        stages = [
            (1, "Imagem recebida"),
            (2, "Texto extraído"),
            (3, "Estrutura contratual identificada"),
            (4, "Evidências localizadas"),
            (5, "Comparação em andamento"),
            (6, "Análise concluída")
        ]
    else:
        stages = [
            (1, "Documento recebido"),
            (2, "Conteúdo extraído"),
            (3, "Estrutura contratual identificada"),
            (4, "Evidências localizadas"),
            (5, "Comparação em andamento"),
            (6, "Análise concluída")
        ]

    items_html = ""
    for stage_num, stage_label in stages:
        if stage_num < current_stage:
            icon = f'<span style="color:{COLORS.SUCCESS}; font-weight:700; font-size:14px; margin-right:8px;">✓</span>'
            text = f'<span style="color:{COLORS.PRIMARY_NAVY}; font-size:13px; font-weight:600;">{stage_label}</span>'
            sub = ""
        elif stage_num == current_stage:
            icon = f'<span style="color:{COLORS.PRIMARY_BLUE}; font-weight:700; font-size:14px; margin-right:8px;">◉</span>'
            text = f'<span style="color:{COLORS.PRIMARY_BLUE}; font-size:13px; font-weight:700;">{stage_label}</span>'
            sub = f'<div style="font-size:11.5px; color:{COLORS.TEXT_MUTED}; margin-left:22px; margin-top:2px;">{current_desc}</div>' if current_desc else ""
        else:
            icon = '<span style="color:#94A3B8; font-size:14px; margin-right:8px;">○</span>'
            text = f'<span style="color:#94A3B8; font-size:13px; font-weight:400;">{stage_label}</span>'
            sub = ""

        items_html += f"""
        <div style="margin-bottom:8px;">
            <div style="display:flex; align-items:center;">
                {icon}
                {text}
            </div>
            {sub}
        </div>
        """

    return f"""
        <div style="background:{COLORS.SURFACE}; border:1px solid {COLORS.BORDER}; border-radius:{RADIUS.MD}; padding:18px 20px; margin:16px 0; box-shadow:{SHADOWS.SM};">
            <div style="font-size:11px; text-transform:uppercase; letter-spacing:0.8px; color:{COLORS.TEXT_MUTED}; font-weight:700; margin-bottom:12px;">
                PROGRESSO DA ANÁLISE CONTRATUAL
            </div>
            {items_html}
        </div>
    """


def _process_uploaded_pair(file_a, file_b):
    """Executa o pipeline multi-agente nos dois arquivos enviados com telemetria orientada a tarefas."""
    checklist_placeholder = st.empty()
    progress_bar = st.progress(0)

    docs_processed = []
    files_to_proc = [("Documento de referência (A)", file_a), ("Documento para comparação (B)", file_b)]

    for doc_idx, (label, uploaded_file) in enumerate(files_to_proc):
        filename = uploaded_file.name
        ext = Path(filename).suffix.lower()
        is_img = ext in IMAGE_EXTENSIONS

        try:
            dest_path = get_safe_destination_path(UPLOADS_DIR, filename)
            dest_path.write_bytes(uploaded_file.getbuffer())
        except Exception as e:
            checklist_placeholder.markdown(f"""
                <div style="background:#FDE8E8; border:1px solid #F8B4B4; border-radius:6px; padding:12px; color:{COLORS.CRITICAL}; font-size:13px;">
                    ✕ <b>Erro de gravação segura:</b> Não foi possível salvar o arquivo `{filename}`.
                </div>
            """, unsafe_allow_html=True)
            with st.expander("Ver detalhes técnicos do erro", expanded=False):
                st.code(str(e))
            return

        def on_step(step_num: int, agent_name: str, desc: str):
            checklist_placeholder.markdown(
                _render_task_checklist(step_num, f"{label}: {desc}", is_image=is_img),
                unsafe_allow_html=True
            )

        state = run_document_pipeline_with_progress(
            file_path=str(dest_path),
            file_name=filename,
            on_step_callback=on_step,
            force_reprocess=True
        )

        if state.status == "erro":
            err_title = "Não foi possível ler esta imagem:" if is_img else "Não foi possível concluir a análise deste documento:"
            err_details = ", ".join(state.errors) if state.errors else ("A imagem foi recebida, mas o conteúdo textual não pôde ser extraído com qualidade suficiente." if is_img else "Falha não especificada na extração.")
            checklist_placeholder.markdown(f"""
                <div style="background:#FDE8E8; border:1px solid #F8B4B4; border-radius:6px; padding:12px; color:{COLORS.CRITICAL}; font-size:13px;">
                    ✕ <b>{err_title}</b> `{filename}`.
                    <div style="margin-top:6px; font-size:12px; color:#991B1B;">{err_details}</div>
                </div>
            """, unsafe_allow_html=True)
            with st.expander("Ver detalhes técnicos do erro", expanded=False):
                st.code(err_details)
            return

        if state.structured_data:
            docs_processed.append(state.structured_data)

        progress_bar.progress((doc_idx + 1) / 2)

    if len(docs_processed) == 2:
        checklist_placeholder.markdown(
            _render_task_checklist(5, "Confrontando cláusulas e calculando similaridade semântica..."),
            unsafe_allow_html=True
        )
        st.session_state["active_doc_a"] = docs_processed[0]
        st.session_state["active_doc_b"] = docs_processed[1]
        st.session_state["selected_for_compare"] = docs_processed

        checklist_placeholder.markdown(
            _render_task_checklist(6, "Ambos os documentos foram estruturados com evidências rastreáveis."),
            unsafe_allow_html=True
        )
        st.rerun()


def _process_preset_pair(filename_a: str, filename_b: str):
    """Carrega e estrutura o par de benchmark oficial sem necessidade de upload externo."""
    path_a = DATASET_DO_DIR / filename_a
    if not path_a.exists():
        path_a = SAMPLE_POLICIES_DIR / filename_a

    path_b = DATASET_DO_DIR / filename_b
    if not path_b.exists():
        path_b = SAMPLE_POLICIES_DIR / filename_b

    if not path_a.exists() or not path_b.exists():
        st.error(f"Arquivos do benchmark não foram localizados: {filename_a} / {filename_b}")
        return

    checklist_placeholder = st.empty()
    progress_bar = st.progress(0)

    docs_processed = []
    pairs = [("Documento de referência (A)", path_a), ("Documento para comparação (B)", path_b)]

    for doc_idx, (label, file_path) in enumerate(pairs):
        def on_step(step_num: int, agent_name: str, desc: str):
            checklist_placeholder.markdown(
                _render_task_checklist(step_num, f"{label}: {desc}"),
                unsafe_allow_html=True
            )

        state = run_document_pipeline_with_progress(
            file_path=str(file_path),
            file_name=file_path.name,
            on_step_callback=on_step,
            force_reprocess=False
        )

        if state.structured_data:
            docs_processed.append(state.structured_data)
        else:
            checklist_placeholder.markdown(f"""
                <div style="background:#FDE8E8; border:1px solid #F8B4B4; border-radius:6px; padding:12px; color:{COLORS.CRITICAL}; font-size:13px;">
                    ✕ <b>Erro ao carregar benchmark:</b> {state.errors}
                </div>
            """, unsafe_allow_html=True)
            return

        progress_bar.progress((doc_idx + 1) / 2)

    if len(docs_processed) == 2:
        checklist_placeholder.markdown(
            _render_task_checklist(5, "Confrontando cláusulas e calculando similaridade semântica..."),
            unsafe_allow_html=True
        )
        st.session_state["active_doc_a"] = docs_processed[0]
        st.session_state["active_doc_b"] = docs_processed[1]
        st.session_state["selected_for_compare"] = docs_processed

        checklist_placeholder.markdown(
            _render_task_checklist(6, "Benchmark carregado e estruturado com sucesso."),
            unsafe_allow_html=True
        )
        navigate_to("Comparações")
        st.rerun()


def _render_structured_success_view(doc_a: ApoliceDAO, doc_b: ApoliceDAO):
    """Renderiza a confirmação de sucesso com os cartões estruturados e ação para comparação."""
    render_success_state(
        "Análise estruturada concluída com sucesso.",
        "Ambos os documentos foram processados com evidências auditáveis e estão prontos para o confronto contratual."
    )

    col_card_a, col_card_b = st.columns(2)
    with col_card_a:
        render_structured_doc_card(doc_a, title_prefix="Documento de referência (A)")
    with col_card_b:
        render_structured_doc_card(doc_b, title_prefix="Documento para comparação (B)")

    col_act1, col_act2 = st.columns([2, 1.2])
    with col_act1:
        if st.button("⚖️ Visualizar Comparação Contratual A ↔ B ➔", type="primary", key="btn_go_compare_from_success"):
            st.session_state["selected_for_compare"] = [doc_a, doc_b]
            navigate_to("Comparações")
            st.rerun()
    with col_act2:
        if st.button("🔄 Carregar Outro Par de Documentos", key="btn_reset_active_docs"):
            st.session_state.pop("active_doc_a", None)
            st.session_state.pop("active_doc_b", None)
            st.rerun()


def render_structured_doc_card(dao: ApoliceDAO, title_prefix: str = "Documento"):
    """Exibe a visão estruturada da análise para um documento específico (utilizado em Upload e em Comparações)."""
    tipo_map = {
        "condicoes_gerais": "Condições Gerais",
        "apolice_individual": "Apólice Individual",
        "endosso": "Endosso Aditivo",
        "proposta": "Proposta de Seguro",
        "outros": "Documento Suplementar",
        "unknown": "Não Identificado"
    }
    tipo_str = tipo_map.get(dao.document_type or "unknown", dao.document_type or "Não Identificado")

    num_cobs = len(dao.coberturas or [])
    num_excs = len(dao.exclusoes or [])
    num_ces = len(dao.clausulas_especiais or [])
    num_evs = len(dao.evidencias or [])

    with st.container():
        st.markdown(f"""
            <div class="doc-summary-card">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
                    <div>
                        <span class="badge-tag">{title_prefix}</span>
                        <h4 style="margin:4px 0 0 0; color:{COLORS.PRIMARY_NAVY}; font-size:16px; font-weight:700; word-break:break-all;">
                            {dao.nome_arquivo}
                        </h4>
                    </div>
                    <span style="font-size:12px; font-weight:600; background:#F1F5F9; color:{COLORS.PRIMARY_NAVY}; padding:3px 10px; border-radius:4px; border:1px solid {COLORS.BORDER};">
                        📄 {tipo_str}
                    </span>
                </div>
                <div style="font-size:12.5px; color:{COLORS.TEXT_MUTED}; margin-bottom:14px; line-height:1.5;">
                    <b>Seguradora:</b> <span style="color:{COLORS.PRIMARY_BLUE}; font-weight:600;">{dao.seguradora or 'Não identificada'}</span> &nbsp;·&nbsp;
                    <b>Processo SUSEP:</b> <span style="font-family:{TYPOGRAPHY.FONT_CODE}; font-weight:600; color:{COLORS.PRIMARY_NAVY};">{dao.processo_susep or 'Não identificado'}</span> &nbsp;·&nbsp;
                    <b>Tomador/Segurado:</b> <span style="color:{COLORS.TEXT_MAIN};">{dao.segurado or 'N/A (Condições Gerais)'}</span>
                </div>
                <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:8px; margin-top:12px;">
                    <div style="background:#EFF6FF; border:1px solid #BFDBFE; border-radius:6px; padding:10px 6px; text-align:center;">
                        <div style="font-size:10px; color:#1E40AF; font-weight:700; text-transform:uppercase;">🛡️ Coberturas</div>
                        <div style="font-size:20px; font-weight:700; color:#1E40AF; font-family:{TYPOGRAPHY.FONT_UI}; margin-top:2px;">{num_cobs}</div>
                        <div style="font-size:10px; color:#6B7785;">cláusulas</div>
                    </div>
                    <div style="background:#FEF2F2; border:1px solid #FECACA; border-radius:6px; padding:10px 6px; text-align:center;">
                        <div style="font-size:10px; color:#991B1B; font-weight:700; text-transform:uppercase;">⛔ Exclusões</div>
                        <div style="font-size:20px; font-weight:700; color:#991B1B; font-family:{TYPOGRAPHY.FONT_UI}; margin-top:2px;">{num_excs}</div>
                        <div style="font-size:10px; color:#6B7785;">itens</div>
                    </div>
                    <div style="background:#F5F3FF; border:1px solid #DDD6FE; border-radius:6px; padding:10px 6px; text-align:center;">
                        <div style="font-size:10px; color:#5B21B6; font-weight:700; text-transform:uppercase;">📑 Especiais</div>
                        <div style="font-size:20px; font-weight:700; color:#5B21B6; font-family:{TYPOGRAPHY.FONT_UI}; margin-top:2px;">{num_ces}</div>
                        <div style="font-size:10px; color:#6B7785;">cláusulas</div>
                    </div>
                    <div style="background:#F0FDFA; border:1px solid #99F6E4; border-radius:6px; padding:10px 6px; text-align:center;">
                        <div style="font-size:10px; color:#0F766E; font-weight:700; text-transform:uppercase;">🔍 Evidências</div>
                        <div style="font-size:20px; font-weight:700; color:#0F766E; font-family:{TYPOGRAPHY.FONT_UI}; margin-top:2px;">{num_evs}</div>
                        <div style="font-size:10px; color:#6B7785;">auditáveis</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        with st.expander(f"🔍 Detalhes Técnicos & Parâmetros de {dao.nome_arquivo}", expanded=False):
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.markdown(f"• **LMG (Limite de Responsabilidade):** <span style='color:{COLORS.PRIMARY_BLUE}; font-weight:600;'>{dao.limite_responsabilidade or 'N/A'}</span>", unsafe_allow_html=True)
                st.markdown(f"• **Franquia / Retenção:** {dao.franquia or 'N/A'}")
                st.markdown(f"• **Prêmio Comercial:** {dao.premio_total or 'N/A'}")
                st.markdown(f"• **Vigência:** {dao.vigencia_inicio or '?'} até {dao.vigencia_fim or '?'}")
            with col_d2:
                st.markdown(f"• **Data de Retroatividade:** {dao.retroatividade or 'N/A'}")
                st.markdown(f"• **Âmbito Territorial:** {dao.territorio or 'N/A'}")
                st.markdown(f"• **Método de Extração:** <code>{dao.metodo_extracao}</code>", unsafe_allow_html=True)
                st.markdown(f"• **Confiança Analítica:** <span style='color:{COLORS.SUCCESS}; font-weight:700;'>{dao.confianca_extracao * 100:.0f}%</span>", unsafe_allow_html=True)

            if dao.coberturas:
                st.markdown("---")
                st.markdown("**Amostra de Cláusulas Identificadas no Contrato:**")
                for c in dao.coberturas[:4]:
                    ev = dao.evidencias.get(c.split(":")[0].strip()) if dao.evidencias else None
                    page_badge = f"<span style='color:{COLORS.PRIMARY_BLUE}; font-weight:600;'>(Pág. {ev.page})</span>" if ev and ev.page else ""
                    st.markdown(f"""<div style="font-size:12px; color:{COLORS.TEXT_MAIN}; margin-bottom:4px;">✓ {c} {page_badge}</div>""", unsafe_allow_html=True)
