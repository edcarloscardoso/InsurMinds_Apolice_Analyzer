"""Testes de Integração UI/Backend da Fase 6 — Analisador D&O InsurMinds.
Valida os 12 requisitos da interface:
1. Suporte a dois documentos PDF
2. Acompanhamento de progresso e estado do pipeline
3. Extração dos 8 metadados obrigatórios por documento (nome, tipo, seguradora, SUSEP, 4 contagens)
4. Visão estruturada da análise
5. Execução do confronto A x B
6. Classificação das 7 relações semânticas canônicas
7. Priorização de diferenças substantivas sobre estruturais
8. Presença dos 8 pontos obrigatórios por diferença (item A/B, pág A/B, relação, equivalência, confiança, explicação)
9. Expansão de evidências contratuais com trecho e método
10. Presença do aviso legal obrigatório contra desvio regulatório
11. Tratamento visível de contingência/fallback sem falhas não tratadas
12. Natureza auxiliar do score de similaridade estrutural
"""
from pathlib import Path
import pytest

from core.config import DATASET_DO_DIR
from core.database import db
from core.schemas import ApoliceDAO, ComparisonResult, SemanticMatchItem, EvidenceItem
from core.diff_engine import compare_policies, compare_clauses_semantically
from core.llm_client import GeminiClient, llm_client
from agents.graph import run_document_pipeline_with_progress
from ui.page_compare import SEMANTIC_RELATION_CONFIG

DOC_DO010 = DATASET_DO_DIR / "DO_SOMPO_CONDICOES_GERAIS_V1_2_2024_010.pdf"
DOC_DO012 = DATASET_DO_DIR / "DO_SOMPO_CONDICOES_GERAIS_V1_5_2025_012.pdf"
DOC_DO005 = DATASET_DO_DIR / "DO_CHUBB_CONDICOES_GERAIS_OFERTA_PUBLICA_2024_005.pdf"
DOC_DO014 = DATASET_DO_DIR / "DO_CHUBB_CONDICOES_GERAIS_OFERTA_PUBLICA_2025_014.pdf"

MANDATORY_DISCLAIMER = "A análise é assistida por IA e não substitui a avaliação jurídica, técnica ou de subscrição."


def test_fase6_legal_disclaimer_present_in_ui_pages():
    """Requisito 10: Garante presença do aviso legal obrigatório em todas as páginas analíticas da UI."""
    upload_code = Path("ui/page_upload.py").read_text(encoding="utf-8")
    compare_code = Path("ui/page_compare.py").read_text(encoding="utf-8")
    report_code = Path("ui/page_report.py").read_text(encoding="utf-8")
    library_code = Path("ui/page_library.py").read_text(encoding="utf-8")

    assert MANDATORY_DISCLAIMER in upload_code
    assert MANDATORY_DISCLAIMER in compare_code
    assert MANDATORY_DISCLAIMER in report_code
    assert MANDATORY_DISCLAIMER in library_code


def test_fase6_semantic_relation_config_covers_all_seven_types():
    """Requisito 6: Garante que as 7 relações semânticas estão formalmente mapeadas no frontend."""
    expected_relations = {
        "semantic_equivalent",
        "different",
        "broader",
        "narrower",
        "changed_scope",
        "changed_condition",
        "changed_limit"
    }
    assert set(SEMANTIC_RELATION_CONFIG.keys()) == expected_relations
    for rel, cfg in SEMANTIC_RELATION_CONFIG.items():
        assert "label" in cfg
        assert "badge_class" in cfg
        assert "icon" in cfg
        assert "desc" in cfg


def test_fase6_dual_document_pipeline_and_eight_metadata_fields():
    """Requisitos 1, 2, 3 e 4: Processa dois PDFs reais e valida os 8 metadados obrigatórios."""
    if not (DOC_DO010.exists() and DOC_DO012.exists()):
        pytest.skip("Documentos Sompo não encontrados.")

    steps_recorded = []

    def on_step(num: int, agent_name: str, desc: str):
        steps_recorded.append((num, agent_name, desc))

    # Executa ingestão com telemetria
    state_a = run_document_pipeline_with_progress(
        str(DOC_DO010), DOC_DO010.name, on_step_callback=on_step, force_reprocess=False
    )
    state_b = run_document_pipeline_with_progress(
        str(DOC_DO012), DOC_DO012.name, on_step_callback=on_step, force_reprocess=False
    )

    assert state_a.structured_data is not None
    assert state_b.structured_data is not None

    dao_a = state_a.structured_data
    dao_b = state_b.structured_data

    # Validação dos 8 metadados obrigatórios para Documento A
    assert dao_a.nome_arquivo == DOC_DO010.name
    assert dao_a.document_type == "condicoes_gerais"
    assert "Sompo" in dao_a.seguradora
    assert "15414.652408" in (dao_a.processo_susep or "")
    assert len(dao_a.coberturas) > 0
    assert len(dao_a.exclusoes) > 0
    assert len(dao_a.clausulas_especiais) > 0
    assert len(dao_a.evidencias) > 0

    # Validação dos 8 metadados obrigatórios para Documento B
    assert dao_b.nome_arquivo == DOC_DO012.name
    assert dao_b.document_type == "condicoes_gerais"
    assert "Sompo" in dao_b.seguradora
    assert "15414.652408" in (dao_b.processo_susep or "")
    assert len(dao_b.coberturas) > 0
    assert len(dao_b.exclusoes) > 0
    assert len(dao_b.clausulas_especiais) > 0
    assert len(dao_b.evidencias) > 0


