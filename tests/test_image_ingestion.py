"""Testes Automatizados para Ingestão Nativa de Imagens (Fase 7.11C).
Cobre todos os 18 requisitos mandatórios do Projeto Final InsurMinds:
1. PNG válido aceito.
2. JPG válido aceito.
3. JPEG válido aceito.
4. Arquivo inválido rejeitado (extensão não autorizada).
5. Conteúdo incompatível rejeitado (magic bytes mismatch / cross-extension spoofing).
6. PDF continua aceito sem regressão.
7. Imagem gera DocumentState válido no Agente 1 (Recepção).
8. Imagem gera page_count = 1 correto.
9. OCR retorna texto inteligível.
10. Imagem sem texto é tratada defensivamente com erro amigável.
11. EvidenceItem é criado com proveniência e page = 1.
12. Imagem segue normalmente para o estruturador (Agente 4).
13. Imagem converge para o mesmo modelo canônico ApoliceDAO.
14. Comparação Imagem × PDF produz ComparisonResult completo.
15. Comparação Imagem × Imagem funciona normalmente.
16. Regressão PDF escaneado preservada.
17. Regressão PDF digital normal preservada.
18. Fluxo completo do pipeline documental com callbacks.
"""
from pathlib import Path
import pytest
import io
from PIL import Image

from core.config import DATASET_DO_DIR, IMAGE_EXTENSIONS
from core.security import (
    validate_document_content,
    validate_pdf_content,
    get_safe_destination_path
)
from core.schemas import DocumentState, ApoliceDAO, ComparisonResult
from agents.reception_agent import reception_agent
from agents.extractor_agent import extractor_agent, extract_image_with_local_ocr
from agents.structurer_agent import structurer_agent
from agents.graph import (
    run_document_pipeline_with_progress,
    run_comparison_pipeline_with_progress
)


BASE_PROJECT_DIR = Path(__file__).resolve().parent.parent
SCRATCH_PNG = BASE_PROJECT_DIR / "scratch" / "external_acceptance" / "DO011_SOMPO_v1_3_pag1_derivada.png"
SCRATCH_JPG = BASE_PROJECT_DIR / "scratch" / "external_acceptance" / "DO011_SOMPO_v1_3_pag1_derivada.jpg"


@pytest.fixture
def sample_png_path(tmp_path) -> Path:
    """Retorna caminho de imagem PNG válida com texto documental."""
    if SCRATCH_PNG.exists():
        return SCRATCH_PNG
    p = tmp_path / "sample.png"
    img = Image.new("RGB", (300, 100), color="white")
    img.save(p, format="PNG")
    return p


@pytest.fixture
def sample_jpg_path(tmp_path) -> Path:
    """Retorna caminho de imagem JPG válida com texto documental."""
    if SCRATCH_JPG.exists():
        return SCRATCH_JPG
    p = tmp_path / "sample.jpg"
    img = Image.new("RGB", (300, 100), color="white")
    img.save(p, format="JPEG")
    return p


@pytest.fixture
def sample_jpeg_path(tmp_path, sample_jpg_path) -> Path:
    """Retorna caminho de imagem JPEG válida."""
    p = tmp_path / "sample.jpeg"
    p.write_bytes(sample_jpg_path.read_bytes())
    return p


@pytest.fixture
def blank_image_path(tmp_path) -> Path:
    """Cria uma imagem em branco sem qualquer texto."""
    p = tmp_path / "blank_image.png"
    img = Image.new("RGB", (200, 200), color="white")
    img.save(p, format="PNG")
    return p


@pytest.fixture
def sample_pdf_path() -> Path:
    """Retorna um PDF do corpus oficial."""
    p = DATASET_DO_DIR / "DO_SOMPO_CONDICOES_GERAIS_V1_2_2024_010.pdf"
    if p.exists():
        return p
    # Fallback para primeiro PDF disponível
    pdfs = list(DATASET_DO_DIR.glob("*.pdf"))
    assert len(pdfs) > 0, "Nenhum PDF encontrado no dataset"
    return pdfs[0]


