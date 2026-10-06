# Relatório de Auditoria — Fase 8.0E
## Consolidação Final de Dependências e Contrato de Ambiente

**Projeto:** InsurMinds Apólice Analyzer
**Fase:** 8.0E — Consolidação Final de Dependências e Contrato de Ambiente
**Data:** 30 de Setembro de 2026
**Ambiente de Homologação Real:** Linux openSUSE Tumbleweed (Kernel 7.2.7-1-default, x86_64, Python 3.13.15)
**Ambiente Alvo de Portabilidade:** Windows 11 Pro / Enterprise (x86_64, Build >= 22000)
**Veredito da Fase:** **PASS** (Linux Homologado 182/182 | Windows 11 Preparado / Pending Real Validation)

---

## 1. Resumo Executivo & Objetivos

O objetivo primordial da **Fase 8.0E** consistiu em consolidar definitivamente o contrato de ambiente do InsurMinds Apólice Analyzer para Linux e Windows 11, auditando a totalidade das importações estáticas, eliminando inconsistências conceituais de documentação herdadas de fases anteriores (especificamente a menção errônea a `pypdfium2`), refinando os scripts de inicialização/diagnóstico e formalizando o contrato de infraestrutura antes da reconstrução final do README.md na Fase 8.0F.

### Estado dos Gates:
- **Gate 8.0A (Corpus Externo):** PASS
- **Gate 8.0B (Homologação Inédita D&O):** PASS
- **Gate 8.0C (Auditoria de Dependências Linux):** PASS
- **Gate 8.0D (Portabilidade Windows 11):** PREPARED / PENDING REAL VALIDATION
- **Gate 8.0E (Consolidação de Ambiente):** **PASS**

---

## 2. Auditoria e Matriz Final de Dependências

Foi executada uma análise estática abrangente baseada na árvore sintática abstrata (AST) de todos os arquivos Python do projeto (`app.py`, `core/`, `agents/`, `ui/`, `scripts/`, `tests/`, `data/`).

### 2.1. Dependências Oficiais de Runtime (`requirements.txt`)
Contém estritamente **9 pacotes diretos de primeiro nível**. Zero pacotes não utilizados; zero ausências de pacotes.

| Pacote | Versão Mínima | Uso no Projeto | Arquivos de Importação Primários | Linux | Windows 11 |
|---|---|---|---|:---:|:---:|
| `streamlit` | `>=1.39.0` | Interface gráfica, navegação, componentes de visualização | `app.py`, `ui/*` | PASS | PENDING |
| `pandas` | `>=2.0.0` | Estruturação tabular, conciliação contábil (PSL/Sinistros) | `ui/page_compare.py`, `ui/page_accounting.py` | PASS | PENDING |
| `langgraph` | `>=0.2.0` | Orquestração da máquina de estados finita multi-agente | `agents/graph.py` | PASS | PENDING |
| `pydantic` | `>=2.0.0` | Schemas de apólices, contratos de dados, Structured Output | `core/schemas.py`, `core/llm_client.py` | PASS | PENDING |
| `google-genai` | `>=2.20.0` | SDK oficial Google Gemini 2.0 (LLM e Vision) | `core/llm_client.py` | PASS | PENDING |
| `pdfplumber` | `>=0.11.0` | Motor primário de extração de texto digital de PDFs | `agents/extractor_agent.py`, `ui/page_upload.py` | PASS | PENDING |
| `pymupdf` | `>=1.24.0` | Conversão de PDF/imagem e OCR determinístico via C-bindings | `agents/extractor_agent.py`, `scripts/validate_environment.py` | PASS | PENDING |
| `Pillow` | `>=10.0.0` | Validação de magic bytes binários de segurança (PNG, JPG) | `core/security.py`, `tests/test_image_ingestion.py` | PASS | PENDING |
| `python-dotenv` | `>=1.0.0` | Carregamento de variáveis de ambiente de arquivos `.env` | `core/config.py` | PASS | PENDING |

### 2.2. Dependências de Desenvolvimento e Testes (`requirements-dev.txt`)
Herda `-r requirements.txt` e adiciona estritamente:

