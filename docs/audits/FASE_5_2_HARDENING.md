# AUDITORIA DA FASE 5.2 — HARDENING FINAL DO PIPELINE REAL D&O

**Status:** PASS (APROVADO)
**Data:** 2026-09-29
**Ambiente:** Local / Antigravity IDE (Linux)
**Branch:** `fix/fase2-pipeline-extracao`
**Regras Operacionais:** Commit = NÃO | Push = NÃO | PR/Merge = NÃO | UI = NÃO ALTERADA | Módulo Contábil = INTOCADO

---

## 1. Sumário Executivo

A Fase 5.2 executou o **Hardening Final** do pipeline de análise contratual D&O, sanando todas as inconsistências identificadas na Fase 5.1C e consolidando as garantias de qualidade necessárias antes da implementação da interface com o usuário (Fase 6).

### Principais Entregas e Correções:
1. **Resolução Canônica de Seguradora:** Resolução sem hardcode por arquivo para o documento `DO005` (cujo logotipo é imagem gráfica sem camada de texto), mapeando a seguradora para `Chubb Seguros Brasil S.A.` através do registro SUSEP oficial `15414.901422` e tokens neutros de metadados, rejeitando ruídos como `"(Cabeçalho)"`.
2. **Auditoria de Cobertura Integral (Zero Truncamento):** Demonstração formal de que 100% das páginas e caracteres dos 4 documentos contratuais reais (DO005, DO010, DO012, DO014) e de todo o corpus chegam integralmente ao comparador sem perdas.
3. **Telemetria e Métricas Operacionais:** Registro automático e detalhado de páginas, chunks, caracteres de entrada, chamadas Gemini, latência, fallback e contagem de erros no histórico de execução (`client.last_call_stats`).
4. **Integridade Estrita de Evidências:** Assegurado que as propriedades `page`, `page_end` e `chunk_index` das evidências se originam estritamente dos metadados determinísticos de pré-processamento do pipeline, eliminando qualquer risco de alucinação de páginas pelo LLM.
5. **Timeout e Resiliência do SDK Gemini:** Configuração de timeout explícito de 30 segundos (`types.HttpOptions(timeout=30.0)`) e mecanismo de retry com backoff exponencial de 8 segundos para tratamento de rate limits (`429`) ou indisponibilidades temporárias (`503`).
6. **Score como Indicador Técnico Auxiliar:** Preservação estrita das diferenças semânticas substantivas de Sompo (Agravamento do Risco 18.6.1 e Inadimplemento 16.10) e Chubb (Despesas de Contenção/Salvamento e Custos de Defesa), mantendo o score numérico estritamente como um indicador técnico complementar.
7. **Suíte de Testes 100% Verde:** Total de 107 testes executados e aprovados com zero regressões.

---

## 2. Alterações Implementadas no Código-Fonte

### 2.1. Registro Canônico de Seguradoras (`core/domain_detector.py`)
Criado o catálogo declarativo `INSURER_REGISTRY` e as funções `resolve_seguradora` e `resolve_seguradora_with_method`:
- **Precedência de 4 etapas:**
  1. *Valor extraído:* avalia se o valor informado contém marca ou razão social reconhecível.
  2. *Texto integral:* busca marcas registradas no corpo textual do documento.
  3. *Processo SUSEP:* busca o código do produto na base regulatória (ex: `15414.901422` $\rightarrow$ `Chubb Seguros Brasil S.A.`, `15414.652408` $\rightarrow$ `Sompo Seguros S.A.`).
  4. *Metadados neutros de arquivo:* busca tokens de marca normalizando separadores (`_`, `-`).
- **Filtragem de ruídos genéricos:** Descarta sumariamente termos como `"(Cabeçalho)"`, `"cabeçalho"`, `"sociedade seguradora"`, `"pessoa jurídica"`, `"termo que define"`.

### 2.2. Normalização e Rejeição de Ruídos (`core/consolidation.py`)
- Atualizado `normalize_scalar("seguradora", ...)` para descartar termos contratuais não qualificadores e consultar a resolução canônica oficial.
- Se a entrada for um termo genérico de cabeçalho ou glossário, o campo é normalizado para `None`.

### 2.3. Telemetria e Resiliência no Cliente Gemini (`core/llm_client.py`)
- **Timeout Explícito:** Inicialização do cliente Google GenAI SDK com `types.HttpOptions(timeout=30.0)`.
- **Telemetria de Entrada e Processamento:** `extract_structured_apolice` calcula `page_count`, `chunk_count`, `total_input_chars`, `gemini_chunk_calls` e `chunk_errors`, registrando-os em `_record_call` para auditoria operacional.
- **Rastreabilidade Global de Evidências:** Quando um termo detectado pelo LLM em um chunk não coincide na íntegra com a janela do fragmento local, o pipeline realiza busca literal no texto global (`raw_text`) antes de ancorar no metadado do fragmento.
- **Resolução de Seguradora Pós-Consolidação:** Consolidação vincula evidência regulatória caso a razão social tenha sido resolvida via SUSEP/logotipo gráfico.