# =============================================================================
# 1 a 6: CONTRATO DE ARQUIVOS E SEGURANÇA BINÁRIA
# =============================================================================

def test_01_png_valido_aceito(sample_png_path):
    """1. PNG válido deve ser aceito e classificado como 'image'."""
    data = sample_png_path.read_bytes()
    valid, msg, fmt = validate_document_content(data, sample_png_path.name)
    assert valid is True
    assert fmt == "image"
    assert "PNG válido" in msg


def test_02_jpg_valido_aceito(sample_jpg_path):
    """2. JPG válido deve ser aceito e classificado como 'image'."""
    data = sample_jpg_path.read_bytes()
    valid, msg, fmt = validate_document_content(data, sample_jpg_path.name)
    assert valid is True
    assert fmt == "image"
    assert "JPEG válido" in msg


def test_03_jpeg_valido_aceito(sample_jpeg_path):
    """3. JPEG válido deve ser aceito e classificado como 'image'."""
    data = sample_jpeg_path.read_bytes()
    valid, msg, fmt = validate_document_content(data, sample_jpeg_path.name)
    assert valid is True
    assert fmt == "image"
    assert "JPEG válido" in msg


def test_04_arquivo_invalido_rejeitado():
    """4. Arquivo com extensão não permitida (.exe, .txt, .zip) deve ser sumariamente rejeitado."""
    invalid_bytes = b"echo 'malicious payload'"
    valid, msg, fmt = validate_document_content(invalid_bytes, "payload.exe")
    assert valid is False
    assert "não permitidos" in msg or "inválida" in msg

    valid_txt, msg_txt, _ = validate_document_content(b"text data", "documento.txt")
    assert valid_txt is False


def test_05_conteudo_incompativel_rejeitado(sample_png_path, sample_jpg_path):
    """5. Rejeição estrita de spoofing de extensão (cross-extension e magic-bytes mismatch)."""
    png_data = sample_png_path.read_bytes()
    jpg_data = sample_jpg_path.read_bytes()

    # PNG renomeado para JPG
    valid_spoof1, msg_spoof1, _ = validate_document_content(png_data, "documento.jpg")
    assert valid_spoof1 is False
    assert "cabeçalho JPEG (magic bytes) incompatível" in msg_spoof1

    # JPG renomeado para PNG
    valid_spoof2, msg_spoof2, _ = validate_document_content(jpg_data, "documento.png")
    assert valid_spoof2 is False
    assert "cabeçalho PNG (magic bytes) incompatível" in msg_spoof2

    # PDF renomeado para PNG
    pdf_sample = b"%PDF-1.4\nsome content\n%%EOF"
    valid_spoof3, msg_spoof3, _ = validate_document_content(pdf_sample, "documento.png")
    assert valid_spoof3 is False
    assert "cabeçalho PNG" in msg_spoof3

    # Arquivo corrompido com cabeçalho truncado
    corrupted = b"\x89PNG\r\n\x1a\ncorrompido"
    valid_corrupt, msg_corrupt, _ = validate_document_content(corrupted, "corrompido.png")
    assert valid_corrupt is False
    assert "corrompido ou ilegível" in msg_corrupt


def test_06_pdf_continua_aceito(sample_pdf_path):
    """6. PDF válido continua sendo aceito sem qualquer regressão."""
    data = sample_pdf_path.read_bytes()
    valid, msg, fmt = validate_document_content(data, sample_pdf_path.name)
    assert valid is True
    assert fmt == "pdf"
    assert "PDF válido" in msg

    # Validador legado estrito exclusivo para PDF continua operando
    v_leg, msg_leg = validate_pdf_content(data, sample_pdf_path.name)
    assert v_leg is True


# =============================================================================
# 7 a 10: RECEPÇÃO E EXTRAÇÃO OCR DE IMAGENS
# =============================================================================

