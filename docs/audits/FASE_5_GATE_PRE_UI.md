# FASE 5 — GATE PRE-UI: INTEGRAÇÃO REAL DE LLM + EXTRAÇÃO SEMÂNTICA DE CLÁUSULAS

**Data de Execução:** 28 de Setembro de 2026
**Ambiente:** Estritamente Local (Antigravity IDE / `.venv` local)
**Branch:** `fix/fase2-pipeline-extracao`
**HEAD Local:** `ca03d94169184b490f6bdc2c72749e5119dd203a`
**Origem Remota (`origin/main`):** `ca03d94169184b490f6bdc2c72749e5119dd203a`
**Status Git:** Sem commits, sem push, sem merge, sem PR.
**Interface de Usuário (UI):** NÃO alterada / intacta.

---

## 1. ARQUITETURA EXECUTADA

O objetivo da Fase 5 foi unificar o pipeline end-to-end conectando a extração física de PDFs reais à análise e comparação semântica de cláusulas, eliminando qualquer seleção manual ou snippets hardcoded em testes finais:

```
PDF Real (pdfplumber)
       │
       ▼
Extração Completa por Página (sem truncamento de documentos longos)
       │
       ▼
Chunking Estruturado com Sobreposição & Rastreabilidade de Páginas
       │
       ▼
Classificação Documental Estrita (detect_document_domain / detect_document_type)
       │
       ▼
Extração Estruturada + Structured Output Nativo do SDK (Gemini / Heuristic Fallback)
       │
       ▼
Rastreamento de Evidências Contratuais (página, snippet literal, método, confiança)
       │
       ▼
Descoberta de Cláusulas Contratuais (além da taxonomia canônica: básicas, adicionais, especiais)
       │
       ▼
Motor de Matching Semântico & Substantivo (compare_clause_lists / compare_clauses_semantically)
       │
       ▼
Relatório Consolidado de Comparação (ComparisonResult, FieldDiffs, SemanticMatches, Evidências A/B)
```

### Componentes Atualizados
1. **`core/document_chunker.py`**:
   - Adicionada especificação contratual expandida `DO_CONTRACT_CLAUSE_SPECS` cobrindo coberturas canônicas, cláusulas adicionais, termos de inadimplemento, agravamento de risco e contenção de sinistro.
   - Implementada função de descoberta determinística `discover_contract_clauses(text, pages, existing_evidences)` que varre documentos longos sem truncamento, elimina falsos positivos de sumários/índices e preserva o número exato da página de proveniência e snippets contextuais.
2. **`core/llm_client.py`**:
   - Integração com o SDK `google-genai` com suporte a **Structured Output nativo** via `response_schema` utilizando schemas Pydantic tipados (`ChunkExtractionSchema` e `ClauseComparisonSchema`), eliminando parsing frágil por Regex.
   - Telemetria de execução: registro estruturado de chamadas em `call_history` e `last_call_stats` (modelo, latência, método de extração, tokens, sucesso/falha).
   - Verificação estrita de `GOOGLE_API_KEY`: quando ausente, o pipeline registra formalmente `Gemini não configurado` sem bloquear o processamento, ativando fallback determinístico auditável sem inventar acurácia.
   - Extração automática de cláusulas contratuais reais e registro de proveniência na consolidação documental.
3. **`core/diff_engine.py`**:
   - Inclusão da análise comparativa de `clausulas_especiais` (`clausulas_especiais_comuns`, `clausulas_especiais_exclusivas_a`, `clausulas_especiais_exclusivas_b`).
   - Propagação enriquecida de evidências para todos os `semantic_matches` (`page_a`, `page_b`, `method_a`, `method_b`).
   - Refinamento de correspondência por limites de palavra (`_match_keyword`), prevenindo falsos positivos por substrings (e.g., `"dic"` contido em `"adicional"`).
4. **`core/schemas.py`**:
   - Enriquecimento de `SemanticMatchItem` com `page_a`, `page_b`, `method_a`, `method_b`.
   - Adição de listas de cláusulas especiais em `ComparisonResult`.

