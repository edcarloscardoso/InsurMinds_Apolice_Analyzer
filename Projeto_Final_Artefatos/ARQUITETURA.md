# Documento de Arquitetura de Dados & Pipeline Analítico
**InsurMinds Apólice Analyzer · Plataforma de Análise e Comparação Assistida de Apólices D&O**<br>
*Instituto de Inteligência Artificial Aplicada — I2A2 (2026)*

---

| Metadado | Informação |
|---|---|
| **Projeto** | InsurMinds Apólice Analyzer |
| **Versão** | Release Candidate (RC) |
| **Curso** | Inteligência Artificial Aplicada às Finanças e Seguros (InsurMinds) |
| **Instituição** | I2A2 — Instituto de Inteligência Artificial Aplicada |
| **Equipe** | Seguros Connect |
| **Data da Entrega** | 06 de Outubro de 2026 |
| **Status da Arquitetura** | Homologada em Linux (182/182 testes) · Windows 11: PENDING REAL VALIDATION |

---

## 1. Visão Geral da Arquitetura

O **InsurMinds Apólice Analyzer** adota o padrão arquitetural de **Camadas Desacopladas com Modelagem de Estados Multi-Agente**, orquestrado conceitualmente via **LangGraph** e executado na interface por *runners* procedurais determinísticos integrados ao ciclo de vida do **Streamlit**.

A persistência de dados opera sobre banco relacional embarcado **SQLite 3**, garantindo idempotência estrita via hash criptográfico MD5, integridade transacional ACID e rastreabilidade documental integral por meio de entidades dedicadas de evidência contratual (`EvidenceItem` e tabela `policy_evidence`).

```
                               ┌────────────────────────────────────────────────────────┐
                               │             CAMADA DE APRESENTAÇÃO (STREAMLIT UI)      │
                               │  [Início] [Nova análise] [Comparações] [Documentos]    │
                               │  [Relatórios] [Configurações] + Drawer de Evidências   │
                               └───────────────────────────┬────────────────────────────┘
                                                           │ Eventos / Callbacks de Progresso
                                                           ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                    CAMADA DE ORQUESTRAÇÃO (MODELAGEM LANGGRAPH + RUNNERS PROCEDURAIS)                         │
│                                                                                                               │
│   ┌─────────────────────┐        ┌─────────────────────┐        ┌─────────────────────┐        ┌────────────┐ │
│   │   Agente 1          │        │   Agente 2          │        │   Agente 3          │        │  Agente 4  │ │
│   │   Reception         │───────►│   Extractor         │───────►│   Identifier        │───────►│  Structurer│ │
│   │   (Magic Bytes/MD5) │        │   (Híbrido/OCR)     │        │   (SUSEP Ramo 0378) │        │  (Pydantic)│ │
│   └──────────┬──────────┘        └──────────┬──────────┘        └─────────────────────┘        └─────┬──────┘ │
│              │                              │                                                        │        │
│              │ Cache Hit                    │ Branch Multimodal                                      │ Salva  │
│              ▼                              ▼                                                        ▼        │
│      [ Pula Extração ]             ┌────────────────┐                                            [ SQLite ]  │
│      (Recupera do DB)              │ Gemini Vision  │ (Online)                                                │
│                                    │ PyMuPDF + Tess │ (Offline)                                               │
│                                    └────────────────┘                                                         │
│                                                                                                               │
│   ─────────────────────────────────────────────────────────────────────────────────────────────────────────   │
│                                                                                                               │
│   ┌──────────────────────────────────────────────────┐        ┌───────────────────────────────────────────┐   │
│   │                     Agente 5                     │        │                 Agente 6                  │   │
│   │                     Comparator                   │───────►│                 Reporter                  │   │
│   │   (Diff Determinístico + Jaccard Ponderado)      │        │      (Parecer Narrativo Técnico + Evid.)  │   │
│   └─────────────────────────┬────────────────────────┘        └─────────────────────┬─────────────────────┘   │
└─────────────────────────────┼───────────────────────────────────────────────────────┼─────────────────────────┘
                              │                                                       │
                              ▼                                                       ▼
                  ┌───────────────────────┐                               ┌───────────────────────┐
                  │   ComparisonResult    │                               │    Parecer Final      │
                  │   (JSON Estruturado)  │                               │  (Markdown / Export)  │
                  └───────────────────────┘                               └───────────────────────┘
```

