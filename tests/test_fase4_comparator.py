"""Testes para a Fase 4 — Comparador D&O Explicável + Normalização Semântica.
Validação completa dos requisitos A até P definidos na especificação.
"""
import pytest
from pathlib import Path
from core.database import DatabaseManager
from core.schemas import ApoliceDAO, EvidenceItem, FieldDiff, ComparisonResult, SemanticMatchItem
from core.diff_engine import (
    normalize_text,
    normalize_money,
    normalize_percentage,
    normalize_date,
    normalize_list,
    are_values_equal,
    compare_scalar_field,
    compare_clause_lists,
    compare_policies,
    TAXONOMY_CATEGORIES,
)


@pytest.fixture
def temp_db(tmp_path):
    """Cria uma instância isolada de banco de dados para testes."""
    db_file = tmp_path / "test_fase4.db"
    return DatabaseManager(db_path=db_file)


# =============================================================================
# A. Valores monetários equivalentes em formatos diferentes
# =============================================================================
def test_requisito_a_money_equivalence():
    # 10 milhões vs R$ 10.000.000,00
    assert are_values_equal("R$ 10.000.000,00", "10 milhões", is_financial=True) is True
    assert are_values_equal("10 milhoes", "R$ 10M", is_financial=True) is True
    assert are_values_equal("R$ 50 mil", "50000", is_financial=True) is True
    assert are_values_equal("isento", "R$ 0,00", is_financial=True) is True

    diff = compare_scalar_field(
        "limite_responsabilidade", "Limite Máximo de Garantia",
        "R$ 10.000.000,00", "10 milhões", is_financial=True
    )
    assert diff.ha_diferenca is False
    assert diff.tipo_diferenca == "igual"
    assert "equivalentes após normalização" in diff.explicacao or "idênticos" in diff.explicacao
    assert diff.normalized_a == "R$ 10.000.000,00"
    assert diff.normalized_b == "R$ 10.000.000,00"


# =============================================================================
# B. Datas equivalentes
# =============================================================================
def test_requisito_b_date_equivalence():
    assert are_values_equal("15/01/2025", "2025-01-15", is_date=True) is True
    assert are_values_equal("15 de janeiro de 2025", "15/01/2025", is_date=True) is True

    diff = compare_scalar_field(
        "vigencia_inicio", "Início de Vigência",
        "15/01/2025", "2025-01-15", is_date=True
    )
    assert diff.ha_diferenca is False
    assert diff.tipo_diferenca == "igual"
    assert diff.normalized_a == "2025-01-15"
    assert diff.normalized_b == "2025-01-15"


# =============================================================================
# C. Texto com diferenças somente de formatação
# =============================================================================
def test_requisito_c_text_formatting_equivalence():
    diff = compare_scalar_field(
        "segurado", "Empresa Segurada",
        "Empresa Alpha S.A. - Gestão & Participações",
        "empresa alpha sa gestao participacoes"
    )
    assert diff.ha_diferenca is False
    assert diff.tipo_diferenca == "igual"
    assert diff.normalized_a == diff.normalized_b


# =============================================================================
# D. Valores realmente diferentes
# =============================================================================
def test_requisito_d_truly_different_values():
    diff = compare_scalar_field(
        "limite_responsabilidade", "Limite Máximo de Garantia (LMG)",
        "R$ 50.000.000,00", "R$ 25.000.000,00", is_financial=True
    )
    assert diff.ha_diferenca is True
    assert diff.tipo_diferenca == "diferente"
    assert "diferentes: R$ 50.000.000,00 na Apólice A vs R$ 25.000.000,00 na Apólice B" in diff.explicacao
    assert "melhor" not in diff.explicacao.lower()
    assert "vantajosa" not in diff.explicacao.lower()


