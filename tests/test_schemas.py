"""Testes unitários para validação de esquemas e contratos de dados Pydantic v2."""
import pytest
from core.schemas import ApoliceDAO, FieldDiff, ComparisonResult, DocumentState, ComparisonState


def test_apolice_dao_creation_and_serialization():
    """Valida instanciação e serialização de ApoliceDAO."""
    dao = ApoliceDAO(
        id="md5_sample_hash_123",
        nome_arquivo="apolice_teste.pdf",
        data_processamento="2026-09-04T12:00:00",
        seguradora="Allianz Seguros",
        segurado="TechCorp Brasil S.A.",
        numero_apolice="01.234.567/89",
        vigencia_inicio="01/01/2026",
        vigencia_fim="01/01/2027",
        premio_total="R$ 100.000,00",
        limite_responsabilidade="R$ 10.000.000,00",
        franquia="R$ 50.000,00",
        coberturas=["Side A", "Side B"],
        exclusoes=["Dolo", "Fraude"],
        retroatividade="01/01/2023",
        territorio="Brasil",
        legislacao_aplicavel="Brasileira",
        metodo_extracao="pdfplumber",
        confianca_extracao=0.95
    )

    assert dao.id == "md5_sample_hash_123"
    assert dao.seguradora == "Allianz Seguros"
    assert len(dao.coberturas) == 2
    assert len(dao.exclusoes) == 2

    # Validação dos campos regulatórios SUSEP
    assert dao.cod_ramo == "0378"
    assert dao.tipo_movimento == "101"
    assert "D&O" in dao.ramo_descricao
    assert "Emissão" in dao.tipo_movimento_descricao

    # Validação de serialização JSON
    json_str = dao.model_dump_json()
    assert "TechCorp Brasil S.A." in json_str
    assert "0378" in json_str

    # Desserialização
    recovered = ApoliceDAO.model_validate_json(json_str)
    assert recovered.limite_responsabilidade == "R$ 10.000.000,00"
    assert recovered.cod_ramo == "0378"
    assert recovered.tipo_movimento == "101"


def test_field_diff_validation():
    """Valida o esquema de divergência de campos."""
    diff = FieldDiff(
        campo="limite_responsabilidade",
        rotulo="Limite de Responsabilidade",
        valor_apolice_a="R$ 10M",
        valor_apolice_b="R$ 5M",
        ha_diferenca=True,
        tipo_diferenca="valor"
    )
    assert diff.ha_diferenca is True
    assert diff.tipo_diferenca == "valor"


def test_comparison_result_validation():
    """Valida o esquema consolidado de resultado de comparação."""
    comp = ComparisonResult(
        apolice_a_id="hash_a",
        apolice_b_id="hash_b",
        apolice_a_nome="Allianz",
        apolice_b_nome="Chubb",
        data_comparacao="2026-09-04T12:00:00",
        score_similaridade=85.5,
        diffs=[],
        coberturas_exclusivas_a=["Penhora Online"],
        coberturas_exclusivas_b=["Side A DIC"],
        coberturas_comuns=["Side A", "Side B"]
    )
    assert comp.score_similaridade == 85.5
    assert len(comp.coberturas_exclusivas_a) == 1
    assert "Side A" in comp.coberturas_comuns


def test_sinistro_item_and_auditoria_report_schemas():
    """Valida os schemas de auditoria contábil de sinistros e variação."""
    from core.schemas import SinistroItem, RamoVarianceSummary, AuditoriaVarianceReport

    sinistro = SinistroItem(
        numero_sinistro="SIN-01",
        numero_apolice="AP-100",
        segurado="TechCorp",
        seguradora="Allianz",
        cod_ramo="0378",
        ramo_nome="D&O",
        tipo_mov="101",
        saldo_anterior=100000.0,
        saldo_atual=250000.0,
        delta_variacao=150000.0,
        status_sinistro="Avisado",
        causa_sinistro="Processo arbitral"
    )
    assert sinistro.delta_variacao == 150000.0
    assert sinistro.cod_ramo == "0378"

    summary = RamoVarianceSummary(
        cod_ramo="0378",
        ramo_nome="D&O",
        qtd_sinistros=1,
        total_anterior=100000.0,
        total_atual=250000.0,
        delta_absoluto=150000.0,
        delta_percentual=150.0,
        share_na_variacao_total=100.0,
        is_maior_ofensor=True
    )
    assert summary.is_maior_ofensor is True

    report = AuditoriaVarianceReport(
        periodo_referencia="08/2026",
        total_anterior_geral=100000.0,
        total_atual_geral=250000.0,
        delta_global=150000.0,
        delta_global_percentual=150.0,
        ramo_maior_ofensor=summary,
        sinistro_maior_ofensor=sinistro
    )
    assert report.ramo_maior_ofensor.cod_ramo == "0378"
    assert report.sinistro_maior_ofensor.numero_sinistro == "SIN-01"