---

## 2. Camadas da Solução

### 2.1 Camada de Apresentação (UI)
- **Tecnologia:** Streamlit (≥ 1.39.0).
- **Design System:** Tema executivo *Dark Obsidian* com tokens centralizados (`ui/tokens.py`) e estilos CSS corporativos (`ui/styles.py`).
- **Navegação (6 Páginas Oficiais):**
  1. `Início (Workspace)`: Painel de métricas, status do pipeline e seletor rápido para comparação de apólices.
  2. `Nova análise (Upload)`: Ingestão de arquivos (PDF, PNG, JPG, JPEG) com timeline dos agentes e barra de progresso em tempo real.
  3. `Comparações`: Matriz comparativa campo a campo, scorecards de divergência e *drawer* de evidências documentais.
  4. `Documentos (Biblioteca)`: Catálogo de apólices salvas no SQLite com filtros e acesso à tela de **Detalhe da Apólice**.
  5. `Relatórios`: Visualização do parecer executivo narrativo e exportação em Markdown e JSON estruturado.
  6. `Configurações`: Diagnóstico de serviços, validação de chaves e inspeção do ambiente local.
- **Telas Especializadas:**
  - `ui/page_detail.py`: Subvisão de detalhe cadastral de um documento e de suas evidências contratuais.
  - `ui/page_accounting.py`: Módulo de apoio à auditoria contábil, conciliação de provisões (PSL) e variação de sinistros conforme padrões SUSEP.

### 2.2 Camada de Orquestração (LangGraph & Runners)
- **Modelagem de Grafos:** Compilação de dois grafos finitos em `agents/graph.py` com o framework **LangGraph**:
  - `DocumentState`: Grafo de ingestão (Agentes 1 a 4) com transições condicionais de *Cache Hit* ou erro de validação.
  - `ComparisonState`: Grafo de comparação e síntese (Agentes 5 e 6).
- **Execução Procedural no MVP:** A execução interativa na interface Streamlit adota funções controladas (`run_document_pipeline_with_progress` e `run_comparison_pipeline_with_progress`), permitindo emissão de callbacks granulares de progresso visual, atualização de status e tratamento resiliente de exceções sem bloqueio do navegador.

### 2.3 Camada de Domínio e Inteligência
- **Contratos Canônicos (Pydantic v2):** `ApoliceDAO`, `EvidenceItem`, `FieldDiff`, `ComparisonResult`, `SemanticMatchItem`.
- **Estratégia de Dupla Rota:**
  - **Rota IA Generativa (com `GOOGLE_API_KEY`):** Google Gemini 2.0 Flash Lite via SDK oficial `google-genai` com Structured Output para estruturação sem quebra de schema e Vision para imagens e PDFs escaneados.
  - **Rota de Contingência Determinística (Offline):** Heurísticas canônicas baseadas na Circular SUSEP nº 637/2021 (Ramo 0378) e motor local PyMuPDF + Tesseract OCR 5.x.
- **Motor de Confronto Determinístico (`core/diff_engine.py`):** Normalização escalar, comparação de conjuntos de cláusulas, cálculo de Similaridade de Jaccard ponderado e detecção de assimetrias contratuais críticas de D&O.

### 2.4 Camada de Persistência Relacional
- **Banco de Dados:** SQLite 3 embarcado (`data/apolices.db`), gerenciado por `core/database.py` (`DatabaseManager`).
- **Garantias:** Idempotência via hash MD5, transações ACID, consultas estritamente parametrizadas e migração automática de esquemas DDL.

---

## 3. Descrição dos Agentes do Sistema

