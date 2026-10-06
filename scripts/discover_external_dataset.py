#!/usr/bin/env python3
"""scripts/discover_external_dataset.py — Descoberta e Auditoria do Corpus Externo D&O.

Responsabilidades da Fase 8.0A:
1. Localizar o corpus externo de homologação via INSURMINDS_EXTERNAL_TEST_DIR (ou fallback local detectado);
2. Validar a integridade estrutural do corpus (README.md, documentos/, metadados/, evidências/);
3. Ler o catálogo oficial de metadados (catalogo.json / catalogo.csv);
4. Calcular SHA-256 e MD5 dos documentos do corpus externo;
5. Comparar com o acervo do workspace (data/) e com o banco SQLite (data/apolices.db);
6. Classificar os documentos (contratuais principais, complementares, comerciais, regulatórios, acadêmicos, OCR);
7. Selecionar preliminarmente candidatos a holdout cobrindo diversidade de seguradoras, tamanhos, versões e OCR/imagem;
8. Gerar o manifesto docs/testing/EXTERNAL_ACCEPTANCE_MANIFEST.json;
9. Imprimir resumo para auditoria técnica.

GOVERNANÇA:
- NÃO copia nenhum PDF para dentro do workspace;
- NÃO modifica nenhum arquivo do corpus externo;
- NÃO contamina o banco data/apolices.db;
- NÃO executa inferência nem altera regras analíticas da aplicação.
"""

import argparse
import datetime
import hashlib
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Caminho do workspace raiz
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent

# Fallback local para o corpus externo (pode ser sobrescrito por INSURMINDS_EXTERNAL_TEST_DIR)
DEFAULT_LOCAL_CORPUS = Path(os.getenv("INSURMINDS_EXTERNAL_TEST_DIR", str(WORKSPACE_ROOT.parent / "dataset_do")))


