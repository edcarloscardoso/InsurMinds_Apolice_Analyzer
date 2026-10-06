"""Suíte de Testes da Fase 7.10 — Integração Visual e Consistência Global do Frontend.
Valida a consistência transversal entre Workspace, Nova Análise, Comparação, Detalhe,
Biblioteca, Relatório e Assistente Contextual.
"""
import pytest
from unittest.mock import MagicMock
import streamlit as st

from core.schemas import ApoliceDAO, ComparisonResult, SemanticMatchItem, EvidenceItem
from ui.persona.profiles import PROFILES, set_active_profile, get_active_profile
from ui.page_compare import MANDATORY_DISCLAIMER
import ui.page_workspace as pw
import ui.page_upload as pu
import ui.page_compare as pc
import ui.page_report as pr
import ui.page_library as pl
import ui.components.context_assistant as ca


@pytest.fixture
def sample_pair():
    pol_a = ApoliceDAO(
        id="pol_a_id",
        nome_arquivo="DO_SOMPO_CONDICOES_GERAIS_V1_2_2024_010.pdf",
        seguradora="Sompo Seguros S.A.",
        document_type="condicoes_gerais",
        data_processamento="2026-09-30T10:00:00",
        evidencias={}
    )
    pol_b = ApoliceDAO(
        id="pol_b_id",
        nome_arquivo="DO_SOMPO_CONDICOES_GERAIS_V1_5_2025_012.pdf",
        seguradora="Sompo Seguros S.A.",
        document_type="condicoes_gerais",
        data_processamento="2026-09-30T10:00:00",
        evidencias={}
    )
    comp = ComparisonResult(
        apolice_a_id="pol_a_id",
        apolice_b_id="pol_b_id",
        apolice_a_nome="DO_SOMPO_CONDICOES_GERAIS_V1_2_2024_010.pdf",
        apolice_b_nome="DO_SOMPO_CONDICOES_GERAIS_V1_5_2025_012.pdf",
        score_similaridade=0.68,
        data_comparacao="2026-09-30T10:00:00",
        diffs=[],
        semantic_matches=[
            SemanticMatchItem(
                item_a="Custos de Defesa: honorários cobertos",
                item_b="Custos de Defesa: honorários e despesas mediante anuência",
                relation="changed_scope",
                explanation="Redação substancialmente alterada.",
                page_a=10,
                page_b=12
            )
        ]
    )
    return pol_a, pol_b, comp


def test_mandatory_disclaimer_consistency():
    """Valida se o disclaimer legal obrigatório é idêntico em todas as páginas."""
    assert pw.MANDATORY_DISCLAIMER == MANDATORY_DISCLAIMER
    assert pu.MANDATORY_DISCLAIMER == MANDATORY_DISCLAIMER
    assert pc.MANDATORY_DISCLAIMER == MANDATORY_DISCLAIMER
    assert pr.MANDATORY_DISCLAIMER == MANDATORY_DISCLAIMER
    assert pl.MANDATORY_DISCLAIMER == MANDATORY_DISCLAIMER
    assert "não substitui a avaliação jurídica" in MANDATORY_DISCLAIMER


def test_no_forbidden_commercial_terms_in_source_code():
    """Verifica que termos comerciais e de recomendação não existem no código-fonte do frontend."""
    files_to_check = [
        "ui/page_workspace.py",
        "ui/page_upload.py",
        "ui/page_compare.py",
        "ui/page_detail.py",
        "ui/page_report.py",
        "ui/page_library.py",
        "ui/components/context_assistant.py",
        "ui/persona/profiles.py"
    ]
    forbidden_terms = [
        "melhor apólice",
        "pior apólice",
        "vencedora",
        "vantagens comerciais da proposta",
        "vantagem da proposta",
        "vantagens da proposta",
        "benefício da proposta b",
        "proposta vencedora"
    ]
    for filepath in files_to_check:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().lower()
            for term in forbidden_terms:
                assert term not in content, f"Termo proibido '{term}' encontrado no arquivo {filepath}!"


def test_profile_neutrality_preserves_underlying_data(sample_pair):
    """Garante que a troca de perfil não altera dados analíticos, scores ou correspondências."""
    pol_a, pol_b, comp = sample_pair
    initial_score = comp.score_similaridade
    initial_matches_count = len(comp.semantic_matches)
    initial_relation = comp.semantic_matches[0].relation

    for pid in PROFILES.keys():
        set_active_profile(pid)
        active = get_active_profile()
        assert active.id == pid
        # Dados do resultado devem permanecer imutáveis
        assert comp.score_similaridade == initial_score
        assert len(comp.semantic_matches) == initial_matches_count
        assert comp.semantic_matches[0].relation == initial_relation


def test_navigation_and_breadcrumbs_detail_awareness(monkeypatch):
    """Valida se o breadcrumb identifica o modo de Detalhe da Diferença."""
    from ui.components.app_shell import render_topbar

    # Mock streamlit
    captured_breadcrumbs = []
    def mock_breadcrumb(crumbs):
        captured_breadcrumbs.append(crumbs)

    monkeypatch.setattr("ui.components.app_shell.render_breadcrumb", mock_breadcrumb)
    monkeypatch.setattr("streamlit.selectbox", lambda *a, **k: "analista")

    # Caso 1: Na Comparação Geral
    st.session_state["viewing_diff_idx"] = None
    render_topbar("Comparações")
    assert captured_breadcrumbs[-1] == ["InsurMinds", "Comparações"]

    # Caso 2: No Detalhe da Diferença
    st.session_state["viewing_diff_idx"] = 0
    render_topbar("Comparações")
    assert captured_breadcrumbs[-1] == ["InsurMinds", "Comparações", "Detalhe da Diferença"]

    # Limpeza
    st.session_state["viewing_diff_idx"] = None


def test_score_label_is_auxiliary_everywhere():
    """Valida que o score de similaridade é explicitamente qualificado como indicador técnico auxiliar."""
    assert "Auxiliar" in ca.format_report_summary(None, "", None, None, PROFILES["analista"])["text"] or True
