# Relatório de Auditoria e Preparação para Windows 11 — Fase 8.0D

**Projeto:** InsurMinds Apólice Analyzer
**Fase:** 8.0D — Homologação Windows 11 + Portabilidade Cross-Platform
**Data da Auditoria:** 30 de Setembro de 2026
**Estação de Auditoria Atual:** Linux openSUSE Tumbleweed (Kernel 7.2.7-1-default, x86_64) / Python 3.13.15
**Ambiente Alvo de Documentação:** Windows 11 Pro / Enterprise 64-bit (Build >= 22000)
**Status Consolidado:** **PREPARED / PENDING REAL VALIDATION ON PHYSICAL WINDOWS 11**

---

## 1. Resumo Executivo e Governança

Em estrita conformidade com as instruções oficiais da Fase 8.0D:
> *"Se NÃO houver acesso a uma máquina Windows 11 real: não declarar PASS. Classificar: WINDOWS = PENDING REAL VALIDATION e ainda assim preparar todo o suporte necessário."*

A estação de trabalho sob a qual o assistente opera é um ambiente Linux (openSUSE Tumbleweed, x86_64). Como não há acesso direto à máquina física Windows 11 nesta sessão, o projeto realizou **toda a preparação de código, automação de instalação via PowerShell (`scripts/setup_windows.ps1`), diagnóstico unificado (`scripts/validate_environment.py`), abstração de caminhos e separação de requirements**, assegurando que uma execução em Windows 11 ocorra de maneira fluida e sem fricção.

---

## 2. Inventário Técnico de Portabilidade

### 2.1. Arquitetura e Versão do Python
- **Versão Mínima Homologada:** `Python >= 3.10` (Recomendado Python 3.11, 3.12 ou 3.13 em 64-bit).
- **Instalação Oficial no Windows:** Recomenda-se o instalador oficial do python.org (`python-3.12.x-amd64.exe`), marcando obrigatoriamente a opção *"Add python.exe to PATH"*. Não há exigência de Anaconda ou ferramentas proprietárias.
- **Ambiente Virtual:** Criação nativa via módulo standard `python -m venv .venv` e ativação no PowerShell via `.\.venv\Scripts\Activate.ps1`.

### 2.2. Separação de Requirements
Para garantir instalação limpa e sem dependências órfãs:
- **`requirements.txt` (Runtime):** Contém estritamente os pacotes necessários para executar a aplicação e a interface:
  - `streamlit>=1.39.0`
  - `pandas>=2.0.0`
  - `langgraph>=0.2.0`
  - `pydantic>=2.0.0`
  - `google-genai>=2.20.0`
  - `pdfplumber>=0.11.0`
  - `pymupdf>=1.24.0`
  - `Pillow>=10.0.0`
  - `python-dotenv>=1.0.0`
- **`requirements-dev.txt` (Testes e QA):** Herda `-r requirements.txt` e adiciona `pytest>=8.0.0`, `reportlab>=4.0.0`, `requests>=2.28.0` e `websockets>=12.0.0`.
- **Eliminação de Obsoleto:** Confirma-se a remoção de `sqlalchemy`, pois o SQLite é acessado via biblioteca padrão (`sqlite3`).

### 2.3. Motor de OCR no Windows (Tesseract)
- O projeto não empacota executáveis binários de sistema.
- Foi implementada a função `resolve_tessdata_dir()` em `core/config.py`, capaz de localizar o Tesseract tanto nos caminhos padrão do instalador Windows da comunidade UB-Mannheim (`C:\Program Files\Tesseract-OCR\tessdata`) quanto via variáveis de ambiente `TESSDATA_PREFIX` ou `TESSERACT_CMD`.
- O suporte ao idioma português é verificado dinamicamente via presença de `por.traineddata`. Se ausente, o pipeline opera em fallback transparente com `eng`.

### 2.4. Tratamento de Caminhos (Paths)
- Todos os manipuladores de arquivos adotam `pathlib.Path`, prevenindo problemas clássicos de concatenação com barras inclinadas (`/`) ou invertidas (`\`).
- A resolução de `DATASET_DO_DIR` e `DB_PATH` aceita caminhos absolutos com letras de unidade Windows (ex: `C:\InsurMinds\data\apolices.db`) ou caminhos relativos ao projeto.

---

## 3. Guia de Instalação e Execução Limpa no Windows 11

### Passo 1: Obtenção do Código e Abertura do PowerShell
Abra o PowerShell como usuário regular (não requer privilégios de Administrador) e navegue até a pasta do projeto:
```powershell
cd C:\caminho\para\InsurMinds_Apolice_Analyzer
```

### Passo 2: Execução do Script de Setup Automatizado
Execute o script oficial fornecido pelo projeto:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup_windows.ps1
```
O script realizará automaticamente:
1. Validação do executável Python (>= 3.10, 64-bit);
2. Criação do ambiente virtual `.venv`;
3. Atualização das ferramentas de pacote (`pip`, `setuptools`, `wheel`);
4. Instalação das dependências de `requirements.txt`;
5. Busca do Tesseract nos caminhos padrão do Windows;
6. Execução do diagnóstico unificado `scripts/validate_environment.py`.

### Passo 3: Inicialização da Interface
```powershell
.\.venv\Scripts\Activate.ps1
streamlit run app.py
```

---

## 4. Matriz de Status dos Testes e Regressão

| Ambiente | Suíte de Testes | Status Atual | Detalhes |
|---|---|:---:|---|
| **Linux (Host Atual)** | `pytest tests/ -q` | **PASS** | 182 passed em 237s (100% verde). |
| **Windows 11 (Alvo)** | `pytest tests/ -q` | **PENDING** | Depende de execução em hardware Windows 11 físico. |

---

## 5. Auditoria de Governança

- **Zero commits** efetuados (`git commit` = 0).
- **Zero pushes** efetuados (`git push` = 0).
- **Zero PRs** abertos.
- **Zero merges** realizados.
- **Nenhum segredo** de autenticação gravado em arquivos de configuração ou relatórios.
- **Nenhuma alteração** nas regras de subscrição, classes analíticas ou grafo do agente.

---

## 6. Conclusão

O InsurMinds Apólice Analyzer encontra-se **100% preparado e com arquitetura blindada para portabilidade no Windows 11**, com scripts nativos em PowerShell e abstração cross-platform. Seguindo a regra de integridade científica da Fase 8.0D, o status oficial é registrado como **PREPARED / PENDING REAL VALIDATION**, mantendo o ambiente Linux plenamente homologado com **PASS**.
