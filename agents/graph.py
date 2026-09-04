"""Orquestração de Grafos de Agentes via LangGraph.
Define o StateGraph para o pipeline de Ingestão de Documentos e o pipeline de Comparação & Parecer.
"""
from typing import Callable, Optional
from langgraph.graph import StateGraph, END, START
from core.schemas import DocumentState, ComparisonState, ApoliceDAO
from agents.reception_agent import reception_agent
from agents.extractor_agent import extractor_agent
from agents.identifier_agent import identifier_agent
from agents.structurer_agent import structurer_agent
from agents.comparator_agent import comparator_agent
from agents.reporter_agent import reporter_agent


def _check_cache_or_error(state: DocumentState) -> str:
    """Roteamento condicional no grafo de documentos."""
    if state.status == "erro":
        return END
    if state.status == "concluido_em_cache":
        return END
    return "extractor"


def build_document_graph() -> StateGraph:
    """Constrói o Grafo LangGraph para Ingestão e Estruturação de Apólices (Agentes 1 a 4)."""
    workflow = StateGraph(DocumentState)

    # Registro de Nós
    workflow.add_node("reception", reception_agent)
    workflow.add_node("extractor", extractor_agent)
    workflow.add_node("identifier", identifier_agent)
    workflow.add_node("structurer", structurer_agent)

    # Conexões e Roteamentos
    workflow.add_edge(START, "reception")
    workflow.add_conditional_edges(
        "reception",
        _check_cache_or_error,
        {
            "extractor": "extractor",
            END: END
        }
    )
    workflow.add_edge("extractor", "identifier")
    workflow.add_edge("identifier", "structurer")
    workflow.add_edge("structurer", END)

    return workflow.compile()


def build_comparison_graph() -> StateGraph:
    """Constrói o Grafo LangGraph para Comparação e Síntese de Parecer Executivo (Agentes 5 e 6)."""
    workflow = StateGraph(ComparisonState)

    workflow.add_node("comparator", comparator_agent)
    workflow.add_node("reporter", reporter_agent)

    workflow.add_edge(START, "comparator")
    workflow.add_edge("comparator", "reporter")
    workflow.add_edge("reporter", END)

    return workflow.compile()


# Grafos compilados em singleton
document_pipeline = build_document_graph()
comparison_pipeline = build_comparison_graph()


def run_document_pipeline_with_progress(
    file_path: str,
    file_name: str,
    on_step_callback: Optional[Callable[[int, str, str], None]] = None
) -> DocumentState:
    """Executa o pipeline dos Agentes 1 a 4 emitindo callbacks de progresso para a UI do Streamlit."""
    initial_state = DocumentState(file_path=file_path, file_name=file_name)
    current_state = initial_state

    # Etapa 1: Reception
    if on_step_callback:
        on_step_callback(1, "Agente 1 — Recepção", "Validando cabeçalhos PDF e calculando hash...")
    current_state = reception_agent(current_state)
    if current_state.status in ("erro", "concluido_em_cache"):
        return current_state

    # Etapa 2: Extractor
    if on_step_callback:
        on_step_callback(2, "Agente 2 — Extração", "Extraindo texto digital ou acionando fallback OCR...")
    current_state = extractor_agent(current_state)
    if current_state.status == "erro":
        return current_state

    # Etapa 3: Identifier
    if on_step_callback:
        on_step_callback(3, "Agente 3 — Identificação", "Segmentando cláusulas, coberturas e limites...")
    current_state = identifier_agent(current_state)
    if current_state.status == "erro":
        return current_state

    # Etapa 4: Structurer
    if on_step_callback:
        on_step_callback(4, "Agente 4 — Estruturação", "Mapeando dados canônicos e persistindo no banco...")
    current_state = structurer_agent(current_state)

    return current_state


def run_comparison_pipeline_with_progress(
    apolice_a: ApoliceDAO,
    apolice_b: ApoliceDAO,
    on_step_callback: Optional[Callable[[int, str, str], None]] = None
) -> ComparisonState:
    """Executa o pipeline dos Agentes 5 e 6 com atualização de progresso."""
    state = ComparisonState(apolice_a=apolice_a, apolice_b=apolice_b)

    # Etapa 5: Comparator
    if on_step_callback:
        on_step_callback(5, "Agente 5 — Comparação", "Confrontando campos, franquias e calculando similaridade...")
    state = comparator_agent(state)
    if state.status == "erro":
        return state

    # Etapa 6: Reporter
    if on_step_callback:
        on_step_callback(6, "Agente 6 — Relator", "Sintetizando parecer executivo comparativo...")
    state = reporter_agent(state)

    return state
