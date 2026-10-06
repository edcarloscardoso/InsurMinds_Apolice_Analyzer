# Contrato de Ambiente de Execução & Portabilidade Cross-Platform
## InsurMinds Apólice Analyzer

**Versão do Contrato:** 1.0.0 (Fase 8.0E — Consolidação de Ambiente)
**Data:** 30 de Setembro de 2026
**Status do Contrato:** HOMOLOGADO (Linux x86_64) | PREPARADO / PENDING (Windows 11 x86_64)
**Governança:** Contrato imutável de runtime sem acoplamento a caminhos locais ou segredos.

---

## 1. Escopo & Objetivos do Contrato

Este documento estabelece o **contrato formal de infraestrutura, dependências e ambiente de execução** do InsurMinds Apólice Analyzer. Qualquer estação de trabalho, contêiner ou pipeline de CI/CD que atenda aos requisitos aqui descritos executará o sistema sem divergências comportamentais entre **Linux (POSIX)** e **Windows 11 (NT)**.

---

## 2. Requisitos de Sistema Operacional & Arquitetura

| Parâmetro | Linux (Homologado) | Windows 11 (Preparado) |
|---|---|---|
| **Família de SO** | Linux Kernel >= 5.15 (openSUSE, Ubuntu, Debian, Fedora, Arch) | Windows 11 Pro / Enterprise / Home (Build >= 22000) |
| **Arquitetura** | `x86_64` (64-bit obrigatório) | `x86_64` / `AMD64` (64-bit obrigatório) |
| **Shell Padrão** | `bash` / `zsh` | `PowerShell 5.1+` ou `PowerShell Core 7+` |
| **Privilégios** | Usuário padrão (não requer `root` para execução) | Usuário padrão (não requer Administrador para execução) |

> **Nota de Arquitetura:** Arquiteturas de 32 bits (`x86`) **não são suportadas** devido a restrições de paginação de memória dos C-bindings do PyMuPDF e buffers de tensores de imagem no Pillow.

---

## 3. Especificação do Interpretador Python

- **Versão Mínima Obrigatória:** `Python >= 3.10`
  - *Justificativa Técnica:* Requer suporte a *Structural Pattern Matching* (`match/case`), anotações de tipo PEP 604 (`X | Y`), modelos Pydantic v2 e grafo de estados compilado do `langgraph`.
- **Versões Recomendadas:** `Python 3.11`, `3.12` ou `3.13` (64-bit).
- **Ambiente de Homologação Real:** Python `3.13.15` (openSUSE Tumbleweed, x86_64).
- **Ambiente Virtual:** Uso obrigatório de `venv` limpo (`python -m venv .venv`).
  - Não utilizar distribuições Conda/Anaconda para execução padrão do contrato.

---

## 4. Contrato de Dependências Python (PIP)

O projeto adota uma segregação estrita entre dependências de execução (*runtime*) e ferramentas de suporte (*development/testing*).

### 4.1. Runtime Oficial (`requirements.txt`)

Total de **9 pacotes diretos de primeiro nível**. Zero dependências supérfluas.

| Pacote | Versão Mínima | Finalidade Técnica no Sistema | Módulo Importado |
|---|---|---|---|
| **streamlit** | `>=1.39.0` | Servidor de aplicação web reativa, páginas multipage, widgets analíticos | `import streamlit as st` |
| **pandas** | `>=2.0.0` | Estruturação de dados tabulares, conciliação contábil (PSL) e dataframes | `import pandas as pd` |
| **langgraph** | `>=0.2.0` | Orquestração da máquina de estados finita multi-agente | `from langgraph.graph import StateGraph` |
| **pydantic** | `>=2.0.0` | Validação estrita de contratos de dados e Structured Output de IA | `from pydantic import BaseModel, Field` |
| **google-genai** | `>=2.20.0` | SDK oficial do Google Gemini 2.0 (LLM e Multimodal Vision) | `from google import genai` |
| **pdfplumber** | `>=0.11.0` | Motor primário de extração de texto digital de apólices em PDF | `import pdfplumber` |
| **pymupdf** | `>=1.24.0` | Conversão de PDF/imagem e motor de OCR local via C-bindings | `import pymupdf as fitz` |
| **Pillow** | `>=10.0.0` | Validação de magic bytes binários de imagens (PNG, JPG, JPEG) | `from PIL import Image` |
| **python-dotenv** | `>=1.0.0` | Carregamento resiliente de variáveis de ambiente de arquivos `.env` | `from dotenv import load_dotenv` |

