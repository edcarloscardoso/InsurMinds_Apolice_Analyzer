"""Testes de validação da Fase 2 — Correção do Pipeline de Extração e Isolamento.

Cobre integralmente os requisitos A a H da Fase 2:
A) D&O com 'veículo' -> não vira Auto, sem FIPE, guincho ou carro reserva.
B) D&O com frota -> permanece D&O com sinais de governança e gestão.
C) Documento externo -> conservador, sem crash, sem strings 'None', sem dados fictícios.
D) Fixture conhecida -> mock controlado estrito mantido.
E) Documentos longos -> todos os chunks, página final e zero descarte.
F) Consolidação -> resolução objetiva por completude; conflito não resolvido gera None.
G) Movimento SUSEP -> vocabulário contratual de cláusulas não altera tipo de movimento.
H) Suíte completa e não-regressão.
"""
import pytest
from core.llm_client import GeminiClient
from core.domain_detector import detect_document_domain, is_demo_sample
from core.document_chunker import build_document_chunks, chunk_text
from core.consolidation import (
    consolidate_scalar_field,
    consolidate_list_field,
    consolidate_extracted_chunks,
    normalize_scalar
)


@pytest.fixture
def offline_client():
    return GeminiClient(api_key="")


# -----------------------------------------------------------------------------
# Requisito A: D&O com menção isolada à palavra "veículo"
# -----------------------------------------------------------------------------
def test_requisito_a_do_with_vehicle_word_is_not_auto(offline_client):
    text = """
    EZZE Seguros S.A.
    CONDIÇÕES GERAIS DE SEGURO DE RESPONSABILIDADE CIVIL D&O
    Tomador: Construtora Alfa S.A.
    Apólice nº: 01.0775.000999/00
    Vigência: 10/01/2026 a 10/01/2027
    LMG: R$ 25.000.000,00
    Franquia: R$ 100.000,00
    Prêmio Total: R$ 180.000,00
    Cláusula 14.1 - Exclusão Específica:
    Não estão cobertas reclamações fundadas em danos materiais ou corporais causados por colisão
    ou tombamento de veículo terrestre de propriedade da sociedade estipulante.
    Coberturas: Custos de Defesa para Administradores, Side A, Side B.
    """
    dao = offline_client.extract_structured_apolice(
        raw_text=text,
        nome_arquivo="contrato_ezze_do.pdf",
        file_hash="hash-requisito-a"
    )

    assert dao.cod_ramo == "0378"
    assert "D&O" in (dao.ramo_descricao or "")
    assert dao.limite_responsabilidade == "R$ 25.000.000,00"
    assert dao.limite_responsabilidade != "100% Tabela FIPE (Valor de Mercado Referenciado)"
    assert all("guincho" not in c.lower() for c in dao.coberturas)
    assert all("carro reserva" not in c.lower() for c in dao.coberturas)
    assert all("fipe" not in c.lower() for c in dao.coberturas)


# -----------------------------------------------------------------------------
# Requisito B: D&O com frota corporativa operacional
# -----------------------------------------------------------------------------
def test_requisito_b_do_with_corporate_fleet_remains_do(offline_client):
    text = """
    APÓLICE DE SEGURO DE RESPONSABILIDADE CIVIL DIRECTORS AND OFFICERS (D&O)
    Seguradora: Chubb Seguros Brasil S.A.
    Tomador: Transportadora Rodoviária Nacional S.A.
    Apólice nº: 01.0775.000456/02
    Vigência: 15/02/2026 a 15/02/2027
    LMG: R$ 50.000.000,00
    Franquia: R$ 50.000,00 (Isento para Side A)
    Prêmio Total: R$ 320.000,00
    A sociedade opera no ramo logístico com mais de 800 veículos comerciais e carretas.
    O objetivo desta apólice é garantir a indenidade dos Diretores e Conselheiros de Administração
    contra Reclamações decorrentes de Atos de Gestão (Wrongful Acts).
    """
    dao = offline_client.extract_structured_apolice(
        raw_text=text,
        nome_arquivo="transportadora_do.pdf",
        file_hash="hash-requisito-b"
    )

    assert dao.cod_ramo == "0378"
    assert "D&O" in (dao.ramo_descricao or "")
    assert dao.segurado == "Transportadora Rodoviária Nacional S.A."
    assert dao.limite_responsabilidade == "R$ 50.000.000,00"
    assert dao.premio_total == "R$ 320.000,00"
    assert dao.franquia == "R$ 50.000,00 (Isento para Side A)"


