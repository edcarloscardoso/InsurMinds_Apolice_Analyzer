"""Testes unitários e de integração para o runner de descoberta do corpus externo (Fase 8.0A).
Garante conformidade estrita com governança, resolução de paths, cálculo de hashes e manifesto.
"""

import json
import os
import tempfile
from pathlib import Path
import pytest

from scripts.discover_external_dataset import (
    resolve_corpus_path,
    compute_hashes,
    validate_corpus_structure,
    build_manifest,
    get_workspace_file_hashes,
    get_database_processed_records,
    WORKSPACE_ROOT,
    DEFAULT_LOCAL_CORPUS
)


def test_compute_hashes_accuracy(tmp_path: Path):
    """Verifica se compute_hashes calcula SHA-256 e MD5 com precisão determinística."""
    test_file = tmp_path / "sample.txt"
    test_file.write_text("InsurMinds Apólice Analyzer - Homologação Externa D&O", encoding="utf-8")

    sha256, md5, size = compute_hashes(test_file)
    assert len(sha256) == 64
    assert len(md5) == 32
    assert size == len(test_file.read_bytes())


def test_resolve_corpus_path_env_var(monkeypatch, tmp_path: Path):
    """Garante que INSURMINDS_EXTERNAL_TEST_DIR tem prioridade sobre detecção automática."""
    fake_corpus = tmp_path / "fake_dataset_do"
    fake_corpus.mkdir()

    monkeypatch.setenv("INSURMINDS_EXTERNAL_TEST_DIR", str(fake_corpus))
    resolved_path, source = resolve_corpus_path()
    assert resolved_path == fake_corpus.resolve()
    assert "environment_variable" in source


def test_resolve_corpus_path_explicit_override(tmp_path: Path):
    """Garante que o parâmetro explícito sobrepõe qualquer outra configuração."""
    explicit_corpus = tmp_path / "explicit_dataset_do"
    explicit_corpus.mkdir()

    resolved_path, source = resolve_corpus_path(explicit_path=str(explicit_corpus))
    assert resolved_path == explicit_corpus.resolve()
    assert "cli_argument" in source


def test_resolve_corpus_path_nonexistent_raises(monkeypatch, tmp_path: Path):
    """Garante que caminhos inválidos na variável de ambiente lançam FileNotFoundError."""
    monkeypatch.setenv("INSURMINDS_EXTERNAL_TEST_DIR", str(tmp_path / "nao_existe_12345"))
    with pytest.raises(FileNotFoundError):
        resolve_corpus_path()


def test_corpus_structure_integrity_if_available():
    """Valida a estrutura do corpus externo caso o diretório esteja acessível na máquina."""
    if not DEFAULT_LOCAL_CORPUS.exists():
        pytest.skip("Corpus externo não disponível nesta máquina para teste direto")

    checks = validate_corpus_structure(DEFAULT_LOCAL_CORPUS)
    assert checks["readme_exists"] is True
    assert checks["documentos_dir_exists"] is True
    assert checks["metadados_dir_exists"] is True
    assert checks["catalogo_json_exists"] is True
    assert checks["catalogo_csv_exists"] is True
    assert checks["evidencias_dir_exists"] is True


def test_build_manifest_structure_and_governance(tmp_path: Path):
    """Valida a montagem do manifesto, integridade dos 15 documentos e conformidade de governança."""
    if not DEFAULT_LOCAL_CORPUS.exists():
        pytest.skip("Corpus externo não disponível nesta máquina para teste do manifesto")

    db_path = WORKSPACE_ROOT / "data" / "apolices.db"
    data_dir = WORKSPACE_ROOT / "data"

    manifest = build_manifest(
        corpus_dir=DEFAULT_LOCAL_CORPUS,
        corpus_source="test_runner",
        db_path=db_path,
        data_dir=data_dir
    )

    assert "metadata" in manifest
    assert "summary" in manifest
    assert "documents" in manifest
    assert "holdout_candidates_summary" in manifest
    assert "holdout_pairs_recommended" in manifest

    sm = manifest["summary"]
    assert sm["total_contractual_documents"] == 15
    assert sm["contractual_principais"] == 12
    assert sm["contractual_complementares"] == 3
    assert sm["copiados_para_workspace"] == 0  # Requisito crítico: zero PDFs copiados!
    assert sm["documentos_ineditos_no_db"] >= 4  # Pelo menos 4 documentos inéditos identificados

    # Verifica se os candidatos a holdout estão preenchidos com justificativas factuais
    assert len(manifest["holdout_candidates_summary"]) >= 4
    for c in manifest["holdout_candidates_summary"]:
        assert c["role"] is not None
        assert len(c["justificativa"]) > 20
        assert c["sha256"] is not None

    # Verifica se o manifesto pode ser serializado para JSON sem exceção
    dumped = json.dumps(manifest)
    assert len(dumped) > 1000
