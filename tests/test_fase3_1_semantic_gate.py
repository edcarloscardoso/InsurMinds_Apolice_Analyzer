"""Testes de validação da Fase 3.1 — Gate de Qualidade Semântica.

Garante que Processo SUSEP e Número da Apólice sejam tratados como identificadores
distintos e independentes:
- Processo SUSEP NÃO contamina numero_apolice.
- Quando houver apenas Processo SUSEP (ex: Condições Gerais), numero_apolice permanece None.
- Evidências acompanham estritamente seus respectivos campos.
- Quando ambos existirem no mesmo documento, ambos são extraídos e evidenciados.
- Persistência e idempotência no banco preservam ambos os identificadores.
"""
import pytest
from core.schemas import ApoliceDAO, EvidenceItem
from core.llm_client import GeminiClient
from core.diff_engine import compare_policies
from core.database import DatabaseManager


@pytest.fixture
def offline_client():
    return GeminiClient(api_key="")


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_semantic_gate.db"
    return DatabaseManager(db_path=db_file)


# -----------------------------------------------------------------------------
# A. Processo SUSEP não é número de apólice
# C. Documento somente com processo SUSEP mantém numero_apolice=None
# D. Evidência do processo SUSEP aponta para o campo correto
# -----------------------------------------------------------------------------
def test_processo_susep_is_not_numero_apolice(offline_client):
    text = """
    --- PÁGINA 1 ---
    EZZE Seguros S.A.
    CONDIÇÕES GERAIS DE SEGURO D&O
    Processo SUSEP 15414.601633.2021-88
    Ramo: 0378 - Responsabilidade Civil D&O
    """
    dao = offline_client.extract_structured_apolice(
        raw_text=text,
        nome_arquivo="condicoes_gerais_ezze.pdf",
        file_hash="hash-susep-only"
    )

    # Processo SUSEP deve ser capturado em processo_susep
    assert dao.processo_susep == "Proc. SUSEP 15414.601633.2021-88"
    assert "processo_susep" in dao.evidencias
    ev_susep = dao.evidencias["processo_susep"]
    assert ev_susep.page == 1
    assert "15414.601633.2021-88" in ev_susep.snippet
    assert ev_susep.method == "pdf_text"
    assert ev_susep.confidence >= 0.90

    # numero_apolice DEVE ser None e NÃO ter evidência
    assert dao.numero_apolice is None
    assert "numero_apolice" not in dao.evidencias
    assert dao.evidencias.get("numero_apolice") is None


# -----------------------------------------------------------------------------
# B. Número explícito de apólice é reconhecido corretamente
# -----------------------------------------------------------------------------
def test_numero_apolice_explicito_is_extracted_correctly(offline_client):
    text = """
    --- PÁGINA 1 ---
    Chubb Seguros Brasil S.A.
    ESPECIFICAÇÃO DA APÓLICE
    Apólice nº: 01.0775.000999/00
    Tomador: Global Tech S.A.
    """
    dao = offline_client.extract_structured_apolice(
        raw_text=text,
        nome_arquivo="especificacao_apolice_chubb.pdf",
        file_hash="hash-apolice-only"
    )

    assert dao.numero_apolice == "01.0775.000999/00"
    assert "numero_apolice" in dao.evidencias
    ev_apolice = dao.evidencias["numero_apolice"]
    assert ev_apolice.page == 1
    assert "01.0775.000999/00" in ev_apolice.snippet

    # Não havendo menção a processo regulatório, processo_susep permanece None
    assert dao.processo_susep is None
    assert "processo_susep" not in dao.evidencias


# -----------------------------------------------------------------------------
# Teste Específico: Ambos os identificadores presentes no mesmo documento
# -----------------------------------------------------------------------------
def test_both_identifiers_in_same_document_extracted_independently(offline_client):
    text = """
    --- PÁGINA 1 ---
    Allianz Global Corporate & Specialty
    Processo SUSEP: 15414.900123/2023-11
    Front Sheet - Apólice nº 02.0889.001924/02
    Tomador: BioFarmacêutica do Brasil S.A.
    """
    dao = offline_client.extract_structured_apolice(
        raw_text=text,
        nome_arquivo="front_sheet_allianz.pdf",
        file_hash="hash-both-ids"
    )

    # Identificadores distintos e corretos
    assert dao.processo_susep == "Proc. SUSEP 15414.900123/2023-11"
    assert dao.numero_apolice == "02.0889.001924/02"

    # Evidências distintas apontando para seus respectivos trechos
    assert "processo_susep" in dao.evidencias
    assert "numero_apolice" in dao.evidencias

    ev_susep = dao.evidencias["processo_susep"]
    assert "15414.900123/2023-11" in ev_susep.snippet

    ev_apolice = dao.evidencias["numero_apolice"]
    assert "02.0889.001924/02" in ev_apolice.snippet


