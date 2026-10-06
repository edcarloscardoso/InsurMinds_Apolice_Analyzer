"""Testes automatizados da Fase 7.6 — Redesign da Tela 'Detalhe da Diferença'.
Garante que a tela de detalhe atenda aos princípios do Insurance Intelligence Design System:
- "Como mudou? → Onde está a prova?"
- Preservação da cadeia de custódia e fidelidade literal
- Neutralidade analítica absoluta (sem vocabulário comercial ou decisões automáticas)
- Respeito aos 5 perfis de trabalho
- Tratamento estrito de estados (detalhe encontrado, evidência ausente, navegação inválida, etc.)
"""
import pytest
from unittest.mock import patch, MagicMock

from core.schemas import ApoliceDAO, ComparisonResult, SemanticMatchItem, EvidenceItem
from ui.persona.profiles import PROFILES, get_profile_metadata
from ui.page_detail import (
    render_detail_page,
    _get_item_category,
    _get_profile_review_note
)
from ui.components.badges import SEMANTIC_RELATION_CONFIG


@pytest.fixture
def mock_apolice_a():
    return ApoliceDAO(
        id="pol_a_hash",
        nome_arquivo="DO_SOMPO_CONDICOES_GERAIS_V1_2_2024_010.pdf",
        data_processamento="2026-09-30T10:00:00Z",
        seguradora="Sompo Seguros S.A.",
        evidencias={
            "Inadimplemento do Prêmio": EvidenceItem(
                page=26,
                section="Cláusula 18.6.1",
                snippet="O não pagamento do prêmio nas datas acordadas poderá implicar a suspensão da cobertura.",
                method="pdf_text",
                confidence=0.98
            )
        }
    )


@pytest.fixture
def mock_apolice_b():
    return ApoliceDAO(
        id="pol_b_hash",
        nome_arquivo="DO_SOMPO_CONDICOES_GERAIS_V1_5_2025_012.pdf",
        data_processamento="2026-09-30T10:00:00Z",
        seguradora="Sompo Seguros S.A.",
        evidencias={
            "Inadimplemento do Prêmio": EvidenceItem(
                page=28,
                section="Cláusula 16.10",
                snippet="O inadimplemento acarretará cancelamento automático após notificação prévia de 10 dias.",
                method="pdf_text",
                confidence=0.95
            )
        }
    )


@pytest.fixture
def mock_comparison_result():
    return ComparisonResult(
        apolice_a_id="pol_a_hash",
        apolice_b_id="pol_b_hash",
        apolice_a_nome="Sompo Seguros S.A. 2024",
        apolice_b_nome="Sompo Seguros S.A. 2025",
        data_comparacao="2026-09-30T10:05:00Z",
        score_similaridade=88.5,
        semantic_matches=[
            SemanticMatchItem(
                item_a="Inadimplemento do Prêmio: Cláusula 18.6.1",
                item_b="Inadimplemento do Prêmio: Cláusula 16.10",
                equivalence=False,
                relation="changed_scope",
                explanation="A redação de 2025 inclui notificação prévia de 10 dias antes do cancelamento da cobertura.",
                confidence=0.94,
                page_a=26,
                page_b=28,
                method_a="pdf_text",
                method_b="pdf_text"
            ),
            SemanticMatchItem(
                item_a="Cobertura Side A: Garantia Individual Direta",
                item_b="Cobertura Side A: Garantia Individual Direta",
                equivalence=True,
                relation="semantic_equivalent",
                explanation="Redações substancialmente idênticas no escopo de indenização direta aos administradores.",
                confidence=0.99,
                page_a=36,
                page_b=39,
                method_a="pdf_text",
                method_b="pdf_text"
            )
        ]
    )


def test_get_item_category():
    assert _get_item_category("Poluição e Danos Ambientais") == "EXCLUSÕES CONTRATUAIS"
    assert _get_item_category("Inadimplemento do Prêmio") == "CONDIÇÕES GERAIS E OPERACIONAIS"
    assert _get_item_category("Limite Máximo de Garantia (LMG)") == "PARÂMETROS FINANCEIROS"
    assert _get_item_category("Cobertura Side B") == "COBERTURAS & GARANTIAS D&O"


def test_profile_review_notes_coverage():
    """Valida que todos os 5 perfis possuem microcopy neutro e diferenciado."""
    for p_id in ["analista", "subscritor", "corretor", "juridico", "visitante"]:
        note_divergent = _get_profile_review_note(p_id, "changed_condition")
        note_equiv = _get_profile_review_note(p_id, "semantic_equivalent")

        assert isinstance(note_divergent, str) and len(note_divergent) > 20
        assert isinstance(note_equiv, str) and len(note_equiv) > 20

        # Proibição absoluta de vocabulário tendencioso/comercial
        for forbidden in ["melhor", "pior", "vencedora", "vantagem", "benefício"]:
            assert forbidden not in note_divergent.lower()
            assert forbidden not in note_equiv.lower()


def test_render_detail_page_happy_path(mock_comparison_result, mock_apolice_a, mock_apolice_b):
    """Testa renderização sem erros no Streamlit com perfil padrão."""
    profile = get_profile_metadata("analista")
    with patch("streamlit.session_state", {}):
        # Não deve lançar exceção
        render_detail_page(mock_comparison_result, mock_apolice_a, mock_apolice_b, profile, item_idx=0)


def test_render_detail_page_all_profiles(mock_comparison_result, mock_apolice_a, mock_apolice_b):
    """Testa renderização sob todos os 5 perfis de usuário."""
    for p in PROFILES.values():
        with patch("streamlit.session_state", {}):
            render_detail_page(mock_comparison_result, mock_apolice_a, mock_apolice_b, p, item_idx=0)


def test_render_detail_page_missing_comparison():
    """Valida o estado defensivo quando ComparisonResult for None."""
    profile = get_profile_metadata("analista")
    with patch("streamlit.session_state", {}):
        render_detail_page(None, None, None, profile, item_idx=0)


def test_render_detail_page_invalid_index(mock_comparison_result, mock_apolice_a, mock_apolice_b):
    """Valida tratamento seguro de índice fora da faixa."""
    profile = get_profile_metadata("analista")
    with patch("streamlit.session_state", {}):
        render_detail_page(mock_comparison_result, mock_apolice_a, mock_apolice_b, profile, item_idx=999)


def test_render_detail_page_missing_evidence(mock_comparison_result, mock_apolice_a, mock_apolice_b):
    """Valida quando um dos lados não possui evidência documental disponível."""
    profile = get_profile_metadata("analista")
    # Limpa as evidências
    mock_apolice_a.evidencias = {}
    mock_comparison_result.semantic_matches[0].evidence_a = None
    mock_comparison_result.semantic_matches[0].evidence_b = None
    with patch("streamlit.session_state", {}):
        render_detail_page(mock_comparison_result, mock_apolice_a, mock_apolice_b, profile, item_idx=0)