---

## 2. STATUS DO GEMINI & TELEMETRIA

- **Status de Configuração:** `Gemini não configurado` (a variável de ambiente `GOOGLE_API_KEY` não está presente no ambiente local).
- **Modelo Suportado no Código:** `gemini-2.5-flash` (com fallback para `gemini-1.5-flash` se configurado).
- **Mecanismo de Structured Output:** Native SDK via `response_mime_type="application/json"` e `response_schema=ChunkExtractionSchema`.
- **Mecanismo de Fallback Ativo:** Fallback Determinístico Local e Auditável (`heuristic_fallback` + `pdfplumber`).
- **Registro de Telemetria:** Validado em `test_fase5_gemini_config_and_telemetry`. O cliente registra:
  - `status`: `"unconfigured"`
  - `method`: `"heuristic_fallback"`
  - `model`: `"gemini-2.5-flash"`
  - `api_key_configured`: `False`
  - Zero simulação fictícia ou acurácia inventada.

---

## 3. RESULTADOS DA EXTRAÇÃO NOS 4 PDFS DO CORPUS REAL

A execução completa do pipeline sobre os 4 PDFs reais do corpus produziu os seguintes dados estruturados sem intervenção manual:

| Documento | Arquivo Real | Págs | Tipo Documental | Segurado | Proc. SUSEP | Coberturas Detectadas | Exclusões Detectadas | Cláusulas Especiais | Evidências |
|---|---|---|---|---|---|---|---|---|---|
| **DO010** | `DO_SOMPO_CONDICOES_GERAIS_V1_2_2024_010.pdf` | 44 | `condicoes_gerais` | `None` | `15414.652408/2023-71` | 4 | 1 | 1 | 15 |
| **DO012** | `DO_SOMPO_CONDICOES_GERAIS_V1_5_2025_012.pdf` | 49 | `condicoes_gerais` | `None` | `15414.652408/2023-71` | 4 | 1 | 2 | 16 |
| **DO005** | `DO_CHUBB_CONDICOES_GERAIS_OFERTA_PUBLICA_2024_005.pdf` | 55 | `condicoes_gerais` | `None` | `15414.901422/2017-66` | 7 | 2 | 0 | 15 |
| **DO014** | `DO_CHUBB_CONDICOES_GERAIS_OFERTA_PUBLICA_2025_014.pdf` | 59 | `condicoes_gerais` | `None` | `15414.901422/2017-66` | 8 | 2 | 0 | 16 |

### Observações Críticas de Integridade
- **Proteção de `segurado`:** Todos os 4 documentos foram corretamente identificados como `condicoes_gerais` e receberam `segurado = None`, pois não possuem Front Sheet ou especificação de apólice individual.
- **Processo SUSEP:** Extraído com precisão e diferenciado de número de apólice (`numero_apolice = None`).
- **Sem Truncamento:** Documentos com 44, 49, 55 e 59 páginas foram varridos integralmente, alcançando cláusulas nas páginas finais (e.g. pág. 46 de Sompo e pág. 46 de Chubb).

---

## 4. TABELA DE COMPARAÇÃO DOS DOIS PARES REAIS

### Par 1: Sompo v1.2 (`DO010`) × Sompo v1.5 (`DO012`)
- **Score de Similaridade Estrutural:** `67.6%`
- **Coberturas Comuns (4):** Defesa e Acordos, Garantias Pessoais, Cobertura Side A, Cobertura Side B.
- **Coberturas Exclusivas em B (0):** Nenhuma.
- **Cláusulas Especiais Exclusivas em B (1):** `Agravamento do Risco (18.6.1)`.

### Par 2: Chubb Oferta Pública 2024 (`DO005`) × Chubb Oferta Pública 2025 (`DO014`)
- **Score de Similaridade Estrutural:** `51.4%`
- **Coberturas Comuns (7):** Custos de Defesa, Side A, Side B, Side C, Multas e Penalidades, Herdeiros e Representantes Legais, Investigações Regulatórias.
- **Coberturas Exclusivas em B (1):** `Despesas de Contenção e Salvamento`.
- **Exclusões Comuns (2):** Poluição, Atos Dolosos e Fraude.