| Pacote | Versão Mínima | Uso no Projeto | Arquivos de Importação |
|---|---|---|---|
| `pytest` | `>=8.0.0` | Framework de testes unitários e de integração (182 testes) | `tests/*` (22 suítes) |
| `reportlab` | `>=4.0.0` | Gerador determinístico de apólices sintéticas D&O | `data/generate_samples.py` |
| `requests` | `>=2.28.0` | Testes automatizados de health-check e validação HTTP | `scripts/qa_*.py` |
| `websockets` | `>=12.0.0` | Telemetria CDP (Chrome DevTools Protocol) em testes de UI | `scripts/qa_*.py` |

---

## 3. Análise da Inconsistência `pypdfium2`

### 3.1. Diagnóstico do Código-Fonte
A auditoria investigou minuciosamente todas as ocorrências de `pypdfium2`:
- **Grep em todo o código Python:** Nenhuma linha de código (`core/`, `agents/`, `ui/`, `scripts/`, `tests/`) importa `pypdfium2`.
- **Origem do pacote no ambiente:** O utilitário `pip show pypdfium2` confirmou que o pacote está presente no ambiente virtual como dependência estritamente transitiva exigida pelo pacote `pdfplumber` (`Required-by: pdfplumber`).
- **Inconsistência identificada:** Na documentação da Fase 8.0D (`CROSS_PLATFORM_MATRIX.md`, linha 20), o pacote havia sido citado como componente de primeiro nível: *"Extração via `pdfplumber` e `pypdfium2`"*.

### 3.2. Ação Corretiva Implementada
1. A menção direta a `pypdfium2` foi **removida** de `CROSS_PLATFORM_MATRIX.md` e de toda especificação de ambiente.
2. O contrato documental agora reflete com exatidão a realidade do código:
   - **Extração Digital Primária:** `pdfplumber`.
   - **Renderização, Conversão e OCR Local:** `PyMuPDF` (`fitz` / `pymupdf`).
3. O pacote `pypdfium2` permanece como detalhe interno e automático do `pdfplumber`, sem necessidade de declaração explícita no `requirements.txt`.

---

## 4. Contrato de Interpretador Python

- **Requisito Mínimo Formal:** `Python >= 3.10`
  - Requerido para: PEP 604 (`TypeA | TypeB`), Pattern Matching (`match/case`), Pydantic v2 e LangGraph.
- **Recomendação Prática:** `Python 3.11`, `3.12` ou `3.13` (64-bit).
- **Ambiente Linux Testado:** Python `3.13.15` (openSUSE Tumbleweed, x86_64).
- **Diretriz Windows 11:** Utilizar o instalador oficial de 64 bits (`amd64`) de python.org, marcando obrigatoriamente a opção *"Add Python to PATH"*. Ambientes de 32 bits não são suportados.

---

## 5. Contrato do Motor de OCR

O motor de OCR local do InsurMinds baseia-se em uma clara separação entre a camada Python e o sistema operacional:

1. **Camada Python:** `pymupdf` (com C-bindings integrados para Tesseract) e `Pillow` (para pré-processamento de imagens).
2. **Camada de Sistema Operacional (Binários e Modelos):**
   - **Linux:** Pacotes de sistema da distribuição (`tesseract-ocr` e `tesseract-ocr-traineddata-por`).
   - **Windows 11:** Instalador oficial UB-Mannheim 64-bit com dados de idioma em Português (`por.traineddata`).
3. **Resolução de Caminhos (`core/config.py`):**
   - Função `resolve_tessdata_dir()`: Detecta automaticamente o diretório de dados em Linux (`/usr/share/tessdata`) e Windows (`C:\Program Files\Tesseract-OCR\tessdata` ou via `TESSERACT_CMD` / `TESSDATA_PREFIX`).
   - Função `get_ocr_language()`: Detecta a presença de `por.traineddata` e ativa `por+eng`; na ausência, opera em modo seguro com `eng`.
4. **Resiliência:** Caso o Tesseract não esteja instalado na máquina, a aplicação **não quebra**: o `ExtractorAgent` redireciona a extração para o fallback determinístico regulatório com log transparente.

