"""Módulo de segurança, higienização e validação de artefatos.
Implementa controles estritos contra Path Traversal, arquivos maliciosos e injeção de payload.
"""
from pathlib import Path
import hashlib
import re
from typing import Tuple
from core.config import MAX_FILE_SIZE_BYTES, ALLOWED_EXTENSIONS


def sanitize_filename(filename: str) -> str:
    """Higieniza o nome do arquivo, removendo caracteres especiais e sequências de navegação de diretório.
    Garante proteção contra Path Traversal (ex: ../).
    """
    # Remove qualquer caminho de diretório
    base_name = Path(filename).name
    # Permite apenas caracteres alfanuméricos, sublinhado, hífen e ponto
    cleaned = re.sub(r'[^a-zA-Z0-9_.-]', '_', base_name)
    # Remove múltiplos pontos consecutivos para evitar extensões disfarçadas
    cleaned = re.sub(r'\.{2,}', '.', cleaned)
    return cleaned if cleaned else "documento.pdf"


def validate_pdf_content(file_bytes: bytes, filename: str) -> Tuple[bool, str]:
    """Valida se o conteúdo atende às restrições de formato, tamanho e integridade de arquivo PDF.
    
    Retorna:
        Tuple[bool, str]: (sucesso, mensagem_ou_erro)
    """
    if not file_bytes:
        return False, "Arquivo vazio ou não fornecido."

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        return False, f"Arquivo excede o tamanho máximo permitido de {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB."

    # Validação de extensão
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Extensão '{ext}' inválida. Somente arquivos PDF são permitidos."

    # Validação de Magic Bytes (%PDF-)
    # A especificação PDF exige que o cabeçalho %PDF- esteja presente nos primeiros 1024 bytes
    header_sample = file_bytes[:1024]
    if b"%PDF-" not in header_sample:
        return False, "Conteúdo binário inválido: cabeçalho PDF (%PDF-) não encontrado no arquivo."

    return True, "Arquivo PDF válido."


def compute_file_hashes(file_bytes: bytes) -> Tuple[str, str]:
    """Calcula hash MD5 e SHA-256 do arquivo binário."""
    md5_hash = hashlib.md5(file_bytes).hexdigest()
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()
    return md5_hash, sha256_hash


def get_safe_destination_path(base_dir: Path, filename: str) -> Path:
    """Gera um caminho absoluto seguro e restrito ao diretório base, impedindo path traversal."""
    safe_name = sanitize_filename(filename)
    dest_path = (base_dir / safe_name).resolve()
    base_resolved = base_dir.resolve()

    if not dest_path.is_relative_to(base_resolved):
        raise ValueError(f"Tentativa de escape de diretório detectada para o arquivo {filename}")

    return dest_path
