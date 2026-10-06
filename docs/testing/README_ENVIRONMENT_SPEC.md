# Especificação de Ambiente & Guia de Instalação (README Specification)
## InsurMinds Apólice Analyzer

> **Nota de Fase:** Este artefato é a especificação formal e definitiva das seções de ambiente, instalação, configuração e execução que serão incorporadas ao `README.md` principal na **Fase 8.0F**.

---

## 🛠️ Pré-requisitos de Sistema

O InsurMinds Apólice Analyzer foi projetado com arquitetura cross-platform nativa, homologado no Linux e preparado com suporte nativo para Windows 11.

| Componente | Requisito Mínimo | Recomendado | Notas |
|---|---|---|---|
| **Sistema Operacional** | Linux x86_64 / Windows 11 x86_64 | Linux (openSUSE, Ubuntu 22.04+) / Windows 11 23H2+ | Arquitetura 64-bit obrigatória. |
| **Python** | Python 3.10 | Python 3.11, 3.12 ou 3.13 (64-bit) | Requer PEP 604, Pydantic v2 e LangGraph. |
| **Ambiente Virtual** | `venv` padrão | `venv` isolado | Evite ambientes Anaconda/Conda. |
| **OCR (Tesseract)** | Opcional (possui fallback) | Tesseract 5.x com modelo em Português (`por`) | C-bindings via PyMuPDF com detecção automática. |
| **Google Gemini** | Opcional (possui fallback) | Chave de API Google AI Studio ativa | Executa em contingência determinística sem chave. |

---

## 🚀 Instalação Rápida (Quickstart)

### Opção A: Linux (Instalação Automatizada)

O projeto disponibiliza um script reproduzível que cria o ambiente virtual, instala as dependências auditadas e valida o sistema:

```bash
# 1. Clone ou acesse o repositório
cd InsurMinds_Apolice_Analyzer

# 2. Execute o assistente de instalação
bash scripts/setup_linux.sh

# 3. Ative o ambiente virtual
source .venv/bin/activate

# 4. Inicie o servidor Streamlit
streamlit run app.py
```

*(Opcional — Tesseract no Linux):*
- **openSUSE:** `sudo zypper install tesseract-ocr tesseract-ocr-traineddata-por`
- **Ubuntu/Debian:** `sudo apt-get install tesseract-ocr tesseract-ocr-por`
- **Fedora:** `sudo dnf install tesseract tesseract-langpack-por`

---

### Opção B: Windows 11 (Instalação via PowerShell)

No Windows 11, execute o script PowerShell nativo sem modificar configurações globais:

```powershell
# 1. Abra o PowerShell no diretório do projeto
cd InsurMinds_Apolice_Analyzer

# 2. Execute o assistente de instalação (permita execução se necessário)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup_windows.ps1

# 3. Ative o ambiente virtual
.\.venv\Scripts\Activate.ps1

# 4. Inicie o servidor Streamlit
streamlit run app.py
```

*(Opcional — Tesseract no Windows):*
1. Baixe o instalador oficial de 64 bits: [UB-Mannheim Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki).
2. Durante a instalação, marque a opção **"Additional language data (download) -> Portuguese"**.
3. O InsurMinds detectará o executável automaticamente em `C:\Program Files\Tesseract-OCR\`.

---

## ⚙️ Configuração de Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto (ou configure as variáveis no seu shell). **Nenhuma variável é estritamente obrigatória** para inicializar o sistema:

```ini
# ==============================================================================
# InsurMinds Apólice Analyzer — Configuração de Ambiente
# ==============================================================================

# [Opcional] Chave oficial do Google Gemini 2.0 (LLM e Multimodal Vision)
# Se ausente, o sistema opera 100% via heurísticas determinísticas SUSEP locais.
GOOGLE_API_KEY=sua_chave_aqui

# [Opcional] Modelo LLM utilizado (Padrão: gemini-flash-lite-latest)
GEMINI_MODEL=gemini-flash-lite-latest
GEMINI_VISION_MODEL=gemini-flash-lite-latest

# [Opcional] Caminho do Banco de Dados SQLite (Padrão: data/apolices.db)
# Linux:   ./data/apolices.db
# Windows: C:\InsurMinds\data\apolices.db
DB_PATH=data/apolices.db

# [Opcional] Diretório de Corpus Externo de Apólices D&O Reais
# INSURMINDS_EXTERNAL_TEST_DIR=/caminho/para/dataset_do

# [Opcional] Porta do servidor Streamlit (Padrão: 8503)
SERVER_PORT=8503
```

---

## 🩺 Diagnóstico Unificado do Ambiente

Para auditar seu sistema e garantir que todos os componentes (SO, Python, dependências, OCR, SQLite e Gemini) estão operando em conformidade:

```bash
# Linux
python scripts/validate_environment.py

# Windows
python .\scripts\validate_environment.py
```

O utilitário emitirá um relatório estruturado com veredito padronizado:
- **`[PASS]`**: Sistema 100% calibrado e operacional.
- **`[WARNING]`**: Operação assegurada com contingência ativada (ex.: chave Gemini não informada ou Tesseract CLI ausente).
- **`[BLOCKER]`**: Ausência de pacote crítico ou Python < 3.10.

---

## 🧪 Execução dos Testes Automatizados

O sistema conta com uma suíte de testes robusta composta por **182 testes automatizados** cobrindo ingestão, OCR, schemas regulatórios SUSEP, diff semântico e conciliação contábil:

```bash
# Execução rápida (modo silencioso)
pytest tests/ -q

# Execução detalhada com relatório de cobertura
pytest tests/ -v
```

---

## 📦 Matriz de Dependências Auditadas

### Runtime (`requirements.txt`)
- `streamlit>=1.39.0`: Interface e visualizações analíticas.
- `pandas>=2.0.0`: Manipulação de dataframes e conciliação contábil (PSL).
- `langgraph>=0.2.0`: Máquina de estados finita do pipeline multi-agente.
- `pydantic>=2.0.0`: Validação de esquemas e Structured Output.
- `google-genai>=2.20.0`: SDK oficial do Google Gemini 2.0.
- `pdfplumber>=0.11.0`: Extração primária de texto digital em PDFs.
- `pymupdf>=1.24.0`: Conversão de formatos, renderização e OCR determinístico local.
- `Pillow>=10.0.0`: Validação binária de segurança (magic bytes).
- `python-dotenv>=1.0.0`: Carregamento seguro de configurações.

### Desenvolvimento e Testes (`requirements-dev.txt`)
- `-r requirements.txt`: Herança integral do runtime.
- `pytest>=8.0.0`: Motor de testes unitários e de integração.
- `reportlab>=4.0.0`: Gerador sintético de apólices D&O.
- `requests>=2.28.0` & `websockets>=12.0.0`: Automação de QA e telemetria CDP.