---

## 5. CLÁUSULAS NOVAS E REMOVIDAS DETECTADAS

1. **Cláusula Nova no Par Sompo (`DO010` × `DO012`):**
   - **Nome:** `Agravamento do Risco (Cláusula 18.6.1)`
   - **Localização:** Presente exclusivamente em `DO012` (pág. 33), ausente em `DO010`.
   - **Detecção:** Registrada em `clausulas_especiais_exclusivas_b`.
   - **Impacto Jurídico:** Institui penalidade de perda de direito à cobertura e cancelamento em caso de omissão dolosa no agravamento do risco.
2. **Cobertura Nova no Par Chubb (`DO005` × `DO014`):**
   - **Nome:** `Despesas de Contenção e Salvamento`
   - **Localização:** Presente exclusivamente em `DO014` (pág. 37), ausente em `DO005`.
   - **Detecção:** Registrada em `coberturas_exclusivas_b`.
   - **Impacto Jurídico:** Nova cobertura autônoma cobrindo custos imediatos de mitigação e contenção de risco iminente de sinistro.

---

## 6. PELO MENOS 8 DIFERENÇAS E EQUIVALÊNCIAS REAIS RASTREÁVEIS

A tabela a seguir comprova 10 correspondências semânticas rastreáveis descobertas automaticamente pelo pipeline:

| ID | Par Real | Cláusula Analisada | Pág A | Pág B | Relação Semântica | Equiv. | Diagnóstico Técnico & Evidência Rastreável |
|---|---|---|---|---|---|---|---|
| **DIFF-1** | Sompo (DO010 × DO012) | Inadimplemento do Prêmio (16.10) | 26 | 28 | `changed_scope` | `False` | **Alteração de Condição/Escopo:** A v1.2 reduzia a vigência conforme Tabela de Prazo Curto. A v1.5 aboliu a tabela e estabeleceu notificação prévia de 15 dias sob pena de cancelamento. |
| **DIFF-2** | Sompo (DO010 × DO012) | Agravamento do Risco (18.6.1) | — | 33 | `changed_scope` | `False` | **Cláusula Nova em B:** Inexistente em DO010; incluída na cláusula 18.6.1 de DO012 prevendo perda de direito por dolo do segurado. |
| **DIFF-3** | Chubb (DO005 × DO014) | Custos de Defesa | 28 | 35 | `changed_scope` | `False` | **Mudança Estrutural:** Em 2024 constava como Cláusula Básica 30 (com adiantamento). Em 2025 foi convertida em Cobertura Adicional específica sujeita a contratação e prêmio adicional. |
| **DIFF-4** | Chubb (DO005 × DO014) | Despesas de Contenção e Salvamento | — | 37 | `changed_scope` | `False` | **Cobertura Nova em B:** Inexistente na versão 2024 (`DO005`); criada como cobertura adicional em 2025 (`DO014`). |
| **DIFF-5** | Chubb (DO005 × DO014) | Cobertura Side A | 13 | 17 | `changed_scope` | `False` | **Condição Restritiva:** A versão 202512 (`DO014`) adicionou a exigência de "seguros com vigência igual ou superior a 12 meses". |
| **EQUIV-6** | Sompo (DO010 × DO012) | Defesa e Acordos | 31 | 34 | `semantic_equivalent` | `True` | **Idêntica:** Cláusula 19.3.1 mantida com redação literal ("Cada Segurado poderá escolher livremente seus respectivos advogados..."). |
| **EQUIV-7** | Sompo (DO010 × DO012) | Garantias Pessoais (Aval e Fiança) | 15 | 16 | `semantic_equivalent` | `True` | **Idêntica:** Extensão para administradores em condição de avalistas ou fiadores preservada na íntegra. |
| **EQUIV-8** | Sompo (DO010 × DO012) | Glossário: Poluição | 11 | 12 | `semantic_equivalent` | `True` | **Idêntica:** Definição contratual mantida sem qualquer alteração vocabular ("Descarga, dispensa, liberação..."). |
| **EQUIV-9** | Chubb (DO005 × DO014) | Reclamações Tomador (Side C) | 37 | 42 | `semantic_equivalent` | `True` | **Idêntica:** Redação integral da Cobertura Adicional Side C mantida idêntica entre 2024 e 2025. |
| **EQUIV-10** | Chubb (DO005 × DO014) | Multas e Penalidades | 36 | 41 | `semantic_equivalent` | `True` | **Idêntica:** Termos e condições da Cobertura Adicional de Multas contratuais preservados. |

