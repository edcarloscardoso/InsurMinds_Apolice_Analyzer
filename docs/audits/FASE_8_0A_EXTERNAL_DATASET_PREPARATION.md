# Relatório de Auditoria — Fase 8.0A: Preparação do Corpus Externo e Ambiente de Homologação

**Data de Execução:** 30/09/2026
**Responsável Técnico:** Antigravity Agentic Pair Programmer
**Status da Auditoria:** **APROVADO (PASS)**
**Conformidade de Governança:** 100% de aderência (zero commit, zero push, zero PR, zero merge, zero PDFs copiados, zero contaminação do banco de demonstração).

---

## 1. Localização e Descoberta do Corpus

* **Diretório do Corpus Externo:**
  `/caminho/para/dataset_do`
* **Diretório do Workspace:**
  `/caminho/para/InsurMinds_Apolice_Analyzer`
* **Mecanismo de Descoberta:**
  Variável de ambiente `INSURMINDS_EXTERNAL_TEST_DIR`. Caso não esteja configurada no ambiente atual, o runner implementa fallback detectado para a estação de trabalho local com emissão de alerta técnico de portabilidade, sem hardcodar o caminho na lógica de negócio da aplicação.
* **Integridade da Estrutura Externa:**
  Todos os subdiretórios e catálogos obrigatórios foram validados:
  - `README.md` (presente, 8.474 bytes)
  - `documentos/` (presente, 15 PDFs contratuais)
  - `metadados/` (`catalogo.json`, `catalogo.csv`, `sha256.txt`, `tabela_fontes.md`)
  - `evidencias/` (15 arquivos Markdown com rastreabilidade)
  - `por_seguradora/` (espelhos por companhia)
  - `documentos_complementares/` (3 PDFs complementares)
  - `materiais_comerciais/` (1 PDF de folder comercial)
  - `materiais_regulatorios/` (Circular SUSEP 541/2016)
  - `referencias_academicas/` (TCC UnB sobre D&O)
  - `derivados_para_teste_ocr/` (PDF sintético rasterizado a 150 DPI)

---

## 2. Quantidade de Arquivos e Inventário

* **Total de Documentos Contratuais D&O:** 15 PDFs (941 páginas no total)
  - **Documentos Contratuais Principais:** 12 arquivos (DO001 a DO012)
  - **Documentos Contratuais Complementares:** 3 arquivos (DO013 a DO015)
* **Outros Arquivos Auditados no Corpus:** 5 arquivos (não contratuais ou derivados)
* **Seguradoras Abrangidas:** 5 companhias líderes do mercado D&O brasileiro:
  1. AIG Brasil (2 documentos)
  2. Berkley Brasil (1 documento)
  3. Chubb Seguros (4 documentos)
  4. EZZE Seguros (4 documentos)
  5. Sompo Seguradora (4 documentos)

---

## 3. Hashes Criptográficos e Tabela de Rastreabilidade

Todos os 15 documentos contratuais tiveram suas assinaturas SHA-256 e MD5 auditadas e confrontadas com o banco de dados oficial e com o catálogo de fontes:

| ID | Nome do Arquivo | Seguradora | Páginas | Tamanho | SHA-256 (Truncado) | Status no DB |
|---|---|---|---|---|---|---|
| **DO001** | `DO_AIG_CONDICOES_GERAIS_2025_001.pdf` | AIG Brasil | 171 | 1.365 KB | `ea5e2a16b588...` | Previamente Processado |
| **DO002** | `DO_AIG_CONDICOES_GERAIS_AIGGO_2025_002.pdf` | AIG Brasil | 72 | 719 KB | `700a08f26ab8...` | **INÉDITO** |
| **DO003** | `DO_BERKLEY_CONDICOES_GERAIS_2022_003.pdf` | Berkley Brasil | 62 | 653 KB | `ff9752986e7b...` | Previamente Processado |
| **DO004** | `DO_CHUBB_CONDICOES_GERAIS_CAPITAL_FECHADO_2025_004.pdf` | Chubb | 70 | 573 KB | `bd070d40cdb7...` | Previamente Processado |
| **DO005** | `DO_CHUBB_CONDICOES_GERAIS_OFERTA_PUBLICA_2024_005.pdf` | Chubb | 55 | 504 KB | `2a1bdde1d332...` | Previamente Processado |
| **DO006** | `DO_CHUBB_CONDICOES_GERAIS_FUNDOS_INVESTIMENTO_2024_006.pdf` | Chubb | 64 | 936 KB | `ea8bb3d38b1f...` | **INÉDITO** |
| **DO007** | `DO_EZZE_CONDICOES_GERAIS_2019_007.pdf` | EZZE Seguros | 55 | 612 KB | `46559801fd0c...` | Previamente Processado |
| **DO008** | `DO_EZZE_CONDICOES_GERAIS_2022_008.pdf` | EZZE Seguros | 53 | 605 KB | `d5e2339844aa...` | Previamente Processado |
| **DO009** | `DO_EZZE_CONDICOES_GERAIS_2026_009.pdf` | EZZE Seguros | 84 | 826 KB | `6a018b1e88fb...` | Previamente Processado |
| **DO010** | `DO_SOMPO_CONDICOES_GERAIS_V1_2_2024_010.pdf` | Sompo Seguradora | 44 | 660 KB | `b69e6b39ca13...` | Previamente Processado |
| **DO011** | `DO_SOMPO_CONDICOES_GERAIS_V1_3_2024_011.pdf` | Sompo Seguradora | 46 | 651 KB | `36cff6b19710...` | **INÉDITO** |
| **DO012** | `DO_SOMPO_CONDICOES_GERAIS_V1_5_2025_012.pdf` | Sompo Seguradora | 49 | 762 KB | `a6964c4f6098...` | Previamente Processado |
| **DO013** | `DO_SOMPO_CONDICOES_GERAIS_V1_4_2025_013.pdf` | Sompo Seguradora | 46 | 651 KB | `a9f48c95c953...` | Previamente Processado |
| **DO014** | `DO_CHUBB_CONDICOES_GERAIS_OFERTA_PUBLICA_2025_014.pdf` | Chubb | 59 | 501 KB | `faf59c288905...` | Previamente Processado |
| **DO015** | `DO_EZZE_CONDICOES_COMPLEMENTARES_RISCOS_AMBIENTAIS_2021_015.pdf` | EZZE Seguros | 11 | 284 KB | `27b5cfc4af08...` | **INÉDITO** |