---

## 6. Contrato do Google Gemini & Segurança

- **Variável de Controle:** `GOOGLE_API_KEY`
- **Obrigatoriedade:** **OPCIONAL**.
- **Operação Sem Chave:** Modo de Contingência Determinístico Local baseado nas normas da SUSEP (Circular 637/2021). 100% da navegação e das funcionalidades do produto permanecem ativas.
- **Operação Com Chave:** LLM e Multimodal Vision via SDK oficial `google-genai` com Structured Output validado via Pydantic.
- **Segurança da Chave:**
  - A chave é lida via `os.getenv` e **nunca** é persistida no banco SQLite `apolices.db`.
  - Scripts de diagnóstico reportam apenas o status de presença (mascarada com tamanho em caracteres), nunca o segredo.
  - `.env` e `*.env.local` estão devidamente incluídos no `.gitignore`.

---

## 7. Contratos de Persistência e Dataset Externo

### 7.1. Banco de Dados SQLite (`DB_PATH`)
- Respeita a variável `DB_PATH`, com fallback padrão para `data/apolices.db`.
- Opera integralmente via `pathlib.Path`, aceitando caminhos relativos ou caminhos absolutos com letras de unidade Windows (`C:\...`).
- Cria automaticamente os diretórios pais necessários e migra schemas DDL se o banco não existir.

### 7.2. Dataset Externo (`INSURMINDS_EXTERNAL_TEST_DIR`)
- Variável opcional que permite conectar apólices reais D&O localizadas fora do workspace sem copiar arquivos para o repositório.
- Caso não configurada, o sistema opera de forma autônoma utilizando o corpus sintético homologado em `data/sample_policies/`.

---

## 8. Auditoria de Scripts de Automação

Os scripts foram inspecionados quanto à segurança, portabilidade e ausência de efeitos colaterais destrutivos:

1. **`scripts/setup_linux.sh`:**
   - Valida Python >= 3.10; cria `.venv`; atualiza pip; instala `requirements.txt`; checa Tesseract; executa `validate_environment.py`.
   - Zero caminhos pessoais; zero segredos; seguro para execução repetida.
2. **`scripts/setup_windows.ps1`:**
   - Script nativo em PowerShell; verifica `py` / `python`; cria `.venv`; instala `requirements.txt`; localiza Tesseract em caminhos padrão; orienta sobre execução e chave Gemini.
   - Não altera variáveis globais de sistema; não faz download de binários sem confirmação; não expõe segredos.
3. **`scripts/validate_environment.py`:**
   - Diagnóstico em 8 etapas com saída padronizada `PASS / WARNING / BLOCKER`.
   - Atualizado para importar `pymupdf as fitz`, eliminando warnings de depreciação.

---

## 9. Documentos Gerados na Fase 8.0E

1. **`docs/testing/ENVIRONMENT_CONTRACT.md`:**
   - Contrato formal e exaustivo de infraestrutura, interpretador Python, dependências diretas vs transitivas, OCR, Gemini, SQLite, variáveis de ambiente e comandos de execução.
2. **`docs/testing/README_ENVIRONMENT_SPEC.md`:**
   - Especificação modular completa e pronta para transposição no `README.md` principal na Fase 8.0F.
3. **`docs/testing/CROSS_PLATFORM_MATRIX.md` (Atualizado):**
   - Removida a referência indevida a `pypdfium2`; mantida a governança estrita de **PASS** no Linux e **PENDING REAL VALIDATION** no Windows 11.
4. **`docs/audits/FASE_8_0E_ENVIRONMENT_CONSOLIDATION.md`:**
   - Este relatório de auditoria consolidado.

---

## 10. Governança e Declaração de Conformidade

- **Commits no Git:** 0
- **Pushes no Git:** 0
- **Pull Requests:** 0
- **Merges:** 0
- **Alterações em Lógica Analítica / ComparatorAgent:** 0
- **Segredos ou Chaves Expostas:** 0
- **Caminhos Pessoais Hardcoded:** 0