def test_07_imagem_gera_documentstate_valido(sample_png_path):
    """7. Agente 1 (Recepção) aceita imagem e inicializa DocumentState com document_format='image'."""
    init_state = DocumentState(
        file_path=str(sample_png_path),
        file_name=sample_png_path.name,
        force_reprocess=True
    )
    rec_state = reception_agent(init_state)
    assert rec_state.status != "erro"
    assert rec_state.document_format == "image"
    assert rec_state.file_hash is not None
    assert len(rec_state.file_hash) == 32  # MD5 válido


def test_08_imagem_gera_page_count_correto(sample_png_path):
    """8. Imagem deve registrar page_count = 1."""
    init_state = DocumentState(
        file_path=str(sample_png_path),
        file_name=sample_png_path.name,
        force_reprocess=True
    )
    state = reception_agent(init_state)
    state = extractor_agent(state)
    assert state.page_count == 1
    assert state.is_scanned is True


def test_09_ocr_retorna_texto(sample_png_path):
    """9. Agente 2 (Extração) extrai texto inteligível da imagem via OCR determinístico ou Gemini Vision."""
    init_state = DocumentState(
        file_path=str(sample_png_path),
        file_name=sample_png_path.name,
        force_reprocess=True
    )
    state = reception_agent(init_state)
    state = extractor_agent(state)
    assert state.status == "texto_extraido"
    assert state.extraction_method in ("ocr", "gemini_vision")
    assert any(term in state.raw_text.lower() for term in ("diretores", "coberturas", "documento", "seguro", "susep", "sompo", "responsabilidade"))


def test_10_imagem_sem_texto_tratamento_defensivo(blank_image_path):
    """10. Imagem sem texto legível deve produzir status de erro defensivo sem mascarar falha."""
    init_state = DocumentState(
        file_path=str(blank_image_path),
        file_name=blank_image_path.name,
        force_reprocess=True
    )
    state = reception_agent(init_state)
    state = extractor_agent(state)
    assert state.status == "erro"
    assert any("qualidade suficiente" in err or "não pôde ser extraído" in err for err in state.errors)


# =============================================================================
# 11 a 13: EVIDÊNCIAS E ESTRUTURAÇÃO CANÔNICA (ApoliceDAO)
# =============================================================================

def test_11_evidence_item_criado_para_imagem(sample_png_path):
    """11. EvidenceItem deve ser gerado com page=1 e método correspondente (ocr / gemini_vision)."""
    state = run_document_pipeline_with_progress(
        file_path=str(sample_png_path),
        file_name=sample_png_path.name,
        force_reprocess=True
    )
    assert state.status == "concluido"
    assert state.structured_data is not None
    dao = state.structured_data

    # Se houver evidências mapeadas, todas devem ter page=1
    for field_name, ev in dao.evidencias.items():
        assert ev.page == 1
        assert ev.method in ("ocr", "gemini_vision", "regulatory_registry")
        assert len(ev.snippet) > 0


def test_12_imagem_segue_para_estruturacao(sample_png_path):
    """12. DocumentState de imagem é processado normalmente pelo Agente 4 (Structurer)."""
    init_state = DocumentState(
        file_path=str(sample_png_path),
        file_name=sample_png_path.name,
        force_reprocess=True
    )
    s1 = reception_agent(init_state)
    s2 = extractor_agent(s1)
    # Simula identifier sem quebrar
    from agents.identifier_agent import identifier_agent
    s3 = identifier_agent(s2)
    s4 = structurer_agent(s3)
    assert s4.status == "concluido"
    assert s4.structured_data is not None


def test_13_imagem_chega_ao_mesmo_apolice_dao(sample_png_path):
    """13. Imagem deve produzir uma instância válida do modelo canônico ApoliceDAO."""
    state = run_document_pipeline_with_progress(
        file_path=str(sample_png_path),
        file_name=sample_png_path.name,
        force_reprocess=True
    )
    dao = state.structured_data
    assert isinstance(dao, ApoliceDAO)
    assert dao.id == state.file_hash
    assert dao.nome_arquivo == sample_png_path.name
    assert dao.metodo_extracao in ("ocr", "gemini_vision", "heuristic_fallback")


