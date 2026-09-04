"""Testes unitários de validação de segurança e mitigação de vulnerabilidades (OWASP / Secure Web)."""
import pytest
from pathlib import Path
from core.security import (
    sanitize_filename,
    validate_pdf_content,
    compute_file_hashes,
    get_safe_destination_path
)


def test_sanitize_filename_prevents_directory_traversal():
    """Verifica se sequências de path traversal são neutralizadas."""
    dangerous = "../../etc/passwd"
    clean = sanitize_filename(dangerous)
    assert ".." not in clean
    assert "/" not in clean
    assert clean == "passwd"

    dangerous_windows = "..\\..\\windows\\system32\\cmd.exe"
    clean_win = sanitize_filename(dangerous_windows)
    assert "\\" not in clean_win
    assert "cmd.exe" in clean_win


def test_validate_pdf_content_accepts_valid_pdf():
    """Verifica aceitação de PDF legítimo com magic bytes %PDF-."""
    valid_pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    is_valid, msg = validate_pdf_content(valid_pdf_bytes, "apolice.pdf")
    assert is_valid is True
    assert "válido" in msg.lower()


def test_validate_pdf_content_rejects_non_pdf():
    """Verifica rejeição de extensões não permitidas e magic bytes ausentes."""
    # Extensão incorreta
    is_valid, msg = validate_pdf_content(b"%PDF-1.4...", "script.sh")
    assert is_valid is False
    assert "extensão" in msg.lower()

    # Conteúdo malicioso disfarçado de PDF
    fake_pdf = b"<html><script>alert(1)</script></html>"
    is_valid_fake, msg_fake = validate_pdf_content(fake_pdf, "malicioso.pdf")
    assert is_valid_fake is False
    assert "cabeçalho pdf" in msg_fake.lower()


def test_get_safe_destination_path_blocks_escape(tmp_path):
    """Verifica se tentativas de escape de diretório levantam exceção de segurança."""
    safe_path = get_safe_destination_path(tmp_path, "documento_normal.pdf")
    assert safe_path.parent == tmp_path

    # Tentativa com nomes com pontos múltiplos
    safe_traversal = get_safe_destination_path(tmp_path, "....//....//etc//passwd")
    assert safe_traversal.is_relative_to(tmp_path)
