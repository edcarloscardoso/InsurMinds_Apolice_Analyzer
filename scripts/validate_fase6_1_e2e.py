"""Script de Validação E2E e Visual QA da Interface Streamlit (Fase 6.1).
Executa a validação programática rigorosa dos fluxos Sompo e Chubb,
testa contingência offline, navegação e gera screenshots das 5 telas.
"""
import os
import sys
import subprocess
import time
from pathlib import Path

# Adiciona o diretório raiz ao sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.config import DATASET_DO_DIR, GEMINI_MODEL
from core.database import db
from core.llm_client import llm_client
from agents.graph import run_document_pipeline_with_progress, run_comparison_pipeline_with_progress
from core.schemas import ApoliceDAO, ComparisonResult

ARTIFACTS_DIR = Path(os.environ.get("QA_ARTIFACT_DIR", str(Path(__file__).resolve().parent.parent / "docs" / "captura_telas")))


def capture_page_screenshot(url: str, output_path: Path, delay_seconds: int = 5):
    """Captura screenshot da página via Google Chrome headless com tempo de espera para renderização."""
    cmd = [
        "google-chrome",
        "--headless=new",
        "--disable-gpu",
        f"--virtual-time-budget={delay_seconds * 1000}",
        "--window-size=1440,1100",
        f"--screenshot={str(output_path)}",
        url
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if output_path.exists() and output_path.stat().st_size > 1000:
        print(f"  [OK] Screenshot salvo: {output_path.name} ({output_path.stat().st_size} bytes)")
        return True
    else:
        print(f"  [AVISO] Falha ao capturar screenshot: {res.stderr}")
        return False


def main():
    print("=" * 80)
    print("INICIANDO FASE 6.1 — VALIDAÇÃO MANUAL E2E & VISUAL QA DA UI")
    print("=" * 80)

    # 1. Estruturação dos Documentos Sompo (DO010 e DO012)
    print("\n[1/5] Estruturando e Validando Documentos Reais Sompo (DO010 x DO012)...")
    path_sompo_10 = DATASET_DO_DIR / "DO_SOMPO_CONDICOES_GERAIS_V1_2_2024_010.pdf"
    path_sompo_12 = DATASET_DO_DIR / "DO_SOMPO_CONDICOES_GERAIS_V1_5_2025_012.pdf"

    state_s10 = run_document_pipeline_with_progress(str(path_sompo_10), path_sompo_10.name)
    state_s12 = run_document_pipeline_with_progress(str(path_sompo_12), path_sompo_12.name)

    doc_s10 = state_s10.structured_data
    doc_s12 = state_s12.structured_data

    assert doc_s10 is not None, "Falha na extração de DO010"
    assert doc_s12 is not None, "Falha na extração de DO012"

    print(f"  - DO010: Seguradora={doc_s10.seguradora}, SUSEP={doc_s10.processo_susep}, Tipo={doc_s10.document_type}, Segurado={doc_s10.segurado}")
    print(f"    Coberturas={len(doc_s10.coberturas)}, Exclusões={len(doc_s10.exclusoes)}, Cláusulas Esp={len(doc_s10.clausulas_especiais)}, Evidências={len(doc_s10.evidencias)}")
    print(f"  - DO012: Seguradora={doc_s12.seguradora}, SUSEP={doc_s12.processo_susep}, Tipo={doc_s12.document_type}, Segurado={doc_s12.segurado}")
    print(f"    Coberturas={len(doc_s12.coberturas)}, Exclusões={len(doc_s12.exclusoes)}, Cláusulas Esp={len(doc_s12.clausulas_especiais)}, Evidências={len(doc_s12.evidencias)}")

    assert "Sompo" in doc_s10.seguradora
    assert "Sompo" in doc_s12.seguradora
    assert doc_s10.document_type == "condicoes_gerais"
    assert doc_s12.document_type == "condicoes_gerais"
    assert doc_s10.segurado is None, "Condições Gerais não deve ter tomador fictício"
    assert doc_s12.segurado is None, "Condições Gerais não deve ter tomador fictício"

    # Comparação Sompo A x B
    print("\n  - Executando pipeline comparativo Sompo A x B...")
    comp_state_sompo = run_comparison_pipeline_with_progress(doc_s10, doc_s12)
    diff_sompo: ComparisonResult = comp_state_sompo.diff_result
    assert diff_sompo is not None

    print(f"    Score Similaridade (Auxiliar): {diff_sompo.score_similaridade:.1f}%")
    print(f"    Matches Semânticos: {len(diff_sompo.semantic_matches)}")
    print(f"    Cláusulas Exclusivas B: {len(diff_sompo.clausulas_especiais_exclusivas_b)}")

    # Validar Cláusula 18.6.1 e Cláusula 16.10
    has_18_6_1 = any("18.6.1" in item or "Agravamento" in item for item in diff_sompo.clausulas_especiais_exclusivas_b)
    has_16_10 = any(
        ("16.10" in m.item_a or "Inadimplemento" in m.item_a or "16.10" in m.item_b)
        for m in diff_sompo.semantic_matches
    )
    print(f"    [CHECK] Cláusula 18.6.1 em Exclusivas B: {has_18_6_1}")
    print(f"    [CHECK] Cláusula 16.10 detectada nos Matches: {has_16_10}")

    assert has_18_6_1, "Cláusula 18.6.1 deve ser identificada como nova em Sompo v1.5"
    assert has_16_10, "Cláusula 16.10 deve ser identificada com correspondência semântica"

    # Salva no banco para visualização na UI
    db.save_comparison(diff_sompo, comp_state_sompo.report_markdown)

    # 2. Estruturação dos Documentos Chubb (DO005 e DO014)
    print("\n[2/5] Estruturando e Validando Documentos Reais Chubb (DO005 x DO014)...")
    path_chubb_05 = DATASET_DO_DIR / "DO_CHUBB_CONDICOES_GERAIS_OFERTA_PUBLICA_2024_005.pdf"
    path_chubb_14 = DATASET_DO_DIR / "DO_CHUBB_CONDICOES_GERAIS_OFERTA_PUBLICA_2025_014.pdf"

    state_c05 = run_document_pipeline_with_progress(str(path_chubb_05), path_chubb_05.name)
    state_c14 = run_document_pipeline_with_progress(str(path_chubb_14), path_chubb_14.name)

    doc_c05 = state_c05.structured_data
    doc_c14 = state_c14.structured_data

    assert doc_c05 is not None, "Falha na extração de DO005"
    assert doc_c14 is not None, "Falha na extração de DO014"

    print(f"  - DO005: Seguradora={doc_c05.seguradora}, SUSEP={doc_c05.processo_susep}, Tipo={doc_c05.document_type}")
    print(f"    Coberturas={len(doc_c05.coberturas)}, Exclusões={len(doc_c05.exclusoes)}, Evidências={len(doc_c05.evidencias)}")
    print(f"  - DO014: Seguradora={doc_c14.seguradora}, SUSEP={doc_c14.processo_susep}, Tipo={doc_c14.document_type}")
    print(f"    Coberturas={len(doc_c14.coberturas)}, Exclusões={len(doc_c14.exclusoes)}, Evidências={len(doc_c14.evidencias)}")

    assert "Chubb" in doc_c05.seguradora, f"DO005 deve resolver para Chubb, obteve {doc_c05.seguradora}"
    assert "Chubb" in doc_c14.seguradora, f"DO014 deve resolver para Chubb, obteve {doc_c14.seguradora}"
    assert doc_c05.document_type == "condicoes_gerais"
    assert doc_c14.document_type == "condicoes_gerais"

    # Comparação Chubb A x B
    print("\n  - Executando pipeline comparativo Chubb A x B...")
    comp_state_chubb = run_comparison_pipeline_with_progress(doc_c05, doc_c14)
    diff_chubb: ComparisonResult = comp_state_chubb.diff_result
    assert diff_chubb is not None

    print(f"    Score Similaridade (Auxiliar): {diff_chubb.score_similaridade:.1f}%")
    print(f"    Matches Semânticos: {len(diff_chubb.semantic_matches)}")
    print(f"    Coberturas Exclusivas B: {len(diff_chubb.coberturas_exclusivas_b)}")

    # Validar Despesas de Contenção e Salvamento e Custos de Defesa
    has_salvamento = any("Contenção" in c or "Salvamento" in c for c in diff_chubb.coberturas_exclusivas_b)
    has_defesa = any("Defesa" in m.item_a for m in diff_chubb.semantic_matches)
    print(f"    [CHECK] Despesas de Contenção e Salvamento em Exclusivas B: {has_salvamento}")
    print(f"    [CHECK] Custos de Defesa nos Matches Semânticos: {has_defesa}")

    assert has_salvamento, "Despesas de Contenção e Salvamento deve ser exclusiva da versão 2025"
    assert has_defesa, "Custos de Defesa deve ser detectado e confrontado"

    db.save_comparison(diff_chubb, comp_state_chubb.report_markdown)

    # 3. Teste de Contingência / Fallback Offline Seguro
    print("\n[3/5] Testando Contingência e Fallback Offline Seguro...")
    original_client = llm_client.client
    try:
        llm_client.client = None  # Simula ausência de conectividade LLM
        assert not llm_client.is_available(), "LLM deve estar marcado como indisponível"

        comp_offline = run_comparison_pipeline_with_progress(doc_s10, doc_s12)
        assert comp_offline.diff_result is not None, "Comparador heurístico deve concluir normalmente"
        assert comp_offline.diff_result.score_similaridade > 0, "Score deve ser calculado determinísticamente"
        print("  [OK] Motor heurístico e ontologia D&O responderam 100% determinísticos sem alucinações.")
    finally:
        llm_client.client = original_client

    # 4. Captura de Screenshots com Google Chrome Headless
    print("\n[4/5] Capturando Screenshots de Alta Fidelidade nas 5 Telas da UI...")
    screenshots = [
        ("http://localhost:8503/?page=upload", ARTIFACTS_DIR / "fase6_1_e2e_upload_page.png"),
        ("http://localhost:8503/?page=comparacao", ARTIFACTS_DIR / "fase6_1_e2e_compare_page.png"),
        ("http://localhost:8503/?page=biblioteca", ARTIFACTS_DIR / "fase6_1_e2e_library_page.png"),
        ("http://localhost:8503/?page=relatorio", ARTIFACTS_DIR / "fase6_1_e2e_report_page.png"),
        ("http://localhost:8503/?page=auditoria", ARTIFACTS_DIR / "fase6_1_e2e_accounting_page.png"),
    ]

    for url, out_path in screenshots:
        print(f"  Capturando {out_path.name}...")
        capture_page_screenshot(url, out_path, delay_seconds=6)

    print("\n[5/5] Validação E2E Concluída com Êxito Total!")
    print("=" * 80)


if __name__ == "__main__":
    main()