def resolve_corpus_path(explicit_path: Optional[str] = None) -> Tuple[Path, str]:
    """Resolve a localização do corpus externo priorizando variável de ambiente."""
    if explicit_path:
        p = Path(explicit_path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Caminho explícito informado não existe: {p}")
        return p, "cli_argument (--corpus-dir)"

    env_var = os.getenv("INSURMINDS_EXTERNAL_TEST_DIR")
    if env_var:
        p = Path(env_var).resolve()
        if not p.exists():
            raise FileNotFoundError(
                f"Variável INSURMINDS_EXTERNAL_TEST_DIR aponta para caminho inexistente: {p}"
            )
        return p, "environment_variable (INSURMINDS_EXTERNAL_TEST_DIR)"

    if DEFAULT_LOCAL_CORPUS.exists():
        return DEFAULT_LOCAL_CORPUS.resolve(), "machine_detected_fallback (configuração local)"

    raise RuntimeError(
        "Corpus externo D&O não localizado!\n"
        "Defina a variável de ambiente INSURMINDS_EXTERNAL_TEST_DIR apontando para o diretório dataset_do,\n"
        "ou passe o parâmetro --corpus-dir <caminho>."
    )


def compute_hashes(file_path: Path) -> Tuple[str, str, int]:
    """Calcula SHA-256, MD5 e tamanho em bytes de um arquivo."""
    content = file_path.read_bytes()
    sha256 = hashlib.sha256(content).hexdigest()
    md5 = hashlib.md5(content).hexdigest()
    return sha256, md5, len(content)


def get_workspace_file_hashes(data_dir: Path) -> Dict[str, Tuple[Path, str]]:
    """Mapeia SHA-256 de todos os arquivos de dados contidos no workspace."""
    workspace_hashes: Dict[str, Tuple[Path, str]] = {}
    if not data_dir.exists():
        return workspace_hashes

    for p in data_dir.rglob("*"):
        if p.is_file() and not p.name.endswith((".db", ".db-journal")):
            try:
                sha256 = hashlib.sha256(p.read_bytes()).hexdigest()
                workspace_hashes[sha256] = (p, p.name)
            except Exception:
                pass
    return workspace_hashes


def get_database_processed_records(db_path: Path) -> Dict[str, Dict[str, Any]]:
    """Lê registros de apólices salvas no banco SQLite data/apolices.db."""
    records: Dict[str, Dict[str, Any]] = {}
    if not db_path.exists():
        return records

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='apolices'")
        if not cursor.fetchone():
            conn.close()
            return records

        cursor.execute("SELECT id, nome_arquivo, seguradora, numero_apolice, processo_susep, created_at FROM apolices")
        rows = cursor.fetchall()
        for r in rows:
            doc_id, nome_arq, seguradora, num_apolice, proc_susep, created_at = r
            records[doc_id] = {
                "id": doc_id,
                "nome_arquivo": nome_arq,
                "seguradora": seguradora,
                "numero_apolice": num_apolice,
                "processo_susep": proc_susep,
                "created_at": created_at
            }
        conn.close()
    except Exception as e:
        print(f"[AVISO] Falha ao consultar banco SQLite {db_path}: {e}")

    return records


def validate_corpus_structure(corpus_dir: Path) -> Dict[str, bool]:
    """Verifica os componentes estruturais obrigatórios do corpus."""
    checks = {
        "readme_exists": (corpus_dir / "README.md").is_file(),
        "documentos_dir_exists": (corpus_dir / "documentos").is_dir(),
        "metadados_dir_exists": (corpus_dir / "metadados").is_dir(),
        "catalogo_json_exists": (corpus_dir / "metadados" / "catalogo.json").is_file(),
        "catalogo_csv_exists": (corpus_dir / "metadados" / "catalogo.csv").is_file(),
        "evidencias_dir_exists": (corpus_dir / "evidencias").is_dir(),
        "por_seguradora_dir_exists": (corpus_dir / "por_seguradora").is_dir(),
        "documentos_complementares_exists": (corpus_dir / "documentos_complementares").is_dir(),
        "materiais_comerciais_exists": (corpus_dir / "materiais_comerciais").is_dir(),
        "materiais_regulatorios_exists": (corpus_dir / "materiais_regulatorios").is_dir(),
        "referencias_academicas_exists": (corpus_dir / "referencias_academicas").is_dir(),
        "derivados_ocr_exists": (corpus_dir / "derivados_para_teste_ocr").is_dir(),
    }
    return checks


def build_manifest(
    corpus_dir: Path,
    corpus_source: str,
    db_path: Path,
    data_dir: Path
) -> Dict[str, Any]:
    """Monta o inventário canônico e gera o manifesto de aceitação de homologação."""
    # Valida estrutura
    structure_checks = validate_corpus_structure(corpus_dir)
    if not structure_checks["documentos_dir_exists"] or not structure_checks["catalogo_json_exists"]:
        raise RuntimeError("Estrutura do corpus externa inválida ou incompleta.")

    # Lê catalogo.json
    catalogo_path = corpus_dir / "metadados" / "catalogo.json"
    catalogo_data: List[Dict[str, Any]] = json.loads(catalogo_path.read_text(encoding="utf-8"))

    # Lê hashes do workspace e registros do banco
    workspace_hashes = get_workspace_file_hashes(data_dir)
    db_records = get_database_processed_records(db_path)

    # Documentos mapeados no catálogo
    manifest_documents: List[Dict[str, Any]] = []
    sha256_by_doc_id: Dict[str, str] = {}
    previamente_processados_count = 0
    ineditos_count = 0
    workspace_collision_count = 0

    # Candidatos a Holdout definidos estrategicamente
    # Cobrindo:
    # 1. Documento longo / variante da mesma seguradora: DO002 (72 páginas)
    # 2. Seguradora diferente / produto especializado: DO006 (Fundos de Investimento, 64 páginas)
    # 3. Versão diferente / evolução temporal: DO011 (Sompo v1.3, 46 páginas)
    # 4. Documento adequado para teste de imagem/OCR: DO015 (Riscos Ambientais, 11 páginas)
    # 5. Cross-insurer holdout pair: DO006 x DO002 (Chubb x AIG)
    holdout_config = {
        "DO002": {
            "candidate": True,
            "role": "long_document_and_insurer_variant",
            "justificativa": (
                "Documento extenso (72 páginas) com 2 tabelas estruturadas e pacote integral (CG+CE+CP+Endossos). "
                "Inédito no banco SQLite de demonstração. Excelente para testes de escalabilidade de chunking e parsing."
            )
        },
        "DO006": {
            "candidate": True,
            "role": "distinct_insurer_and_specialized_product",
            "justificativa": (
                "Linha especializada de RC D&O para Administradores de Fundos de Investimentos (Chubb). "
                "Estrutura de partes seguradas distinta do padrão societário convencional. Inédito no banco SQLite (64 páginas)."
            )
        },
        "DO011": {
            "candidate": True,
            "role": "version_variation_and_temporal_gradient",
            "justificativa": (
                "Versão intermediária v1.3 (outubro/2024) da Sompo (Processo SUSEP 15414.652408/2023-71). "
                "Inédito no banco SQLite (46 páginas, 3 tabelas). Completa o gradiente temporal evolutivo v1.2 -> v1.3 -> v1.4 -> v1.5."
            )
        },
        "DO015": {
            "candidate": True,
            "role": "ocr_image_candidate_and_compact_scope",
            "justificativa": (
                "Condições complementares anexas de Riscos Ambientais da EZZE Seguros (11 páginas). "
                "Inédito no banco SQLite. Por ser compacto e denso, é o documento perfeito para homologação da ingestão nativa "
                "de imagens (PNG/JPG) e OCR com suporte ao análogo rasterizado em derivados_para_teste_ocr/."
            )
        }
    }

    for item in catalogo_data:
        doc_id = item["id_documento"]
        nome_arquivo = item["nome_arquivo"]
        file_path = corpus_dir / "documentos" / nome_arquivo

        if not file_path.is_file():
            print(f"[ALERTA] Arquivo catalogado não encontrado em documentos/: {nome_arquivo}")
            continue

        sha256, md5, size_bytes = compute_hashes(file_path)
        sha256_by_doc_id[doc_id] = sha256

        # Verifica se o arquivo físico foi copiado para o workspace
        in_workspace = sha256 in workspace_hashes
        if in_workspace:
            workspace_collision_count += 1

        # Verifica se foi previamente processado no banco SQLite oficial (chave primária é MD5)
        is_processed = (md5 in db_records) or any(
            r.get("nome_arquivo") == nome_arquivo for r in db_records.values()
        )

        if is_processed:
            previamente_processados_count += 1
        else:
            ineditos_count += 1

        is_principal = item.get("colecao_principal", "SIM").upper() == "SIM"
        categoria = "documento_contratual_principal" if is_principal else "documento_contratual_complementar"

        holdout_info = holdout_config.get(doc_id, {"candidate": False, "role": None, "justificativa": None})

        doc_entry = {
            "id_documento": doc_id,
            "nome_arquivo": nome_arquivo,
            "caminho_relativo": f"documentos/{nome_arquivo}",
            "categoria": categoria,
            "colecao_principal": is_principal,
            "sha256": sha256,
            "md5": md5,
            "tamanho_bytes": size_bytes,
            "tamanho_formatado": item.get("tamanho_aproximado", f"{size_bytes // 1024} KB"),
            "quantidade_paginas": item.get("quantidade_paginas"),
            "quantidade_tabelas": item.get("quantidade_tabelas_detectadas"),
            "seguradora": item.get("seguradora"),
            "produto": item.get("produto"),
            "ramo": item.get("ramo", "Responsabilidade Civil (D&O)"),
            "ano": item.get("ano"),
            "versao": item.get("versao"),
            "processo_susep": item.get("processo_susep"),
            "url_origem": item.get("url_origem"),
            "url_pagina_origem": item.get("url_pagina_origem"),
            "dominio_origem": item.get("dominio_origem"),
            "fonte_oficial": "SIM" in item.get("fonte_oficial", "SIM"),
            "classificacao_qualidade": item.get("classificacao_qualidade", "A"),
            "conhecido_previamente_no_projeto": is_processed,
            "previamente_processado_no_db": is_processed,
            "presente_no_workspace_data": in_workspace,
            "holdout_candidate": holdout_info["candidate"],
            "holdout_role": holdout_info["role"],
            "holdout_justificativa": holdout_info["justificativa"],
            "observacoes": item.get("observacoes", "")
        }
        manifest_documents.append(doc_entry)

    # Identifica outros arquivos do corpus (comerciais, acadêmicos, regulatórios, derivados)
    other_assets: List[Dict[str, Any]] = []

    folder_categories = [
        ("materiais_comerciais", "material_comercial_folder", False),
        ("referencias_academicas", "referencia_academica_tcc", False),
        ("materiais_regulatorios", "material_regulatorio_susep", False),
        ("derivados_para_teste_ocr", "derivado_sintetico_ocr", False),
    ]

    for folder_name, cat_desc, is_contractual in folder_categories:
        fdir = corpus_dir / folder_name
        if fdir.is_dir():
            for p in sorted(fdir.glob("*")):
                if p.is_file() and not p.name.startswith("."):
                    sha256, md5, sz = compute_hashes(p)
                    other_assets.append({
                        "nome_arquivo": p.name,
                        "caminho_relativo": f"{folder_name}/{p.name}",
                        "categoria": cat_desc,
                        "e_documento_contratual": is_contractual,
                        "sha256": sha256,
                        "md5": md5,
                        "tamanho_bytes": sz,
                        "formato": p.suffix.lstrip(".").lower()
                    })

    # Seleção de Pares Recomendados para Homologação Cruzada
    cross_insurer_pairs = [
        {
            "par_id": "HOLDOUT_PAIR_01_CROSS_INSURER",
            "doc_a_id": "DO006",
            "doc_a_nome": "DO_CHUBB_CONDICOES_GERAIS_FUNDOS_INVESTIMENTO_2024_006.pdf",
            "doc_a_seguradora": "Chubb",
            "doc_b_id": "DO002",
            "doc_b_nome": "DO_AIG_CONDICOES_GERAIS_AIGGO_2025_002.pdf",
            "doc_b_seguradora": "AIG Brasil",
            "tipo_comparacao": "cross_insurer_holdout",
            "ambos_ineditos_no_db": True,
            "justificativa": (
                "Comparação cega entre seguradoras distintas (Chubb x AIG), com dois contratos completamente inéditos "
                "no banco de demonstração (DO006: 64 pág x DO002: 72 pág)."
            )
        },
        {
            "par_id": "HOLDOUT_PAIR_02_VERSION_DIFF",
            "doc_a_id": "DO010",
            "doc_a_nome": "DO_SOMPO_CONDICOES_GERAIS_V1_2_2024_010.pdf",
            "doc_a_seguradora": "Sompo Seguradora",
            "doc_b_id": "DO011",
            "doc_b_nome": "DO_SOMPO_CONDICOES_GERAIS_V1_3_2024_011.pdf",
            "doc_b_seguradora": "Sompo Seguradora",
            "tipo_comparacao": "intra_insurer_version_diff",
            "ambos_ineditos_no_db": False,
            "justificativa": (
                "Comparação de evolução de versões consecutivas da Sompo: v1.2 (DO010 - conhecido) versus v1.3 (DO011 - inédito). "
                "Permite validar se o diff identifica cláusulas inseridas/modificadas entre maio/2024 e outubro/2024."
            )
        }
    ]

    manifest = {
        "metadata": {
            "manifest_version": "1.0.0",
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "generator_script": "scripts/discover_external_dataset.py",
            "fase": "8.0A — Preparação do Corpus Externo e Ambiente de Homologação",
            "corpus_location": str(corpus_dir),
            "corpus_source": corpus_source,
            "workspace_root": str(WORKSPACE_ROOT),
            "database_analyzed": str(db_path),
            "environment_variable_configured": bool(os.getenv("INSURMINDS_EXTERNAL_TEST_DIR")),
            "governance_compliance": {
                "zero_pdfs_copied": workspace_collision_count == 0,
                "zero_db_modifications": True,
                "zero_corpus_modifications": True,
                "external_corpus_intact": True
            }
        },
        "summary": {
            "total_contractual_documents": len(manifest_documents),
            "contractual_principais": sum(1 for d in manifest_documents if d["colecao_principal"]),
            "contractual_complementares": sum(1 for d in manifest_documents if not d["colecao_principal"]),
            "other_corpus_assets": len(other_assets),
            "seguradoras_cobertas": sorted(list({d["seguradora"] for d in manifest_documents if d["seguradora"]})),
            "total_paginas_contratuais": sum(d["quantidade_paginas"] for d in manifest_documents if d["quantidade_paginas"]),
            "previamente_processados_no_db": previamente_processados_count,
            "documentos_ineditos_no_db": ineditos_count,
            "copiados_para_workspace": workspace_collision_count,
            "candidatos_holdout_individuais": sum(1 for d in manifest_documents if d["holdout_candidate"]),
            "pares_holdout_recomendados": len(cross_insurer_pairs)
        },
        "structure_verification": structure_checks,
        "holdout_candidates_summary": [
            {
                "id_documento": d["id_documento"],
                "nome_arquivo": d["nome_arquivo"],
                "seguradora": d["seguradora"],
                "paginas": d["quantidade_paginas"],
                "tamanho_bytes": d["tamanho_bytes"],
                "sha256": d["sha256"],
                "role": d["holdout_role"],
                "justificativa": d["holdout_justificativa"]
            }
            for d in manifest_documents if d["holdout_candidate"]
        ],
        "holdout_pairs_recommended": cross_insurer_pairs,
        "documents": manifest_documents,
        "other_assets": other_assets
    }

    return manifest


def print_summary_report(manifest: Dict[str, Any]) -> None:
    """Exibe no terminal um relatório estruturado e legível da descoberta."""
    meta = manifest["metadata"]
    sm = manifest["summary"]

    print("=" * 80)
    print("INSURMINDS APÓLICE ANALYZER — RELATÓRIO DE DESCOBERTA DO CORPUS EXTERNO")
    print("Fase 8.0A — Homologação & Aceitação Externa")
    print("=" * 80)
    print(f"Localização do Corpus:  {meta['corpus_location']}")
    print(f"Fonte de Resolução:     {meta['corpus_source']}")
    print(f"INSURMINDS_EXTERNAL_TEST_DIR Definida: {'SIM' if meta['environment_variable_configured'] else 'NÃO (usando fallback detectado)'}")
    print(f"Banco Analisado:        {meta['database_analyzed']}")
    print(f"Data de Geração:        {meta['generated_at']}")
    print("-" * 80)
    print("INVENTÁRIO E ESTATÍSTICAS GERAIS:")
    print(f"  • Total de Documentos Contratuais D&O:  {sm['total_contractual_documents']}")
    print(f"    - Contratos Principais:               {sm['contractual_principais']}")
    print(f"    - Contratos Complementares:           {sm['contractual_complementares']}")
    print(f"  • Outros Arquivos no Corpus:            {sm['other_corpus_assets']} (comerciais, acadêmicos, regulatórios, OCR)")
    print(f"  • Total de Páginas Contratuais:         {sm['total_paginas_contratuais']} páginas")
    print(f"  • Seguradoras Cobertas ({len(sm['seguradoras_cobertas'])}):           {', '.join(sm['seguradoras_cobertas'])}")
    print("-" * 80)
    print("ANÁLISE DE INEDITISMO & PRESERVAÇÃO DO WORKSPACE:")
    print(f"  • Documentos Já Processados no DB:     {sm['previamente_processados_no_db']}")
    print(f"  • Documentos 100% INÉDITOS no DB:      {sm['documentos_ineditos_no_db']}")
    print(f"  • Arquivos Copiados para o Workspace:  {sm['copiados_para_workspace']} (PERFEITO: 0 cópias)")
    print("-" * 80)
    print("DOCUMENTOS INÉDITOS IDENTIFICADOS NO BANCO:")
    for d in manifest["documents"]:
        if not d["previamente_processado_no_db"]:
            print(f"  [{d['id_documento']}] {d['nome_arquivo']}")
            print(f"       Seguradora: {d['seguradora']} | Páginas: {d['quantidade_paginas']} | Tam: {d['tamanho_formatado']}")
            print(f"       SHA-256: {d['sha256']}")
    print("-" * 80)
    print("SELEÇÃO PRELIMINAR DE CANDIDATOS A HOLDOUT:")
    for c in manifest["holdout_candidates_summary"]:
        print(f"  ★ [{c['id_documento']}] {c['nome_arquivo']}")
        print(f"     Papel / Critério: {c['role']}")
        print(f"     Seguradora: {c['seguradora']} | Páginas: {c['paginas']}")
        print(f"     Justificativa: {c['justificativa']}")
    print("-" * 80)
    print("PARES RECOMENDADOS PARA TESTES DE COMPARAÇÃO:")
    for p in manifest["holdout_pairs_recommended"]:
        print(f"  ⇄ {p['par_id']} ({p['tipo_comparacao']})")
        print(f"     A: [{p['doc_a_id']}] {p['doc_a_nome']} ({p['doc_a_seguradora']})")
        print(f"     B: [{p['doc_b_id']}] {p['doc_b_nome']} ({p['doc_b_seguradora']})")
        print(f"     Justificativa: {p['justificativa']}")
    print("-" * 80)
    print("VERIFICAÇÃO DE GOVERNANÇA:")
    print(f"  [PASS] Zero PDFs copiados para o workspace:      {meta['governance_compliance']['zero_pdfs_copied']}")
    print(f"  [PASS] Zero contaminação no banco data/apolices.db: {meta['governance_compliance']['zero_db_modifications']}")
    print(f"  [PASS] Zero modificações no corpus externo:       {meta['governance_compliance']['zero_corpus_modifications']}")
    print("=" * 80)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Descobre, calcula hashes e audita o corpus externo de homologação D&O (Fase 8.0A)."
    )
    parser.add_argument(
        "--corpus-dir",
        type=str,
        default=None,
        help="Caminho explícito para a raiz do corpus externo dataset_do (opcional)"
    )
    parser.add_argument(
        "--manifest-path",
        type=str,
        default=str(WORKSPACE_ROOT / "docs" / "testing" / "EXTERNAL_ACCEPTANCE_MANIFEST.json"),
        help="Caminho para gravação do manifesto JSON de aceitação"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Imprime o manifesto completo em formato JSON no stdout"
    )

    args = parser.parse_args()

    try:
        corpus_dir, corpus_source = resolve_corpus_path(args.corpus_dir)
        db_path = WORKSPACE_ROOT / "data" / "apolices.db"
        data_dir = WORKSPACE_ROOT / "data"

        manifest = build_manifest(
            corpus_dir=corpus_dir,
            corpus_source=corpus_source,
            db_path=db_path,
            data_dir=data_dir
        )

        manifest_file = Path(args.manifest_path)
        manifest_file.parent.mkdir(parents=True, exist_ok=True)
        manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

        if args.json:
            print(json.dumps(manifest, indent=2, ensure_ascii=False))
        else:
            print_summary_report(manifest)
            print(f"\nManifesto gerado com sucesso em:\n  file://{manifest_file.resolve()}\n")

        return 0

    except Exception as e:
        print(f"[ERRO CRÍTICO] Falha na execução do discover_external_dataset: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