# -----------------------------------------------------------------------------
# E. Documento desconhecido continua sem dados fabricados
# -----------------------------------------------------------------------------
def test_documento_desconhecido_has_no_susep_or_apolice(offline_client):
    text = """
    MANUAL DO PROPRIETÁRIO - TELEVISOR SMART 4K
    Para conectar a rede Wi-Fi, acesse o menu Configurações de Rede.
    """
    dao = offline_client.extract_structured_apolice(
        raw_text=text,
        nome_arquivo="manual_tv.txt",
        file_hash="hash-manual-tv"
    )

    assert dao.numero_apolice is None
    assert dao.processo_susep is None
    assert len(dao.evidencias) == 0


# -----------------------------------------------------------------------------
# H. Persistência e Idempotência com processo_susep
# -----------------------------------------------------------------------------
def test_database_persistence_and_idempotency_with_processo_susep(temp_db):
    ev_apolice = EvidenceItem(page=1, snippet="Apólice: 01.999.000", method="pdf_text")
    ev_susep = EvidenceItem(page=2, snippet="Processo SUSEP 15414.123/2021", method="pdf_text")

    dao = ApoliceDAO(
        id="hash-db-susep-test",
        nome_arquivo="apolice_susep_db.pdf",
        data_processamento="2026-09-28T16:30:00",
        seguradora="EZZE Seguros S.A.",
        numero_apolice="01.999.000",
        processo_susep="Proc. SUSEP 15414.123/2021",
        evidencias={
            "numero_apolice": ev_apolice,
            "processo_susep": ev_susep
        }
    )

    # 1. Salva no banco
    temp_db.save_apolice(dao)

    # 2. Recupera e valida integridade relacional
    evs_apolice = temp_db.get_policy_evidence(dao.id, field_name="numero_apolice")
    assert len(evs_apolice) == 1
    assert evs_apolice[0]["page"] == 1
    assert "01.999.000" in evs_apolice[0]["snippet"]

    evs_susep = temp_db.get_policy_evidence(dao.id, field_name="processo_susep")
    assert len(evs_susep) == 1
    assert evs_susep[0]["page"] == 2
    assert "15414.123/2021" in evs_susep[0]["snippet"]

    # 3. Idempotência: resalvar não duplica linhas
    temp_db.save_apolice(dao)
    all_evs = temp_db.get_policy_evidence(dao.id)
    assert len(all_evs) == 2

    # 4. Leitura do ApoliceDAO recupera ambos os campos
    loaded = temp_db.get_apolice_by_id(dao.id)
    assert loaded is not None
    assert loaded.numero_apolice == "01.999.000"
    assert loaded.processo_susep == "Proc. SUSEP 15414.123/2021"


# -----------------------------------------------------------------------------
# Comparador: FieldDiff suporta numero_apolice e processo_susep
# -----------------------------------------------------------------------------
def test_diff_engine_compares_processo_susep_and_numero_apolice():
    ev_a = EvidenceItem(page=1, snippet="Proc. SUSEP 15414.111/2020", method="pdf_text")
    ev_b = EvidenceItem(page=1, snippet="Proc. SUSEP 15414.222/2021", method="pdf_text")

    dao_a = ApoliceDAO(
        id="pol_susep_a",
        nome_arquivo="pol_a.pdf",
        data_processamento="2026-09-28T16:30:00",
        seguradora="Seguradora Alfa",
        processo_susep="Proc. SUSEP 15414.111/2020",
        evidencias={"processo_susep": ev_a}
    )
    dao_b = ApoliceDAO(
        id="pol_susep_b",
        nome_arquivo="pol_b.pdf",
        data_processamento="2026-09-28T16:30:00",
        seguradora="Seguradora Beta",
        processo_susep="Proc. SUSEP 15414.222/2021",
        evidencias={"processo_susep": ev_b}
    )

    result = compare_policies(dao_a, dao_b)
    susep_diff = next(d for d in result.diffs if d.campo == "processo_susep")

    assert susep_diff.ha_diferenca is True
    assert susep_diff.evidence_a is not None
    assert "15414.111/2020" in susep_diff.evidence_a.snippet
    assert susep_diff.evidence_b is not None
    assert "15414.222/2021" in susep_diff.evidence_b.snippet