---

## 4. Comparação com o Workspace e Banco SQLite

1. **Varredura no Workspace (`data/`):**
   O confronto de hashes SHA-256 com todo o diretório `data/` confirmou que **zero PDFs externos foram copiados para o workspace**. As apólices presentes em `data/sample_policies/` são artefatos sintéticos de teste inicial com hashes inteiramente divergentes.
2. **Confronto com o Banco `data/apolices.db`:**
   O banco SQLite de demonstração continha 11 apólices processadas em gates anteriores e 4 documentos **100% inéditos**.
3. **Preservação de Integridade:**
   Nenhum registro foi inserido, alterado ou excluído de `data/apolices.db` durante esta fase. O arquivo permanece intacto com 577.536 bytes.

---

## 5. Seleção Preliminar de Candidatos a Holdout

Com base na taxonomia exigida e no ineditismo confirmado pelo banco de dados:

1. **Documento Longo / Variante de Seguradora:**
   `DO002` (*DO_AIG_CONDICOES_GERAIS_AIGGO_2025_002.pdf* — 72 pág., AIG Brasil, inédito).
   *Justificativa:* Avaliação de chunking, tabelas de fracionamento e parsing de contratos volumosos.
2. **Seguradora Diferente / Produto Especializado:**
   `DO006` (*DO_CHUBB_CONDICOES_GERAIS_FUNDOS_INVESTIMENTO_2024_006.pdf* — 64 pág., Chubb, inédito).
   *Justificativa:* Análise de linha especializada para fundos de investimento com partes seguradas distintas.
3. **Versão Diferente / Gradiente Temporal:**
   `DO011` (*DO_SOMPO_CONDICOES_GERAIS_V1_3_2024_011.pdf* — 46 pág., Sompo, inédito).
   *Justificativa:* Completa a evolução contratual v1.2 -> v1.3 -> v1.4 -> v1.5 da Sompo.
4. **Documento Compacto / Teste de Imagem e OCR:**
   `DO015` (*DO_EZZE_CONDICOES_COMPLEMENTARES_RISCOS_AMBIENTAIS_2021_015.pdf* — 11 pág., EZZE, inédito).
   *Justificativa:* Compacto e denso, dispõe de espelho rasterizado em `derivados_para_teste_ocr/` para teste de imagens.
5. **Cross-Insurer Holdout Pair:**
   `DO006` (Chubb) vs `DO002` (AIG).
   *Justificativa:* Comparação cega e cruzada entre duas seguradoras distintas em documentos jamais processados pelo banco de dados.

---

## 6. Isolamento de Resultados de Homologação

Foi estabelecido o protocolo de isolamento:
* Todo resultado de homologação futura deverá ser gravado em:
  `scratch/external_acceptance/`
* Para testes que exigem escrita relacional, a plataforma suporta a variável `DB_PATH`, permitindo direcionar execuções de teste para `scratch/external_acceptance/homologacao.db` sem qualquer risco de contaminação ao banco principal `data/apolices.db`.

---

## 7. Runner Criado

Foi desenvolvido e validado o script de automação:
* `scripts/discover_external_dataset.py`
  Responsável por:
  - Localizar o corpus via CLI, variável de ambiente ou fallback;
  - Validar a integridade estrutural das pastas;
  - Calcular SHA-256 e MD5 de todos os arquivos;
  - Comparar com o acervo do workspace e o banco SQLite;
  - Classificar os documentos entre contratuais e complementares;
  - Gerar o manifesto formal `docs/testing/EXTERNAL_ACCEPTANCE_MANIFEST.json`;
  - Imprimir resumo gerencial no terminal.

---

## 8. Testes Executados

1. **Testes Unitários do Runner (`tests/test_discover_external_dataset.py`):**
   - 6 testes cobrindo cálculo de hashes, resolução de caminhos, validação estrutural e integridade do manifesto.
   - Resultado: **6 passed in 0.11s**.
2. **Suíte Geral de Regressão do Projeto:**
   - Execução completa com `./.venv/bin/pytest tests/ -q`.
   - Resultado: **Todos os testes continuam verdes (PASS)** sem regressão.

---

## 9. Governança Git

* `git commit`: **NÃO EXECUTADO** (0 commits).
* `git push`: **NÃO EXECUTADO** (0 pushes).
* `PR / Merge`: **NÃO EXECUTADO** (0 PRs).
* Arquivos criados estritamente dentro do escopo:
  - `scripts/discover_external_dataset.py`
  - `docs/testing/EXTERNAL_ACCEPTANCE_MANIFEST.json`
  - `docs/testing/EXTERNAL_ACCEPTANCE_DATASET.md`
  - `docs/audits/FASE_8_0A_EXTERNAL_DATASET_PREPARATION.md`
  - `tests/test_discover_external_dataset.py`