# =============================================================================
# E. Campo presente somente em A
# =============================================================================
def test_requisito_e_present_only_in_a():
    ev_a = EvidenceItem(page=4, snippet="Retroatividade: 01/01/2020", method="pdf_text")
    diff = compare_scalar_field(
        "retroatividade", "Data de Retroatividade",
        "01/01/2020", None, is_date=True, evidence_a=ev_a
    )
    assert diff.ha_diferenca is True
    assert diff.tipo_diferenca == "ausente_em_B"
    assert diff.valor_apolice_a == "01/01/2020"
    assert diff.valor_apolice_b is None
    assert diff.evidence_a == ev_a
    assert diff.evidence_b is None
    assert "ausente na Apólice B" in diff.explicacao


# =============================================================================
# F. Campo presente somente em B
# =============================================================================
def test_requisito_f_present_only_in_b():
    ev_b = EvidenceItem(page=5, snippet="Franquia de R$ 50.000,00", method="pdf_text")
    diff = compare_scalar_field(
        "franquia", "Franquia / Retenção",
        None, "R$ 50.000,00", is_financial=True, evidence_b=ev_b
    )
    assert diff.ha_diferenca is True
    assert diff.tipo_diferenca == "ausente_em_A"
    assert diff.valor_apolice_a is None
    assert diff.valor_apolice_b == "R$ 50.000,00"
    assert diff.evidence_b == ev_b
    assert diff.evidence_a is None
    assert "ausente na Apólice A" in diff.explicacao


# =============================================================================
# G. Listas com itens em comum/exclusivos
# =============================================================================
def test_requisito_g_list_common_and_exclusive():
    list_a = ["Side A (Garantia Individual)", "Side B (Reembolso)", "Penhora Online"]
    list_b = ["Side A (Garantia Individual)", "Side B (Reembolso)", "Custos de Extradição"]

    excl_a, excl_b, comuns, _ = compare_clause_lists(list_a, list_b)

    assert len(comuns) == 2
    assert len(excl_a) == 1
    assert "Penhora Online" in excl_a
    assert len(excl_b) == 1
    assert "Custos de Extradição" in excl_b


# =============================================================================
# H. Coberturas semanticamente equivalentes
# =============================================================================
def test_requisito_h_semantic_equivalent_clauses():
    list_a = ["Custos de Defesa"]
    list_b = ["Honorários Advocatícios e Despesas de Defesa"]

    excl_a, excl_b, comuns, sem_matches = compare_clause_lists(list_a, list_b)

    assert len(comuns) == 1
    assert len(excl_a) == 0
    assert len(excl_b) == 0
    assert len(sem_matches) >= 1
    match = sem_matches[0]
    assert match.equivalence is True
    assert match.relation == "semantic_equivalent"
    assert "Custos e Despesas de Defesa" in match.explanation


# =============================================================================
# I. Coberturas semanticamente diferentes (ex: Side A vs Side A DIC)
# =============================================================================
def test_requisito_i_semantic_different_clauses_dic():
    list_a = ["Side A"]
    list_b = ["Side A DIC"]

    excl_a, excl_b, comuns, sem_matches = compare_clause_lists(list_a, list_b)

    assert "Side A" in excl_a
    assert "Side A DIC" in excl_b
    assert len(comuns) == 0
    dic_match = next((m for m in sem_matches if m.relation == "different"), None)
    assert dic_match is not None
    assert dic_match.equivalence is False
    assert "DIC" in dic_match.explanation


# =============================================================================
# J. Conflito interno em A
# =============================================================================
def test_requisito_j_conflict_in_a():
    ev_a = EvidenceItem(page=2, snippet="R$ 10.000.000,00", method="pdf_text")
    diff = compare_scalar_field(
        "limite_responsabilidade", "Limite Máximo de Garantia",
        "R$ 10.000.000,00", "R$ 10.000.000,00",
        is_financial=True,
        evidence_a=ev_a,
        conflito_a=True,
        conflito_b=False
    )
    assert diff.ha_diferenca is True
    assert diff.tipo_diferenca == "conflito_A"
    assert "conflito documental interno" in diff.explicacao