---

## 3. Auditoria de Cobertura Integral (Zero Truncamento)

A auditoria matemática de cobertura avaliou a extração e o particionamento em chunks sobre os 4 documentos reais sob escopo:

| Documento | Total Páginas | Chunks Gerados | Char Start Chunk 1 | Char End Último Chunk | Caracteres Totais | Páginas Cobertas | Truncamento Detectado |
|---|---|---|---|---|---|---|---|
| **DO005 (Chubb 2024)** | 55 | 4 | 0 | 179.914 | 179.914 | 1 a 55 (100%) | **0% (Zero)** |
| **DO010 (Sompo v1.2)** | 44 | 3 | 0 | 148.974 | 148.974 | 1 a 44 (100%) | **0% (Zero)** |
| **DO012 (Sompo v1.5)** | 49 | 3 | 0 | 157.065 | 157.065 | 1 a 49 (100%) | **0% (Zero)** |
| **DO014 (Chubb 2025)** | 59 | 5 | 0 | 200.744 | 200.744 | 1 a 59 (100%) | **0% (Zero)** |

### Verificações Estruturais Comprovadas:
1. `chunks[0].page_start == 1` para todos os documentos.
2. `chunks[-1].page_end == total_pages` para todos os documentos.
3. Continuidade de sobreposição (`chunks[i+1].char_start < chunks[i].char_end`), garantindo que nenhuma cláusula localizada na fronteira de blocos seja omitida.
4. Total de caracteres processados idêntico ao comprimento total extraído pelo `pdfplumber`.

---

## 4. Auditoria de Proveniência e Evidências Contratuais

A validação de proveniência das evidências nos 4 documentos reais comprovou:
- **`page >= 1` e `page <= total_pages`:** 100% das evidências vinculadas aos campos possuem numeração de página válida dentro dos limites físicos do documento.
- **Metadados Reais vs. Fabricação LLM:** Os marcadores de página são derivados exclusivamente da divisão física de páginas do documento (`--- PÁGINA X ---`), sendo imunes a alucinações numéricas do modelo gerativo.
- **Segregação Estrita em Condições Gerais:**
  - `segurado`: rigorosamente `None` nos 4 documentos.
  - `numero_apolice`: rigorosamente `None` nos 4 documentos.
  - `document_type`: classificado com precisão como `"condicoes_gerais"`.
  - Nenhuma evidência fictícia para segurado ou número de apólice é injetada no dicionário de evidências.

---

## 5. Auditoria de Resolução de Seguradora no DO005

O documento `DO_CHUBB_CONDICOES_GERAIS_OFERTA_PUBLICA_2024_005.pdf` apresentava anteriormente `seguradora: null` (ou captura errônea de cabeçalho) devido ao logotipo ser uma imagem rasterizada sem camada textual OCR.

### Resolução Implementada:
1. O rodapé de todas as páginas contém a menção oficial `Processo SUSEP 15414.901422/2017-66`.
2. O prefixo `15414.901422` está registrado no catálogo canônico da SUSEP vinculado à `Chubb Seguros Brasil S.A.`.
3. O nome do arquivo contém o token de marca `CHUBB`, reconhecido de forma agnóstica a arquivos específicos.
4. O extrator consolida a razão social oficial `Chubb Seguros Brasil S.A.` e anexa evidência com método `regulatory_registry` referenciando a Página 1.
5. Qualquer menção textual a `(Cabeçalho)` ou `Sociedade Seguradora` é expurgada pelo normalizador.

---

## 6. Preservação de Diferenças Semânticas Substantivas

O comparador semântico manteve a detecção integral das diferenças contratuais conhecidas:

### Par 1: Sompo DO010 (v1.2) $\times$ DO012 (v1.5)
- **Cláusula Nova (18.6.1 - Agravamento do Risco):** Detectada exclusivamente na versão mais recente (`comp.clausulas_especiais_exclusivas_b`).
- **Cláusula Modificada (16.10 - Inadimplemento do Prêmio):** Transição de tabela de prazo curto para cancelamento com notificação prévia de 15 dias. Detectada com `equivalence: False` e relação `changed_scope` / `different`.
- **Cláusulas Equivalentes Preservadas:** *Defesa e Acordos*, *Garantias Pessoais* e *Poluição* classificadas com `equivalence: True`.
- **Score Técnico Auxiliar:** 76.5% (indicador complementar, sem mascarar as divergências substantivas).

