"""Testes de Regressão e Validação da Fase 5 — Integração Real de LLM + Extração Semântica de Cláusulas.

Verifica o fluxo completo ponta a ponta:
PDF real -> extração completa -> chunking/páginas -> classificação documental ->
extração estruturada -> evidências -> identificação de cláusulas -> matching ->
comparação semântica -> relatório.
"""
import os
import pytest
from pathlib import Path

from core.llm_client import GeminiClient, llm_client
from core.diff_engine import compare_policies, compare_clauses_semantically, compare_clause_lists
from core.schemas import ApoliceDAO, EvidenceItem
from core.document_chunker import build_document_chunks, discover_contract_clauses
from agents.extractor_agent import extract_with_pdfplumber

from core.config import DATASET_DO_DIR
DATASET_DIR = DATASET_DO_DIR


@pytest.fixture
def offline_client():
    """Cliente Gemini sem API key para teste estrito de contingência."""
    return GeminiClient(api_key="")


# =============================================================================
# 1. DOCUMENTO LONGO SEM TRUNCAMENTO
# =============================================================================

def test_fase5_documento_longo_sem_truncamento(offline_client):
    """Garante que documento longo (ex: 45+ páginas) não tenha suas seções truncadas."""
    # Simula documento longo com 40 páginas e cláusulas na última página
    pages = []
    for i in range(1, 41):
        pages.append(f"--- PÁGINA {i} ---\nConteúdo textual da página {i} de condições gerais.")
    pages.append("--- PÁGINA 41 ---\n19.3.1. Cada Segurado poderá escolher livremente seus respectivos advogados e deverá contestar e se defender em qualquer Reclamação.")
    raw_text = "\n\n".join(pages)

    chunks = build_document_chunks(raw_text, max_chars=1000, overlap=100)
    assert len(chunks) >= 3

    # Cláusula na página 41 deve ser descoberta deterministicamente
    cobs, excs, esp, evs = discover_contract_clauses(raw_text, document_domain="do")
    assert any("Defesa e Acordos" in c for c in cobs)
    assert evs["Defesa e Acordos"].page == 41
    assert "escolher livremente" in evs["Defesa e Acordos"].snippet


# =============================================================================
# 2. CLÁUSULA NOVA DETECTADA EM B (EXCLUSIVA DE B)
# =============================================================================

def test_fase5_clausula_nova_detectada_exclusiva_b(offline_client):
    """Detecta automaticamente cláusula inédita em B via pipeline de extração e comparador."""
    text_a = "--- PÁGINA 1 ---\nCONTRATO DE SEGURO D&O\nCobertura Básica A: Indenização direta."
    text_b = (
        "--- PÁGINA 1 ---\nCONTRATO DE SEGURO D&O\nCobertura Básica A: Indenização direta.\n"
        "--- PÁGINA 15 ---\nCOBERTURA ADICIONAL DE DESPESAS DE CONTENÇÃO E SALVAMENTO DE SINISTRO\n"
        "Pago prêmio adicional, o seguro cobrirá despesas de contenção até o LMI."
    )

    dao_a = offline_client.extract_structured_apolice(text_a, "contrato_a.pdf", "hash-a")
    dao_b = offline_client.extract_structured_apolice(text_b, "contrato_b.pdf", "hash-b")

    res = compare_policies(dao_a, dao_b, llm_client=offline_client)

    assert any("Despesas de Contenção e Salvamento" in c for c in res.coberturas_exclusivas_b)
    assert not any("Despesas de Contenção e Salvamento" in c for c in res.coberturas_exclusivas_a)
    assert not any("Despesas de Contenção e Salvamento" in c for c in res.coberturas_comuns)


# =============================================================================
# 3. CLÁUSULA REMOVIDA DETECTADA EM A (EXCLUSIVA DE A)
# =============================================================================