# =============================================================================
# K. Conflito interno em B
# =============================================================================
def test_requisito_k_conflict_in_b():
    diff = compare_scalar_field(
        "premio_total", "Prêmio Total",
        "R$ 100.000,00", "R$ 100.000,00",
        is_financial=True,
        conflito_a=False,
        conflito_b=True
    )
    assert diff.ha_diferenca is True
    assert diff.tipo_diferenca == "conflito_B"
    assert "Apólice B apresenta conflito" in diff.explicacao


# =============================================================================
# L. Ausência de evidência documental
# =============================================================================
def test_requisito_l_absence_of_evidence():
    diff = compare_scalar_field(
        "territorio", "Âmbito Territorial",
        "Brasil", "Mundial",
        evidence_a=None,
        evidence_b=None
    )
    assert diff.evidence_a is None
    assert diff.evidence_b is None
    assert diff.confidence < 1.0  # Confiança reduzida por falta de sustentação documental
    assert diff.ha_diferenca is True


# =============================================================================
# M. Evidência A/B propagada corretamente
# =============================================================================
def test_requisito_m_evidence_propagation():
    ev_a = EvidenceItem(page=10, snippet="Cláusula 10: Limite R$ 50M", method="pdf_text")
    ev_b = EvidenceItem(page=12, snippet="Cláusula 8: Limite R$ 25M", method="pdf_text")

    dao_a = ApoliceDAO(
        id="pol_ev_a",
        nome_arquivo="pol_a.pdf",
        data_processamento="2026-09-28T17:00:00",
        limite_responsabilidade="R$ 50.000.000,00",
        evidencias={"limite_responsabilidade": ev_a}
    )
    dao_b = ApoliceDAO(
        id="pol_ev_b",
        nome_arquivo="pol_b.pdf",
        data_processamento="2026-09-28T17:00:00",
        limite_responsabilidade="R$ 25.000.000,00",
        evidencias={"limite_responsabilidade": ev_b}
    )

    result = compare_policies(dao_a, dao_b)
    diff = next(d for d in result.diffs if d.campo == "limite_responsabilidade")

    assert diff.evidence_a == ev_a
    assert diff.evidence_b == ev_b
    assert diff.evidence_a.page == 10
    assert diff.evidence_b.page == 12


# =============================================================================
# N. numero_apolice e processo_susep comparados separadamente
# =============================================================================
def test_requisito_n_numero_apolice_and_processo_susep_separated():
    ev_num = EvidenceItem(page=1, snippet="Apólice: 01.999.888", method="pdf_text")
    ev_susep = EvidenceItem(page=1, snippet="Proc. SUSEP 15414.601633/2021-88", method="pdf_text")

    dao_a = ApoliceDAO(
        id="pol_sep_a",
        nome_arquivo="pol_a.pdf",
        data_processamento="2026-09-28T17:00:00",
        numero_apolice="01.999.888",
        processo_susep="15414.601633/2021-88",
        evidencias={"numero_apolice": ev_num, "processo_susep": ev_susep}
    )
    dao_b = ApoliceDAO(
        id="pol_sep_b",
        nome_arquivo="pol_b.pdf",
        data_processamento="2026-09-28T17:00:00",
        numero_apolice="02.111.222",
        processo_susep="15414.601633/2021-88",
    )

    result = compare_policies(dao_a, dao_b)
    apolice_diff = next(d for d in result.diffs if d.campo == "numero_apolice")
    susep_diff = next(d for d in result.diffs if d.campo == "processo_susep")

    assert apolice_diff.ha_diferenca is True
    assert apolice_diff.categoria == "1. Identificação"
    assert susep_diff.ha_diferenca is False
    assert susep_diff.categoria == "1. Identificação"
    assert susep_diff.evidence_a == ev_susep


