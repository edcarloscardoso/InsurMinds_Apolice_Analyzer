"""Regressão para o fallback heurístico do pipeline de documentos.

O fallback deve ser conservador: ausência de evidência não pode virar dado inventado
nem um documento D&O pode ser reclassificado como Automóvel por uma palavra isolada.
"""
from core.llm_client import GeminiClient


def _offline_client() -> GeminiClient:
    return GeminiClient(api_key="")


def test_do_document_with_isolated_vehicle_word_is_not_classified_as_auto():
    client = _offline_client()
    text = """
    EZZE Seguros S.A.
    Seguro de Responsabilidade Civil de Administradores e Diretores (D&O).
    Cobertura Side A e Side B para administradores.
    O contrato também menciona veículo para fins de exemplo de dano material.
    """
    dao = client.extract_structured_apolice(
        raw_text=text,
        nome_arquivo="contrato_real_ezze.pdf",
        file_hash="hash-ezze",
    )

    assert dao.cod_ramo == "0378"
    assert "D&O" in (dao.ramo_descricao or "")
    assert dao.limite_responsabilidade != "100% Tabela FIPE (Valor de Mercado Referenciado)"
    assert all("guincho" not in c.lower() for c in dao.coberturas)
    assert all("carro reserva" not in c.lower() for c in dao.coberturas)


def test_unknown_document_does_not_receive_fabricated_insurance_data():
    client = _offline_client()
    text = """
    Documento contratual genérico.
    O texto menciona veículo apenas em uma definição.
    Não há identificação suficiente do produto de seguro.
    """
    dao = client.extract_structured_apolice(
        raw_text=text,
        nome_arquivo="documento_generico.pdf",
        file_hash="hash-unknown",
    )

    assert dao.cod_ramo is None
    assert dao.seguradora is None
    assert dao.segurado is None
    assert dao.limite_responsabilidade is None
    assert dao.franquia is None
    assert dao.premio_total is None
    assert dao.coberturas == []
    assert dao.exclusoes == []
    assert dao.metodo_extracao == "heuristic_fallback"
    assert dao.confianca_extracao <= 0.5


def test_demo_fixture_keeps_explicit_mock_fallback_scope():
    client = _offline_client()
    text = """
    Allianz Global Corporate & Specialty
    Side A Side B
    Limite R$ 10.000.000,00
    """
    dao = client.extract_structured_apolice(
        raw_text=text,
        nome_arquivo="apolice_do_allianz.pdf",
        file_hash="hash-demo",
    )

    assert dao.metodo_extracao == "mock_fallback"
    assert dao.cod_ramo == "0378"


def test_long_documents_are_split_into_overlapping_chunks_without_truncation():
    client = _offline_client()
    text = "".join(f"--- PÁGINA {i} ---\n" + ("conteudo " * 7000) + "\n" for i in range(1, 7))

    chunks = client._chunk_text(text, max_chars=15000, overlap=1000)

    assert len(chunks) > 1
    assert chunks[0]
    assert chunks[-1]
    assert "PÁGINA 6" in chunks[-1]
    assert sum(len(chunk) for chunk in chunks) > len(text)
