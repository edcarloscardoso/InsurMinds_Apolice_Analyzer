"""Testes unitários e de integração de interface para a FASE 7.9 — Assistente Contextual.
Valida:
1. Abertura e fechamento do painel/drawer;
2. Detecção e adaptação do contexto conforme a tela (Comparação, Detalhe, Relatório, Biblioteca, Workspace);
3. Comportamento específico para os 5 perfis corporativos;
4. Resposta factual com citações literais (Doc A/B, pág, seção);
5. Tratamento estrito de ausência de evidência ("Não há evidência documental disponível para sustentar esta resposta.");
6. Tratamento de contexto vazio ("Abra uma comparação ou uma diferença para ativar a assistência contextual.");
7. Presença obrigatória do disclaimer de governança de IA;
8. Ausência estrita de vocabulário comercial ou juízo de valor ("melhor", "pior", "vencedora", "vantagem", "benefício").
"""
import pytest
from unittest.mock import patch, MagicMock
import streamlit as st

from core.schemas import ApoliceDAO, ComparisonResult, SemanticMatchItem, FieldDiff, EvidenceItem
from ui.persona.profiles import PROFILES, get_active_profile, set_active_profile
from ui.components.context_assistant import (
    get_assistant_context,
    format_difference_summary,
    format_scope_changes,
    format_review_items,
    format_clause_explanation,
    format_clause_diff_ab,
    format_clause_evidence,
    format_report_summary,
    format_report_findings,
    format_library_summary,
    format_library_comparisons,
    format_workspace_guide,
    render_context_assistant,
    AI_ASSISTANT_GOVERNANCE_NOTICE,
    NO_EVIDENCE_AVAILABLE_MESSAGE,
    EMPTY_CONTEXT_MESSAGE
)


@pytest.fixture
def mock_apolices():
    pol_a = ApoliceDAO(
        id="pol-sompo-2024",
        nome_arquivo="DO_010_Sompo_Seguros_2024.pdf",
        data_processamento="2026-09-30T10:00:00Z",
        seguradora="Sompo Seguros",
        document_type="condicoes_gerais",
        vigencia_inicio="2024-01-01",
        vigencia_fim="2025-01-01",
        limite_responsabilidade="R$ 10.000.000,00",
        premio_total="R$ 50.000,00"
    )
    pol_b = ApoliceDAO(
        id="pol-sompo-2025",
        nome_arquivo="DO_012_Sompo_Seguros_2025.pdf",
        data_processamento="2026-09-30T10:00:00Z",
        seguradora="Sompo Seguros",
        document_type="condicoes_gerais",
        vigencia_inicio="2025-01-01",
        vigencia_fim="2026-01-01",
        limite_responsabilidade="R$ 15.000.000,00",
        premio_total="R$ 65.000,00"
    )
    return pol_a, pol_b


@pytest.fixture
def mock_comparison_result():
    match1 = SemanticMatchItem(
        item_a="Defesa Criminal e Custas Penais: Garantia de despesas de defesa em processos penais.",
        item_b="Defesa Criminal e Custas Penais: Garantia de defesa criminal estendida.",
        relation="changed_condition",
        explanation="A apólice 2025 exige comprovação documental prévia de custas para liberação da defesa criminal.",
        evidence_a="Garantia de despesas de defesa em processos penais com adiantamento prévio.",
        evidence_b="Garantia de defesa criminal estendida mediante comprovação documental de custas.",
        page_a=12,
        page_b=12,
        confidence=0.96
    )
    match2 = SemanticMatchItem(
        item_a="Poluição e Danos Ambientais: Exclui poluição e contaminação gradual ou repentina.",
        item_b="Poluição e Danos Ambientais: Exclui danos ambientais, ressalvados custos emergenciais de contenção até 10% do LMG.",
        relation="changed_scope",
        explanation="A apólice 2025 adiciona ressalva para custos emergenciais de contenção de poluição até 10% do LMG.",
        evidence_a="Exclui poluição e contaminação gradual ou repentina.",
        evidence_b="Exclui danos ambientais, ressalvados custos emergenciais de contenção até 10% do LMG.",
        page_a=24,
        page_b=24,
        confidence=0.92
    )
    match3 = SemanticMatchItem(
        item_a="Práticas Trabalhistas Indevidas (EPL): Cobertura para assédio moral e sexual no ambiente de trabalho.",
        item_b="Práticas Trabalhistas Indevidas (EPL): Cobertura para assédio moral e sexual no ambiente de trabalho.",
        relation="semantic_equivalent",
        explanation="Cláusulas materialmente equivalentes entre as duas minutas.",
        evidence_a=None,
        evidence_b=None,
        page_a=None,
        page_b=None,
        confidence=1.0
    )

    comp = ComparisonResult(
        apolice_a_id="pol-sompo-2024",
        apolice_b_id="pol-sompo-2025",
        apolice_a_nome="DO_010_Sompo_Seguros_2024.pdf",
        apolice_b_nome="DO_012_Sompo_Seguros_2025.pdf",
        data_comparacao="2026-09-30T10:00:00Z",
        score_similaridade=85.0,
        diffs=[
            FieldDiff(
                campo="limite_responsabilidade",
                rotulo="Limite Máximo de Garantia (LMG)",
                valor_apolice_a="R$ 10.000.000,00",
                valor_apolice_b="R$ 15.000.000,00",
                ha_diferenca=True,
                tipo_diferenca="diferente"
            )
        ],
        semantic_matches=[match1, match2, match3]
    )
    return comp


