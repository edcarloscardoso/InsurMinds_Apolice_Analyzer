"""Testes para o Gate de Qualidade Semântica da Fase 4.1.
Validação estrita dos problemas auditados A até I:
- Tipo de movimento sem default 101 em Condições Gerais.
- Validade de comercialização de Condições Gerais não é vigência individual de apólice.
- Ausência não é igualdade substantiva (score não infla indevidamente).
- Score possui papel técnico/estrutural auxiliar.
- Equivalência semântica restrita com distinções lexicais de D&O.
- Evidências A/B e conflitos devidamente propagados.
"""
import pytest
from core.schemas import ApoliceDAO, EvidenceItem, FieldDiff, ComparisonResult, SemanticMatchItem
from core.llm_client import GeminiClient
from core.diff_engine import (
    compare_policies,
    compare_scalar_field,
    compare_clauses_semantically,
    calculate_similarity_score
)


@pytest.fixture
def offline_client():
    return GeminiClient(api_key="")


# =============================================================================
# 1. Condições Gerais sem movimento explícito não recebem 101
# =============================================================================
def test_condicoes_gerais_sem_movimento_explicit_receives_none(offline_client):
    raw_text = """
    SOMPO SEGURO DE RESPONSABILIDADE CIVIL D&O
    PROCESSO SUSEP 15414.652408/2023-71
    CONDIÇÕES GERAIS
    Cláusula 1ª - Objetivo do Seguro: Garantir a indenização dos administradores.
    Cláusula 7ª - Aceitação da proposta de seguro pela companhia seguradora.
    """
    dao = offline_client.extract_structured_apolice(
        raw_text=raw_text,
        nome_arquivo="DO_SOMPO_CONDICOES_GERAIS_V1_2_2024_010.pdf",
        file_hash="hash-cg-test"
    )

    assert dao.tipo_movimento is None
    assert dao.tipo_movimento_descricao is None
    assert "tipo_movimento" not in dao.evidencias


# =============================================================================
# 2. Data de aplicabilidade de Condições Gerais não vira vigência individual
# =============================================================================
def test_condicoes_gerais_applicability_date_does_not_become_policy_vigencia(offline_client):
    raw_text = """
    SOMPO SEGUROS S.A.
    Versão 1.2 - Versão: fevereiro/2024
    Válida para os seguros comercializados a partir de 21/02/2024 até 14/03/2024.
    PROCESSO SUSEP 15414.652408/2023-71
    Condições Gerais aplicáveis aos contratos celebrados no território nacional.
    """
    dao = offline_client.extract_structured_apolice(
        raw_text=raw_text,
        nome_arquivo="DO_SOMPO_CG_V1_2.pdf",
        file_hash="hash-sompo-vig-test"
    )

    assert dao.vigencia_inicio is None
    assert dao.vigencia_fim is None
    assert "vigencia_inicio" not in dao.evidencias
    assert "vigencia_fim" not in dao.evidencias


# =============================================================================
# 3. Ausência não é igualdade substantiva: score não infla indevidamente
# =============================================================================
def test_ausencia_nao_infla_score_de_similaridade():
    # Duas apólices onde apenas a seguradora é informada e igual; todos os outros 13 campos são ambos_ausentes
    dao_a = ApoliceDAO(
        id="pol_a",
        nome_arquivo="cg_a.pdf",
        data_processamento="2026-09-28T18:00:00",
        seguradora="Chubb Seguros Brasil S.A.",
        coberturas=[],
        exclusoes=[]
    )
    dao_b = ApoliceDAO(
        id="pol_b",
        nome_arquivo="cg_b.pdf",
        data_processamento="2026-09-28T18:00:00",
        seguradora="Chubb Seguros Brasil S.A.",
        coberturas=[],
        exclusoes=[]
    )

    comp = compare_policies(dao_a, dao_b)

    # Apenas seguradora é substantive igual (1 de 14 campos escalares)
    # 13 campos são ambos_ausentes
    # O score DEVE ser baixo (apenas 1/14 * 40 ≈ 2.9%), e NUNCA 100% ou inflacionado
    assert comp.score_similaridade < 10.0
    diff_lmg = next(d for d in comp.diffs if d.campo == "limite_responsabilidade")
    assert diff_lmg.tipo_diferenca == "ambos_ausentes"
    assert diff_lmg.ha_diferenca is False