# =============================================================================
# O. Reprodutibilidade do resultado determinístico
# =============================================================================
def test_requisito_o_deterministic_reproducibility():
    dao_a = ApoliceDAO(
        id="rep_a",
        nome_arquivo="rep_a.pdf",
        data_processamento="2026-09-28T17:00:00",
        seguradora="Chubb Seguros",
        limite_responsabilidade="R$ 10.000.000,00",
        franquia="R$ 50.000,00",
        coberturas=["Side A", "Custos de Defesa"],
        exclusoes=["Dolo Comprovado"]
    )
    dao_b = ApoliceDAO(
        id="rep_b",
        nome_arquivo="rep_b.pdf",
        data_processamento="2026-09-28T17:00:00",
        seguradora="Sompo Seguros",
        limite_responsabilidade="10 milhões",
        franquia="R$ 100.000,00",
        coberturas=["Side A", "Honorários e Despesas de Defesa"],
        exclusoes=["Dolo Comprovado"]
    )

    run_1 = compare_policies(dao_a, dao_b)
    run_2 = compare_policies(dao_a, dao_b)

    assert run_1.score_similaridade == run_2.score_similaridade
    assert len(run_1.diffs) == len(run_2.diffs)
    for d1, d2 in zip(run_1.diffs, run_2.diffs):
        assert d1.campo == d2.campo
        assert d1.ha_diferenca == d2.ha_diferenca
        assert d1.tipo_diferenca == d2.tipo_diferenca
        assert d1.explicacao == d2.explicacao
    assert run_1.coberturas_comuns == run_2.coberturas_comuns
    assert run_1.coberturas_exclusivas_a == run_2.coberturas_exclusivas_a
    assert run_1.categories == run_2.categories


# =============================================================================
# P. Falha / Fallback da camada Gemini
# =============================================================================
def test_requisito_p_gemini_fallback():
    class BrokenGeminiClient:
        def is_available(self):
            return True

        def compare_clauses_semantically(self, a, b):
            raise RuntimeError("API quota exceeded ou timeout de rede simulado")

    broken_client = BrokenGeminiClient()

    # Deve degradar graciosamente para o motor determinístico sem lançar exceção
    list_a = ["Custos de Defesa"]
    list_b = ["Honorários Advocatícios e Despesas de Defesa"]

    excl_a, excl_b, comuns, matches = compare_clause_lists(list_a, list_b, llm_client=broken_client)

    assert len(comuns) == 1
    assert len(matches) >= 1
    assert matches[0].equivalence is True
    assert "Custos e Despesas de Defesa" in matches[0].explanation


# =============================================================================
# Q. Persistência relacional completa do ComparisonResult da Fase 4
# =============================================================================
def test_requisito_persistencia_fase4(temp_db):
    dao_a = ApoliceDAO(
        id="pers_a",
        nome_arquivo="pers_a.pdf",
        data_processamento="2026-09-28T17:00:00",
        seguradora="Chubb Seguros",
        limite_responsabilidade="R$ 10.000.000,00"
    )
    dao_b = ApoliceDAO(
        id="pers_b",
        nome_arquivo="pers_b.pdf",
        data_processamento="2026-09-28T17:00:00",
        seguradora="Sompo Seguros",
        limite_responsabilidade="R$ 20.000.000,00"
    )

    comp = compare_policies(dao_a, dao_b)
    comp_id = temp_db.save_comparison(comp, "# Relatório de Auditoria")

    saved_dict = temp_db.get_comparison("pers_a", "pers_b")
    assert saved_dict is not None
    loaded_comp = saved_dict["resultado"]
    assert isinstance(loaded_comp, ComparisonResult)
    assert len(loaded_comp.categories) > 0
    assert len(loaded_comp.diffs) > 0
    assert loaded_comp.diffs[0].categoria != ""
    assert loaded_comp.diffs[0].explicacao != ""
    assert loaded_comp.summary != ""
