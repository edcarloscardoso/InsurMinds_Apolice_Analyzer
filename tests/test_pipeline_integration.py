"""Testes de integração end-to-end do pipeline de agentes LangGraph com as apólices sintéticas."""
import pytest
from pathlib import Path
from agents.graph import run_document_pipeline_with_progress, run_comparison_pipeline_with_progress
from core.database import db


def test_document_and_comparison_pipeline_integration():
    """Executa o fluxo completo de ponta a ponta dos 6 agentes nas apólices de exemplo."""
    sample_dir = Path(__file__).resolve().parent.parent / "data" / "sample_policies"
    pdf_allianz = sample_dir / "apolice_do_allianz.pdf"
    pdf_chubb = sample_dir / "apolice_do_chubb.pdf"

    assert pdf_allianz.exists(), "PDF Allianz de teste deve existir."
    assert pdf_chubb.exists(), "PDF Chubb de teste deve existir."

    # Ingestão da Apólice Allianz (Agentes 1 a 4)
    state_allianz = run_document_pipeline_with_progress(
        file_path=str(pdf_allianz),
        file_name=pdf_allianz.name
    )
    assert state_allianz.status in ("concluido", "concluido_em_cache")
    assert state_allianz.structured_data is not None
    assert "Allianz" in (state_allianz.structured_data.seguradora or "")

    # Ingestão da Apólice Chubb (Agentes 1 a 4)
    state_chubb = run_document_pipeline_with_progress(
        file_path=str(pdf_chubb),
        file_name=pdf_chubb.name
    )
    assert state_chubb.status in ("concluido", "concluido_em_cache")
    assert state_chubb.structured_data is not None
    assert "Chubb" in (state_chubb.structured_data.seguradora or "")

    # Comparação e Parecer (Agentes 5 e 6)
    comp_state = run_comparison_pipeline_with_progress(
        apolice_a=state_allianz.structured_data,
        apolice_b=state_chubb.structured_data
    )
    assert comp_state.status == "concluido"
    assert comp_state.diff_result is not None
    assert comp_state.diff_result.score_similaridade > 0
    assert len(comp_state.report_markdown) > 100
    assert "Relatório" in comp_state.report_markdown or "Resumo Executivo" in comp_state.report_markdown

    # Validação no banco SQLite
    apolices_salvas = db.list_apolices()
    assert len(apolices_salvas) >= 2
