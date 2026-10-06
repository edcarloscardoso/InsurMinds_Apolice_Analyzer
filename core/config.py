"""Configurações centrais do InsurMinds Apólice Analyzer.
Gerencia variáveis de ambiente, caminhos do sistema de arquivos e parâmetros globais.
"""
from pathlib import Path
import os
import platform
from typing import Optional
from dotenv import load_dotenv

# Diretórios base
BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega arquivo .env caso exista
load_dotenv(BASE_DIR / ".env", override=True)
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
SAMPLE_POLICIES_DIR = DATA_DIR / "sample_policies"
DRIVE_POLICIES_DIR = DATA_DIR / "drive_policies"
ARTEFATOS_DIR = BASE_DIR / "Projeto_Final_Artefatos"
# Diretório do corpus externo opcional (resolvido dinamicamente via ENV ou caminho relativo estrutural)
_ext_dataset_env = os.getenv("INSURMINDS_EXTERNAL_TEST_DIR") or os.getenv("DATASET_DO_DIR")
if _ext_dataset_env:
    _ext_p = Path(_ext_dataset_env).resolve()
    DATASET_DO_DIR = _ext_p / "documentos" if (_ext_p / "documentos").is_dir() else _ext_p
elif (BASE_DIR.parent.parent / "desafio_final_docs" / "dataset_do" / "documentos").is_dir():
    DATASET_DO_DIR = (BASE_DIR.parent.parent / "desafio_final_docs" / "dataset_do" / "documentos").resolve()
else:
    DATASET_DO_DIR = (BASE_DIR / "data" / "dataset_do").resolve()

# Garante a existência dos diretórios fundamentais
for directory in [DATA_DIR, UPLOADS_DIR, SAMPLE_POLICIES_DIR, DRIVE_POLICIES_DIR, ARTEFATOS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Parâmetros de Ingestão e Segurança (PDF e Imagens)
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
ALLOWED_DOCUMENT_EXTENSIONS = ALLOWED_EXTENSIONS

# Banco de Dados
DB_PATH = Path(os.getenv("DB_PATH", str(DATA_DIR / "apolices.db"))).resolve()

# Configurações do Google Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
GEMINI_VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", "gemini-flash-lite-latest")

# Configurações do Servidor e Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
SERVER_ADDRESS = os.getenv("SERVER_ADDRESS", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8503"))


def resolve_tessdata_dir() -> Optional[Path]:
    """Resolve dinamicamente o diretório do tessdata em Linux e Windows 11.

    Ordem de Resolução:
    1. Variável de ambiente TESSDATA_PREFIX (se válida e existente)
    2. Variável de ambiente TESSERACT_CMD (procura pasta tessdata no mesmo diretório do executável)
    3. Windows:
       - %LOCALAPPDATA%\\Programs\\Tesseract-OCR\\tessdata
       - C:\\Program Files\\Tesseract-OCR\\tessdata
       - C:\\Program Files (x86)\\Tesseract-OCR\\tessdata
    4. Linux / POSIX:
       - /usr/share/tessdata
       - /usr/share/tesseract-ocr/5/tessdata
       - /usr/share/tesseract-ocr/4.00/tessdata
       - /usr/local/share/tessdata
    """
    # 1. TESSDATA_PREFIX existente
    if "TESSDATA_PREFIX" in os.environ:
        p = Path(os.environ["TESSDATA_PREFIX"]).resolve()
        if p.is_dir():
            return p

    # 2. TESSERACT_CMD
    tesseract_cmd = os.getenv("TESSERACT_CMD")
    if tesseract_cmd:
        cmd_p = Path(tesseract_cmd).resolve()
        cand = cmd_p.parent / "tessdata" if cmd_p.is_file() else cmd_p / "tessdata"
        if cand.is_dir():
            os.environ["TESSDATA_PREFIX"] = str(cand)
            return cand

    # 3. Candidatos por Sistema Operacional
    if platform.system() == "Windows":
        candidates = []
        local_app = os.getenv("LOCALAPPDATA")
        if local_app:
            candidates.append(Path(local_app) / "Programs" / "Tesseract-OCR" / "tessdata")
        candidates.extend([
            Path(r"C:\Program Files\Tesseract-OCR\tessdata"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR\tessdata"),
        ])
    else:
        candidates = [
            Path("/usr/share/tessdata"),
            Path("/usr/share/tesseract-ocr/5/tessdata"),
            Path("/usr/share/tesseract-ocr/4.00/tessdata"),
            Path("/usr/local/share/tessdata"),
        ]

    for c in candidates:
        if c.is_dir():
            os.environ["TESSDATA_PREFIX"] = str(c)
            return c

    return None


def get_ocr_language(tessdata_dir: Optional[Path] = None) -> str:
    """Determina o idioma de OCR com base na disponibilidade de modelos treinados (por+eng se por.traineddata existir)."""
    td = tessdata_dir or resolve_tessdata_dir()
    if td and (td / "por.traineddata").exists():
        return "por+eng"
    return "eng"