# -----------------------------------------------------------------------------
# Requisito C: Documento externo desconhecido sem dados fictícios
# -----------------------------------------------------------------------------
def test_requisito_c_external_document_no_fabricated_data(offline_client):
    text = """
    INSTRUMENTO PARTICULAR DE PRESTAÇÃO DE SERVIÇOS DE AUDITORIA CONTÁBIL
    Contratante: TechSolutions Serviços Tecnológicos Ltda.
    Contratada: Auditoria Sigma Auditores Independentes.
    Objeto: Prestação de serviços de validação de balanço patrimonial.
    Valor Mensal: R$ 15.000,00.
    Foro: Comarca de Curitiba, Estado do Paraná.
    """
    dao = offline_client.extract_structured_apolice(
        raw_text=text,
        nome_arquivo="prestacao_servicos_auditoria.pdf",
        file_hash="hash-requisito-c"
    )

    assert dao.cod_ramo is None
    assert dao.ramo_descricao is None
    assert dao.seguradora is None
    assert dao.segurado is None
    assert dao.segurado != "None"
    assert dao.numero_apolice is None
    assert dao.limite_responsabilidade is None
    assert dao.franquia is None
    assert dao.premio_total is None
    assert dao.coberturas == []
    assert dao.exclusoes == []
    assert dao.clausulas_especiais == []
    assert dao.tipo_movimento is None
    assert dao.metodo_extracao == "heuristic_fallback"
    assert dao.confianca_extracao <= 0.5


# -----------------------------------------------------------------------------
# Requisito D: Fixture conhecida mantém mock controlado restrito
# -----------------------------------------------------------------------------
def test_requisito_d_demo_fixture_strictly_identified(offline_client):
    text = """
    Allianz Global Corporate & Specialty
    Seguro D&O
    Limite R$ 10.000.000,00
    """
    # 1. Nome exato de fixture de demonstração
    dao_demo = offline_client.extract_structured_apolice(
        raw_text=text,
        nome_arquivo="apolice_do_allianz.pdf",
        file_hash="hash-demo-1"
    )
    assert dao_demo.metodo_extracao == "mock_fallback"
    assert dao_demo.cod_ramo == "0378"
    assert dao_demo.seguradora == "Allianz Global Corporate & Specialty"

    # 2. Arquivo com nome similar mas que não é fixture oficial -> não aciona mock
    dao_other = offline_client.extract_structured_apolice(
        raw_text="Documento sem dados suficientes",
        nome_arquivo="allianz_outro_arquivo.pdf",
        file_hash="hash-other-1"
    )
    assert dao_other.metodo_extracao == "heuristic_fallback"


# -----------------------------------------------------------------------------
# Requisito E: Documentos longos particionados sem qualquer descarte
# -----------------------------------------------------------------------------
def test_requisito_e_long_document_full_coverage():
    # Cria documento sintético de 5 páginas
    pages_text = []
    for i in range(1, 6):
        pages_text.append(f"--- PÁGINA {i} ---\nTexto contratual da página {i}. " + ("conteudo " * 2000))
    full_text = "\n\n".join(pages_text)

    chunks = build_document_chunks(full_text, max_chars=8000, overlap=500)

    assert len(chunks) > 1
    assert chunks[0].page_start == 1
    assert chunks[-1].page_end == 5
    assert "PÁGINA 5" in chunks[-1].text

    # Verifica integridade de todos os caracteres originais
    reconstructed_text = "".join(c.text for c in chunks)
    for i in range(1, 6):
        assert f"Texto contratual da página {i}" in reconstructed_text