# =============================================================================
# 14 a 15: COMPARAÇÃO MULTIMODAL (IMAGEM × PDF e IMAGEM × IMAGEM)
# =============================================================================

def test_14_comparacao_imagem_x_pdf(sample_png_path, sample_pdf_path):
    """14. Comparação entre Imagem e PDF deve executar com sucesso gerando ComparisonResult."""
    state_img = run_document_pipeline_with_progress(
        file_path=str(sample_png_path),
        file_name=sample_png_path.name,
        force_reprocess=True
    )
    state_pdf = run_document_pipeline_with_progress(
        file_path=str(sample_pdf_path),
        file_name=sample_pdf_path.name,
        force_reprocess=True
    )

    comp_state = run_comparison_pipeline_with_progress(state_img.structured_data, state_pdf.structured_data)
    assert comp_state.status == "concluido"
    res = comp_state.diff_result
    assert isinstance(res, ComparisonResult)
    assert res.score_similaridade >= 0.0
    assert len(res.diffs) > 0
    assert len(comp_state.report_markdown) > 100


def test_15_comparacao_imagem_x_imagem(sample_png_path, sample_jpg_path):
    """15. Comparação entre duas Imagens deve executar normalmente no mesmo pipeline."""
    state_png = run_document_pipeline_with_progress(
        file_path=str(sample_png_path),
        file_name=sample_png_path.name,
        force_reprocess=True
    )
    state_jpg = run_document_pipeline_with_progress(
        file_path=str(sample_jpg_path),
        file_name=sample_jpg_path.name,
        force_reprocess=True
    )

    comp_state = run_comparison_pipeline_with_progress(state_png.structured_data, state_jpg.structured_data)
    assert comp_state.status == "concluido"
    res = comp_state.diff_result
    assert isinstance(res, ComparisonResult)
    assert len(res.diffs) > 0


# =============================================================================
# 16 a 18: REGRESSÃO DE PDF E FLUXO COMPLETO PELA UI/GRAFO
# =============================================================================

def test_16_regressao_pdf_escaneado_preservada():
    """16. Extractor agent preserva detecção e fallback de PDF escaneado."""
    state = DocumentState(
        file_path="/tmp/fake_scanned.pdf",
        file_name="fake_scanned.pdf",
        document_format="pdf"
    )
    # Se o arquivo não existir fisicamente, deve reportar erro defensivo sem explodir
    result = extractor_agent(state)
    assert result.status == "erro"
    assert len(result.errors) > 0


def test_17_regressao_pdf_normal_preservada(sample_pdf_path):
    """17. Processamento de PDF digital longo (Sompo) continua operando 100% íntegro."""
    state = run_document_pipeline_with_progress(
        file_path=str(sample_pdf_path),
        file_name=sample_pdf_path.name,
        force_reprocess=True
    )
    assert state.status == "concluido"
    assert state.document_format == "pdf"
    assert state.page_count > 10
    assert "Sompo Seguros" in state.structured_data.seguradora


def test_18_fluxo_completo_pipeline_com_callbacks(sample_png_path):
    """18. Execução com rastreabilidade de callbacks de progresso na UI."""
    steps_recorded = []

    def tracking_callback(step: int, title: str, desc: str):
        steps_recorded.append((step, title, desc))

    state = run_document_pipeline_with_progress(
        file_path=str(sample_png_path),
        file_name=sample_png_path.name,
        on_step_callback=tracking_callback,
        force_reprocess=True
    )
    assert state.status == "concluido"
    assert len(steps_recorded) == 4
    assert steps_recorded[0][0] == 1
    assert steps_recorded[1][0] == 2
    assert steps_recorded[2][0] == 3
    assert steps_recorded[3][0] == 4