### 4.2. Desenvolvimento, Testes e QA (`requirements-dev.txt`)

Herda o runtime (`-r requirements.txt`) e adiciona estritamente:

| Pacote | Versão Mínima | Finalidade Técnica | Módulo Importado |
|---|---|---|---|
| **pytest** | `>=8.0.0` | Execução da suíte completa de 182 testes automatizados | `import pytest` |
| **reportlab** | `>=4.0.0` | Gerador determinístico de apólices D&O sintéticas (`generate_samples.py`) | `import reportlab` |
| **requests** | `>=2.28.0` | Requisições HTTP em testes de health-check e validação de rotas | `import requests` |
| **websockets** | `>=12.0.0` | Comunicação via Chrome DevTools Protocol (CDP) em testes E2E | `import websockets` |

### 4.3. Esclarecimento Sobre o Pacote `pypdfium2`

- O pacote `pypdfium2` **NÃO é uma dependência direta do InsurMinds Apólice Analyzer**.
- Nenhuma linha de código em `core/`, `agents/`, `ui/`, `scripts/` ou `tests/` importa `pypdfium2`.
- O `pypdfium2` é resolvido de forma estritamente interna e transitiva pelo `pdfplumber` (usado internamente em `Page.to_image()`).
- O stack de renderização e OCR direto do InsurMinds baseia-se exclusivamente em **`pdfplumber` + `PyMuPDF` (`fitz`)**.

---

## 5. Contrato do Motor de OCR (Tesseract / PyMuPDF)

O sistema possui uma rota de extração híbrida para imagens escaneadas e documentos digitalizados:

```
[Documento Ingerido]
        │
        ├── (PDF Digital) ─────────► pdfplumber (Extração Direta)
        │
        └── (Imagem / PDF Escaneado)
                │
                ├── [Com Chave Gemini] ──► Google Gemini Multimodal Vision
                │
                └── [Sem Chave / Offline] ─► PyMuPDF C-bindings (Tesseract Local)
                                                    │
                                                    ▼
                                            resolve_tessdata_dir()
                                                    │
                                                    ├── Linux:   /usr/share/tessdata
                                                    └── Windows: C:\Program Files\Tesseract-OCR\tessdata
```

### 5.1. Separação de Responsabilidades

