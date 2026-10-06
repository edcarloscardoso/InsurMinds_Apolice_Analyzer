"""Testes para o Gate de Qualidade Profunda do Comparador D&O — Fase 4.2.

Validação exaustiva e determinística:
1. Casos Sintéticos A a G de Mudança Substantiva.
2. Não equiparação de cláusulas com mesmo nome mas redação/escopo/limite alterados.
3. Não inflação do Score Técnico diante de mudanças substantivas (Score != 100%).
4. Segregação documental (Condições Gerais vs Apólice Individual).
5. Prevenção de segurado fictício extraído de glossários/definições.
6. Validação do schema SemanticMatchItem com evidências A/B.
"""
import pytest
from core.schemas import ApoliceDAO, EvidenceItem, FieldDiff, ComparisonResult, SemanticMatchItem
from core.llm_client import GeminiClient
from core.domain_detector import detect_document_type
from core.diff_engine import (
    compare_clauses_semantically,
    compare_policies,
    calculate_similarity_score
)


@pytest.fixture
def offline_client():
    return GeminiClient(api_key="")


# =============================================================================
# ETAPA 1 — CASOS SINTÉTICOS DE MUDANÇA SUBSTANTIVA
# =============================================================================

def test_caso_a_mesmo_titulo_mesmo_conteudo():
    """CASO A — MESMO TÍTULO, MESMO CONTEÚDO -> semantic_equivalent."""
    clause_a = "Custos de Defesa: Garante o adiantamento de honorários periciais e advocatícios incorridos na defesa dos administradores segurados."
    clause_b = "Custos de Defesa: Garante o adiantamento de honorários periciais e advocatícios incorridos na defesa dos administradores segurados."

    match = compare_clauses_semantically(clause_a, clause_b)
    assert match is not None
    assert match.relation == "semantic_equivalent"
    assert match.equivalence is True
    assert match.confidence >= 0.90
    assert match.evidence_a == clause_a
    assert match.evidence_b == clause_b


def test_caso_b_mesmo_titulo_escopo_alterado():
    """CASO B — MESMO TÍTULO, ESCOPO ALTERADO -> não tratar como equivalente sem considerar a restrição."""
    clause_a = "Custos de Defesa: Cobre honorários e despesas de defesa para quaisquer reclamações fundadas em atos de gestão dos administradores."
    clause_b = "Custos de Defesa: Cobre honorários e despesas de defesa para quaisquer reclamações fundadas em atos de gestão dos administradores, exceto atos de negligência e compliance."

    match = compare_clauses_semantically(clause_a, clause_b)
    assert match is not None
    assert match.relation == "changed_scope"
    assert match.equivalence is False
    assert "escopo" in match.explanation.lower() or "ressalvas" in match.explanation.lower()


def test_caso_c_mesmo_nome_limite_diferente():
    """CASO C — MESMO NOME, LIMITE DIFERENTE -> changed_limit, nunca semantic_equivalent puro."""
    clause_a = "Despesas de Publicidade: Sub-limite de indenização de até R$ 500.000,00 para contenção de imagem."
    clause_b = "Despesas de Publicidade: Sub-limite de indenização de até R$ 2.000.000,00 para contenção de imagem."

    match = compare_clauses_semantically(clause_a, clause_b)
    assert match is not None
    assert match.relation == "changed_limit"
    assert match.equivalence is False
    assert "limites" in match.explanation.lower() or "sub-limite" in match.explanation.lower()


def test_caso_d_mais_amplo_vs_mais_restrito():
    """CASO D — MAIS AMPLO VS MAIS RESTRITO -> broader/narrower."""
    clause_a = "Penhora de Bens: Cobertura ampla para qualquer indisponibilidade e apreensão de bens dos administradores segurados."
    clause_b = "Penhora de Bens: Cobertura restrita exclusivamente a bloqueio eletrônico de contas online bacenjud."

    match_ab = compare_clauses_semantically(clause_a, clause_b)
    assert match_ab is not None
    assert match_ab.relation == "broader"
    assert match_ab.equivalence is True

    match_ba = compare_clauses_semantically(clause_b, clause_a)
    assert match_ba is not None
    assert match_ba.relation == "narrower"
    assert match_ba.equivalence is True