| Agente | Responsabilidade | Tecnologias Utilizadas | Entrada / Saída |
|---|---|---|---|
| **1. Reception Agent** | Validação de segurança por *magic bytes* (`%PDF-`, `\x89PNG\r\n\x1a\n`, `\xFF\xD8\xFF`), limite de 50MB, higienização contra *Path Traversal*, cálculo de hashes MD5/SHA-256 e consulta de cache no banco. | `hashlib`, `pathlib`, `re`, `core/security.py` | `DocumentState.file_path` ➔ `DocumentState.file_hash`, `file_size`, `status` |
| **2. Extractor Agent** | Roteamento inteligente de extração com base no formato e densidade textual (<100 chars/pág ativa rota visual). Extração vetorial via `pdfplumber` ou rota multimodal (Gemini Vision / PyMuPDF + Tesseract local). | `pdfplumber`, `PyMuPDF (fitz)`, `google-genai`, `core/config.py` | `file_path` ➔ `DocumentState.raw_text`, `is_scanned`, `extraction_method` |
| **3. Identifier Agent** | Segmentação e classificação semântica das seções contratuais de D&O (Condições Gerais, Coberturas Básicas e Adicionais, Exclusões, Franquias/POS, Retroatividade, Âmbito Territorial) alinhadas à Circular SUSEP 637/2021. | `core/llm_client.py` / Heurísticas SUSEP (`core/domain_detector.py`) | `raw_text` ➔ `DocumentState.identified_sections` |
| **4. Structurer Agent** | Instanciação e validação do modelo canônico Pydantic v2 `ApoliceDAO`. Normalização de valores monetários (BRL), percentuais e datas. Vinculação dos objetos `EvidenceItem` e persistência no SQLite. | `Pydantic v2`, `sqlite3`, `google-genai`, `core/database.py` | `identified_sections` ➔ `ApoliceDAO` ➔ `apolices` e `policy_evidence` (DB) |
| **5. Comparator Agent** | Confronto analítico determinístico campo a campo de dados escalares, categorização de coberturas/exclusões exclusivas vs comuns, detecção de assimetrias D&O e cálculo do Score Global de Similaridade. | Motor `core.diff_engine` (Python puro em memória) | `(ApoliceDAO, ApoliceDAO)` ➔ `ComparisonResult` |
| **6. Reporter Agent** | Síntese executiva técnica em linguagem natural (PT-BR) fundamentada em fatos e evidências documentais extraídas. Operação via Gemini 2.0 ou templates técnicos estruturados offline. | `Gemini 2.0 Flash Lite` / Sintetizador Determinístico | `ComparisonResult` ➔ Markdown Relatório ➔ `comparacoes` (DB) |

---

## 4. Modelo de Dados e Diagrama Entidade-Relacionamento (DER)

A camada de persistência utiliza o banco relacional embarcado **SQLite 3**, garantindo zero infraestrutura externa e portabilidade entre sistemas operacionais.