def test_fase5_clausula_removida_detectada_exclusiva_a(offline_client):
    """Detecta automaticamente cláusula removida em B (presente exclusivamente em A)."""
    text_a = (
        "--- PÁGINA 1 ---\nCONTRATO DE SEGURO D&O\n"
        "--- PÁGINA 10 ---\nCOBERTURA ADICIONAL DE MULTAS E PENALIDADES\n"
        "Cobre multas civis e administrativas aplicadas a administradores."
    )
    text_b = "--- PÁGINA 1 ---\nCONTRATO DE SEGURO D&O\nSem coberturas de multas."

    dao_a = offline_client.extract_structured_apolice(text_a, "contrato_a.pdf", "hash-a")
    dao_b = offline_client.extract_structured_apolice(text_b, "contrato_b.pdf", "hash-b")

    res = compare_policies(dao_a, dao_b, llm_client=offline_client)

    assert any("Multas e Penalidades" in c for c in res.coberturas_exclusivas_a)
    assert not any("Multas e Penalidades" in c for c in res.coberturas_exclusivas_b)


# =============================================================================
# 4. MESMO TÍTULO COM ESCOPO DIFERENTE
# =============================================================================

def test_fase5_mesmo_titulo_escopo_diferente():
    """Duas cláusulas nominais idênticas com escopos ou ressalvas divergentes retornam changed_scope."""
    c_a = "Custos de Defesa: Adiantamento direto de todas as despesas incorridas sem necessidade de contratação adicional."
    c_b = "Custos de Defesa: É obrigatória a contratação da cobertura adicional específica; pagamento somente após trânsito em julgado."

    match = compare_clauses_semantically(c_a, c_b)
    assert match is not None
    assert match.relation in ("changed_scope", "different")
    assert match.equivalence is False


# =============================================================================
# 5. MESMO TÍTULO COM CONDIÇÃO DIFERENTE
# =============================================================================

def test_fase5_mesmo_titulo_condicao_diferente():
    """Duas cláusulas nominais idênticas com exigências procedimentais divergentes retornam changed_condition."""
    c_a = "Adiantamento de Custos de Defesa: O adiantamento será efetuado mediante prévia aprovação expressa por escrito da Seguradora."
    c_b = "Adiantamento de Custos de Defesa: O adiantamento será efetuado mediante solicitação simples, sem necessidade de consentimento prévio."

    match = compare_clauses_semantically(c_a, c_b)
    assert match is not None
    assert match.relation == "changed_condition"
    assert match.equivalence is False


# =============================================================================
# 6. MESMO TÍTULO COM LIMITE DIFERENTE
# =============================================================================

def test_fase5_mesmo_titulo_limite_diferente():
    """Duas cláusulas nominais idênticas com limites monetários divergentes retornam changed_limit."""
    c_a = "Gestão de Crise de Imagem: Fica estipulado o sublimite de até R$ 1.000.000,00 por sinistro."
    c_b = "Gestão de Crise de Imagem: Fica estipulado o sublimite de até R$ 5.000.000,00 por sinistro."

    match = compare_clauses_semantically(c_a, c_b)
    assert match is not None
    assert match.relation == "changed_limit"
    assert match.equivalence is False


# =============================================================================
# 7. EVIDÊNCIA A/B PRESERVADA COM PÁGINA, SNIPPET E MÉTODO
# =============================================================================

def test_fase5_evidencia_ab_preservada_com_pagina_snippet_metodo(offline_client):
    """Comprova que SemanticMatchItem retém proveniência completa de A e B (página, snippet, método)."""
    text_a = "--- PÁGINA 12 ---\nSEGURO D&O - CONDIÇÕES GERAIS\n19.3.1. Cada Segurado poderá escolher livremente seus respectivos advogados e deverá contestar e se defender em qualquer Reclamação."
    text_b = "--- PÁGINA 25 ---\nSEGURO D&O - CONDIÇÕES GERAIS\n19.3.1. Cada Segurado poderá escolher livremente seus respectivos advogados e deverá contestar e se defender em qualquer Reclamação."

    dao_a = offline_client.extract_structured_apolice(text_a, "sompo_do_v1.pdf", "hash-a")
    dao_b = offline_client.extract_structured_apolice(text_b, "sompo_do_v2.pdf", "hash-b")

    res = compare_policies(dao_a, dao_b, llm_client=offline_client)

    match_defesa = next((m for m in res.semantic_matches if "Defesa e Acordos" in m.item_a), None)
    assert match_defesa is not None
    assert match_defesa.equivalence is True
    assert match_defesa.relation == "semantic_equivalent"
    assert match_defesa.page_a == 12
    assert match_defesa.page_b == 25
    assert match_defesa.method_a == "pdf_text"
    assert match_defesa.method_b == "pdf_text"
    assert "escolher livremente" in match_defesa.evidence_a
    assert "escolher livremente" in match_defesa.evidence_b


