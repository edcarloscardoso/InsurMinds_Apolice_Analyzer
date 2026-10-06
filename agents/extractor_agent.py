"""Agente 2 — Extractor Agent.
Responsabilidade: Extração de texto bruto do documento (PDF digital, PDF escaneado ou Imagem PNG/JPG/JPEG)
com suporte a OCR multimodal (Gemini Vision) e fallback determinístico local via PyMuPDF/Tesseract.
"""
from pathlib import Path
import os
import logging
from core.config import IMAGE_EXTENSIONS, resolve_tessdata_dir, get_ocr_language
from core.schemas import DocumentState
from core.llm_client import llm_client

logger = logging.getLogger(__name__)


def extract_with_pdfplumber(file_path: Path) -> tuple[str, int]:
    """Extrai texto e contagem de páginas usando pdfplumber."""
    import pdfplumber

    text_parts = []
    page_count = 0
    with pdfplumber.open(str(file_path)) as pdf:
        page_count = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text() or ""
            text_parts.append(f"--- PÁGINA {i + 1} ---\n" + page_text)

    return "\n\n".join(text_parts), page_count


def extract_with_pymupdf(file_path: Path) -> tuple[str, int]:
    """Extrai texto e contagem de páginas usando PyMuPDF (fitz) como alternativa de alta performance."""
    import fitz

    doc = fitz.open(str(file_path))
    page_count = len(doc)
    text_parts = []
    for i, page in enumerate(doc):
        text = page.get_text() or ""
        text_parts.append(f"--- PÁGINA {i + 1} ---\n" + text)

    return "\n\n".join(text_parts), page_count


def extract_image_with_local_ocr(file_path: Path) -> str:
    """Extrai texto de imagem usando PyMuPDF com Tesseract nativo."""
    import fitz

    td = resolve_tessdata_dir()
    lang = get_ocr_language(td)

    img_doc = fitz.open(str(file_path))
    try:
        pdf_bytes = img_doc.convert_to_pdf()
        pdf_doc = fitz.open("pdf", pdf_bytes)
        try:
            page = pdf_doc[0]
            tp = page.get_textpage_ocr(language=lang, dpi=150)
            return (tp.extractText() or "").strip()
        finally:
            pdf_doc.close()
    finally:
        img_doc.close()