```
┌────────────────────────────────────────────────────────┐
│                        apolices                        │
├────────────────────────────────────────────────────────┤
│ PK  id                          TEXT  (Hash MD5)       │
│     nome_arquivo                TEXT  NOT NULL         │
│     data_processamento          TEXT  NOT NULL         │
│     segurado                    TEXT                   │
│     seguradora                  TEXT                   │
│     numero_apolice              TEXT                   │
│     processo_susep              TEXT                   │
│     vigencia_inicio             TEXT                   │
│     vigencia_fim                TEXT                   │
│     premio_total                TEXT                   │
│     limite_responsabilidade     TEXT                   │
│     franquia                    TEXT                   │
│     coberturas_json             TEXT  (JSON Array)     │
│     exclusoes_json              TEXT  (JSON Array)     │
│     clausulas_especiais_json    TEXT  (JSON Array)     │
│     retroatividade              TEXT                   │
│     territorio                  TEXT                   │
│     legislacao_aplicavel        TEXT                   │
│     cod_ramo                    TEXT  DEFAULT '0378'   │
│     ramo_descricao              TEXT  DEFAULT 'D&O'    │
│     tipo_movimento              TEXT                   │
│     tipo_movimento_descricao    TEXT                   │
│     document_type               TEXT  DEFAULT 'unknown'│
│     metodo_extracao             TEXT                   │
│     confianca_extracao          REAL                   │
│     campos_nao_encontrados_json TEXT  (JSON Array)     │
│     dados_completos_json        TEXT  NOT NULL         │
│     created_at                  TIMESTAMP              │
└───────────────────────────┬────────────────────────────┘
                            │ 1
                            │
              ┌─────────────┴─────────────┐
              │ 1                         │ 1
              ▼ N                         ▼ N
┌────────────────────────────────┐  ┌────────────────────────────────────┐
│          comparacoes           │  │          policy_evidence           │
├────────────────────────────────┤  ├────────────────────────────────────┤
│ PK  id               TEXT      │  │ PK  id               INTEGER AUTO  │
│ FK  apolice_a_id     TEXT      │  │ FK  policy_id        TEXT NOT NULL │
│ FK  apolice_b_id     TEXT      │  │     field_name       TEXT NOT NULL │
│     score_similaridade REAL    │  │     value            TEXT          │
│     data_comparacao  TEXT      │  │     page             INTEGER       │
│     resultado_json   TEXT      │  │     page_end         INTEGER       │
│     relatorio_markdown TEXT    │  │     section          TEXT          │
│     created_at       TIMESTAMP │  │     snippet          TEXT          │
└────────────────────────────────┘  │     method           TEXT          │
                                    │     confidence       REAL          │
                                    │     chunk_index      INTEGER       │
                                    │     char_start       INTEGER       │
                                    │     char_end         INTEGER       │
                                    │     is_conflict      INTEGER       │
                                    │     created_at       TIMESTAMP     │
                                    └────────────────────────────────────┘
```

### Índices de Performance Criados
- `idx_apolices_seguradora`: Otimização de filtros por seguradora.
- `idx_apolices_segurado`: Otimização de busca por empresa tomadora.
- `idx_apolices_ramo`: Otimização de consultas setoriais SUSEP.
- `idx_apolices_tipo_mov`: Otimização por tipo de movimentação regulatória.
- `idx_comparacoes_pares`: Otimização de consultas do par `(apolice_a_id, apolice_b_id)`.
- `idx_policy_evidence_policy`: Acesso rápido a todas as evidências de uma apólice.
- `idx_policy_evidence_field`: Consulta indexada de evidências por campo específico.

---

## 5. Fórmula do Score de Similaridade Composto

O índice percentual de similaridade ($S$) entre duas apólices é calculado segundo a seguinte ponderação matemática (`core/diff_engine.py`):

$$S = S_{\text{escalar}} \times 0.40 + J(\text{Coberturas}) \times 0.40 + J(\text{Exclusões}) \times 0.20$$

Onde:
1. **$S_{\text{escalar}}$**: Razão entre o número de campos escalares equivalentes e o total de campos comparados (LMG, franquia, prêmio, retroatividade, território, foro, vigência):
   $$S_{\text{escalar}} = \frac{\sum_{i=1}^{N} \mathbb{I}(\text{campo}_{A,i} \equiv \text{campo}_{B,i})}{N}$$
2. **$J(\text{Coberturas})$**: Índice de Similaridade de Jaccard aplicado sobre os conjuntos de cláusulas de cobertura:
   $$J(\text{Coberturas}) = \frac{|C_A \cap C_B|}{|C_A \cup C_B|}$$
3. **$J(\text{Exclusões})$**: Índice de Similaridade de Jaccard aplicado sobre os conjuntos de cláusulas de exclusão:
   $$J(\text{Exclusões}) = \frac{|E_A \cap E_B|}{|E_A \cup E_B|}$$

### Regras Especializadas de Domínio D&O
- Tratamento específico para assimetrias de **Side A DIC** (*Difference in Conditions*).
- Análise de severabilidade de declarações e exigência de decisão judicial transitada em julgado para exclusão de dolo.
- Ponderação de retroatividade temporal e extensão de jurisdição para Estados Unidos/Canadá.

