# Documento de Arquitetura de Dados & Pipeline Analítico
**InsurMinds Apólice Analyzer · Projeto Final I2A2 (2026)**

---

## 1. Visão Geral da Arquitetura

O **InsurMinds Apólice Analyzer** adota o padrão de arquitetura de **Pipeline Multi-Agente Orientado a Estados (State-Driven Multi-Agent Pipeline)** orquestrado via **LangGraph**, com persistência relacional local em **SQLite**, garantindo idempotência, rastreabilidade e zero-crash com fallbacks inteligentes.

```
                               ┌────────────────────────────────────────┐
                               │           STREAMLIT WEB UI             │
                               │  [Upload] [Biblioteca] [Compare] [Doc] │
                               └───────────────────┬────────────────────┘
                                                   │ Chamada de Funções / Eventos
                                                   ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 LANGGRAPH ORCHESTRATION PIPELINE                                       │
│                                                                                                        │
│   ┌───────────────────┐       ┌───────────────────┐       ┌───────────────────┐       ┌──────────────┐ │
│   │   Agente 1        │       │   Agente 2        │       │   Agente 3        │       │   Agente 4   │ │
│   │   Reception       │──────►│   Extractor       │──────►│   Identifier      │──────►│   Structurer │ │
│   │   (Hash/Security) │       │   (Hybrid Text)   │       │   (Segmentation)  │       │   (Pydantic) │ │
│   └─────────┬─────────┘       └─────────┬─────────┘       └───────────────────┘       └──────┬───────┘ │
│             │                           │                                                    │         │
│             │ Cache Hit                 │ Fallback OCR                                       │ Salva   │
│             ▼                           ▼                                                    ▼         │
│     [ Pula Extração ]          [ Gemini Vision ]                                        [ SQLite DB ]  │
│                                                                                                        │
│   ───────────────────────────────────────────────────────────────────────────────────────────────────  │
│                                                                                                        │
│   ┌───────────────────────────────────────────────┐       ┌────────────────────────────────────────┐   │
│   │                   Agente 5                    │       │                Agente 6                │   │
│   │                   Comparator                  │──────►│                Reporter                │   │
│   │   (Diff Determinístico + Jaccard Composite)   │       │   (Parecer Narrativo Executivo LLM)    │   │
│   └───────────────────────┬───────────────────────┘       └───────────────────┬────────────────────┘   │
└───────────────────────────┼───────────────────────────────────────────────────┼────────────────────────┘
                            │                                                   │
                            ▼                                                   ▼
                ┌───────────────────────┐                           ┌───────────────────────┐
                │   ComparisonResult    │                           │    Relatório Final    │
                │   (JSON Estruturado)  │                           │   (Markdown / Export) │
                └───────────────────────┘                           └───────────────────────┘
```

---

## 2. Descrição dos Agentes do Sistema

| Agente | Responsabilidade | Tecnologias Utilizadas | Entrada / Saída |
|---|---|---|---|
| **1. Reception Agent** | Validação de segurança (magic bytes `%PDF-`), checagem de tamanho (máx 50MB), higienização de caminhos contra *Path Traversal*, hashing MD5/SHA-256 e verificação de cache. | `hashlib`, `pathlib`, `re` | `DocumentState.file_path` ➔ `DocumentState.file_hash`, `file_size` |
| **2. Extractor Agent** | Extração de texto digital preservando paginação. Detecção de PDFs escaneados (<100 chars/pág) e disparo automático de fallback multimodal. | `pdfplumber`, `PyMuPDF (fitz)`, `Gemini 2.0 Flash Vision` | `file_path` ➔ `DocumentState.raw_text`, `is_scanned` |
| **3. Identifier Agent** | Segmentação e categorização semântica das seções contratuais de D&O (Condições Gerais, Coberturas, Exclusões, Franquias, Retroatividade). | `Gemini 2.0 Flash` / Modelo de Regras Heurísticas | `raw_text` ➔ `DocumentState.identified_sections` |
| **4. Structurer Agent** | Extração estruturada normalizada e validação de tipos através do contrato Pydantic v2 `ApoliceDAO`. Persistência atômica no SQLite. | `Pydantic v2`, `sqlite3`, `google-genai` | `identified_sections` ➔ `ApoliceDAO` ➔ `apolices.db` |
| **5. Comparator Agent** | Comparação campo a campo dos dados escalares, categorização de coberturas/exclusões exclusivas vs comuns e cálculo do Score de Similaridade Composto. | Motor `core.diff_engine` (Python puro otimizado) | `(ApoliceDAO, ApoliceDAO)` ➔ `ComparisonResult` |
| **6. Reporter Agent** | Geração do parecer executivo narrativo em Linguagem Natural (PT-BR) com recomendações para corretores e comitês de risco. | `Gemini 2.0 Flash` / Modelo Narrativo Paramétrico | `ComparisonResult` ➔ Markdown Relatório ➔ `comparacoes` (DB) |

