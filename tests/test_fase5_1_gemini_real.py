"""Testes de Validação da Fase 5.1 — Gate Gemini Real.

Valida a integração real do Google Gemini dentro do pipeline:
1. Chamada com Structured Output nativo (ClauseComparisonSchema / ChunkExtractionSchema).
2. Extração estruturada ponta a ponta com chegada a ApoliceDAO.
3. Evidências contratuais reais (página, snippet, método, confiança).
4. Proteção de Condições Gerais (segurado=None, numero_apolice=None).
5. Execução do pipeline nos pares reais (DO010 x DO012 e DO005 x DO014).
6. Contingência controlada e fallback auditável (API key ausente, inválida ou erro 400/503).
"""
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from core.llm_client import GeminiClient, ClauseComparisonSchema, ChunkExtractionSchema
from core.diff_engine import compare_policies, compare_clauses_semantically
from core.schemas import ApoliceDAO, EvidenceItem
from agents.extractor_agent import extract_with_pdfplumber

from core.config import DATASET_DO_DIR
DATASET_DIR = DATASET_DO_DIR


@pytest.fixture
def online_or_fallback_client():
    """Cliente Gemini configurado com a chave do ambiente ou contingência auditável."""
    return GeminiClient()


def test_gemini_real_structured_output_schema():
    """A) Validação do schema Pydantic de Structured Output nativo sem regex."""
    payload = {
        "equivalence": True,
        "relation": "semantic_equivalent",
        "explanation": "As duas cláusulas são textualmente idênticas e semanticamente equivalentes no seguro D&O.",
        "confidence": 1.0
    }
    schema = ClauseComparisonSchema(**payload)
    assert schema.equivalence is True
    assert schema.relation == "semantic_equivalent"
    assert schema.confidence == 1.0

    chunk_payload = {
        "seguradora": "SOMPO SEGUROS S.A.",
        "segurado": None,
        "document_type": "condicoes_gerais",
        "processo_susep": "15414.652408/2023-71",
        "coberturas": ["Cobertura A", "Cobertura B"]
    }
    chunk_schema = ChunkExtractionSchema(**chunk_payload)
    assert chunk_schema.seguradora == "SOMPO SEGUROS S.A."
    assert chunk_schema.segurado is None


def test_gemini_real_call_or_graceful_error_logging(online_or_fallback_client):
    """B) Chamada real ao Gemini registra sucesso ou falha sanitizada sem crash."""
    clause_a = "19.3.1. Cada Segurado poderá escolher livremente seus respectivos advogados e deverá contestar e se defender em qualquer Reclamação."
    clause_b = "19.3.1. Cada Segurado poderá escolher livremente seus respectivos advogados e deverá contestar e se defender em qualquer Reclamação."

    result = online_or_fallback_client.compare_clauses_semantically(clause_a, clause_b)

    # Se a chave for válida, retorna o resultado estruturado; se foi revogada/expirada, registra gemini_error
    if result is not None:
        assert result.get("equivalence") is True
        assert result.get("relation") == "semantic_equivalent"
        assert online_or_fallback_client.last_call_stats.get("success") is True
    else:
        stats = online_or_fallback_client.last_call_stats
        assert stats.get("success") is False
        assert stats.get("extraction_method") in ("gemini_error", "heuristic_fallback")
        assert "error" in stats.get("details", {}) or "reason" in stats.get("details", {})


def test_gemini_structured_output_mock_simulation():
    """C) Simulação controlada de resposta do SDK google.genai com Structured Output."""
    mock_client = GeminiClient(api_key="simulated-key")
    mock_client.client = MagicMock()

    mock_response = MagicMock()
    mock_response.text = '{"equivalence": false, "relation": "changed_condition", "explanation": "A Cláusula A estipula redução de vigência por Tabela de Prazo Curto, enquanto a B estabelece cancelamento após 15 dias de notificação.", "confidence": 0.95}'
    mock_client.client.models.generate_content.return_value = mock_response

    res = mock_client.compare_clauses_semantically("Clausula A", "Clausula B")
    assert res is not None
    assert res["equivalence"] is False
    assert res["relation"] == "changed_condition"
    assert "Prazo Curto" in res["explanation"]
    assert mock_client.last_call_stats["success"] is True
    assert mock_client.last_call_stats["extraction_method"] == "gemini_structured_output"