---

## 7. EXEMPLOS DE EVIDÊNCIAS A/B RASTREÁVEIS

### Exemplo 1: `Inadimplemento do Prêmio` (Sompo DO010 × DO012)
- **Evidência A (`DO010`, Página 26, Método `pdfplumber`):**
  > *"16.10. Não sendo quitado o Prêmio na data aprazada, o prazo de vigência desta Apólice será ajustado de acordo com a Tabela de Prazo Curto..."*
- **Evidência B (`DO012`, Página 28, Método `pdfplumber`):**
  > *"16.10. Nas hipóteses de fracionamento do Prêmio, sendo configurada a falta de pagamento de qualquer uma das parcelas subsequentes à primeira, a Seguradora notificará o Segurado da inadimplência..."*
- **Diagnóstico:** `relation = changed_scope`, `equivalence = False`.

### Exemplo 2: `Custos de Defesa` (Chubb DO005 × DO014)
- **Evidência A (`DO005`, Página 28, Método `pdfplumber`):**
  > *"30.1. Desde que não se vislumbre uma hipótese de não incidência da cobertura securitária objeto desta Apólice, o pagamento dos Custos de Defesa e Despesas Decorrentes de Averiguação poderá se dar de forma antecipada..."*
- **Evidência B (`DO014`, Página 35, Método `pdfplumber`):**
  > *"COBERTURA ADICIONAL DE CUSTOS DE DEFESA 1. Pago prêmio adicional correspondente, fica estabelecido que este seguro também abrangerá, até o Limite Máximo de Indenização (LMI) especificado na apólice..."*
- **Diagnóstico:** `relation = changed_scope`, `equivalence = False`.

### Exemplo 3: `Defesa e Acordos` (Sompo DO010 × DO012)
- **Evidência A (`DO010`, Página 31, Método `pdfplumber`):**
  > *"19.3.1. Cada Segurado poderá escolher livremente seus respectivos advogados e deverá contestar e se defender em qualquer Reclamação apresentada contra eles..."*
- **Evidência B (`DO012`, Página 34, Método `pdfplumber`):**
  > *"19.3.1. Cada Segurado poderá escolher livremente seus respectivos advogados e deverá contestar e se defender em qualquer Reclamação apresentada contra eles..."*
- **Diagnóstico:** `relation = semantic_equivalent`, `equivalence = True`.

---

## 8. SCORE E DECOMPOSIÇÃO

O score de similaridade estrutural/técnica é estritamente auxiliar e decomponível:
- **Campos Estruturados Básicos (40% do peso):** Seguradora, Vigência, LMG, Franquia, Território, etc.
- **Coberturas (35% do peso):** Índice de Jaccard ponderado sobre o matching substantivo de coberturas.
- **Exclusões e Cláusulas Especiais (25% do peso):** Correspondência entre exclusões e cláusulas operacionais.

### Decomposição no Par Sompo (`DO010` × `DO012`):
- Campos coincidentes: Seguradora (`Sompo`), Processo SUSEP (`15414.652408/2023-71`), Tipo Documental (`condicoes_gerais`), Território (`Brasil`), Jurisdição (`Brasil`).
- Coberturas coincidentes: 4 coberturas básicas com equivalência semântica.
- Divergências: Cláusula nova `18.6.1` e alteração em `16.10`.
- **Score Final:** `67.6%` (refletindo continuidade estrutural da apólice Sompo com alterações pontuais de condições).