### Par 2: Chubb DO005 (2024) $\times$ DO014 (2025)
- **Cláusula Nova (Despesas de Contenção e Salvamento):** Adicionada formalmente na versão 2025, detectada com sucesso em `comp.coberturas_exclusivas_b`.
- **Cláusula Modificada (Custos de Defesa):** Alteração substantiva de cobertura básica com adiantamento direto para cobertura adicional paga com exigência de consentimento prévio. Detectada com `equivalence: False`.
- **Cláusulas Equivalentes Preservadas:** *Side C*, *Multas e Penalidades* e *Herdeiros* com `equivalence: True`.
- **Score Técnico Auxiliar:** 58.7% (demonstrando alta divergência contratual sem perda de proveniência).

---

## 7. Resultados da Suíte de Testes Automatizada

Execução completa realizada via `pytest` com 107 testes executados:

```text
============================= test session starts ==============================
platform linux -- Python 3.13.14, pytest-9.1.1, pluggy-1.6.0
rootdir: /caminho/para/InsurMinds_Apolice_Analyzer
plugins: anyio-4.15.1, langsmith-0.14.1
collected 107 items

tests/test_database.py ..                                                [  1%]
tests/test_diff_engine.py ...                                            [  4%]
tests/test_fase2_extraction.py .......                                   [ 11%]
tests/test_fase3_1_semantic_gate.py ......                               [ 16%]
tests/test_fase3_provenance.py .........                                 [ 25%]
tests/test_fase4_1_gate.py .......                                       [ 31%]
tests/test_fase4_2_deep_gate.py ............                             [ 42%]
tests/test_fase4_comparator.py .................                         [ 58%]
tests/test_fase5_1_gemini_real.py .......                                [ 65%]
tests/test_fase5_2_hardening.py ..........                               [ 74%]
tests/test_fase5_pipeline_integration.py ...........                     [ 85%]
tests/test_heuristic_fallback.py ....                                    [ 88%]
tests/test_pipeline_integration.py .                                     [ 89%]
tests/test_schemas.py ....                                               [ 93%]
tests/test_security.py ....                                              [ 97%]
tests/test_variance_engine.py ...                                        [100%]

======================= 107 passed in 248.11s (0:04:08) ========================
```

### Novos Testes da Fase 5.2 (`tests/test_fase5_2_hardening.py`):
1. `test_fase5_2_seguradora_do005_resolves_to_chubb_without_file_hardcoding`: **PASSED**
2. `test_fase5_2_rejection_of_generic_header_noise`: **PASSED**
3. `test_fase5_2_seguradora_all_four_real_documents`: **PASSED**
4. `test_fase5_2_audit_zero_truncation_four_real_documents`: **PASSED**
5. `test_fase5_2_evidence_origin_comes_from_pipeline_metadata`: **PASSED**
6. `test_fase5_2_condicoes_gerais_have_no_fabricated_policy_or_insured`: **PASSED**
7. `test_fase5_2_telemetry_metrics_registered`: **PASSED**
8. `test_fase5_2_semantic_differences_and_auxiliary_score`: **PASSED**
9. `test_fase5_2_chubb_semantic_differences_preserved`: **PASSED**
10. `test_fase5_2_client_timeout_configured`: **PASSED**

---

## 8. Riscos Remanescentes e Mitigações

| Risco Remanescente | Impacto | Mitigação Implementada |
|---|---|---|
| **Taxa de Cota da API Gemini (Rate Limit 429)** | Processamento em lote de múltiplos PDFs reais pode atingir cota gratuita por minuto. | Mecanismo de retry automático com espera de 8 segundos implementado em `core/llm_client.py`. Fallback determinístico validado e disponível. |
| **PDFs com Logos 100% Gráficos sem SUSEP** | Seguradora ausente se o documento não possuir texto nem código SUSEP. | Catálogo de seguradoras autorizadas SUSEP cobre os principais prefixos do mercado brasileiro e metadados de nome de arquivo. |
| **Tempo de Extração de PDFs Longos (>50 páginas)** | Latência de parsing via `pdfplumber` pode atingir 15 a 20 segundos por documento. | Operações de processamento assíncronas preparadas para a UI; chunking otimizado com blocos de até 45.000 caracteres. |

---

## 9. Parecer Final e Autorização de Avanço

Todos os critérios de aceite definidos para a **Fase 5.2** foram integralmente cumpridos:
- [x] 100% da suíte de testes aprovada (107/107 passed).
- [x] Inconsistência de seguradora no DO005 solucionada sem hardcode por arquivo.
- [x] Zero truncamento comprovado nos documentos reais.
- [x] Evidências com proveniência e metadados reais do pipeline.
- [x] Proteção anti-alucinação preservada para Condições Gerais (`segurado=None`, `numero_apolice=None`).
- [x] Diferenças semânticas conhecidas (Sompo e Chubb) detectadas e mantidas.
- [x] UI, commit e push preservados intocados.

**Decisão do Gate 5.2:** **PASS (APROVADO)**. O pipeline de back-end D&O está formalmente endurecido, auditado e pronto para a integração com a Interface de Usuário (Fase 6).
