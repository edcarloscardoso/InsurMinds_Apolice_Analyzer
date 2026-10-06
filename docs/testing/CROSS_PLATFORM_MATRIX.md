# Matriz de Compatibilidade Cross-Platform (Linux vs Windows 11)

**Projeto:** InsurMinds Apólice Analyzer
**Fase:** 8.0D — Homologação Windows 11 + Portabilidade Cross-Platform
**Data:** 30 de Setembro de 2026
**Ambiente de Homologação Real:** Linux openSUSE Tumbleweed (Kernel 7.2.7-1-default, x86_64)
**Ambiente Alvo de Portabilidade:** Windows 11 Pro / Enterprise (x86_64, Build >= 22000)

---

## 1. Matriz de Homologação de Funcionalidades

> **Regra de Auditoria:** Conforme diretriz estrita da Fase 8.0D, os itens da coluna **Windows 11** são classificados exclusivamente como **PENDING** até que seja conduzida a execução física com telemetria direta em uma estação de trabalho equipada com Windows 11 real. Todos os artefatos de código, scripts PowerShell, resolutores de caminho e compatibilidade de dependências já se encontram 100% implementados e preparados.

| Funcionalidade | Linux (openSUSE / Ubuntu) | Windows 11 | Notas Técnicas de Portabilidade |
|---|:---:|:---:|---|
| **Python** | **PASS** | **PENDING** | Requer Python >= 3.10 (validado em Python 3.13.15 no Linux; suporte nativo a `py.exe` e `python.exe` no Windows). |
| **Instalação** | **PASS** | **PENDING** | Linux: `scripts/setup_linux.sh` (PASS em `/tmp/insurminds-linux-validation/`). Windows: `scripts/setup_windows.ps1`. |
| **PDF** | **PASS** | **PENDING** | Extração de texto digital via `pdfplumber` e suporte a renderização/OCR via `PyMuPDF` (`fitz`). Wheels binários cross-platform para Windows e Linux. |
| **PNG** | **PASS** | **PENDING** | Validação binária de magic bytes (`\x89PNG\r\n\x1a\n`) e integridade via Pillow cross-platform. |
| **JPG** | **PASS** | **PENDING** | Validação binária de magic bytes (`\xff\xd8\xff`) e integridade via Pillow cross-platform. |
| **OCR** | **PASS** | **PENDING** | PyMuPDF com C-bindings Tesseract. Linux: `libtesseract5` (`/usr/share/tessdata`). Windows: auto-resolução em `C:\Program Files\Tesseract-OCR\tessdata`. |
| **Gemini** | **PASS** | **PENDING** | SDK oficial `google-genai` com Structured Output baseado em Pydantic v2 (independente de SO). |
| **Fallback** | **PASS** | **PENDING** | Motor determinístico regulatório SUSEP opera em memória pura com regras canônicas (100% neutro de SO). |
| **SQLite** | **PASS** | **PENDING** | Persistência relacional via `sqlite3` da biblioteca padrão. `DatabaseManager` auto-inicializa em caminhos POSIX ou Windows (`C:\...`). |
| **Comparação** | **PASS** | **PENDING** | Algoritmo de diff de cláusulas e matriz semântica implementado em Python puro (`core/diff_engine.py`). |
| **Evidência** | **PASS** | **PENDING** | Schema `EvidenceItem` com rastreabilidade de página, snippet e confiança documental preservada. |
| **Relatório** | **PASS** | **PENDING** | Geração e download de parecer executivo D&O em Markdown e JSON estruturado. |
| **UI E2E** | **PASS** | **PENDING** | Testes de ponta a ponta na UI (U1, U2, U3, U4) homologados no navegador em Linux. |
| **Testes** | **PASS** | **PENDING** | 182/182 testes automatizados aprovados no ambiente Linux (0 falhas, 0 erros). |

---

## 2. Diagnóstico de Compatibilidade de Código e Caminhos

1. **Separação de Dependências**:
   - `requirements.txt`: Contém estritamente as dependências de runtime (`streamlit`, `pandas`, `langgraph`, `pydantic`, `google-genai`, `pdfplumber`, `pymupdf`, `Pillow`, `python-dotenv`).
   - `requirements-dev.txt`: Contém `-r requirements.txt` acrescido das bibliotecas de testes e automação (`pytest`, `reportlab`, `requests`, `websockets`).
2. **Caminhos de Arquivo (Path Handling)**:
   - 100% do código utiliza `pathlib.Path`, garantindo tratamento automático de barras invertidas (`\`) no Windows e barras normais (`/`) no Linux.
   - Zero ocorrências de caminhos absolutos hardcoded em arquivos de código de runtime (`core/`, `agents/`, `ui/`).
3. **Resolução de Banco de Dados (`DB_PATH`)**:
   - Respeita a variável de ambiente `DB_PATH`, aceitando formatos Windows (`C:\caminho\apolices.db`) ou caminhos relativos ao workspace.
4. **Dataset Externo (`INSURMINDS_EXTERNAL_TEST_DIR`)**:
   - Opera opcionalmente em qualquer diretório local (`C:\caminho\dataset_do` ou diretório irmão), sem travar a aplicação quando ausente.