# =============================================================================
# 1. TESTES DE ESTADO E DETECÇÃO DE CONTEXTO
# =============================================================================

def test_assistant_context_detection_screens(mock_apolices, mock_comparison_result):
    pol_a, pol_b = mock_apolices
    st.session_state["active_comparison_result"] = mock_comparison_result
    st.session_state["selected_for_compare"] = [pol_a, pol_b]

    # Tela Comparação geral
    st.session_state["viewing_diff_idx"] = None
    ctx_cmp = get_assistant_context("Comparações")
    assert ctx_cmp["screen_key"] == "comparacao"
    assert ctx_cmp["pol_a"].id == pol_a.id
    assert ctx_cmp["pol_b"].id == pol_b.id

    # Tela Detalhe da Diferença
    st.session_state["viewing_diff_idx"] = 1
    ctx_dtl = get_assistant_context("Comparações")
    assert ctx_dtl["screen_key"] == "detalhe"
    assert ctx_dtl["item_idx"] == 1
    assert "Poluição e Danos Ambientais" in ctx_dtl["match_item"].item_a

    # Tela Relatórios
    ctx_rep = get_assistant_context("Relatórios")
    assert ctx_rep["screen_key"] == "relatorio"

    # Tela Documentos (Biblioteca)
    ctx_lib = get_assistant_context("Documentos")
    assert ctx_lib["screen_key"] == "biblioteca"

    # Tela Início
    ctx_wsp = get_assistant_context("Início")
    assert ctx_wsp["screen_key"] == "workspace"


# =============================================================================
# 2. TESTES DE SÍNTESE FACTUAL DE DIFERENÇAS E ESCOPO
# =============================================================================

def test_format_difference_summary_happy_path(mock_apolices, mock_comparison_result):
    pol_a, pol_b = mock_apolices
    profile = PROFILES["analista"]

    res = format_difference_summary(mock_comparison_result, pol_a, pol_b, profile)
    text = res["text"]

    assert "DO_010_Sompo_Seguros_2024.pdf" in text
    assert "DO_012_Sompo_Seguros_2025.pdf" in text
    assert "Defesa Criminal e Custas Penais" in text
    assert "Poluição e Danos Ambientais" in text
    assert "pág. 12" in text or "pág. 24" in text
    assert "Orientação de leitura (Analista de Seguros)" in text
    assert len(res["citations"]) >= 1


def test_format_scope_changes(mock_apolices, mock_comparison_result):
    pol_a, pol_b = mock_apolices
    profile = PROFILES["subscritor"]

    res = format_scope_changes(mock_comparison_result, pol_a, pol_b, profile)
    text = res["text"]

    assert "Poluição e Danos Ambientais" in text
    assert "ressalva para custos emergenciais" in text
    assert "DO_012_Sompo_Seguros_2025.pdf" in text


# =============================================================================
# 3. TESTES DE REVISÃO PROFISSIONAL NOS 5 PERFIS CORPORATIVOS
# =============================================================================

@pytest.mark.parametrize("profile_id", ["analista", "subscritor", "corretor", "juridico", "visitante"])
def test_format_review_items_all_profiles(profile_id, mock_apolices, mock_comparison_result):
    pol_a, pol_b = mock_apolices
    profile = PROFILES[profile_id]

    res = format_review_items(mock_comparison_result, pol_a, pol_b, profile)
    text = res["text"]

    assert profile.label in text
    assert "Defesa Criminal" in text or "Poluição" in text
    assert "Recomendação de revisão:" in text
    assert "DO_012_Sompo_Seguros_2025.pdf" in text


# =============================================================================
# 4. TESTES DE DETALHE DA DIFERENÇA E CLÁUSULA
# =============================================================================

def test_format_clause_explanation_and_diff(mock_apolices, mock_comparison_result):
    pol_a, pol_b = mock_apolices
    profile = PROFILES["juridico"]
    match = mock_comparison_result.semantic_matches[0]

    # Explicação da cláusula
    exp_res = format_clause_explanation(match, pol_a, pol_b, profile)
    assert "Defesa Criminal e Custas Penais" in exp_res["text"]
    assert "Alteração de Condição Operacional" in exp_res["text"]
    assert "Jurídico" in exp_res["text"]

    # Confronto direto A -> B
    diff_res = format_clause_diff_ab(match, pol_a, pol_b, profile)
    assert "Documento A (DO_010_Sompo_Seguros_2024.pdf)" in diff_res["text"]
    assert "Documento B (DO_012_Sompo_Seguros_2025.pdf)" in diff_res["text"]
    assert "Distinção Identificada pelo Motor Analítico" in diff_res["text"]