# =============================================================================
# 4. Score não substitui FieldDiff e é documentado como auxiliar
# =============================================================================
def test_score_nao_substitui_field_diff():
    dao_a = ApoliceDAO(
        id="a1", nome_arquivo="a1.pdf", data_processamento="2026-09-28T18:00:00",
        seguradora="Sompo", limite_responsabilidade="R$ 10.000.000,00"
    )
    dao_b = ApoliceDAO(
        id="b1", nome_arquivo="b1.pdf", data_processamento="2026-09-28T18:00:00",
        seguradora="Sompo", limite_responsabilidade="R$ 50.000.000,00"
    )

    comp = compare_policies(dao_a, dao_b)

    assert "similaridade estrutural" in comp.summary.lower()
    assert comp.metadata.get("score_nature") == "similaridade_tecnica_estrutural_auxiliar"
    assert "fielddiffs" in comp.metadata.get("note", "").lower()
    # FieldDiff continua sendo a fonte primária e factual da divergência
    diff_lmg = next(d for d in comp.diffs if d.campo == "limite_responsabilidade")
    assert diff_lmg.ha_diferenca is True
    assert diff_lmg.tipo_diferenca == "diferente"
    assert "R$ 10.000.000,00" in diff_lmg.explicacao
    assert "R$ 50.000.000,00" in diff_lmg.explicacao


# =============================================================================
# 5. Equivalência semântica restrita: prevenção de falsos positivos
# =============================================================================
def test_equivalencia_semantica_distincoes_estritas():
    # A) Danos Morais vs Danos Corporais e Materiais (semelhança lexical de "danos" mas diferentes juridicamente)
    match_danos = compare_clauses_semantically(
        "Exclusão de Danos Corporais e Danos Materiais diretos",
        "Exclusão de Danos Morais e Prejuízos à Honra"
    )
    assert match_danos is not None
    assert match_danos.equivalence is False
    assert match_danos.relation == "different"

    # B) Penhora Genérica vs Penhora Online Bacenjud (relação de escopo amplo vs restrito)
    match_penhora = compare_clauses_semantically(
        "Penhora Online via BACENJUD / Sisbajud",
        "Penhora de Bens Móveis, Imóveis e Ativos Financeiros"
    )
    assert match_penhora is not None
    assert match_penhora.equivalence is True
    assert match_penhora.relation == "narrower"

    # C) Side A pura vs Side A DIC (Difference in Conditions não é Side A pura)
    match_dic = compare_clauses_semantically(
        "Cobertura Side A para Administradores",
        "Cobertura Side A DIC (Difference in Conditions)"
    )
    assert match_dic is not None
    assert match_dic.equivalence is False
    assert match_dic.relation == "different"


# =============================================================================
# 6. Evidência A/B preservada em assimetrias e convergências
# =============================================================================
def test_evidencia_ab_preservada_com_snippet_e_metodo():
    ev_a = EvidenceItem(page=3, snippet="LMG contratado: R$ 20.000.000,00", method="pdfplumber", confidence=0.95)
    ev_b = EvidenceItem(page=7, snippet="LMG da apólice: R$ 40.000.000,00", method="pdfplumber", confidence=0.92)

    diff = compare_scalar_field(
        "limite_responsabilidade", "Limite Máximo de Garantia",
        "R$ 20.000.000,00", "R$ 40.000.000,00",
        is_financial=True,
        evidence_a=ev_a,
        evidence_b=ev_b
    )

    assert diff.ha_diferenca is True
    assert diff.evidence_a == ev_a
    assert diff.evidence_a.page == 3
    assert diff.evidence_a.snippet == "LMG contratado: R$ 20.000.000,00"
    assert diff.evidence_a.method == "pdfplumber"
    assert diff.evidence_b == ev_b
    assert diff.evidence_b.page == 7
    assert diff.evidence_b.snippet == "LMG da apólice: R$ 40.000.000,00"


# =============================================================================
# 7. Conflitos internos continuam explícitos
# =============================================================================
def test_conflitos_internos_explicitamente_marcados():
    diff_a = compare_scalar_field(
        "franquia", "Franquia", "R$ 50.000,00", "R$ 50.000,00",
        conflito_a=True, conflito_b=False
    )
    assert diff_a.tipo_diferenca == "conflito_A"
    assert diff_a.ha_diferenca is True

    diff_ab = compare_scalar_field(
        "franquia", "Franquia", "R$ 50.000,00", "R$ 50.000,00",
        conflito_a=True, conflito_b=True
    )
    assert diff_ab.tipo_diferenca == "conflito_A_e_B"
    assert diff_ab.ha_diferenca is True
