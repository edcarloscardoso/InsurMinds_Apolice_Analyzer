"""Configurações centrais do InsurMinds Apólice Analyzer.
Gerencia variáveis de ambiente, caminhos do sistema de arquivos e parâmetros globais.
"""
from pathlib import Path
import os
from dotenv import load_dotenv

# Carrega arquivo .env caso exista
load_dotenv()

# Diretórios base
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
SAMPLE_POLICIES_DIR = DATA_DIR / "sample_policies"
ARTEFATOS_DIR = BASE_DIR / "Projeto_Final_Artefatos"

# Garante a existência dos diretórios fundamentais
for directory in [DATA_DIR, UPLOADS_DIR, SAMPLE_POLICIES_DIR, ARTEFATOS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Parâmetros de Ingestão e Segurança
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf"}

# Banco de Dados
DB_PATH = Path(os.getenv("DB_PATH", str(DATA_DIR / "apolices.db"))).resolve()

# Configurações do Google Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", "gemini-2.0-flash")

# Configurações do Servidor e Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
SERVER_ADDRESS = os.getenv("SERVER_ADDRESS", "127.0.0.1")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8501"))
