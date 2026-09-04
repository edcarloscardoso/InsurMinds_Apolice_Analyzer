"""Testes unitários para motor de diff determinístico e score de similaridade Jaccard."""
from core.schemas import ApoliceDAO
from core.diff_engine import compare_policies, compare_list_items, are_values_equal


def test_are_values_equal_financial():
    """Valida normalização financeira aproximada."""
    assert are_values_equal("R$ 10.000.000,00", "10000000", is_financial=True) is True
    assert are_values_equal("R$ 50.000,00", "R$ 50.000", is_financial=True) is True
    assert are_values_equal("R$ 10.000.000,00", "R$ 5.000.000,00", is_financial=True) is False


def test_compare_list_items():
    """Valida identificação de coberturas exclusivas e em comum."""
    list_a = [
        "Cobertura Side A (Indivíduos não indenizados)",
        "Cobertura Side B (Reembolso)",
        "Investigação Regulatória CVM"
    ]
    list_b = [
        "cobertura side a",
        "Cobertura Side B",
        "Cobertura Side A DIC"
    ]

    excl_a, excl_b, comuns = compare_list_items(list_a, list_b)

    assert len(comuns) == 2  # Side A e Side B
    assert len(excl_a) == 1
    assert "Investigação Regulatória CVM" in excl_a
    assert len(excl_b) == 1
    assert "Cobertura Side A DIC" in excl_b


def test_compare_policies():
    """Valida execução completa da comparação entre duas apólices."""
    apolice_a = ApoliceDAO(
        id="pol_a",
        nome_arquivo="allianz.pdf",
        data_processamento="2026-09-04T10:00:00",
        seguradora="Allianz",
        segurado="TechCorp S.A.",
        limite_responsabilidade="R$ 10.000.000,00",
        franquia="R$ 50.000,00",
        premio_total="R$ 120.000,00",
        coberturas=["Side A", "Side B", "Investigação Regulatória"],
        exclusoes=["Dolo", "Fraude"]
    )

    apolice_b = ApoliceDAO(
        id="pol_b",
        nome_arquivo="chubb.pdf",
        data_processamento="2026-09-04T10:00:00",
        seguradora="Chubb",
        segurado="TechCorp S.A.",
        limite_responsabilidade="R$ 5.000.000,00",
        franquia="R$ 100.000,00",
        premio_total="R$ 85.000,00",
        coberturas=["Side A", "Side B", "Side A DIC"],
        exclusoes=["Dolo", "Fraude", "SEC"]
    )

    result = compare_policies(apolice_a, apolice_b)

    assert result.apolice_a_id == "pol_a"
    assert result.apolice_b_id == "pol_b"
    assert result.score_similaridade > 0.0
    assert len(result.diffs) > 0

    # LMG deve ser diferente
    lmg_diff = next(d for d in result.diffs if d.campo == "limite_responsabilidade")
    assert lmg_diff.ha_diferenca is True

    # Coberturas exclusivas
    assert "Investigação Regulatória" in result.coberturas_exclusivas_a
    assert "Side A DIC" in result.coberturas_exclusivas_b