def test_caso_e_exclusao_com_mesmo_titulo_texto_alterado():
    """CASO E — EXCLUSÃO COM MESMO TÍTULO, TEXTO ALTERADO -> diferença substantiva detectada."""
    exc_a = "Atos Dolosos: Exclusão aplicável a atos desonestos ou dolosos reconhecidos por decisão judicial final irrecorrível."
    exc_b = "Atos Dolosos: Exclusão aplicável a indícios preliminares apurados em auditoria interna ou inquérito policial."

    match = compare_clauses_semantically(exc_a, exc_b)
    assert match is not None
    assert match.relation in ("changed_scope", "different")
    assert match.equivalence is False


def test_caso_f_texto_diferente_mas_equivalente():
    """CASO F — TEXTO DIFERENTE, MAS EQUIVALENTE -> semantic_equivalent somente com evidência objetiva."""
    clause_a = "Cobertura Side A: Garante proteção financeira para administradores quando a empresa estiver impedida de indenizar."
    clause_b = "Cobertura Side A: Garante indenização direta aos diretores quando a sociedade não indenizar seus gestores."

    match = compare_clauses_semantically(clause_a, clause_b)
    assert match is not None
    assert match.relation == "semantic_equivalent"
    assert match.equivalence is True
    assert match.confidence >= 0.85


def test_caso_g_mesmo_titulo_condicao_alterada():
    """CASO G — MESMO TÍTULO, CONDIÇÃO ALTERADA -> changed_condition."""
    clause_a = "Adiantamento de Custos de Defesa: Liberação direta de valores mediante apresentação de nota de honorários."
    clause_b = "Adiantamento de Custos de Defesa: Liberação condicionada a prévia aprovação e consentimento por escrito da seguradora."

    match = compare_clauses_semantically(clause_a, clause_b)
    assert match is not None
    assert match.relation == "changed_condition"
    assert match.equivalence is False
    assert "condições" in match.explanation.lower() or "exigências" in match.explanation.lower()


# =============================================================================
# ETAPA 5 — AUDITORIA DO SCORE TÉCNICO DIANTE DE MUDANÇA SUBSTANTIVA
# =============================================================================

def test_score_mesmo_numero_de_itens_mas_mudanca_substantiva_nao_e_100():
    """Mesmo número de itens + mudança substantiva em conteúdo != 100% de similaridade."""
    # Apólice A e B possuem as mesmas 3 coberturas nominais, mas com escopo, limite e condição divergentes
    dao_a = ApoliceDAO(
        id="apolice-a",
        nome_arquivo="apolice_a.pdf",
        data_processamento="2026-09-28T12:00:00",
        seguradora="Chubb Seguros Brasil S.A.",
        document_type="apolice_individual",
        coberturas=[
            "Custos de Defesa: Cobre quaisquer reclamações cíveis e administrativas de gestão.",
            "Despesas de Publicidade: Sub-limite de até R$ 500.000,00.",
            "Adiantamento de Custos: Liberação direta ao segurado."
        ],
        exclusoes=[
            "Atos Dolosos: Exclusão somente após trânsito em julgado."
        ]
    )

    dao_b = ApoliceDAO(
        id="apolice-b",
        nome_arquivo="apolice_b.pdf",
        data_processamento="2026-09-28T12:00:00",
        seguradora="Chubb Seguros Brasil S.A.",
        document_type="apolice_individual",
        coberturas=[
            "Custos de Defesa: Cobre reclamações, exceto investigações de compliance e negligência.",
            "Despesas de Publicidade: Sub-limite de até R$ 2.000.000,00.",
            "Adiantamento de Custos: Condicionado a prévia aprovação da seguradora."
        ],
        exclusoes=[
            "Atos Dolosos: Exclusão com base em inquérito preliminar sem trânsito em julgado."
        ]
    )

    res = compare_policies(dao_a, dao_b)

    # Nenhuma das coberturas ou exclusões é substantivamente equivalente
    assert len(res.semantic_matches) >= 3
    for sm in res.semantic_matches:
        assert sm.relation in ("changed_scope", "changed_limit", "changed_condition", "different")
        assert sm.equivalence is False

    # O score técnico/estrutural NÃO deve ser 100%, pois as cláusulas foram penalizadas por mudança substantiva
    assert res.score_similaridade < 85.0
    assert res.score_similaridade > 0.0