def test_gemini_pipeline_extraction_do010(online_or_fallback_client):
    """D) Execução do pipeline completo no documento real DO010 com rastreabilidade."""
    p10 = DATASET_DIR / "DO_SOMPO_CONDICOES_GERAIS_V1_2_2024_010.pdf"
    if not p10.exists():
        pytest.skip("PDF DO010 não encontrado no dataset")

    raw_text, pages = extract_with_pdfplumber(p10)
    dao = online_or_fallback_client.extract_structured_apolice(raw_text, p10.name, "hash-sompo-10")

    assert isinstance(dao, ApoliceDAO)
    assert "SOMPO" in dao.seguradora.upper()
    assert dao.document_type == "condicoes_gerais"
    assert dao.segurado is None
    assert dao.numero_apolice is None
    assert "15414.652408/2023-71" in dao.processo_susep
    assert len(dao.coberturas) >= 4
    assert len(dao.evidencias) > 0


def test_gemini_evidence_integrity(online_or_fallback_client):
    """E) Evidências rastreáveis: página e snippet preservados sem fabricação."""
    p10 = DATASET_DIR / "DO_SOMPO_CONDICOES_GERAIS_V1_2_2024_010.pdf"
    if not p10.exists():
        pytest.skip("PDF DO010 não encontrado no dataset")

    raw_text, pages = extract_with_pdfplumber(p10)
    dao = online_or_fallback_client.extract_structured_apolice(raw_text, p10.name, "hash-sompo-10")

    ev_defesa = dao.evidencias.get("Defesa e Acordos")
    assert ev_defesa is not None
    assert ev_defesa.page == 31
    assert "livremente seus respectivos advogados" in ev_defesa.snippet
    assert ev_defesa.method in ("pdfplumber", "pdf_text", "llm")
    assert ev_defesa.confidence > 0.80


def test_gemini_real_sompo_comparison(online_or_fallback_client):
    """F) Comparação real Sompo DO010 x DO012 com detecção de cláusula nova e alterada."""
    p10 = DATASET_DIR / "DO_SOMPO_CONDICOES_GERAIS_V1_2_2024_010.pdf"
    p12 = DATASET_DIR / "DO_SOMPO_CONDICOES_GERAIS_V1_5_2025_012.pdf"
    if not p10.exists() or not p12.exists():
        pytest.skip("PDFs da Sompo não encontrados")

    text_10, _ = extract_with_pdfplumber(p10)
    text_12, _ = extract_with_pdfplumber(p12)

    dao_10 = online_or_fallback_client.extract_structured_apolice(text_10, p10.name, "h10")
    dao_12 = online_or_fallback_client.extract_structured_apolice(text_12, p12.name, "h12")

    comp = compare_policies(dao_10, dao_12, llm_client=online_or_fallback_client)

    assert comp.score_similaridade > 0
    # Cláusula nova exclusiva em B descoberta
    assert any("Agravamento do Risco" in c for c in comp.clausulas_especiais_exclusivas_b)
    # Inadimplemento do Prêmio detectado como divergente
    inad_match = [m for m in comp.semantic_matches if "inadimplemento" in m.item_a.lower()]
    assert len(inad_match) >= 1
    assert inad_match[0].equivalence is False
    assert inad_match[0].relation in ("changed_condition", "changed_scope")


def test_gemini_controlled_fallback_offline():
    """G) Fallback determinístico seguro quando API key estiver ausente ou desativada."""
    offline_client = GeminiClient(api_key="")
    assert offline_client.is_available() is False

    # Não deve lançar exceção e deve registrar status heuristic_fallback
    res = offline_client.compare_clauses_semantically("Clausula A", "Clausula B")
    assert res is None
    assert offline_client.last_call_stats.get("extraction_method") == "heuristic_fallback"
    assert offline_client.last_call_stats.get("success") is False

    # Extração offline segura
    dao = offline_client.extract_structured_apolice("Contrato de teste...", "teste.pdf", "hash-off")
    assert isinstance(dao, ApoliceDAO)
    assert dao.metodo_extracao == "heuristic_fallback"
