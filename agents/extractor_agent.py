"""Agente 2 — Extractor Agent.
Responsabilidade: Extração de texto bruto do documento PDF com fallback multimodal para documentos escaneados.
"""
from pathlib import Path
import logging
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


def extractor_agent(state: DocumentState) -> DocumentState:
    """Executa o Agente 2: Extrai o conteúdo textual e identifica se o PDF é digital ou escaneado."""
    # Se o documento já veio do cache no Agente 1, pula esta etapa
    if state.status == "concluido_em_cache":
        return state

    logger.info(f"Agente 2 (Extractor): Extraindo texto de {state.file_name}")
    file_path = Path(state.file_path)

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
        logger.info(f"Agente 2: PDF escaneado detectado (média de {avg_chars:.1f} caracteres/página). Acionando Fallback Vision.")
        method = "gemini_vision"
        
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
                        model="gemini-2.0-flash",
                        contents=[
                            {"mime_type": "image/png", "data": img_bytes},
                            prompt
                        ]
                    )
                    vision_text_parts.append(f"--- PÁGINA {i + 1} (OCR Vision) ---\n" + (response.text or ""))
                raw_text = "\n\n".join(vision_text_parts)
            except Exception as e_vis:
                logger.error(f"Erro no fallback Gemini Vision: {e_vis}")

    state.raw_text = raw_text
    state.page_count = page_count
    state.is_scanned = is_scanned
    state.extraction_method = method
    state.status = "texto_extraido"

    logger.info(f"Agente 2: Extração concluída com sucesso. Páginas: {page_count}, Caracteres: {len(raw_text)}")
    return state
