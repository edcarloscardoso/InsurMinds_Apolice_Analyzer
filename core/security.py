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

    # Validação estrita de extensão para PDF
    ext = Path(filename).suffix.lower()
    if ext != ".pdf":
        return False, f"Extensão '{ext}' inválida. Somente arquivos PDF são permitidos."

    # Validação de Magic Bytes (%PDF-)
    header_sample = file_bytes[:1024]
    if b"%PDF-" not in header_sample:
        return False, "Conteúdo binário inválido: cabeçalho PDF (%PDF-) não encontrado no arquivo."

    return True, "Arquivo PDF válido."


def validate_document_content(file_bytes: bytes, filename: str) -> Tuple[bool, str, str]:
    """Valida se o conteúdo atende às restrições de formato, tamanho e integridade de arquivo PDF ou Imagem (PNG, JPG, JPEG).

    Retorna:
        Tuple[bool, str, str]: (sucesso, mensagem_ou_erro, document_format)
        onde document_format pode ser 'pdf', 'image' ou ''
    """
    if not file_bytes:
        return False, "Arquivo vazio ou não fornecido.", ""

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        return False, f"Arquivo excede o tamanho máximo permitido de {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB.", ""

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Extensão '{ext}' inválida. Formatos permitidos: PDF, PNG, JPG, JPEG.", ""

    # Validação de Arquivo PDF (%PDF-)
    if ext == ".pdf":
        header_sample = file_bytes[:1024]
        if b"%PDF-" not in header_sample:
            return False, "Conteúdo binário inválido: cabeçalho PDF (%PDF-) não encontrado no arquivo.", "pdf"
        return True, "Arquivo PDF válido.", "pdf"

    # Validação de Arquivo PNG (Magic bytes: 89 50 4E 47 0D 0A 1A 0A)
    if ext == ".png":
        if len(file_bytes) < 8 or file_bytes[:8] != b"\x89PNG\r\n\x1a\n":
            return False, "Conteúdo binário inválido: cabeçalho PNG (magic bytes) incompatível com extensão .png.", "image"
        try:
            from PIL import Image
            import io
            with Image.open(io.BytesIO(file_bytes)) as img:
                img.verify()
        except Exception as e_corrupt:
            return False, f"Arquivo de imagem PNG corrompido ou ilegível: {str(e_corrupt)}", "image"
        return True, "Arquivo de imagem PNG válido.", "image"

    # Validação de Arquivo JPEG/JPG (Magic bytes: FF D8 FF)
    if ext in (".jpg", ".jpeg"):
        if len(file_bytes) < 3 or file_bytes[:3] != b"\xff\xd8\xff":
            return False, f"Conteúdo binário inválido: cabeçalho JPEG (magic bytes) incompatível com extensão {ext}.", "image"
        try:
            from PIL import Image
            import io
            with Image.open(io.BytesIO(file_bytes)) as img:
                img.verify()
        except Exception as e_corrupt:
            return False, f"Arquivo de imagem JPEG corrompido ou ilegível: {str(e_corrupt)}", "image"
        return True, "Arquivo de imagem JPEG válido.", "image"

    return False, f"Formato '{ext}' não suportado.", ""


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