def extractor_agent(state: DocumentState) -> DocumentState:
    """Executa o Agente 2: Extrai o conteúdo textual de PDF ou Imagem com suporte multimodal e OCR determinístico."""
    # Se o documento já veio do cache no Agente 1, pula esta etapa
    if state.status == "concluido_em_cache":
        return state

    file_path = Path(state.file_path)
    ext = file_path.suffix.lower()
    is_image = state.document_format == "image" or ext in IMAGE_EXTENSIONS

    # =========================================================
    # ROTA EXPLÍCITA DE IMAGEM (PNG, JPG, JPEG)
    # =========================================================
    if is_image:
        logger.info(f"Agente 2 (Extractor): Processando documento em formato IMAGEM ({file_path.name})")
        raw_text = ""
        method = "ocr"

        # Prioridade A: Gemini Multimodal Vision se configurado
        if llm_client.is_available():
            try:
                logger.info(f"Agente 2: Tentando extração via Gemini Vision para imagem {file_path.name}")
                gemini_text = llm_client.extract_text_from_image(file_path)
                if gemini_text and len(gemini_text.strip()) >= 20:
                    raw_text = gemini_text.strip()
                    method = "gemini_vision"
            except Exception as e_vis:
                logger.warning(f"Agente 2: Falha no Gemini Vision para imagem ({e_vis}). Acionando OCR local...")

        # Prioridade B: Fallback Local Determinístico (PyMuPDF / Tesseract)
        if not raw_text:
            try:
                logger.info(f"Agente 2: Executando OCR local nativo para imagem {file_path.name}")
                ocr_text = extract_image_with_local_ocr(file_path)
                if ocr_text and len(ocr_text.strip()) > 0:
                    raw_text = ocr_text.strip()
                    method = "ocr"
            except Exception as e_ocr:
                logger.warning(f"Agente 2: Falha no OCR local de imagem ({e_ocr})")

        # Tratamento defensivo de imagem ilegível / sem texto
        if not raw_text or len(raw_text.strip()) < 20:
            error_msg = "A imagem foi recebida, mas o conteúdo textual não pôde ser extraído com qualidade suficiente."
            logger.error(f"Agente 2: {error_msg} ({file_path.name})")
            state.errors.append(error_msg)
            state.status = "erro"
            return state

        state.raw_text = raw_text
        state.page_count = 1
        state.is_scanned = True
        state.document_format = "image"
        state.extraction_method = method
        state.status = "texto_extraido"
        logger.info(f"Agente 2: Extração de imagem concluída com sucesso via {method}. Caracteres: {len(raw_text)}")
        return state

    # =========================================================
    # ROTA EXISTENTE DE PDF
    # =========================================================
    logger.info(f"Agente 2 (Extractor): Extraindo texto de {state.file_name}")
    raw_text = ""
    page_count = 0
    method = "pdfplumber"

    # Tentativa 1: pdfplumber (requisito do PRD)
    try:
        raw_text, page_count = extract_with_pdfplumber(file_path)
    except Exception as e:
        logger.warning(f"pdfplumber falhou ({e}). Tentando PyMuPDF...")
        try:
            raw_text, page_count = extract_with_pymupdf(file_path)
            method = "pymupdf"
        except Exception as e2:
            state.errors.append(f"Falha na extração de texto: {str(e2)}")
            state.status = "erro"
            return state

    # Heurística de detecção de PDF escaneado (texto < 100 caracteres por página)
    avg_chars = (len(raw_text.strip()) / page_count) if page_count > 0 else 0
    is_scanned = avg_chars < 100

    if is_scanned:
        logger.info(f"Agente 2: PDF escaneado detectado (média de {avg_chars:.1f} caracteres/página). Acionando Fallback Vision / OCR.")

        # Fallback Vision: se o Gemini estiver disponível, processa as imagens
        if llm_client.is_available():
            try:
                import fitz
                doc = fitz.open(str(file_path))
                vision_text_parts = []
                for i, page in enumerate(doc):
                    pix = page.get_pixmap(dpi=150)
                    img_bytes = pix.tobytes("png")

                    prompt = "Transcreva fielmente todo o conteúdo textual e tabelas desta página de apólice de seguro D&O."
                    response = llm_client.client.models.generate_content(
                        model=llm_client.model,
                        contents=[
                            {"mime_type": "image/png", "data": img_bytes},
                            prompt
                        ]
                    )
                    vision_text_parts.append(f"--- PÁGINA {i + 1} (OCR Vision) ---\n" + (response.text or ""))
                doc.close()
                raw_text = "\n\n".join(vision_text_parts)
                method = "gemini_vision"
            except Exception as e_vis:
                logger.error(f"Erro no fallback Gemini Vision: {e_vis}")

        # Se Gemini não estava disponível ou falhou e não há texto suficiente, tenta OCR local
        if not raw_text or len(raw_text.strip()) < 20:
            try:
                import fitz
                td = resolve_tessdata_dir()
                lang = get_ocr_language(td)
                doc = fitz.open(str(file_path))
                ocr_parts = []
                for i, page in enumerate(doc):
                    tp = page.get_textpage_ocr(language=lang, dpi=150)
                    ocr_parts.append(f"--- PÁGINA {i + 1} (OCR Local) ---\n" + (tp.extractText() or ""))
                doc.close()
                local_ocr_text = "\n\n".join(ocr_parts).strip()
                if len(local_ocr_text) > 20:
                    raw_text = local_ocr_text
                    method = "ocr"
            except Exception as e_loc_ocr:
                logger.warning(f"Erro no OCR local para PDF escaneado: {e_loc_ocr}")

    state.raw_text = raw_text
    state.page_count = page_count
    state.is_scanned = is_scanned
    state.extraction_method = method
    state.status = "texto_extraido"

    logger.info(f"Agente 2: Extração concluída com sucesso. Páginas: {page_count}, Caracteres: {len(raw_text)}")
    return state