def test_fase6_substantive_differences_prioritization_and_eight_points():
    """Requisitos 5, 7, 8 e 9: Executa confronto A x B e valida a priorização substantiva e os 8 pontos por diferença."""
    if not (DOC_DO010.exists() and DOC_DO012.exists()):
        pytest.skip("Documentos Sompo não encontrados.")

    state_a = run_document_pipeline_with_progress(str(DOC_DO010), DOC_DO010.name, force_reprocess=False)
    state_b = run_document_pipeline_with_progress(str(DOC_DO012), DOC_DO012.name, force_reprocess=False)

    dao_a = state_a.structured_data
    dao_b = state_b.structured_data

    # Executa comparação
    comp_result = compare_policies(dao_a, dao_b, llm_client=None)
    assert comp_result is not None

    # Substantivas devem ser segregáveis
    substantive_matches = [
        m for m in comp_result.semantic_matches
        if m.relation in ("changed_scope", "changed_condition", "changed_limit", "different")
    ]
    # Inadimplemento do Prêmio (16.10) é substantivamente alterada entre v1.2 e v1.5
    assert len(substantive_matches) >= 1 or len(comp_result.clausulas_especiais_exclusivas_b) >= 1

    # Validação dos 8 pontos obrigatórios em cada diferença encontrada
    for m in comp_result.semantic_matches:
        assert m.item_a != ""
        assert m.item_b != ""
        assert isinstance(m.equivalence, bool)
        assert m.relation in SEMANTIC_RELATION_CONFIG
        assert 0.0 <= m.confidence <= 1.0
        assert m.explanation != ""
        # Páginas válidas
        if m.page_a is not None:
            assert m.page_a >= 1
        if m.page_b is not None:
            assert m.page_b >= 1
        # Evidências textuais presentes para expansão
        assert m.evidence_a is not None
        assert m.evidence_b is not None


def test_fase6_chubb_substantive_differences_and_evidence_expansion():
    """Valida confronto no par Chubb DO005 x DO014 com expansão de evidências e cláusulas exclusivas."""
    if not (DOC_DO005.exists() and DOC_DO014.exists()):
        pytest.skip("Documentos Chubb não encontrados.")

    state_05 = run_document_pipeline_with_progress(str(DOC_DO005), DOC_DO005.name, force_reprocess=False)
    state_14 = run_document_pipeline_with_progress(str(DOC_DO014), DOC_DO014.name, force_reprocess=False)

    dao_05 = state_05.structured_data
    dao_14 = state_14.structured_data

    assert dao_05.seguradora == "Chubb Seguros Brasil S.A."
    assert dao_14.seguradora == "Chubb Seguros Brasil S.A."

    comp_result = compare_policies(dao_05, dao_14, llm_client=None)

    # Despesas de Contenção e Salvamento introduzida em 2025
    assert any("salvamento" in c.lower() or "contencao" in c.lower() for c in comp_result.coberturas_exclusivas_b)

    # Custos de Defesa detectado com alteração substantiva (changed_scope)
    defense_match = next((m for m in comp_result.semantic_matches if "defesa" in m.item_a.lower()), None)
    if defense_match:
        assert defense_match.equivalence is False
        assert defense_match.relation in ("changed_scope", "different", "changed_condition")
        assert defense_match.evidence_a is not None
        assert defense_match.evidence_b is not None


def test_fase6_similarity_score_auxiliary_nature():
    """Requisito 12: Garante que o score é puramente auxiliar e documentado como tal nos metadados."""
    if not (DOC_DO010.exists() and DOC_DO012.exists()):
        pytest.skip("Documentos Sompo não encontrados.")

    state_a = run_document_pipeline_with_progress(str(DOC_DO010), DOC_DO010.name, force_reprocess=False)
    state_b = run_document_pipeline_with_progress(str(DOC_DO012), DOC_DO012.name, force_reprocess=False)

    comp = compare_policies(state_a.structured_data, state_b.structured_data, llm_client=None)

    assert 0.0 <= comp.score_similaridade <= 100.0
    assert comp.metadata.get("score_nature") == "similaridade_tecnica_estrutural_auxiliar"
    assert "caráter estritamente técnico e auxiliar" in comp.summary


def test_fase6_offline_resilience_and_graceful_error_handling():
    """Requisito 11: Simula cliente Gemini offline e valida que o pipeline conclui via fallback sem falhas."""
    offline_client = GeminiClient(api_key="")
    assert offline_client.is_available() is False

    res = compare_clauses_semantically(
        "Custos de Defesa: adiantamento de despesas",
        "Custos de Defesa: reembolso mediante consentimento prévio",
        llm_client=offline_client
    )
    assert res is not None
    assert res.relation in ("changed_condition", "changed_scope")
    assert res.equivalence is False
