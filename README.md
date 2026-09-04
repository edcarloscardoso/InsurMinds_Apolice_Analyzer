# InsurMinds Apólice Analyzer
**Plataforma Inteligente para Análise e Comparação de Apólices D&O**  
*Trabalho de Conclusão de Curso · I2A2 — Instituto de Inteligência Artificial Aplicada (2026)*

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/Orquestra%C3%A7%C3%A3o-LangGraph-orange)](https://github.com/langchain-ai/langgraph)
[![Streamlit](https://img.shields.io/badge/Interface-Streamlit-red)](https://streamlit.io/)
[![Google Gemini](https://img.shields.io/badge/LLM-Gemini%202.0%20Flash-blue)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📌 1. Visão Geral do Produto

Apólices de seguro **D&O (Directors & Officers)** são contratos corporativos extensos (30 a 80 páginas), redigidos em linguagem jurídica densa. Comparar manualmente propostas de diferentes seguradoras consome horas de trabalho especializado de corretores, advogados ou conselhos de administração.

O **InsurMinds Apólice Analyzer** automatiza o ciclo completo de:
1. **Ingestão & Validação**: Checagem de segurança (magic bytes `%PDF-`), integridade e deduplicação (idempotência por hash MD5).
2. **Extração Híbrida**: Extração de texto digital via `pdfplumber` com fallback multimodal inteligente via **Gemini 2.0 Flash Vision** para documentos escaneados.
3. **Estruturação Canônica**: Conversão em esquemas tipados via Pydantic v2 (`ApoliceDAO`).
4. **Armazenamento Relacional**: Banco de dados SQLite (`apolices.db`) com transações seguras.
5. **Comparação Analítica**: Motor determinístico e cálculo de Índice de Similaridade Composto (Jaccard ponderado) para identificar coberturas exclusivas e divergências financeiras.
6. **Parecer Executivo**: Síntese narrativa de alto padrão gerada por IA com recomendações de contratação.

---

## 🏗️ 2. Arquitetura Multi-Agente (LangGraph)

O fluxo é orquestrado através de um grafo de estados composto por **6 agentes inteligentes**:

```
[ PDF Upload ] ──► [ 1. Reception Agent ] ──► [ 2. Extractor Agent ] ──► [ 3. Identifier Agent ]
                                                                                   │
[ Parecer Executivo ] ◄── [ 6. Reporter Agent ] ◄── [ 5. Comparator Agent ] ◄── [ 4. Structurer Agent ]
                                                                                   │
                                                                           [ SQLite Database ]
```

---

## 🚀 3. Instalação e Execução

### Pré-requisitos
- Python 3.12 ou superior instalado.

### Passo 1: Clonar o Repositório
```bash
git clone https://github.com/seu-usuario/insurminds_apolice_analyzer.git
cd insurminds_apolice_analyzer
```

### Passo 2: Criar e Ativar Ambiente Virtual
```bash
python3 -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate
```

### Passo 3: Instalar Dependências
```bash
pip install -r requirements.txt
```

### Passo 4: Configurar Variáveis de Ambiente (Opcional)
Copie o arquivo `.env.example` para `.env` e configure sua chave do Google Gemini (caso deseje utilizar a API externa em tempo real):
```bash
cp .env.example .env
```
> **Nota de Resiliência:** Caso você não possua uma chave da API do Gemini configurada, o sistema aciona automaticamente o **Modo de Contingência Heurístico**, permitindo a execução e demonstração de 100% dos fluxos sem erros.

### Passo 5: Iniciar a Aplicação Streamlit
```bash
streamlit run app.py --server.address 127.0.0.1
```
Acesse a aplicação no navegador em: `http://localhost:8501`.

---

## 🧪 4. Execução dos Testes Automatizados

O projeto possui uma suíte completa de testes unitários e de integração cobrindo esquemas, segurança, banco de dados, motor de comparação e pipeline dos agentes:

```bash
pytest -v
```

---

## 📂 5. Estrutura do Repositório

```
insurminds_apolice_analyzer/
├── .env.example                       # Modelo de variáveis de ambiente
├── .gitignore                         # Exclusão de arquivos sensíveis e temporários
├── README.md                          # Documentação completa do projeto
├── requirements.txt                   # Dependências do projeto
├── app.py                             # Entrada da aplicação Streamlit
├── core/                              # Módulo central de lógica e dados
│   ├── config.py                      # Configurações de ambiente e diretórios
│   ├── schemas.py                     # Contratos canônicos Pydantic v2
│   ├── security.py                    # Validação de magic bytes e sanitização
│   ├── database.py                    # Persistência relacional SQLite e idempotência
│   ├── diff_engine.py                 # Motor de diff determinístico e score Jaccard
│   └── llm_client.py                  # Integração Gemini 2.0 Flash + Contingência
├── agents/                            # Orquestração multi-agente LangGraph
│   ├── graph.py                       # StateGraph e fluxos de execução
│   ├── reception_agent.py             # Agente 1: Recepção e validação
│   ├── extractor_agent.py             # Agente 2: Extração híbrida (pdfplumber + Vision)
│   ├── identifier_agent.py            # Agente 3: Segmentação de cláusulas
│   ├── structurer_agent.py            # Agente 4: Estruturação e persistência
│   ├── comparator_agent.py            # Agente 5: Confronto analítico
│   └── reporter_agent.py              # Agente 6: Parecer executivo narrativo
├── ui/                                # Interface do Usuário (Streamlit)
│   ├── styles.py                      # Estilos executivos customizados (CSS)
│   ├── page_upload.py                 # Tela 1: Ingestão de PDFs e timeline de agentes
│   ├── page_library.py                # Tela 2: Biblioteca de apólices e catálogo
│   ├── page_compare.py                # Tela 3: Matriz comparativa de campos e gap analysis
│   └── page_report.py                 # Tela 4: Parecer executivo com exportação
├── data/                              # Dados e amostras
│   ├── sample_policies/               # PDFs sintéticos de alta fidelidade
│   ├── generate_samples.py            # Compilador de apólices D&O (ReportLab)
│   └── apolices.db                    # Banco de dados SQLite local
├── tests/                             # Suíte de testes automatizados (pytest)
│   ├── test_schemas.py                # Testes de modelos e validações Pydantic
│   ├── test_security.py               # Testes de sanitização, magic bytes e limites
│   ├── test_database.py               # Testes de operações CRUD e idempotência
│   ├── test_diff_engine.py            # Testes do motor analítico de comparação
│   └── test_pipeline_integration.py   # Testes de integração end-to-end dos agentes
└── Projeto_Final_Artefatos/           # Entregáveis acadêmicos para a banca I2A2
    ├── RELATORIO_TECNICO.md           # Relatório técnico completo de conclusão de curso
    ├── ARQUITETURA.md                 # Arquitetura detalhada e diagrama de dados
    ├── DICIONARIO_DADOS.md            # Dicionário de dados canônico
    └── APRESENTACAO_PITCH.md          # Roteiro de pitch de 5 minutos
```

---

## 👥 6. Equipe InsurMinds (I2A2)

- **Equipe de Desenvolvimento e Arquitetura de Dados InsurMinds**
- Curso de Inteligência Artificial Aplicada — **I2A2 (2026)**

---

## 📜 7. Licença

Este projeto é distribuído sob a licença **MIT**. Consulte o arquivo de licença para mais detalhes.
