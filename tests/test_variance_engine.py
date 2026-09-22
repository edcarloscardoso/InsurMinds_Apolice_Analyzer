"""Testes unitários para o motor de variância contábil e detecção de maiores ofensores."""
import pytest
from core.variance_engine import (
    calculate_claims_variance,
    generate_sample_accounting_data,
    get_ramo_name,
    get_tipo_mov_name
)
from core.schemas import SinistroItem


def test_claims_variance_calculation_and_top_offender():
    """Valida o cálculo do delta global, identificação do ramo maior ofensor e sinistro ofensor."""
    sinistros = generate_sample_accounting_data()
    report = calculate_claims_variance(sinistros, periodo_referencia="08/2026")

    assert report.total_anterior_geral > 0
    assert report.total_atual_geral > report.total_anterior_geral
    assert report.delta_global > 0

    # Ramo Maior Ofensor deve ser o Ramo 0378 (D&O)
    assert report.ramo_maior_ofensor is not None
    assert report.ramo_maior_ofensor.cod_ramo == "0378"
    assert report.ramo_maior_ofensor.is_maior_ofensor is True
    assert report.ramo_maior_ofensor.delta_absoluto == 4100000.00

    # Sinistro Maior Ofensor deve ser SIN-2026-0378-01 (TechCorp Brasil, +R$ 3.6M)
    assert report.sinistro_maior_ofensor is not None
    assert report.sinistro_maior_ofensor.numero_sinistro == "SIN-2026-0378-01"
    assert report.sinistro_maior_ofensor.delta_variacao == 3600000.00

    # Deve conter os 5 ramos
    assert len(report.variacao_por_ramo) == 5
    assert len(report.top_sinistros_ofensores) <= 5

    # Justificativa técnica deve estar preenchida
    assert "0378" in report.justificativa_auditoria_markdown
    assert "SIN-2026-0378-01" in report.justificativa_auditoria_markdown


def test_empty_claims_variance():
    """Valida cálculo com lista vazia de sinistros."""
    report = calculate_claims_variance([], periodo_referencia="08/2026")
    assert report.total_anterior_geral == 0.0
    assert report.total_atual_geral == 0.0
    assert report.delta_global == 0.0
    assert report.ramo_maior_ofensor is None
    assert report.sinistro_maior_ofensor is None


def test_ramo_and_mov_naming():
    """Valida nomenclatura de ramos e movimentos SUSEP."""
    assert "D&O" in get_ramo_name("0378")
    assert "Automóvel" in get_ramo_name("0531")
    assert "Emissão" in get_tipo_mov_name("101")
    assert "Endosso" in get_tipo_mov_name("102")