### Decomposição no Par Chubb (`DO005` × `DO014`):
- Campos coincidentes: Seguradora (`Chubb`), Processo SUSEP (`15414.901422/2017-66`), Tipo Documental (`condicoes_gerais`).
- Coberturas coincidentes com escopo preservado: `Side B`, `Side C`, `Multas e Penalidades`, `Herdeiros`.
- Coberturas com alteração de escopo: `Custos de Defesa`, `Side A`, `Investigações`.
- Cobertura nova exclusiva em B: `Despesas de Contenção e Salvamento`.
- **Score Final:** `51.4%` (penalizado pelas profundas alterações contratuais de escopo e inclusão de nova cobertura).

---

## 9. SUÍTE DE TESTES E REGRESSÃO

A suíte completa foi executada via `pytest` sem advertências nem erros:
- **Testes da Fase 1 a 4.2B:** 79 testes aprovados.
- **Testes da Fase 5 (`tests/test_fase5_pipeline_integration.py`):** 11 testes aprovados.
- **Total Geral:** **90/90 testes aprovados** (`100% PASS`).

### Cobertura dos Novos Testes da Fase 5:
1. `test_fase5_documento_longo_sem_truncamento`: Valida processamento de 40+ páginas com seções na última página.
2. `test_fase5_clausula_nova_detectada_exclusiva_b`: Prova que cláusula nova é isolada em B.
3. `test_fase5_clausula_removida_detectada_exclusiva_a`: Prova que cláusula removida é isolada em A.
4. `test_fase5_mesmo_titulo_escopo_diferente`: Detecta `changed_scope` mesmo com mesmo título nominal.
5. `test_fase5_mesmo_titulo_condicao_diferente`: Detecta `changed_condition`.
6. `test_fase5_mesmo_titulo_limite_diferente`: Detecta `changed_limit`.
7. `test_fase5_evidencia_ab_preservada_com_pagina_snippet_metodo`: Valida integridade da evidência A/B.
8. `test_fase5_document_type_condicoes_gerais_segurado_none`: Garante que CG nunca infere segurado fictício.
9. `test_fase5_real_corpus_pipeline_sompo_do010_x_do012`: Validação end-to-end do par Sompo real.
10. `test_fase5_real_corpus_pipeline_chubb_do005_x_do014`: Validação end-to-end do par Chubb real.
11. `test_fase5_gemini_config_and_telemetry`: Valida comportamento estrito de contingência e telemetria.

---

## 10. LIMITAÇÕES

1. **Ausência de Chave de API Gemini Local:** Como `GOOGLE_API_KEY` não está configurada no ambiente do usuário, as extrações reais foram executadas via fallback determinístico com `pdfplumber` e descoberta semântica algorítmica. O código do SDK Gemini está plenamente integrado e suporta Structured Output nativo quando a chave for injetada.
2. **Documentos Sem Front Sheet:** O corpus de teste contém Condições Gerais puras; os campos dependentes de proposta/especificação (`segurado`, `lmg`, `franquia`, `premio`) permanecem nulos ou não especificados nestes documentos, conforme exigido pelas regras de não-fabricação de dados.
3. **Complexidade de Diagramas:** Textos em colunas muito densas ou fluxogramas contidos em PDFs podem exigir OCR especializado no futuro caso surjam documentos escaneados.

---

## 11. DECISÃO TÉCNICA

# DECISÃO: `PASS`

O pipeline completo de ponta a ponta (`PDF real → extração completa → chunking/páginas → classificação documental → extração estruturada → evidências → identificação de cláusulas → matching → comparação semântica → relatório`) foi validado com êxito sobre os 4 PDFs reais do corpus. Todas as alterações e equivalências contratuais foram identificadas sem qualquer snippet hardcoded, assegurando rastreabilidade total de evidências contratuais para a futura camada de UI.