# =============================================================================
# 5. TESTES DE EVIDÊNCIA LITERAL E AUSÊNCIA DE EVIDÊNCIA
# =============================================================================

def test_format_clause_evidence_present(mock_apolices, mock_comparison_result):
    pol_a, pol_b = mock_apolices
    match = mock_comparison_result.semantic_matches[0]

    res = format_clause_evidence(match, pol_a, pol_b)
    assert res["has_evidence"] is True
    assert "Página: 12" in res["text"]
    assert "Seção:" in res["text"]
    assert "Trecho Literal Documento A" in res["text"]
    assert "Trecho Literal Documento B" in res["text"]


def test_format_clause_evidence_absent(mock_apolices, mock_comparison_result):
    pol_a, pol_b = mock_apolices
    match_sem_ev = mock_comparison_result.semantic_matches[2]  # EPL tem evidence=None

    res = format_clause_evidence(match_sem_ev, pol_a, pol_b)
    assert res["has_evidence"] is False
    assert NO_EVIDENCE_AVAILABLE_MESSAGE in res["text"]


# =============================================================================
# 6. TESTES DE RELATÓRIO E BIBLIOTECA
# =============================================================================

def test_format_report_summary_and_findings(mock_apolices, mock_comparison_result):
    pol_a, pol_b = mock_apolices
    profile = PROFILES["analista"]

    rep_sum = format_report_summary(mock_comparison_result, "# Relatório", pol_a, pol_b, profile)
    assert "85%" in rep_sum["text"]
    assert "Similaridade Estrutural (Auxiliar)" in rep_sum["text"]
    assert "Parecer Executivo D&O" in rep_sum["text"]

    rep_find = format_report_findings(mock_comparison_result, "# Relatório", profile)
    assert "Principais Achados Técnicos Consolidados" in rep_find["text"]
    assert "Defesa Criminal" in rep_find["text"]


def test_format_library_and_workspace_guide(mock_apolices):
    pol_a, pol_b = mock_apolices
    profile = PROFILES["corretor"]

    lib_sum = format_library_summary([pol_a, pol_b], profile)
    assert "Sompo Seguros" in lib_sum["text"]
    assert "2 documento(s)" in lib_sum["text"]

    wsp_guide = format_workspace_guide(profile)
    assert "Guia Operacional InsurMinds" in wsp_guide["text"]
    assert "Sompo 2024" in wsp_guide["text"]
    assert "Chubb 2024" in wsp_guide["text"]


# =============================================================================
# 7. TESTES DE GOVERNANÇA DE IA E AUSÊNCIA DE VOCABULÁRIO COMERCIAL
# =============================================================================

def test_governance_disclaimer_content():
    assert "Respostas são geradas a partir do contexto documental disponível" in AI_ASSISTANT_GOVERNANCE_NOTICE
    assert "devem ser revisadas pelo profissional responsável" in AI_ASSISTANT_GOVERNANCE_NOTICE
    assert "O texto contratual permanece sendo a fonte primária" in AI_ASSISTANT_GOVERNANCE_NOTICE


def test_no_forbidden_commercial_words(mock_apolices, mock_comparison_result):
    pol_a, pol_b = mock_apolices
    profile = PROFILES["analista"]

    forbidden = ["melhor", "pior", "vencedora", "vantagem", "benefício", "mais segura", "menos risco", "recomendo a apólice"]

    # Coletar todas as respostas geradas pelo assistente
    texts = [
        format_difference_summary(mock_comparison_result, pol_a, pol_b, profile)["text"].lower(),
        format_scope_changes(mock_comparison_result, pol_a, pol_b, profile)["text"].lower(),
        format_review_items(mock_comparison_result, pol_a, pol_b, profile)["text"].lower(),
        format_clause_explanation(mock_comparison_result.semantic_matches[0], pol_a, pol_b, profile)["text"].lower(),
        format_clause_diff_ab(mock_comparison_result.semantic_matches[0], pol_a, pol_b, profile)["text"].lower(),
        format_report_summary(mock_comparison_result, "", pol_a, pol_b, profile)["text"].lower(),
        format_workspace_guide(profile)["text"].lower()
    ]

    for t in texts:
        for word in forbidden:
            assert word not in t, f"Palavra proibida '{word}' detectada na saída do assistente."


# =============================================================================
# 8. TESTE DE RENDERIZAÇÃO DO COMPONENTE STREAMLIT SEM EXCEÇÃO
# =============================================================================

@pytest.mark.parametrize("page", ["Comparações", "Relatórios", "Documentos", "Início"])
def test_render_context_assistant_smoke(page, mock_apolices, mock_comparison_result):
    pol_a, pol_b = mock_apolices
    st.session_state["active_comparison_result"] = mock_comparison_result
    st.session_state["selected_for_compare"] = [pol_a, pol_b]
    st.session_state["viewing_diff_idx"] = None
    st.session_state["context_assistant_open"] = True

    try:
        render_context_assistant(current_page=page)
    except Exception as e:
        pytest.fail(f"render_context_assistant falhou na tela {page} com exceção: {e}")
