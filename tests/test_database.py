"""Testes unitários para camada de persistência SQLite e controle de idempotência."""
import pytest
from pathlib import Path
from core.database import DatabaseManager
from core.schemas import ApoliceDAO, ComparisonResult


@pytest.fixture
def temp_db(tmp_path):
    """Cria uma instância isolada de banco de dados para testes."""
    db_file = tmp_path / "test_apolices.db"
    return DatabaseManager(db_path=db_file)


def test_database_crud_and_idempotency(temp_db):
    """Valida salvamento, idempotência por hash, listagem e exclusão no SQLite."""
    dao = ApoliceDAO(
        id="hash_md5_teste_1",
        nome_arquivo="allianz_do.pdf",
        data_processamento="2026-09-04T10:00:00",
        seguradora="Allianz",
        segurado="TechCorp S.A.",
        numero_apolice="01.999.888",
        vigencia_inicio="01/01/2026",
        vigencia_fim="01/01/2027",
        premio_total="R$ 100.000,00",
        limite_responsabilidade="R$ 10.000.000,00",
        franquia="R$ 50.000,00",
        coberturas=["Side A", "Side B", "Penhora Online"],
        exclusoes=["Dolo", "Fraude"],
        retroatividade="3 anos",
        territorio="Brasil",
        legislacao_aplicavel="Brasileira",
        cod_ramo="0378",
        ramo_descricao="Responsabilidade Civil D&O",
        tipo_movimento="101",
        tipo_movimento_descricao="Emissão de Apólice",
        metodo_extracao="pdfplumber",
        confianca_extracao=1.0
    )

    # 1. Inserção
    saved_id = temp_db.save_apolice(dao)
    assert saved_id == "hash_md5_teste_1"

    # 2. Idempotência: re-salvar com mesmo hash não duplica
    dao.premio_total = "R$ 105.000,00"
    temp_db.save_apolice(dao)

    apolices = temp_db.list_apolices()
    assert len(apolices) == 1
    assert apolices[0].premio_total == "R$ 105.000,00"
    assert apolices[0].cod_ramo == "0378"
    assert apolices[0].tipo_movimento == "101"

    # 3. Consulta individual
    recovered = temp_db.get_apolice_by_id("hash_md5_teste_1")
    assert recovered is not None
    assert recovered.seguradora == "Allianz"
    assert recovered.cod_ramo == "0378"
    assert recovered.tipo_movimento == "101"
    assert len(recovered.coberturas) == 3

    # 4. Exclusão
    deleted = temp_db.delete_apolice("hash_md5_teste_1")
    assert deleted is True
    assert temp_db.get_apolice_by_id("hash_md5_teste_1") is None
    assert len(temp_db.list_apolices()) == 0


def test_comparison_persistence(temp_db):
    """Valida persistência de resultados de comparação analítica e relatórios."""
    comp = ComparisonResult(
        apolice_a_id="hash_a",
        apolice_b_id="hash_b",
        apolice_a_nome="Allianz",
        apolice_b_nome="Chubb",
        data_comparacao="2026-09-04T12:00:00",
        score_similaridade=78.4,
        diffs=[],
        coberturas_exclusivas_a=["Cobertura 1"],
        coberturas_exclusivas_b=["Cobertura 2"],
        coberturas_comuns=["Side A"]
    )

    report_md = "# Relatório Teste\nComparação concluída."
    comp_id = temp_db.save_comparison(comp, report_md)
    assert "hash_a" in comp_id

    # Recuperação
    res = temp_db.get_comparison("hash_a", "hash_b")
    assert res is not None
    assert res["score_similaridade"] == 78.4
    assert res["relatorio_markdown"] == report_md