# =============================================================================
# ETAPA 6 & 7 — SEGURADO EM CONDIÇÕES GERAIS E TIPO DOCUMENTAL
# =============================================================================

def test_condicoes_gerais_sem_tomador_nao_cria_segurado_ficticio(offline_client):
    """Condições Gerais puras com definições e glossário NÃO fabricam segurado individual."""
    raw_text = """
    SOMPO SEGUROS S.A.
    PROCESSO SUSEP 15414.652408/2023-71
    CONDIÇÕES GERAIS - SEGURO D&O
    DEFINIÇÕES:
    1. Segurado: toda pessoa física que seja ou venha a ser membro estatutário, administrador, diretor
    ou membro do conselho de administração da Sociedade Tomadora.
    2. Sociedade Segurada: a sociedade estipulante identificada na Especificação da Apólice, bem como suas subsidiárias.
    3. Apólice: instrumento jurídico contratual.
    """
    dao = offline_client.extract_structured_apolice(
        raw_text=raw_text,
        nome_arquivo="DO_SOMPO_CG_V1_2.pdf",
        file_hash="hash-cg-def-test"
    )

    assert dao.document_type == "condicoes_gerais"
    assert dao.segurado is None
    assert "segurado" not in dao.evidencias
    assert dao.numero_apolice is None
    assert dao.tipo_movimento is None


def test_apolice_individual_com_front_sheet_mantem_segurado_e_tipo(offline_client):
    """Apólice com Front Sheet / Tomador nominal é devidamente classificada como apolice_individual."""
    raw_text = """
    EZZE Seguros S.A.
    QUADRO DEMONSTRATIVO / ESPECIFICAÇÃO DA APÓLICE
    Apólice nº: 01.0775.000888/00
    Tomador: Construtora Metropolitana de Infraestrutura S.A.
    Vigência: 01/03/2026 a 01/03/2027
    LMG: R$ 50.000.000,00
    Franquia: R$ 250.000,00
    Prêmio Total: R$ 320.000,00
    Tipo de Movimento: 101 - Emissão de Apólice Inicial
    """
    dao = offline_client.extract_structured_apolice(
        raw_text=raw_text,
        nome_arquivo="apolice_individual_ezze.pdf",
        file_hash="hash-indiv-test"
    )

    assert dao.document_type == "apolice_individual"
    assert dao.segurado == "Construtora Metropolitana de Infraestrutura S.A."
    assert dao.numero_apolice == "01.0775.000888/00"
    assert dao.limite_responsabilidade == "R$ 50.000.000,00"
    assert dao.premio_total == "R$ 320.000,00"
    assert dao.tipo_movimento == "101"


def test_detect_document_type_varieties():
    """Valida a enumeração estrita de tipos contratuais de documento."""
    assert detect_document_type("Endosso de Alteração nº 05", "endosso_05.pdf") == "endosso"
    assert detect_document_type("Condições Gerais de Responsabilidade Civil D&O", "SOMPO_CG_D&O.pdf") == "condicoes_gerais"
    assert detect_document_type("Proposta de Seguro D&O assinada", "proposta_seguro.pdf") == "proposta"
    assert detect_document_type("Apólice de Seguro nº 123.456", "apolice_123.pdf") == "apolice_individual"
    assert detect_document_type("Texto genérico qualquer sem marcadores", "documento.pdf") == "unknown"