---

## 3. Modelo de Dados e Diagrama Entidade-Relacionamento (DER)

A camada de persistência utiliza o banco relacional embarcado **SQLite 3**, garantindo zero infraestrutura externa e portabilidade total.

```
┌──────────────────────────────────────────────┐
│                   apolices                   │
├──────────────────────────────────────────────┤
│ PK  id                          TEXT         │  <── Hash MD5 do arquivo PDF (Idempotência)
│     nome_arquivo                TEXT         │
│     data_processamento          TEXT         │
│     segurado                    TEXT         │
│     seguradora                  TEXT         │
│     numero_apolice              TEXT         │
│     vigencia_inicio             TEXT         │
│     vigencia_fim                TEXT         │
│     premio_total                TEXT         │
│     limite_responsabilidade     TEXT         │
│     franquia                    TEXT         │
│     coberturas_json             TEXT         │  <── Array JSON de strings
│     exclusoes_json              TEXT         │  <── Array JSON de strings
│     clausulas_especiais_json    TEXT         │
│     retroatividade              TEXT         │
│     territorio                  TEXT         │
│     legislacao_aplicavel        TEXT         │
│     metodo_extracao             TEXT         │
│     confianca_extracao          REAL         │
│     campos_nao_encontrados_json TEXT         │
│     dados_completos_json        TEXT         │  <── Payload JSON canônico completo
│     created_at                  TIMESTAMP    │
└──────────────────────┬───────────────────────┘
                       │ 1
                       │
                       │ N
┌──────────────────────▼───────────────────────┐
│                 comparacoes                  │
├──────────────────────────────────────────────┤
│ PK  id                          TEXT         │  <── Formato: idA_idB
│ FK  apolice_a_id                TEXT         │
│ FK  apolice_b_id                TEXT         │
│     score_similaridade          REAL         │  <── 0.0 a 100.0%
│     data_comparacao             TEXT         │
│     resultado_json              TEXT         │  <── ComparisonResult serializado
│     relatorio_markdown          TEXT         │  <── Parecer executivo final
│     created_at                  TIMESTAMP    │
└──────────────────────────────────────────────┘
```

---

## 4. Fórmula do Score de Similaridade Composto

O índice percentual de similaridade ($S$) entre duas apólices é calculado segundo a seguinte ponderação:

$$S = S_{\text{escalar}} \times 0.40 + J(\text{Coberturas}) \times 0.40 + J(\text{Exclusões}) \times 0.20$$

Onde:
- $S_{\text{escalar}}$ é a proporção de campos escalares equivalentes (limite, franquia, prêmio, retroatividade, território, vigência).
- $J(\text{Coberturas}) = \frac{|C_A \cap C_B|}{|C_A \cup C_B|}$ é o Índice de Jaccard aplicado sobre os conjuntos de cláusulas de cobertura.
- $J(\text{Exclusões}) = \frac{|E_A \cap E_B|}{|E_A \cup E_B|}$ é o Índice de Jaccard sobre os riscos excluídos.

---

## 5. Medidas de Segurança Implementadas

1. **Proteção contra Path Traversal**: Uso da função `core.security.get_safe_destination_path` que valida se o destino resolvido permanece estritamente contido dentro do diretório sandbox `data/uploads/`.
2. **Validação de Magic Bytes**: Checagem de cabeçalho binário `%PDF-` antes de qualquer parsing, bloqueando arquivos maliciosos renomeados.
3. **Prevenção de SQL Injection**: Todas as instruções SQLite utilizam consultas parametrizadas com placeholders `?`.
4. **Isolamento de Credenciais**: Nenhuma chave ou credencial é gravada em código-fonte; uso de `.env` e variáveis de ambiente.
5. **Rede Local**: Streamlit configurado para escuta restrita em `127.0.0.1`.
