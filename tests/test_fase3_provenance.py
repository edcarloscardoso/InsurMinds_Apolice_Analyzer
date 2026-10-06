"""Testes de validação da Fase 3 — Proveniência e Evidência Contratual Auditável.

Cobre integralmente os requisitos das Etapas 1 a 11 da Fase 3:
- EvidenceItem schema e serialização Pydantic
- Requisitos Obrigatórios A a E:
    A) Campo inexistente: valor None e evidence None.
    B) Valor detectado: valor preenchido e evidence preenchida.
    C) Documento desconhecido: não fabricar valor nem evidência/página.
    D) Conflito: valor None e duas ou mais evidências armazenadas.
    E) Documento longo: evidências em páginas > 10.
- Preservação de proveniência na consolidação
- Persistência relacional em policy_evidence e idempotência
- Contratos do motor de comparação com FieldDiff.evidence_a / evidence_b
"""
import pytest
from pathlib import Path
from core.schemas import EvidenceItem, ApoliceDAO
from core.llm_client import GeminiClient
from core.document_chunker import build_document_chunks, find_evidence_in_text
from core.consolidation import (
    consolidate_scalar_field_with_evidence,
    consolidate_list_field_with_evidence,
    consolidate_extracted_chunks
)
from core.diff_engine import compare_policies
from core.database import DatabaseManager


@pytest.fixture
def offline_client():
    return GeminiClient(api_key="")


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_evidence.db"
    return DatabaseManager(db_path=db_file)


# -----------------------------------------------------------------------------
# 1. EvidenceItem Schema & Pydantic Serialization
# -----------------------------------------------------------------------------
def test_evidence_item_schema_and_serialization():
    ev = EvidenceItem(
        page=12,
        page_end=13,
        section="Cláusula 5.2 - Cobertura Side A",
        snippet="A seguradora indenizará perdas decorrentes de reclamações cobertas...",
        method="pdf_text",
        confidence=0.95,
        chunk_index=2,
        char_start=15400,
        char_end=15480
    )

    dump_json = ev.model_dump_json()
    assert '"page":12' in dump_json
    assert '"method":"pdf_text"' in dump_json

    restored = EvidenceItem.model_validate_json(dump_json)
    assert restored.page == 12
    assert restored.page_end == 13
    assert restored.section == "Cláusula 5.2 - Cobertura Side A"
    assert restored.confidence == 0.95
    assert restored.char_start == 15400


# -----------------------------------------------------------------------------
# 2. Requisito Obrigatório A: Campo Inexistente -> Valor None e Evidence None
# -----------------------------------------------------------------------------
def test_requisito_a_campo_inexistente_has_none_value_and_no_evidence(offline_client):
    # Texto sem franquia e sem retroatividade
    text = """
    EZZE Seguros S.A.
    CONDIÇÕES GERAIS DE SEGURO D&O
    Tomador: Alpha Tech Brasil Ltda.
    Apólice: 01.0775.000123/45
    Vigência: 01/02/2026 a 01/02/2027
    LMG: R$ 10.000.000,00
    Prêmio Total: R$ 85.000,00
    """
    dao = offline_client.extract_structured_apolice(
        raw_text=text,
        nome_arquivo="contrato_sem_franquia.pdf",
        file_hash="hash-req-a"
    )

    # Campo ausente
    assert dao.franquia is None
    assert "franquia" not in dao.evidencias or dao.evidencias.get("franquia") is None

    # Campo ausente
    assert dao.retroatividade is None
    assert "retroatividade" not in dao.evidencias or dao.evidencias.get("retroatividade") is None


# -----------------------------------------------------------------------------
# 3. Requisito Obrigatório B: Valor Detectado -> Valor e Evidência Preenchidos
# -----------------------------------------------------------------------------
def test_requisito_b_valor_detectado_has_evidence_with_page_and_snippet(offline_client):
    text = """
    --- PÁGINA 1 ---
    EZZE Seguros S.A.
    Processo SUSEP 15414.601633.2021-88
    Tomador: Construtora Horizonte S.A.
    Vigência: 15/03/2026 a 15/03/2027
    LMG: R$ 50.000.000,00
    Prêmio Total: R$ 320.000,00
    Franquia: R$ 75.000,00
    Âmbito Territorial: Brasil e Jurisdição Mundial (exceto EUA e Canadá)
    Foro: Comarca de São Paulo/SP
    """
    dao = offline_client.extract_structured_apolice(
        raw_text=text,
        nome_arquivo="contrato_completo.pdf",
        file_hash="hash-req-b"
    )

    # Seguradora
    assert dao.seguradora == "EZZE Seguros S.A."
    ev_seg = dao.evidencias.get("seguradora")
    assert ev_seg is not None
    assert ev_seg.page == 1
    assert "EZZE" in ev_seg.snippet
    assert ev_seg.method == "pdf_text"
    assert ev_seg.confidence >= 0.90

    # LMG / Limite Responsabilidade
    assert dao.limite_responsabilidade == "R$ 50.000.000,00"
    ev_lim = dao.evidencias.get("limite_responsabilidade")
    assert ev_lim is not None
    assert ev_lim.page == 1
    assert "50.000.000" in ev_lim.snippet

    # Franquia
    assert dao.franquia == "R$ 75.000,00"
    ev_fr = dao.evidencias.get("franquia")
    assert ev_fr is not None
    assert ev_fr.page == 1
    assert "75.000" in ev_fr.snippet

    # Processo SUSEP vs Número da Apólice
    assert dao.processo_susep == "Proc. SUSEP 15414.601633.2021-88"
    assert dao.evidencias["processo_susep"].page == 1
    assert dao.numero_apolice is None
    assert "numero_apolice" not in dao.evidencias


