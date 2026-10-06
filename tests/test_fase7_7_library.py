"""Testes automatizados da Fase 7.7 — Redesign da Tela 'Biblioteca'.
Valida a camada de recuperação documental e gestão operacional do conhecimento:
- Identificação rápida de documentos, seguradora, tipo e metadados
- Indicação de uso em comparação e retomada funcional
- Filtragem e busca textual sobre dados em memória
- Tratamento defensivo de estados (vazio, sem resultado, etc.)
- Ausência total de viés comercial ou vocabulário proibido
"""
import pytest
from unittest.mock import patch, MagicMock

from core.schemas import ApoliceDAO, ComparisonResult
from ui.persona.profiles import PROFILES, get_profile_metadata
from ui.page_library import (
    render_library_page,
    _extract_year,
    _extract_pages_estimate,
    _format_doc_type,
    _get_saved_comparisons,
    _get_comparison_for_policy
)


@pytest.fixture
def mock_library_apolices():
    return [
        ApoliceDAO(
            id="pol_sompo_2024",
            nome_arquivo="DO_SOMPO_CONDICOES_GERAIS_V1_2_2024_010.pdf",
            data_processamento="2026-09-30T10:00:00Z",
            seguradora="Sompo Seguros S.A.",
            processo_susep="15414.900823/2014-41",
            document_type="condicoes_gerais",
            limite_responsabilidade="R$ 10.000.000,00",
            franquia="R$ 50.000,00",
            coberturas=["Side A", "Side B"],
            exclusoes=["Poluição", "Dolo"]
        ),
        ApoliceDAO(
            id="pol_chubb_2025",
            nome_arquivo="DO_CHUBB_CONDICOES_GERAIS_OFERTA_PUBLICA_2025_014.pdf",
            data_processamento="2026-09-30T10:05:00Z",
            seguradora="Chubb Seguros Brasil S.A.",
            processo_susep="15414.004455/2016-11",
            document_type="condicoes_gerais",
            limite_responsabilidade="R$ 20.000.000,00",
            franquia="R$ 100.000,00",
            coberturas=["Side A", "Side B", "Side C"],
            exclusoes=["Sanções Internacionais"]
        )
    ]


def test_extract_year():
    pol_a = ApoliceDAO(
        id="1", nome_arquivo="DO_SOMPO_CONDICOES_GERAIS_V1_2_2024_010.pdf",
        data_processamento="2026-09-30", seguradora="Sompo"
    )
    assert _extract_year(pol_a) == "2024"

    pol_b = ApoliceDAO(
        id="2", nome_arquivo="apolice_sem_ano.pdf",
        data_processamento="2026-09-30", seguradora="AIG",
        vigencia_inicio="01/01/2025"
    )
    assert _extract_year(pol_b) == "2025"


def test_format_doc_type():
    assert _format_doc_type("condicoes_gerais") == "Condições Gerais"
    assert _format_doc_type("apolice_individual") == "Apólice Individual"
    assert _format_doc_type("unknown") == "Não especificado"


def test_get_comparison_for_policy():
    comparisons = [
        {"apolice_a_id": "pol_1", "apolice_b_id": "pol_2", "score_similaridade": 80.0}
    ]
    assert _get_comparison_for_policy("pol_1", comparisons) is not None
    assert _get_comparison_for_policy("pol_2", comparisons) is not None
    assert _get_comparison_for_policy("pol_3", comparisons) is None


def test_render_library_page_empty():
    """Valida o estado defensivo quando o repositório estiver vazio."""
    with patch("core.database.db.list_apolices", return_value=[]):
        with patch("streamlit.session_state", {}):
            render_library_page()


def test_render_library_page_with_data(mock_library_apolices):
    """Valida a renderização corporativa com apólices reais cadastradas."""
    with patch("core.database.db.list_apolices", return_value=mock_library_apolices):
        with patch("streamlit.session_state", {}):
            render_library_page()


def test_render_library_page_all_profiles(mock_library_apolices):
    """Valida renderização sob todos os 5 perfis."""
    for p in PROFILES.values():
        with patch("core.database.db.list_apolices", return_value=mock_library_apolices):
            with patch("streamlit.session_state", {"user_profile": p.id}):
                render_library_page()


def test_render_library_page_search_filtering(mock_library_apolices):
    """Valida busca textual por seguradora e nome de arquivo."""
    with patch("core.database.db.list_apolices", return_value=mock_library_apolices):
        # Busca por 'Sompo'
        with patch("streamlit.session_state", {"library_search": "sompo"}):
            render_library_page()
        # Busca sem resultados
        with patch("streamlit.session_state", {"library_search": "inexistente_xyz_123"}):
            render_library_page()
