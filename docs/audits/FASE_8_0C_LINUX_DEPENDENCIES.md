# Auditoria de Dependências e Instalação Reproduzível em Linux — Fase 8.0C

**Projeto:** InsurMinds Apólice Analyzer
**Fase:** 8.0C — Dependency Audit + Linux Reproducible Install
**Data:** 30 de Setembro de 2026
**Ambiente de Homologação:** openSUSE Tumbleweed (Linux x86_64, Kernel 7.2.7)
**Interpretador Python:** Python 3.13.15
**Resultado Geral:** **PASS (HOMOLOGADO)**

---

## 1. Visão Geral da Fase

A Fase 8.0C teve por objetivo primordial comprovar a total independência do projeto em relação ao ambiente virtual original de desenvolvimento (`.venv/`), validando uma instalação reprodutível do zero em um ambiente Linux limpo e isolado (`/tmp/insurminds-linux-validation/`), com auditoria formal de todas as dependências, versionamento de runtime, motor de OCR, integridade de caminhos e validação completa dos 182 testes automatizados.

---

## 2. Dependências Auditadas e requirements.txt Oficial

O arquivo `requirements.txt` foi reestruturado e consolidado como fonte única e oficial de instalação para ambientes de produção e homologação:

```txt
# InsurMinds Apólice Analyzer — Dependências Oficiais (Runtime e Testes)
# Requisito de Sistema: Python >= 3.10

# Interface Web e Visualização
streamlit>=1.39.0
pandas>=2.0.0

# Orquestração Multi-Agente e Schemas Estruturados
langgraph>=0.2.0
pydantic>=2.0.0

# IA Generativa Oficial (Google Gemini SDK)
google-genai>=2.20.0

# Processamento de Documentos (PDF, Imagens e OCR Nativo)
pdfplumber>=0.11.0
pymupdf>=1.24.0
Pillow>=10.0.0

# Configuração e Ambiente
python-dotenv>=1.0.0

# Framework de Testes Automatizados
pytest>=8.0.0

# Utilitário de Compilação de Apólices Sintéticas D&O (data/generate_samples.py)
reportlab>=4.0.0
```

### Remoção de Dependência Obsoleta
- **`sqlalchemy`**: Removido integralmente. O projeto adota `sqlite3` nativo da biblioteca padrão do Python em `core/database.py`, garantindo persistência sem overhead de ORMs externos.

---

## 3. Versão Mínima do Python

- **Declaração Oficial:** **`Python >= 3.10`**
- **Justificativa Técnica:**
  - O SDK oficial `google-genai` (v2.20+) e o `langgraph` exigem no mínimo Python 3.10 devido ao uso extensivo de recursos sintáticos modernos (como tipagem com operador `|`, `typing.TypeAlias` e suporte avançado de introspecção assíncrona).
  - Validado e homologado no ambiente Linux atual sob **Python 3.13.15**.

---

## 4. Dependência de Sistema para OCR (Tesseract)

- **Instalação Não-Pip:** O Tesseract OCR é uma biblioteca compilada de sistema (`libtesseract5`).
- **Mecanismo Integrado:** O pipeline utiliza os C-bindings do `PyMuPDF` (`fitz`), que se conectam diretamente a `libtesseract.so.5` e leem os arquivos de dados em `/usr/share/tessdata/` sem requerer o pacote auxiliar `pytesseract`.
- **Comandos de Instalação Documentados:**
  - **openSUSE Tumbleweed:** `sudo zypper install tesseract-ocr tesseract-ocr-traineddata-por`
  - **Ubuntu / Debian:** `sudo apt-get install tesseract-ocr tesseract-ocr-por`
  - **Fedora / RHEL:** `sudo dnf install tesseract tesseract-langpack-por`
  - **Arch Linux:** `sudo pacman -S tesseract tesseract-data-por`
- **Configuração Automática de Variável:** O sistema configura automaticamente `TESSDATA_PREFIX=/usr/share/tessdata` caso a pasta padrão de idiomas esteja presente no sistema operacional.

---

## 5. Instalação e Teste em Ambiente Limpo (/tmp)

A simulação de instalação do zero foi executada com sucesso estrito:
1. **Criação do Venv Isolado:** `python3 -m venv /tmp/insurminds-linux-validation/`
2. **Atualização de Ferramentas:** `pip install --upgrade pip setuptools wheel`
3. **Instalação dos Requisitos:** `pip install -r requirements.txt` (Instalação concluída com sucesso em 28 segundos).
4. **Validação do Ambiente:** `scripts/validate_environment.py` executado com código de retorno 0.

---

## 6. Validação Funcional no Ambiente Limpo

Dentro de `/tmp/insurminds-linux-validation/`, foram executadas e validadas todas as operações críticas do sistema:
- **Streamlit Server:** Inicializou com sucesso na porta 8505 com status HTTP 200 retornado pelo healthcheck oficial (`/_stcore/health`). Versão: **Streamlit 1.64.0**.
- **Processamento de PDF:** Executou `run_document_pipeline_with_progress` em `apolice_do_aig.pdf` (identificou AIG Seguros Brasil S.A. e 9 coberturas).
- **Processamento de Imagem:** Ingestão de imagem PNG com extração via OCR local determinístico PyMuPDF.
- **Confronto Contratual:** Execução de `compare_policies` gerando FieldDiffs e score de similaridade com sucesso.
- **Evidências Contratuais:** Instanciação e auditoria de `EvidenceItem` com snippet literal, número de página e pontuação de confiança.
- **Banco de Dados SQLite:** Comprovado que `data/apolices.db` não é pré-requisito estático; o `DatabaseManager` inicializa o esquema relacional e todas as 4 tabelas automaticamente a partir do zero em qualquer caminho informado por `DB_PATH`.