# =============================================================================
# 8. CONDIÇÕES GERAIS E SEGURADO NONE SEM FRONT SHEET
# =============================================================================

def test_fase5_document_type_condicoes_gerais_segurado_none(offline_client):
    """Condições gerais sem apólice emitida mantém segurado=None e numero_apolice=None."""
    raw_text = (
        "SOMPO SEGUROS S.A.\n"
        "PROCESSO SUSEP 15414.652408/2023-71\n"
        "CONDIÇÕES GERAIS DO SEGURO D&O\n"
        "Definição de Segurado: administradores da Sociedade Tomadora."
    )
    dao = offline_client.extract_structured_apolice(raw_text, "CG_SOMPO.pdf", "hash-cg")

    assert dao.document_type == "condicoes_gerais"
    assert dao.segurado is None
    assert dao.numero_apolice is None
    assert dao.vigencia_inicio is None
    assert dao.vigencia_fim is None
    assert dao.tipo_movimento is None
    assert "segurado" not in dao.evidencias


# =============================================================================
# 9. EXECUÇÃO REAL DO PAR SOMPO (DO010 x DO012) SEM SNIPPETS HARDCODED
# =============================================================================

@pytest.mark.skipif(not (DATASET_DIR / "DO_SOMPO_CONDICOES_GERAIS_V1_2_2024_010.pdf").exists(), reason="PDFs reais necessários")
def test_fase5_real_corpus_pipeline_sompo_do010_x_do012(offline_client):
    """Execução end-to-end do pipeline completo sobre o par real Sompo v1.2 x v1.5."""
    p10 = DATASET_DIR / "DO_SOMPO_CONDICOES_GERAIS_V1_2_2024_010.pdf"
    p12 = DATASET_DIR / "DO_SOMPO_CONDICOES_GERAIS_V1_5_2025_012.pdf"

    # 1. Extração completa via pdfplumber
    text_10, pages_10 = extract_with_pdfplumber(p10)
    text_12, pages_12 = extract_with_pdfplumber(p12)
    assert pages_10 == 44
    assert pages_12 == 49

    # 2. Estruturação canônica com extração semântica de cláusulas e evidências
    dao_10 = offline_client.extract_structured_apolice(text_10, p10.name, "hash-sompo-10")
    dao_12 = offline_client.extract_structured_apolice(text_12, p12.name, "hash-sompo-12")

    assert dao_10.document_type == "condicoes_gerais"
    assert dao_12.document_type == "condicoes_gerais"
    assert dao_10.segurado is None
    assert dao_12.segurado is None

    # 3. Comparação analítica
    comp = compare_policies(dao_10, dao_12, llm_client=offline_client)

    # 4. Verificação de cláusulas reais
    # A) Inédita na v1.5 (Agravamento do Risco 18.6.1)
    assert any("Agravamento do Risco" in c for c in comp.clausulas_especiais_exclusivas_b)

    # B) Alterada (Inadimplemento do Prêmio 16.10: Tabela Prazo Curto x Notificação 15 dias)
    match_1610 = next((m for m in comp.semantic_matches if "Inadimplemento do Prêmio" in m.item_a), None)
    assert match_1610 is not None
    assert match_1610.relation in ("changed_scope", "different")
    assert match_1610.equivalence is False
    assert match_1610.page_a == 26
    assert match_1610.page_b == 28

    # C) Idênticas continuam equivalentes
    match_defesa = next((m for m in comp.semantic_matches if "Defesa e Acordos" in m.item_a), None)
    assert match_defesa is not None
    assert match_defesa.relation == "semantic_equivalent"
    assert match_defesa.equivalence is True
    assert match_defesa.page_a == 31
    assert match_defesa.page_b == 34

    match_gp = next((m for m in comp.semantic_matches if "Garantias Pessoais" in m.item_a), None)
    assert match_gp is not None
    assert match_gp.relation == "semantic_equivalent"
    assert match_gp.equivalence is True
    assert match_gp.page_a == 15
    assert match_gp.page_b == 16

    match_pol = next((m for m in comp.semantic_matches if "Poluição" in m.item_a), None)
    assert match_pol is not None
    assert match_pol.relation == "semantic_equivalent"
    assert match_pol.equivalence is True
    assert match_pol.page_a == 11
    assert match_pol.page_b == 12

    # Score auxiliar audita alterações
    assert comp.score_similaridade < 85.0
    assert comp.score_similaridade > 50.0