# -----------------------------------------------------------------------------
# 4. Requisito Obrigatório C: Documento Desconhecido -> Sem Fabricação
# -----------------------------------------------------------------------------
def test_requisito_c_documento_desconhecido_no_fabricated_evidence(offline_client):
    text = """
    RECEITA DE BOLO DE CENOURA
    Ingredientes:
    3 cenouras médias raladas
    4 ovos inteiros
    2 xícaras de farinha de trigo
    1 xícara de óleo de milho
    Modo de preparo: bata tudo no liquidificador e asse a 180 graus por 40 minutos.
    """
    dao = offline_client.extract_structured_apolice(
        raw_text=text,
        nome_arquivo="receita_culinaria.txt",
        file_hash="hash-req-c"
    )

    assert dao.seguradora is None
    assert dao.segurado is None
    assert dao.limite_responsabilidade is None
    assert dao.premio_total is None
    assert dao.franquia is None
    assert dao.coberturas == []
    assert dao.exclusoes == []

    # Nenhuma evidência de seguro inventada
    assert len(dao.evidencias) == 0


# -----------------------------------------------------------------------------
# 5. Requisito Obrigatório D: Conflito -> Valor None e Múltiplas Evidências
# -----------------------------------------------------------------------------
def test_requisito_d_conflito_stores_multiple_evidences_and_value_none():
    ev1 = EvidenceItem(
        page=2,
        snippet="Limite Máximo de Garantia (LMG): R$ 10.000.000,00",
        method="pdf_text",
        confidence=0.95
    )
    ev2 = EvidenceItem(
        page=18,
        snippet="Limite Máximo de Garantia da Apólice: R$ 25.000.000,00",
        method="pdf_text",
        confidence=0.95
    )

    resolved_val, conflicts, resolved_ev, conflict_evs = consolidate_scalar_field_with_evidence(
        field_name="limite_responsabilidade",
        candidate_tuples=[
            ("R$ 10.000.000,00", ev1),
            ("R$ 25.000.000,00", ev2)
        ]
    )

    assert resolved_val is None
    assert resolved_ev is None
    assert len(conflicts) == 2
    assert "R$ 10.000.000,00" in conflicts
    assert "R$ 25.000.000,00" in conflicts
    assert len(conflict_evs) == 2
    assert {e.page for e in conflict_evs} == {2, 18}


# -----------------------------------------------------------------------------
# 6. Requisito Obrigatório E: Documento Longo -> Evidência em Página > 10
# -----------------------------------------------------------------------------
def test_requisito_e_documento_longo_evidence_on_page_greater_than_10():
    pages = []
    for p in range(1, 25):
        if p == 15:
            pages.append(f"--- PÁGINA {p} ---\nCláusula 8.4 - Exclusão de Danos por Poluição Ambiental Súbita.")
        elif p == 22:
            pages.append(f"--- PÁGINA {p} ---\nCláusula 19 - Eleição de Foro Exclusivo da Comarca de Belo Horizonte/MG.")
        else:
            pages.append(f"--- PÁGINA {p} ---\nTexto contratual geral do documento na página {p}.")

    long_text = "\n\n".join(pages)

    ev_pol = find_evidence_in_text(long_text, "Poluição Ambiental")
    assert ev_pol is not None
    assert ev_pol.page == 15
    assert ev_pol.page > 10
    assert "Poluição Ambiental" in ev_pol.snippet

    ev_foro = find_evidence_in_text(long_text, "Belo Horizonte")
    assert ev_foro is not None
    assert ev_foro.page == 22
    assert ev_foro.page > 10
    assert "Belo Horizonte" in ev_foro.snippet


# -----------------------------------------------------------------------------
# 7. Preservação de Evidência na Consolidação por Completude
# -----------------------------------------------------------------------------
def test_evidencia_survives_consolidation_by_completeness():
    ev_short = EvidenceItem(
        page=1,
        snippet="Seguradora: Allianz",
        method="pdf_text",
        confidence=0.85
    )
    ev_full = EvidenceItem(
        page=4,
        snippet="Companhia Emissora: Allianz Global Corporate & Specialty do Brasil S.A.",
        method="pdf_text",
        confidence=0.95
    )

    resolved_val, conflicts, resolved_ev, conflict_evs = consolidate_scalar_field_with_evidence(
        field_name="seguradora",
        candidate_tuples=[
            ("Allianz", ev_short),
            ("Allianz Global Corporate & Specialty", ev_full)
        ]
    )

    assert resolved_val == "Allianz Global Corporate & Specialty"
    assert conflicts is None
    assert resolved_ev is not None
    assert resolved_ev.page == 4
    assert resolved_ev.confidence == 0.95