1. **Camada Python:** `pymupdf` (C-bindings para `libtesseract`) + `Pillow` (manipulação de buffers de imagem).
2. **Camada de Sistema Operacional (Binários e Modelos):**
   - **Linux:** Pacotes de sistema da distribuição:
     - openSUSE: `tesseract-ocr`, `tesseract-ocr-traineddata-por`
     - Ubuntu/Debian: `tesseract-ocr`, `tesseract-ocr-por`
     - Fedora: `tesseract`, `tesseract-langpack-por`
     - Arch: `tesseract`, `tesseract-data-por`
   - **Windows 11:**
     - Instalador oficial UB-Mannheim (64-bit) com pacote de idioma Português (*por*).
     - Local padrão: `C:\Program Files\Tesseract-OCR\`

### 5.2. Resolução Dinâmica de Idioma e Caminho

Implementada em `core/config.py`:
- `resolve_tessdata_dir()`: Localiza a pasta `tessdata` inspecionando `TESSDATA_PREFIX`, `TESSERACT_CMD`, caminhos padrão do Windows e caminhos POSIX do Linux.
- `get_ocr_language()`: Retorna `"por+eng"` se o arquivo `por.traineddata` for detectado; caso contrário, opera com segurança em `"eng"`.
- **Resiliência:** Se nenhum binário ou tessdata for encontrado no sistema, a aplicação **NÃO quebra**. O ExtractorAgent redireciona automaticamente para o fallback heurístico determinístico com warning transparente.

---

## 6. Contrato de Inteligência Artificial (Google Gemini)

- **Variável de Controle:** `GOOGLE_API_KEY`
- **Obrigatoriedade:** **OPCIONAL**.
- **Comportamento Sem Chave:**
  - O sistema opera 100% funcional em **Modo de Contingência Determinístico Local**.
  - As regras analíticas de D&O (Circular SUSEP 637/2021) são processadas por heurísticas canônicas pré-calibradas.
  - A inicialização do Streamlit e a navegação entre todas as abas ocorrem normalmente.
- **Comportamento Com Chave:**
  - O sistema utiliza `gemini-flash-lite-latest` via SDK oficial `google-genai` com *Structured Output* baseado em `pydantic`.
- **Segurança de Chaves e Segredos:**
  - A chave é lida da memória (`os.getenv`) e **NUNCA** é gravada no banco SQLite `apolices.db`.
  - Scripts de diagnóstico (`validate_environment.py`) reportam apenas a presença ou ausência da chave (mascarada com contagem de caracteres), nunca o valor.
  - Arquivos `.env` e `.env.local` constam expressamente no `.gitignore`.

---

## 7. Contrato de Persistência Relacional (SQLite)

- **Variável de Controle:** `DB_PATH`
- **Padrão:** `<BASE_DIR>/data/apolices.db`
- **Mecanismo:** Biblioteca padrão do Python (`sqlite3`). Zero ORMs externos pesados.
- **Portabilidade de Caminhos:**
  - O `DatabaseManager` (`core/database.py`) recebe qualquer caminho do tipo `Path` ou `str`, seja relativo ou absoluto com letras de unidade Windows (`C:\...` ou `D:\...`).
  - Cria automaticamente os diretórios pais necessários (`parent.mkdir(parents=True, exist_ok=True)`).
  - Executa migrações automáticas de schema DDL caso o arquivo de banco não exista.

---

## 8. Contrato de Dataset Externo (Opcional)

- **Variável de Controle:** `INSURMINDS_EXTERNAL_TEST_DIR` (ou `DATASET_DO_DIR`)
- **Obrigatoriedade:** **OPCIONAL**.
- **Comportamento:**
  - Caso configurada e apontando para um diretório válido contendo apólices reais D&O, o sistema indexa e disponibiliza os documentos para validação.
  - Caso ausente, o sistema opera plenamente com o diretório interno `data/sample_policies/` contendo apólices sintéticas homologadas.
- **Exemplos de Configuração:**
  - Linux: `export INSURMINDS_EXTERNAL_TEST_DIR="/home/usuario/dataset_do"`
  - Windows: `$env:INSURMINDS_EXTERNAL_TEST_DIR = "C:\InsurMinds\dataset_do"`

---

## 9. Tabela Canônica de Variáveis de Ambiente

| Variável | Tipo | Padrão | Obrigatória? | Descrição |
|---|---|---|:---:|---|
| `GOOGLE_API_KEY` | String | `""` (vazio) | Não | Chave de acesso à API do Google Gemini. Ativa o modo LLM/Vision. |
| `DB_PATH` | Path | `data/apolices.db` | Não | Localização do arquivo de banco de dados SQLite. |
| `INSURMINDS_EXTERNAL_TEST_DIR` | Path | Auto-detect / `None` | Não | Diretório de corpus externo para homologação de documentos D&O. |
| `TESSERACT_CMD` | Path | Auto-detect | Não | Caminho explícito para o executável `tesseract` / `tesseract.exe`. |
| `TESSDATA_PREFIX` | Path | Auto-detect | Não | Caminho explícito para o diretório contendo os arquivos `.traineddata`. |
| `MAX_FILE_SIZE_MB` | Inteiro | `50` | Não | Limite máximo de tamanho por documento ingerido (MB). |
| `SERVER_PORT` | Inteiro | `8503` | Não | Porta TCP de vinculação do servidor Streamlit. |
| `LOG_LEVEL` | String | `INFO` | Não | Nível de detalhamento de log (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |

---

## 10. Scripts de Automação & Validação

| Script | Sistema Alvo | Descrição & Garantias |
|---|---|---|
| `scripts/setup_linux.sh` | Linux (bash) | Verifica Python >= 3.10, cria `.venv`, instala `requirements.txt`, detecta Tesseract e executa validação. |
| `scripts/setup_windows.ps1` | Windows 11 (PowerShell) | Verifica `py`/`python`, cria `.venv`, instala `requirements.txt`, localiza Tesseract em caminhos padrão e executa validação. |
| `scripts/validate_environment.py` | Cross-Platform | Diagnóstico unificado em 8 etapas com saída padronizada `PASS / WARNING / BLOCKER`. |

---

## 11. Comandos de Inicialização & Testes

### Linux
```bash
# 1. Configuração e Instalação
bash scripts/setup_linux.sh

# 2. Ativação
source .venv/bin/activate

# 3. Execução dos Testes Automatizados (182 testes)
pytest tests/ -q

# 4. Inicialização da Aplicação
streamlit run app.py
```

### Windows 11 (PowerShell)
```powershell
# 1. Configuração e Instalação
.\scripts\setup_windows.ps1

# 2. Ativação
.\.venv\Scripts\Activate.ps1

# 3. Execução dos Testes Automatizados
pytest tests/ -q

# 4. Inicialização da Aplicação
streamlit run app.py
```