# =============================================================================
# 10. EXECUÇÃO REAL DO PAR CHUBB (DO005 x DO014) SEM SNIPPETS HARDCODED
# =============================================================================

@pytest.mark.skipif(not (DATASET_DIR / "DO_CHUBB_CONDICOES_GERAIS_OFERTA_PUBLICA_2024_005.pdf").exists(), reason="PDFs reais necessários")
def test_fase5_real_corpus_pipeline_chubb_do005_x_do014(offline_client):
    """Execução end-to-end do pipeline completo sobre o par real Chubb Oferta Pública 2024 x 2025."""
    p05 = DATASET_DIR / "DO_CHUBB_CONDICOES_GERAIS_OFERTA_PUBLICA_2024_005.pdf"
    p14 = DATASET_DIR / "DO_CHUBB_CONDICOES_GERAIS_OFERTA_PUBLICA_2025_014.pdf"

    # 1. Extração completa via pdfplumber
    text_05, pages_05 = extract_with_pdfplumber(p05)
    text_14, pages_14 = extract_with_pdfplumber(p14)
    assert pages_05 == 55
    assert pages_14 == 59

    # 2. Estruturação canônica com extração semântica de cláusulas e evidências
    dao_05 = offline_client.extract_structured_apolice(text_05, p05.name, "hash-chubb-05")
    dao_14 = offline_client.extract_structured_apolice(text_14, p14.name, "hash-chubb-14")

    assert dao_05.document_type == "condicoes_gerais"
    assert dao_14.document_type == "condicoes_gerais"

    # 3. Comparação analítica
    comp = compare_policies(dao_05, dao_14, llm_client=offline_client)

    # 4. Verificação de cláusulas reais
    # A) Inédita na versão 2025 (Despesas de Contenção e Salvamento)
    assert any("Despesas de Contenção e Salvamento" in c for c in comp.coberturas_exclusivas_b)

    # B) Alterada (Custos de Defesa: básica com adiantamento x adicional obrigatória paga)
    match_defesa = next((m for m in comp.semantic_matches if "Custos de Defesa" in m.item_a), None)
    assert match_defesa is not None
    assert match_defesa.relation in ("changed_scope", "different")
    assert match_defesa.equivalence is False
    assert match_defesa.page_a == 28
    assert match_defesa.page_b == 35

    # C) Equivalentes
    match_sidec = next((m for m in comp.semantic_matches if "Side C" in m.item_a), None)
    assert match_sidec is not None
    assert match_sidec.relation == "semantic_equivalent"
    assert match_sidec.equivalence is True
    assert match_sidec.page_a == 37
    assert match_sidec.page_b == 42

    match_multas = next((m for m in comp.semantic_matches if "Multas e Penalidades" in m.item_a), None)
    assert match_multas is not None
    assert match_multas.relation == "semantic_equivalent"
    assert match_multas.equivalence is True
    assert match_multas.page_a == 36
    assert match_multas.page_b == 41

    match_herd = next((m for m in comp.semantic_matches if "Herdeiros" in m.item_a), None)
    assert match_herd is not None
    assert match_herd.relation == "semantic_equivalent"
    assert match_herd.equivalence is True
    assert match_herd.page_a == 34
    assert match_herd.page_b == 39

    # Score auxiliar audita alterações
    assert comp.score_similaridade < 80.0
    assert comp.score_similaridade > 30.0


# =============================================================================
# 11. DETECÇÃO E TELEMETRIA DO CLIENTE GEMINI
# =============================================================================

def test_fase5_gemini_config_and_telemetry():
    """Valida detecção transparente da GOOGLE_API_KEY e registro de telemetria."""
    key = os.getenv("GOOGLE_API_KEY", "")
    client = GeminiClient()

    if not key:
        assert not client.is_available()
        # Fallback executado registra chamada nos logs de telemetria
        client.compare_clauses_semantically("Side A", "Side B")
        assert len(client.call_history) >= 1
        last = client.last_call_stats
        assert last["success"] is False
        assert last["extraction_method"] == "heuristic_fallback"
        assert "Gemini não configurado" in last["details"].get("reason", "")
    else:
        assert client.is_available()