# =============================================================================
# FASE 4.2B — GATE DE VALIDAÇÃO DE PARES REAIS DO CORPUS
# =============================================================================

def test_real_corpus_pairs_gate_4_2b():
    """Valida determinística e objetivamente as cláusulas reais dos pares Sompo e Chubb."""
    # SOMPO DO010 x DO012
    # 1. Defesa e Acordos (idêntica)
    sompo_defesa_a = "Defesa e Acordos: 19.3.1. Cada Segurado poderá escolher livremente seus respectivos advogados e deverá contestar e se defender em qualquer Reclamação apresentada contra eles. A Seguradora terá o direito de participar ativamente em tal defesa."
    sompo_defesa_b = "Defesa e Acordos: 19.3.1. Cada Segurado poderá escolher livremente seus respectivos advogados e deverá contestar e se defender em qualquer Reclamação apresentada contra eles. A Seguradora terá o direito de participar ativamente em tal defesa."
    m_def = compare_clauses_semantically(sompo_defesa_a, sompo_defesa_b)
    assert m_def.relation == "semantic_equivalent"
    assert m_def.equivalence is True
    assert m_def.confidence == 1.0

    # 2. Garantias Pessoais (idêntica)
    sompo_gp_a = "Garantias Pessoais (Aval e Fiança): Reclamação em que o Segurado figure na qualidade de avalista, fiador, fiel depositário ou garantidor da Sociedade, estarão cobertos os Custos de Defesa relacionados a Reclamações contra o Segurado."
    sompo_gp_b = "Garantias Pessoais (Aval e Fiança): Reclamação em que o Segurado figure na qualidade de avalista, fiador, fiel depositário ou garantidor da Sociedade, estarão cobertos os Custos de Defesa relacionados a Reclamações contra o Segurado."
    m_gp = compare_clauses_semantically(sompo_gp_a, sompo_gp_b)
    assert m_gp.relation == "semantic_equivalent"
    assert m_gp.equivalence is True

    # 3. Poluição (idêntica)
    sompo_pol_a = "Poluição: Descarga, dispensa, liberação ou vazamento de Poluentes no meio ambiente."
    sompo_pol_b = "Poluição: Descarga, dispensa, liberação ou vazamento de Poluentes no meio ambiente."
    m_pol = compare_clauses_semantically(sompo_pol_a, sompo_pol_b)
    assert m_pol.relation == "semantic_equivalent"
    assert m_pol.equivalence is True

    # 4. Agravamento do Risco (inédita na v1.5 / ausente na v1.2)
    sompo_agrav_a = "Agravamento do Risco: Cláusula inexistente / não prevista nas Condições Gerais versão 1.2."
    sompo_agrav_b = "Agravamento do Risco: 18.6.1. Na hipótese em que a omissão quanto ao agravamento do risco resultar de conduta dolosa do Segurado ou Tomador, a Seguradora poderá cancelar o seguro, recaindo sobre estes a perda do direito à indenização."
    m_agrav = compare_clauses_semantically(sompo_agrav_a, sompo_agrav_b)
    assert m_agrav.relation in ("changed_scope", "different")
    assert m_agrav.equivalence is False

    # 5. Inadimplemento e Tabela de Prazo Curto (16.10 alterada)
    sompo_1610_a = "Inadimplemento do Prêmio: O prazo de Vigência da cobertura do seguro será ajustado em função do Prêmio efetivamente pago, tomando-se por base a Tabela de Prazo Curto."
    sompo_1610_b = "Inadimplemento do Prêmio: A Seguradora notificará o Segurado da inadimplência. Não sendo feito o pagamento no prazo de 15 dias, operará a suspensão da cobertura ou cancelamento."
    m_1610 = compare_clauses_semantically(sompo_1610_a, sompo_1610_b)
    assert m_1610.relation in ("changed_scope", "different")
    assert m_1610.equivalence is False

    # CHUBB DO005 x DO014
    # 6. Custos de Defesa (alterada: de cláusula básica 30 para Cobertura Adicional obrigatória)
    chubb_def_a = "Custos de Defesa: 30.1. Desde que não se vislumbre uma hipótese de não incidência da cobertura securitária, o pagamento dos Custos de Defesa será feito mediante adiantamento direto das despesas incorridas."
    chubb_def_b = "Custos de Defesa: Cobertura Adicional de Custos de Defesa. É obrigatória a contratação da cobertura adicional específica. O valor do pagamento total com os custos de defesa será efetuado somente após o trânsito em julgado, exceto despesas preliminares."
    m_chubb_def = compare_clauses_semantically(chubb_def_a, chubb_def_b)
    assert m_chubb_def.relation in ("changed_scope", "different")
    assert m_chubb_def.equivalence is False

    # 7. Despesas de Contenção e Salvamento (inédita na versão 2025)
    chubb_salv_a = "Despesas de Contenção e Salvamento: Cláusula inexistente / não prevista nas Condições Gerais de 2024."
    chubb_salv_b = "Despesas de Contenção e Salvamento: Cobertura Adicional de Despesas de Contenção e Salvamento de Sinistro. Pago prêmio adicional, o seguro abrangerá até o LMI o pagamento das quantias despendidas com medidas imediatas de contenção e salvamento."
    m_salv = compare_clauses_semantically(chubb_salv_a, chubb_salv_b)
    assert m_salv.relation in ("changed_scope", "different")
    assert m_salv.equivalence is False

    # 8. Herdeiros e Espólio (equivalente)
    chubb_herd_a = "Herdeiros e Representantes Legais: Caso algum Segurado venha a falecer ou tornar-se incapaz civilmente, esta Apólice cobrirá as Perdas Indenizáveis decorrentes de qualquer Reclamação contra seus herdeiros, representantes legais ou espólio."
    chubb_herd_b = "Herdeiros e Representantes Legais: Caso algum Segurado venha a falecer ou tornar-se incapaz civilmente, esta Apólice cobrirá as Perdas Indenizáveis decorrentes de qualquer Reclamação contra seus herdeiros, representantes legais ou espólio."
    m_herd = compare_clauses_semantically(chubb_herd_a, chubb_herd_b)
    assert m_herd.relation == "semantic_equivalent"
    assert m_herd.equivalence is True

    # 9. Side C (equivalente)
    chubb_sidec_a = "Cobertura Side C: Respeitadas as demais condições, a cobertura garante o pagamento de Perdas decorrentes de Reclamações contra o Tomador por atos de gestão de valores mobiliários."
    chubb_sidec_b = "Cobertura Side C: Respeitadas as demais condições, a cobertura garante o pagamento de Perdas decorrentes de Reclamações contra o Tomador por atos de gestão de valores mobiliários."
    m_sidec = compare_clauses_semantically(chubb_sidec_a, chubb_sidec_b)
    assert m_sidec.relation == "semantic_equivalent"
    assert m_sidec.equivalence is True

    # 10. Multas e Penalidades (equivalente)
    chubb_multas_a = "Multas e Penalidades: Mediante contratação específica, cobre multas civis e administrativas aplicadas a qualquer Segurado pessoa física por órgãos reguladores."
    chubb_multas_b = "Multas e Penalidades: Mediante contratação específica, cobre multas civis e administrativas aplicadas a qualquer Segurado pessoa física por órgãos reguladores."
    m_multas = compare_clauses_semantically(chubb_multas_a, chubb_multas_b)
    assert m_multas.relation == "semantic_equivalent"
    assert m_multas.equivalence is True