---

## 7. Status do Google Gemini e Contingência

- **Configurado:** Suporta autenticação limpa via `GOOGLE_API_KEY` carregada em memória a partir de `.env` ou variável de ambiente.
- **Sem Chave (Contingência):** A aplicação inicia normalmente, emite banner discreto de modo determinístico, preserva 100% da usabilidade e executa a comparação e estruturação por regras regulatórias da SUSEP sem exceções ou interrupções abruptas.
- **Segurança de Credenciais:** Nenhuma chave de API ou segredo foi gravado em logs, relatórios ou versionamento.

---

## 8. Saneamento de Caminhos (Paths)

- **Pesquisa Rigorosa:** Realizada busca por padrões `/home/`, `/Users/`, `/Desktop/`, `/Documents/`, `/mnt/` e `C:\` em todos os diretórios de código (`core/`, `agents/`, `ui/`, `tests/`, `app.py`).
- **Remoção Concluída:** O caminho absoluto presente anteriormente em `core/config.py` para o dataset de teste foi substituído por resolução dinâmica baseada na variável `INSURMINDS_EXTERNAL_TEST_DIR` com fallback estrutural relativo para o diretório de documentos irmão (`desafio_final_docs/dataset_do/documentos`) ou relativo local (`data/dataset_do`).
- **Resultado:** Zero caminhos absolutos específicos da máquina de desenvolvimento na lógica de execução.

---

## 9. Dataset Externo Opcional

- A aplicação funciona integralmente mesmo na ausência de `INSURMINDS_EXTERNAL_TEST_DIR`.
- Os testes que utilizam documentos externos executam a cláusula `@pytest.mark.skipif` de forma graciosa e defensiva quando o corpus externo não estiver montado.

---

## 10. Matriz de Cumprimento dos Critérios de Aceite

| Critério de Aceite | Requisito Oficial | Evidência Técnica | Status |
|:---|:---|:---|:---:|
| **requirements auditado** | Auditoria e higienização do manifest | `requirements.txt` sem pacotes redundantes (ex: `sqlalchemy`) | **PASS** |
| **dependências runtime** | Identificação dos pacotes de execução | `streamlit`, `langgraph`, `google-genai`, `pdfplumber`, etc. | **PASS** |
| **dependências teste** | Identificação dos pacotes de QA/Dev | `pytest`, `reportlab`, `requests`, `websockets` | **PASS** |
| **Python mínimo** | Determinação técnica do Python mínimo | `Python >= 3.10` homologado em Python 3.13.15 | **PASS** |
| **Tesseract documentado** | Instruções de instalação em Linux | Documentado para openSUSE, Ubuntu, Fedora e Arch | **PASS** |
| **validate_environment.py** | Script autônomo de diagnóstico | Criado em `scripts/validate_environment.py` (Exit code 0) | **PASS** |
| **setup_linux.sh** | Script de automação de instalação | Criado e testado em `scripts/setup_linux.sh` | **PASS** |
| **ambiente limpo criado** | Criação de venv isolado fora do projeto | `/tmp/insurminds-linux-validation/` | **PASS** |
| **requirements do zero** | Instalação limpa via pip | Executado com sucesso em venv limpo | **PASS** |
| **Streamlit iniciou** | Execução do servidor web | Streamlit 1.64.0 executado na porta 8505 | **PASS** |
| **health OK** | Endpoint de integridade da UI | HTTP 200 OK retornado em `/_stcore/health` | **PASS** |
| **PDF OK** | Ingestão e extração de PDF | AIG PDF processado com 9 coberturas | **PASS** |
| **imagem OK** | Ingestão de imagem | Imagem PNG processada com sucesso | **PASS** |
| **OCR OK** | Extração de texto por visão | Tesseract via PyMuPDF C-bindings funcional | **PASS** |
| **comparação OK** | Confronto analítico de apólices | `compare_policies` validado no venv limpo | **PASS** |
| **evidência OK** | Estruturação de `EvidenceItem` | Snippet, página e confiança auditados | **PASS** |
| **Gemini configurável** | Validação com/sem chave | Detecção dinâmica sem expor segredos | **PASS** |
| **fallback sem Gemini** | Modo de contingência determinístico | Operacional com regras regulatórias | **PASS** |
| **paths saneados** | Zero caminhos absolutos hardcoded | Resolvido dinamicamente em `core/config.py` e testes | **PASS** |
| **dataset opcional** | Funcionamento sem ENV obrigatório | App inicia e opera normalmente | **PASS** |
| **testes verdes** | 182 testes executados no venv limpo | 182/182 testes aprovados | **PASS** |
| **nenhum segredo** | Chaves e tokens preservados | Zero exposição de API Keys | **PASS** |
| **zero commit/push/PR/merge** | Governança de Git estritamente respeitada | Zero commits, zero pushes, zero PRs, zero merges | **PASS** |

---

## 11. Conclusão

A Fase 8.0C cumpriu com rigor todos os requisitos de auditoria de dependências, portabilidade de caminhos e reprodutibilidade de instalação em sistemas Linux. O projeto InsurMinds Apólice Analyzer atinge o status de **PASS (APROVADO)**.