# -----------------------------------------------------------------------------
# 8. Persistência Relacional em policy_evidence e Idempotência
# -----------------------------------------------------------------------------
def test_database_persistence_and_idempotency_of_evidence(temp_db):
    ev1 = EvidenceItem(
        page=1,
        snippet="EZZE Seguros S.A.",
        method="pdf_text",
        confidence=0.95
    )
    ev2 = EvidenceItem(
        page=5,
        snippet="LMG: R$ 50.000.000,00",
        method="pdf_text",
        confidence=0.95
    )
    conflict_ev_a = EvidenceItem(page=3, snippet="Prêmio R$ 100.000,00", method="pdf_text", confidence=0.90)
    conflict_ev_b = EvidenceItem(page=7, snippet="Prêmio R$ 150.000,00", method="pdf_text", confidence=0.90)

    dao = ApoliceDAO(
        id="hash-persistencia-teste",
        nome_arquivo="teste_evidencias.pdf",
        data_processamento="2026-09-28T16:00:00",
        seguradora="EZZE Seguros S.A.",
        limite_responsabilidade="R$ 50.000.000,00",
        evidencias={
            "seguradora": ev1,
            "limite_responsabilidade": ev2
        },
        evidencias_conflito={
            "premio_total": [conflict_ev_a, conflict_ev_b]
        }
    )

    # 1. Primeira persistência
    saved_id = temp_db.save_apolice(dao)
    assert saved_id == "hash-persistencia-teste"

    # Recupera evidências normais e de conflito
    all_evs = temp_db.get_policy_evidence(dao.id)
    assert len(all_evs) == 4  # 2 principais + 2 de conflito

    seg_ev = temp_db.get_policy_evidence(dao.id, field_name="seguradora")
    assert len(seg_ev) == 1
    assert seg_ev[0]["field_name"] == "seguradora"
    assert seg_ev[0]["page"] == 1
    assert seg_ev[0]["is_conflict"] == 0

    conf_evs = temp_db.get_policy_evidence(dao.id, field_name="premio_total")
    assert len(conf_evs) == 2
    assert all(c["is_conflict"] == 1 for c in conf_evs)

    # 2. Idempotência: salvar novamente não duplica registros na policy_evidence
    temp_db.save_apolice(dao)
    all_evs_again = temp_db.get_policy_evidence(dao.id)
    assert len(all_evs_again) == 4

    # 3. Leitura completa do ApoliceDAO recupera as evidências
    loaded_dao = temp_db.get_apolice_by_id(dao.id)
    assert loaded_dao is not None
    assert "seguradora" in loaded_dao.evidencias
    assert loaded_dao.evidencias["seguradora"].page == 1
    assert "premio_total" in loaded_dao.evidencias_conflito
    assert len(loaded_dao.evidencias_conflito["premio_total"]) == 2


# -----------------------------------------------------------------------------
# 9. Contratos de FieldDiff com Evidence A e Evidence B
# -----------------------------------------------------------------------------
def test_field_diff_receives_evidence_contracts():
    ev_a = EvidenceItem(page=2, snippet="LMG Apólice A: R$ 10.000.000,00", method="pdf_text")
    ev_b = EvidenceItem(page=3, snippet="LMG Apólice B: R$ 25.000.000,00", method="pdf_text")

    dao_a = ApoliceDAO(
        id="hash-a",
        nome_arquivo="apolice_a.pdf",
        data_processamento="2026-09-28T16:00:00",
        seguradora="Chubb Seguros Brasil S.A.",
        limite_responsabilidade="R$ 10.000.000,00",
        evidencias={"limite_responsabilidade": ev_a}
    )
    dao_b = ApoliceDAO(
        id="hash-b",
        nome_arquivo="apolice_b.pdf",
        data_processamento="2026-09-28T16:00:00",
        seguradora="EZZE Seguros S.A.",
        limite_responsabilidade="R$ 25.000.000,00",
        evidencias={"limite_responsabilidade": ev_b}
    )

    comp = compare_policies(dao_a, dao_b)
    lmg_diff = next(d for d in comp.diffs if d.campo == "limite_responsabilidade")

    assert lmg_diff.ha_diferenca is True
    assert lmg_diff.evidence_a is not None
    assert lmg_diff.evidence_a.page == 2
    assert "Apólice A" in lmg_diff.evidence_a.snippet
    assert lmg_diff.evidence_b is not None
    assert lmg_diff.evidence_b.page == 3
    assert "Apólice B" in lmg_diff.evidence_b.snippet
