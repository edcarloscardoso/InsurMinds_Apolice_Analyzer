# Auditoria de Dependências Python e Sistema — InsurMinds Apólice Analyzer

**Projeto:** InsurMinds Apólice Analyzer
**Fase:** 8.0C — Dependency Audit + Linux Reproducible Install
**Data da Auditoria:** 30 de Setembro de 2026
**Ambiente Validado:** openSUSE Tumbleweed (Linux x86_64, Kernel 7.2.7) / Python 3.13.15

---

## 1. Metodologia de Auditoria de Imports

Foi realizada uma varredura estática por Árvore Sintática Abstrata (AST) em **100% dos arquivos Python** do repositório, inspecionando os diretórios:
- `app.py`
- `core/`
- `agents/`
- `ui/`
- `scripts/`
- `tests/`
- `data/`

Todos os módulos importados foram confrontados contra a biblioteca padrão do Python (`sys.stdlib_module_names`) e catalogados em suas respectivas bibliotecas do PyPI ou do sistema operacional.

---

## 2. Tabela de Mapeamento Completo de Dependências Externas

| Biblioteca PyPI | Módulo Importado | Uso / Responsabilidade Principal | Arquivos Principais | Necessária em Runtime? | Necessária em Teste? | Justificativa / Observações |
|---|---|---|---|:---:|:---:|---|
| **streamlit** | `streamlit` | Framework de interface web corporativa reativa, componentes de UI, upload de arquivos e telemetria | `app.py`, `ui/page_upload.py`, `ui/page_compare.py`, `ui/page_report.py`, `ui/page_library.py`, `ui/components/*` | **SIM** | **SIM** | Componente central da camada visual (Requisitos 1 a 12). |
| **pydantic** | `pydantic` | Definição de contratos de dados, esquemas Pydantic v2, validação de tipos, serialização e Structured Output | `core/schemas.py`, `core/llm_client.py` | **SIM** | **SIM** | Núcleo de integridade e tipagem estrita de todo o pipeline analítico. |
| **google-genai** | `google.genai` | SDK oficial do Google Gemini para chamadas de IA Generativa com Structured Output e Gemini Multimodal Vision | `core/llm_client.py`, `agents/extractor_agent.py`, `agents/comparator_agent.py` | **SIM** | **SIM** | Motor oficial de IA (opera com fallback determinístico quando sem chave). |
| **langgraph** | `langgraph` | Orquestração do fluxo multi-agente de análise contratual com estado compartilhado (`DocumentState`) | `agents/graph.py` | **SIM** | **SIM** | Governança da máquina de estados do pipeline multi-agente. |
| **pdfplumber** | `pdfplumber` | Extração de texto de documentos PDF nativos digitais e contagem segura de páginas | `agents/extractor_agent.py`, `ui/page_upload.py` | **SIM** | **SIM** | Motor primário de extração de condições gerais em PDF. |
| **pymupdf** | `fitz` | Renderização de páginas, conversão de formatos de imagem e OCR local nativo via C-bindings do Tesseract | `agents/extractor_agent.py` | **SIM** | **SIM** | Rota paralela e fallback determinístico offline de OCR para imagens. |
| **Pillow** | `PIL` | Validação de magic bytes de imagens (PNG, JPG, JPEG), inspeção de metadados binários e geração de fixtures | `core/security.py`, `tests/test_image_ingestion.py` | **SIM** | **SIM** | Prevenção de ataques de sanitização e suporte multimodal. |
| **pandas** | `pandas` | Estruturação de dados tabulares, cálculo de conciliação contábil (PSL/Sinistros) e exportação analítica | `ui/page_compare.py`, `ui/page_report.py`, `ui/page_accounting.py` | **SIM** | **SIM** | Manipulação de métricas e visualização de tabelas analíticas. |
| **python-dotenv** | `dotenv` | Carregamento automático de variáveis de ambiente a partir de arquivos `.env` locais | `core/config.py` | **SIM** | **SIM** | Configuração semântica e carregamento seguro de chaves locais. |
| **pytest** | `pytest` | Framework de execução, fixtures e asserções da suíte de 182 testes automatizados | `tests/*` (22 arquivos de teste) | NÃO | **SIM** | Exclusivo para garantia de qualidade e regressão contínua. |
| **reportlab** | `reportlab` | Compilação de apólices D&O sintéticas fiéis às normas da SUSEP para testes locais independentes de LGPD | `data/generate_samples.py` | NÃO | **SIM** (Utilitário) | Permite criar massas de teste sem violar termos de confidencialidade. |
| **requests** | `requests` | Requisições HTTP utilitárias nos testes de automação e health check de QA | `scripts/qa_*.py` | NÃO | **SIM** (Scripts QA) | Dependência transitiva de `streamlit` e `google-genai`. |
| **websockets** | `websockets` | Protocolo de comunicação nos testes de CDP/Headless nos scripts de QA visual | `scripts/qa_*.py` | NÃO | **SIM** (Scripts QA) | Dependência transitiva do servidor ASGI/Uvicorn do Streamlit. |

---

## 3. Auditoria de Dependências Removidas / Desnecessárias

Durante a auditoria, identificou-se que o pacote **`sqlalchemy`** constava no `requirements.txt` anterior histórico, porém:
- O projeto adota nativamente o módulo `sqlite3` da biblioteca padrão do Python (`core/database.py`).
- Não existe uma única chamada ou importação a `sqlalchemy` em todo o código-fonte.
- **Ação corretiva:** O pacote `sqlalchemy` foi **removido** do `requirements.txt`, eliminando peso desnecessário e possíveis vulnerabilidades de pacotes secundários.

---

## 4. Dependências de Sistema Operacional (Non-Pip)

O motor de OCR local determinístico do projeto apoia-se na biblioteca `libtesseract` e em arquivos de dicionário de idioma:

- **Não instalável via pip:** O Tesseract OCR é uma dependência de sistema compilada em C/C++.
- **Mecanismo de Ligação:** O `PyMuPDF` (`fitz`) acessa diretamente os C-bindings de `libtesseract5` e lê os arquivos de modelo em `/usr/share/tessdata` (ou no caminho apontado pela variável `TESSDATA_PREFIX`).
- **Instruções de Instalação por Distribuição Linux:**
  - **openSUSE Tumbleweed / Leap:**
    `sudo zypper install tesseract-ocr tesseract-ocr-traineddata-por`
  - **Ubuntu / Debian:**
    `sudo apt-get install tesseract-ocr tesseract-ocr-por`
  - **Fedora / RHEL:**
    `sudo dnf install tesseract tesseract-langpack-por`
  - **Arch Linux:**
    `sudo pacman -S tesseract tesseract-data-por`

---

## 5. Análise de Transitividade e Reprodutibilidade

Ao instalar `requirements.txt` em um ambiente virtual novo, o `pip` resolve automaticamente as seguintes dependências transitivas estáveis:
- **Streamlit:** `altair`, `pyarrow`, `pydeck`, `tornado`, `uvicorn`, `starlette`, `watchdog`, `protobuf`.
- **LangGraph:** `langsmith`, `langchain-core`, `langgraph-checkpoint`.
- **Pydantic:** `pydantic-core`, `annotated-types`.
- **Google GenAI:** `google-auth`, `httpx`, `distro`.
- **PDFPlumber:** `pdfminer.six`, `pypdfium2`.

A política do projeto mantém o `requirements.txt` focado **estritamente nos pacotes diretos de primeiro nível**, evitando o travamento prematuro de transitivos (*over-pinning*) que prejudica atualizações de segurança do sistema operacional.
