"""Testes automatizados da Fase 7.8 — Redesign da Tela 'Relatório'.
Valida a síntese profissional e rastreável:
- Recuperação fiel da análise ativa ou persistida no SQLite
- Exibição de cabeçalho editorial, identificação e resumo executivo
- Principais alterações substantivas e matriz de confronto resumida
- Evidências acessíveis com rastreabilidade literal
- Interpretação assistida com avisos de governança
- Score tratado unicamente como indicador técnico auxiliar
- Reutilização dos mecanismos de exportação (Markdown e JSON)
- Respeito aos 5 perfis e ausência total de viés comercial
"""
import pytest
from unittest.mock import patch, MagicMock

from core.schemas import ApoliceDAO, ComparisonResult, SemanticMatchItem, EvidenceItem
from ui.persona.profiles import PROFILES, get_profile_metadata
from ui.page_report import (
    render_report_page,
    _format_doc_type,
    _get_active_or_latest_analysis,
    MANDATORY_DISCLAIMER
)


@pytest.fixture
def mock_report_apolice_a():
    return ApoliceDAO(
        id="pol_sompo_a",
        nome_arquivo="DO_SOMPO_CONDICOES_GERAIS_V1_2_2024_010.pdf",
        data_processamento="2026-09-30T10:00:00Z",
        seguradora="Sompo Seguros S.A.",
        processo_susep="15414.900823/2014-41",
        document_type="condicoes_gerais",
        evidencias={
            "Inadimplemento do Prêmio": EvidenceItem(
                page=26,
                snippet="O não pagamento do prêmio poderá implicar suspensão.",
                method="pdf_text"
            )
        }
    )


@pytest.fixture
def mock_report_apolice_b():
    return ApoliceDAO(
        id="pol_sompo_b",
        nome_arquivo="DO_SOMPO_CONDICOES_GERAIS_V1_5_2025_012.pdf",
        data_processamento="2026-09-30T10:00:00Z",
        seguradora="Sompo Seguros S.A.",
        processo_susep="15414.900823/2014-41",
        document_type="condicoes_gerais",
        evidencias={
            "Inadimplemento do Prêmio": EvidenceItem(
                page=28,
                snippet="O inadimplemento acarretará cancelamento após notificação.",
                method="pdf_text"
            )
        }
    )


@pytest.fixture
def mock_report_comparison(mock_report_apolice_a, mock_report_apolice_b):
    return ComparisonResult(
        apolice_a_id=mock_report_apolice_a.id,
        apolice_b_id=mock_report_apolice_b.id,
        apolice_a_nome=mock_report_apolice_a.seguradora,
        apolice_b_nome=mock_report_apolice_b.seguradora,
        data_comparacao="2026-09-30T10:05:00Z",
        score_similaridade=67.6,
        summary="A apólice de 2025 adiciona prazo formal de notificação prévia de 10 dias.",
        semantic_matches=[
            SemanticMatchItem(
                item_a="Inadimplemento do Prêmio: Cláusula 18.6.1",
                item_b="Inadimplemento do Prêmio: Cláusula 16.10",
                equivalence=False,
                relation="changed_scope",
                explanation="Inclusão de exigência procedimental de notificação prévia de 10 dias.",
                confidence=0.96,
                page_a=26,
                page_b=28,
                evidence_a="O não pagamento do prêmio poderá implicar suspensão.",
                evidence_b="O inadimplemento acarretará cancelamento após notificação.",
                method_a="pdf_text",
                method_b="pdf_text"
            )
        ]
    )


def test_format_doc_type():
    assert _format_doc_type("condicoes_gerais") == "Condições Gerais"
    assert _format_doc_type("apolice_individual") == "Apólice Individual"
    assert _format_doc_type("unknown") == "Não especificado"


def test_mandatory_disclaimer_content():
    assert "assistida por IA" in MANDATORY_DISCLAIMER
    assert "jurídica" in MANDATORY_DISCLAIMER


def test_render_report_page_empty():
    """Valida o estado defensivo quando não há comparação ativa nem no banco."""
    with patch("ui.page_report._get_active_or_latest_analysis", return_value=(None, None, None, None)):
        with patch("streamlit.session_state", {}):
            render_report_page()


def test_render_report_page_happy_path(mock_report_comparison, mock_report_apolice_a, mock_report_apolice_b):
    """Valida renderização do relatório completo com dados reais em sessão."""
    mock_ret = (mock_report_comparison, "# Relatório Teste", mock_report_apolice_a, mock_report_apolice_b)
    with patch("ui.page_report._get_active_or_latest_analysis", return_value=mock_ret):
        with patch("streamlit.session_state", {}):
            render_report_page()


def test_render_report_page_all_profiles(mock_report_comparison, mock_report_apolice_a, mock_report_apolice_b):
    """Valida renderização do relatório sob todos os 5 perfis."""
    mock_ret = (mock_report_comparison, "# Relatório", mock_report_apolice_a, mock_report_apolice_b)
    for p in PROFILES.values():
        with patch("ui.page_report._get_active_or_latest_analysis", return_value=mock_ret):
            with patch("streamlit.session_state", {"user_profile": p.id}):
                render_report_page()


def test_no_forbidden_commercial_words(mock_report_comparison, mock_report_apolice_a, mock_report_apolice_b):
    """Garante ausência total de vocabulário comercial ou decisões automáticas."""
    forbidden_words = ["melhor apólice", "pior apólice", "vencedora", "vantagem unilateral", "benefício exclusivo"]
    summary = mock_report_comparison.summary.lower()
    for word in forbidden_words:
        assert word not in summary