---

## 6. Arquitetura de Rastreabilidade e Evidências

Cada inferência ou dado extraído é associado a uma instância do modelo canônico `EvidenceItem` (`core/schemas.py`), persistida tanto no payload JSON da apólice quanto na tabela normalizada `policy_evidence`:

| Atributo | Tipo | Papel no Pipeline |
|---|---|---|
| `page` | `Optional[int]` | Número da página inicial da evidência no documento original (1-indexed). |
| `page_end` | `Optional[int]` | Número da página final para cláusulas extensas. |
| `section` | `Optional[str]` | Título da seção ou cláusula contratual de origem. |
| `snippet` | `Optional[str]` | Citação textual literal extraída do documento que comprova o dado. |
| `method` | `str` | Motor de extração (`pdfplumber`, `llm`, `heuristic`, `ocr`, `normalized`). |
| `confidence` | `float` | Grau de confiança analítica atribuído à extração (0.0 a 1.0). |
| `chunk_index` | `Optional[int]` | Índice sequencial do fragmento textual processado. |
| `char_start` / `char_end` | `Optional[int]` | Posição dos caracteres no documento completo para ancoragem de texto. |

Na interface do usuário, essas informações são expostas no **Drawer de Evidências**, permitindo ao analista conferir o trecho original e validar a informação sem folhear dezenas de páginas manualmente.

---

## 7. Estratégia de Fallback e Resiliência

O sistema implementa uma política de **dupla rota e resiliência com tolerância a falhas**:

1. **Rota Primária com IA Generativa (Online):**
   - Ativada na presença da variável de ambiente `GOOGLE_API_KEY`.
   - Utiliza o modelo `gemini-flash-lite-latest` via SDK oficial `google-genai`.
   - Aplica **Structured Output** forçado em esquemas do Pydantic v2, restringindo o formato da resposta e reduzindo falhas sintáticas de parsing.
   - Aplica rota de visão multimodal para documentos escaneados e imagens.
2. **Rota de Contingência Determinística (100% Offline):**
   - Ativada automaticamente na ausência da chave Gemini ou em falhas de conectividade de rede.
   - Utiliza heurísticas canônicas e expressões regulares parametrizadas conforme a Circular SUSEP nº 637/2021.
   - Processamento de documentos escaneados via C-bindings locais do `PyMuPDF` integrados ao motor `Tesseract OCR 5.x` (`por.traineddata`).
   - Ambas as rotas produzem exatamente o mesmo contrato canônico `ApoliceDAO`, sinalizando o método de extração utilizado para auditoria.

---

## 8. Medidas de Segurança Implementadas

1. **Prevenção contra Path Traversal:** A função `core.security.get_safe_destination_path` normaliza caminhos de arquivo e verifica de forma mandatória se o destino reside estritamente contido dentro do diretório sandbox `data/uploads/`, neutralizando manipulações do tipo `../`.
2. **Validação de Magic Bytes Multiformato:** Validação de cabeçalhos binários antes de qualquer leitura ou parsing:
   - PDF: `%PDF-` (`25 50 44 46 2d`);
   - PNG: `\x89PNG\r\n\x1a\n` (`89 50 4e 47 0d 0a 1a 0a`);
   - JPG/JPEG: `\xff\xd8\xff` (`ff d8 ff`).
3. **Cota de Tamanho de Arquivo:** Rejeição na camada de recepção de arquivos com tamanho superior a 50 MB (configurável via `MAX_FILE_SIZE_MB`), prevenindo ataques de negação de serviço por exaustão de memória.
4. **Prevenção contra SQL Injection:** 100% das operações no SQLite utilizam consultas parametrizadas com placeholders `?`.
5. **Isolamento de Credenciais:** As chaves de API são consumidas exclusivamente via `os.getenv` a partir do `.env`. Arquivos `.env` e bancos `.db` constam no `.gitignore` e nunca são versionados.
6. **Segurança de Rede Local:** O servidor Streamlit é configurado por padrão para escutar na interface de *loopback* local (`127.0.0.1`).