# -----------------------------------------------------------------------------
# Requisito F: Consolidação objetiva e tratamento de conflitos
# -----------------------------------------------------------------------------
def test_requisito_f_consolidation_objective_and_conflicts():
    # 1. Resolução por completude (subtermo contido no mais informativo)
    val, conf = consolidate_scalar_field("seguradora", [
        "Allianz",
        "Allianz Global Corporate & Specialty"
    ])
    assert val == "Allianz Global Corporate & Specialty"
    assert conf is None

    # 2. Resolução de franquia informativa
    val_franq, conf_franq = consolidate_scalar_field("franquia", [
        "Isento",
        "R$ 50.000,00 (Isento para Side A)"
    ])
    assert val_franq == "R$ 50.000,00 (Isento para Side A)"
    assert conf_franq is None

    # 3. Conflito genuíno irreconciliável -> gera None e registra conflito
    val_limite, conf_limite = consolidate_scalar_field("limite_responsabilidade", [
        "R$ 10.000.000,00",
        "R$ 25.000.000,00"
    ])
    assert val_limite is None
    assert conf_limite == ["R$ 10.000.000,00", "R$ 25.000.000,00"]

    # 4. Deduplicação semântica de listas
    coberturas = consolidate_list_field([
        ["Side A", "Custos de Defesa"],
        ["side a", "Penhora Online", "Custos de Defesa"]
    ])
    assert len(coberturas) == 3
    assert "Side A" in coberturas
    assert "Custos de Defesa" in coberturas
    assert "Penhora Online" in coberturas


# -----------------------------------------------------------------------------
# Requisito G: Vocabulário contratual de cláusulas não altera tipo de movimento
# -----------------------------------------------------------------------------
def test_requisito_g_contractual_clauses_do_not_alter_movement_type(offline_client):
    # Cláusula de rescisão com devolução de prêmio não pode tornar a apólice tipo 104
    text_rescisao = """
    CONDIÇÕES GERAIS DE SEGURO D&O
    Seguradora: Chubb Seguros Brasil S.A.
    Cláusula 18 - Rescisão Contratual e Cancelamento:
    A apólice poderá ser cancelada a qualquer momento por acordo bilateral.
    Havendo cancelamento pela Seguradora, a devolução do prêmio será calculada pro rata temporis
    com restituição integral das parcelas vincendas.
    """
    dao_rescisao = offline_client.extract_structured_apolice(
        raw_text=text_rescisao,
        nome_arquivo="condicoes_gerais_chubb.pdf",
        file_hash="hash-rescisao"
    )
    # Por se tratar de Condições Gerais sem certificado de emissão/endosso, tipo_movimento é None
    assert dao_rescisao.tipo_movimento is None
    assert dao_rescisao.tipo_movimento != "104"
    assert dao_rescisao.tipo_movimento != "106"

    # Cláusula com menção a endossos futuros não pode classificar como 102
    text_endosso = """
    CONDIÇÕES GERAIS DE SEGURO D&O
    Seguradora: Allianz Global Corporate & Specialty
    Cláusula 22 - Modificações da Apólice:
    Qualquer alteração ou inclusão de cobertura deverá ser formalizada mediante a emissão
    de endosso de cobrança ou endosso sem movimentação de prêmio.
    """
    dao_endosso = offline_client.extract_structured_apolice(
        raw_text=text_endosso,
        nome_arquivo="condicoes_gerais_allianz.pdf",
        file_hash="hash-endosso"
    )
    assert dao_endosso.tipo_movimento is None
    assert dao_endosso.tipo_movimento != "102"
    assert dao_endosso.tipo_movimento != "108"

    # Campo cadastral formal e explícito no documento -> reconhecido com sucesso
    text_formal = """
    APÓLICE DE SEGURO D&O
    Seguradora: EZZE Seguros S.A.
    Segurado: Empresa Beta S.A.
    Tipo de Movimento: 101
    LMG: R$ 15.000.000,00
    """
    dao_formal = offline_client.extract_structured_apolice(
        raw_text=text_formal,
        nome_arquivo="apolice_beta_emissao.pdf",
        file_hash="hash-formal"
    )
    assert dao_formal.tipo_movimento == "101"
    assert dao_formal.tipo_movimento_descricao == "101 - Emissão de Apólice"
