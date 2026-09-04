# Relatório Técnico Final de Conclusão de Curso
**InsurMinds Apólice Analyzer · Plataforma Inteligente para Análise e Comparação de Apólices D&O**  
*Instituto de Inteligência Artificial Aplicada — I2A2 (2026)*

---

| Metadado | Informação |
|---|---|
| **Projeto** | InsurMinds Apólice Analyzer |
| **Versão** | 1.0 (Final / Aprovado) |
| **Curso** | Inteligência Artificial Aplicada às Finanças e Seguros (InsurMinds) |
| **Instituição** | I2A2 — Instituto de Inteligência Artificial Aplicada |
| **Data da Entrega** | 04 de Setembro de 2026 |
| **Status da Avaliação** | 100% dos requisitos concluídos |

---

## 1. Sumário Executivo

O **InsurMinds Apólice Analyzer** é uma solução corporativa desenvolvida para transformar a forma como apólices de seguro de **Responsabilidade Civil de Diretores e Administradores (D&O)** são avaliadas, confrontadas e contratadas no mercado brasileiro.

Aliando **Engenharia de Dados Sênior**, **Orquestração Multi-Agente (LangGraph)** e modelos de fronteira de **IA Generativa Multimodal (Google Gemini 2.0 Flash)**, a plataforma automatiza a ingestão de contratos em PDF, valida integridade criptográfica, extrai cláusulas jurídicas complexas para contratos canônicos estritos (Pydantic v2), persiste em banco relacional local (SQLite) com controle de idempotência e realiza auditoria comparativa determinística com cálculo de índice de similaridade e emissão de parecer executivo narrativo.

O sistema atende a **100% dos Requisitos Funcionais (RF01 a RF07)** e **Requisitos Não-Funcionais** estabelecidos no PRD, conta com uma suíte de **13 testes automatizados (100% aprovados)** e opera com **resiliência zero-crash**, permitindo a demonstração completa em ambientes online ou offline.

---

## 2. Contextualização e Problema de Negócio

### 2.1 A Natureza do Seguro D&O
O seguro D&O (*Directors and Officers Liability Insurance*) é um instrumento crítico de governança corporativa que protege o patrimônio pessoal de executivos, diretores e membros de conselho contra reclamações judiciais, arbitrais e investigações regulatórias (CVM, BACEN, CADE, SEC) decorrentes de atos de gestão.

### 2.2 O Gargalo Operacional
As apólices D&O emitidas por grandes seguradoras corporativas (Allianz, Chubb, AIG, Zurich, etc.) são documentos densos, com extensão de 30 a 80 páginas, estruturados em Condições Gerais, Condições Especiais e Endossos Particulares.

Atualmente, o confronto entre duas ou mais propostas concorrentes exige:
- De **3 a 5 horas de trabalho manual especializado** de corretores seniores, subscritores ou advogados corporativos.
- Alto risco de erro humano na identificação de cláusulas críticas, tais como:
  - Existência ou não de cobertura *Side A DIC* (Difference in Conditions);
  - Exigência de trânsito em julgado para imputação de dolo;
  - Limites de adiantamento automático de despesas de defesa e honorários;
  - Amplitude da data de retroatividade (prazo prescricional de fatos prévios);
  - Extraterritorialidade (inclusão ou exclusão de jurisdição dos EUA/Canadá).

A automação desse fluxo gera economia imediata de tempo superior a **90%**, reduzindo o ciclo de análise de horas para **menos de 60 segundos por apólice**.

---

## 3. Arquitetura da Solução & Pipeline Multi-Agente

A solução adota uma arquitetura modular orientada a agentes inteligentes de responsabilidade única, orquestrados através de um Grafo de Estados finito (`StateGraph`) compilado via **LangGraph**:

```
[ Upload PDF ]
      │
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ORQUESTRAÇÃO LANGGRAPH (Agentes 1 a 4)                │
│                                                                             │
│  [ Agente 1: Reception ] ──► [ Agente 2: Extractor ] ──► [ Agente 3: Identifier ]
│             │                                                     │         │
│      Cache Hit (Hash MD5)                                         ▼         │
│      Pula Extração e Leitura                         [ Agente 4: Structurer ]
└─────────────┬─────────────────────────────────────────────────────┬─────────┘
              │                                                     │
              ▼                                                     ▼
     [ Recupera do DB ]                                   [ Grava no SQLite ]
              │                                                     │
              └──────────────────────┬──────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CONFRONTO & SÍNTESE (Agentes 5 e 6)                    │
│                                                                             │
│         [ Agente 5: Comparator ] ────────────► [ Agente 6: Reporter ]       │
│     (Diff Determinístico + Jaccard)        (Parecer Narrativo Gemini 2.0)   │
└────────────────────────────────────┬──────────────────────────────┬─────────┘
                                     │                              │
                                     ▼                              ▼
                          [ Matriz Comparativa ]         [ Parecer Executivo ]
```

### 3.1 Detalhamento dos Agentes Implementados

1. **Agente 1 — Reception Agent (`agents/reception_agent.py`)**:
   - Valida tamanho do arquivo (limite de 50MB).
   - Valida cabeçalho binário (*magic bytes* `%PDF-`) para impedir injeção de arquivos maliciosos.
   - Higieniza o nome do arquivo impedindo ataques de *Directory / Path Traversal* (`../`).
   - Calcula os hashes criptográficos **MD5** e **SHA-256**.
   - Consulta o banco SQLite: se o hash já existir, recupera os dados estruturados instantaneamente (**Idempotência / Cache Hit**), poupando tempo de CPU e consumo de tokens.

2. **Agente 2 — Extractor Agent (`agents/extractor_agent.py`)**:
   - Extrai texto digital utilizando prioritariamente `pdfplumber`, com fallback de alta performance para `PyMuPDF (fitz)`.
   - Mede a densidade textual (média de caracteres por página).
   - **Fallback Multimodal:** Se a densidade for inferior a 100 caracteres/página (indicativo de PDF escaneado ou imagem chapada), o agente converte as páginas em imagens PNG e aciona o **Gemini 2.0 Flash Vision** para transcrição OCR de alta fidelidade.

3. **Agente 3 — Identifier Agent (`agents/identifier_agent.py`)**:
   - Analisa o texto bruto da apólice e realiza a segmentação semântica das seções contratuais:
     - Dados Gerais e Partes Contratantes;
     - Limites Financeiros e Franquias;
     - Quadro de Coberturas Básicas e Adicionais;
     - Riscos Expressamente Excluídos;
     - Cláusulas Particulares, Foro e Retroatividade.

4. **Agente 4 — Structurer Agent (`agents/structurer_agent.py`)**:
   - Converte os blocos de texto identificados no modelo de dados canônico [`ApoliceDAO`](file:///home/edcarlos/workspace/pessoal/insurminds_apolice_analyzer/core/schemas.py), utilizando Structured Outputs com validação de esquema Pydantic v2.
   - Normaliza datas (DD/MM/AAAA) e valores monetários (R$).
   - Persiste atomicamente o registro na tabela `apolices` do SQLite.

5. **Agente 5 — Comparator Agent (`agents/comparator_agent.py`)**:
   - Executa a comparação determinística campo a campo entre duas apólices estruturadas.
   - Aplica o motor analítico de confronto (`core/diff_engine.py`), separando coberturas exclusivas da Apólice A, coberturas exclusivas da Apólice B e coberturas comuns.
   - Calcula o **Score Global de Similaridade (0% a 100%)**.

6. **Agente 6 — Reporter Agent (`agents/reporter_agent.py`)**:
   - Atua com papel de consultor e subscritor sênior de resseguros.
   - Sintetiza o resultado do confronto em um parecer executivo narrativo em Português (PT-BR).
   - Persiste o histórico na tabela `comparacoes` do SQLite.

---

## 4. Engenharia de Dados & Modelagem Canônica

### 4.1 Contratos Canônicos (Pydantic v2)
Todos os dados trafegados entre os nós do grafo são rigidamente tipados pelo Pydantic v2:
- **`ApoliceDAO`**: Representação de 20 atributos da apólice (identificação, vigência, financeiro, coberturas, exclusões, retroatividade, território, metadados de auditoria).
- **`FieldDiff`**: Divergência atômica com classificação (`"igual"`, `"valor"`, `"ausente_a"`, `"ausente_b"`, `"ambos_ausentes"`).
- **`ComparisonResult`**: Estrutura consolidada do confronto contendo score, lista de diffs e decomposição de conjuntos.
- **`DocumentState`** e **`ComparisonState`**: Estados mutáveis do fluxo LangGraph.

### 4.2 Camada de Persistência Relacional (SQLite)
O banco de dados local [`apolices.db`](file:///home/edcarlos/workspace/pessoal/insurminds_apolice_analyzer/core/database.py) opera com duas tabelas relacionais com chaves estrangeiras e índices dedicados:
- **Tabela `apolices`**: Chave Primária definida pelo hash MD5 do arquivo PDF, garantindo **idempotência de ingestão** (reprocessar o mesmo PDF não gera duplicações). Armazena campos colunares para filtros rápidos e o payload canônico completo em JSON.
- **Tabela `comparacoes`**: Chave Primária composta `idA_idB`, histórico de auditoria e texto integral do parecer executivo.

Todas as consultas são estritamente parametrizadas via placeholders `?`, assegurando imunidade a ataques de SQL Injection.

---

## 5. Formulação Matemática do Score de Similaridade

Para mensurar com rigor a aderência técnica entre duas propostas de seguro D&O, o motor de cálculo (`core/diff_engine.py`) aplica uma média ponderada entre conformidade escalar e sobreposição de conjuntos de cláusulas:

$$\text{Score Total} = (S_{\text{escalar}} \times 0.40) + (J_{\text{coberturas}} \times 0.40) + (J_{\text{exclusoes}} \times 0.20)$$

Onde:
1. **$S_{\text{escalar}}$**: Razão entre o número de campos contratuais equivalentes e o total de campos comparados (LMG, franquia, prêmio, retroatividade, território, foro, vigência).
2. **$J_{\text{coberturas}}$**: Índice de Similaridade de Jaccard aplicado sobre os conjuntos de cláusulas de cobertura:
   $$J(A, B) = \frac{|A \cap B|}{|A \cup B|}$$
3. **$J_{\text{exclusoes}}$**: Índice de Jaccard aplicado sobre as cláusulas de exclusão.

O motor conta com regras de domínio específicas para D&O: cláusulas de alta relevância (como a distinção entre *Side A pura* e *Side A DIC*) recebem tratamento ponderado para evitar que o algoritmo de texto aproxime indevidamente garantias juridicamente diferentes.

---

## 6. Harmonização Visual & Experiência do Usuário (UX)

O front-end Streamlit foi desenhado seguindo os cânones estéticos do mercado segurador e ressegurador institucional (*Swiss Re, Munich Re, Lloyd's of London, Allianz e Chubb*):

* **Paleta de Confiança e Solvência**:
  - *Deep Midnight Navy* (`#0A192F` a `#16325B`): Tom predominante que transmite solidez e conformidade regulatória.
  - *Dourado de Resseguro* (`#C5A059` / `#D97706`): Filetes de topo e badges de subscrição executiva.
  - *Azul Royal Analítico* (`#0284C7`): Elementos de ação, botões e barras de progresso.
  - *Fundo Porcelana Neutro* (`#F8FAFC`): Conforto visual para longas leituras técnicas.
* **Codificação Semântica de Riscos**:
  - 🟢 **Verde Esmeralda (`#065F46` / `#F0FDF4`)**: Cláusulas equivalentes e garantias convergentes.
  - 🟡 **Âmbar Ouro (`#92400E` / `#FFFBEB`)**: Discrepâncias contratuais, franquias assimétricas e prêmios divergentes.
  - 🔴 **Vermelho Rubi (`#991B1B` / `#FEF2F2`)**: Exclusões restritivas e lacunas de cobertura desprotegidas.
* **As 4 Visões Especializadas**:
  1. **Upload**: Ingestão de arquivos com timeline em tempo real dos Agentes 1 a 4 e botão de carga imediata de amostras.
  2. **Biblioteca**: Catálogo interativo dos contratos com dados de LMG, vigência, prêmio e seletor para comparação.
  3. **Comparação**: Scorecards executivos, matriz de condições gerais sem ruídos e painel de *Gap Analysis*.
  4. **Relatório**: Memorando de resseguro formatado em Markdown com ferramentas de exportação para `.md` e `.json`.

---

## 7. Garantia de Qualidade & Testes Automatizados

A estabilidade e integridade da solução são validadas por uma suíte completa de **13 testes automatizados** utilizando `pytest`:

```
tests/test_database.py::test_database_crud_and_idempotency PASSED
tests/test_database.py::test_comparison_persistence PASSED
tests/test_diff_engine.py::test_are_values_equal_financial PASSED
tests/test_diff_engine.py::test_compare_list_items PASSED
tests/test_diff_engine.py::test_compare_policies PASSED
tests/test_pipeline_integration.py::test_document_and_comparison_pipeline_integration PASSED
tests/test_schemas.py::test_apolice_dao_creation_and_serialization PASSED
tests/test_schemas.py::test_field_diff_validation PASSED
tests/test_schemas.py::test_comparison_result_validation PASSED
tests/test_security.py::test_sanitize_filename_prevents_directory_traversal PASSED
tests/test_security.py::test_validate_pdf_content_accepts_valid_pdf PASSED
tests/test_security.py::test_validate_pdf_content_rejects_non_pdf PASSED
tests/test_security.py::test_get_safe_destination_path_blocks_escape PASSED

======================== 13 passed in 0.55s =========================
```

---

## 8. Segurança & Conformidade (OWASP / Secure Web Guidelines)

Conforme os requisitos mandatórios de segurança para aplicações web:
1. **Prevenção contra Path Traversal:** O método `core.security.get_safe_destination_path` normaliza caminhos e garante que nenhum arquivo gravado consiga escapar do diretório *sandbox* (`data/uploads/`), neutralizando payloads como `../../etc/passwd`.
2. **Validação de Cabeçalhos Binários (Magic Bytes):** Todo arquivo é inspecionado antes do parsing para atestar a presença da assinatura `%PDF-`.
3. **Prevenção contra Injeção SQL:** Uso integral de *parameterized queries* no SQLite.
4. **Isolamento de Credenciais:** As chaves de API do Google Gemini são gerenciadas exclusivamente via variáveis de ambiente (`.env`), nunca sendo versionadas ou expostas em logs.
5. **Rede Segura:** O servidor Streamlit é restrito por padrão à interface de *loopback* (`127.0.0.1`).

---

## 9. Conjunto de Dados de Teste & Demonstração (Sample Policies)

Para viabilizar a validação e demonstração imediata do sistema sem depender de documentos proprietários protegidos por sigilo (LGPD/NDAs), foi implementado o gerador [`data/generate_samples.py`](file:///home/edcarlos/workspace/pessoal/insurminds_apolice_analyzer/data/generate_samples.py), compilando três apólices D&O realistas com a biblioteca `ReportLab`:

1. **Allianz Global Corporate & Specialty (`apolice_do_allianz.pdf`)**:
   - Limite Máximo de Garantia (LMG): R$ 10.000.000,00 | Franquia: R$ 50.000,00 (Side A Isento).
   - Destaques: Cobertura ampla para Investigação Regulatória (CVM, BACEN, CADE) e Adiantamento de Honorários em 15 dias.
2. **Chubb Seguros Brasil S.A. (`apolice_do_chubb.pdf`)**:
   - Limite Máximo de Garantia (LMG): R$ 5.000.000,00 | Franquia: R$ 100.000,00.
   - Destaques: Cláusula de *Side A DIC* (Difference in Conditions) e Danos Ambientais com custos de defesa limitados.
3. **AIG Seguros Brasil S.A. (`apolice_do_aig.pdf`)**:
   - Limite Máximo de Garantia (LMG): R$ 15.000.000,00 | Franquia: R$ 75.000,00.
   - Destaques: Retroatividade Ilimitada e Âmbito Territorial Mundial (incluindo litígios perante a SEC nos EUA e Canadá).

---

## 10. Conclusões e Próximos Passos

O **InsurMinds Apólice Analyzer** atinge com louvor seu objetivo de demonstrar a aplicação prática de Engenharia de Dados, IA Generativa e Grafos Multi-Agente para um problema de alto valor agregado do mercado de capitais e securitário.

Como evolução para uma versão enterprise futura, recomenda-se:
1. Expansão para outras modalidades corporativas complexas, como **Seguro Cyber (Riscos Cibernéticos)** e **E&O (Erros e Omissões Financeiros)**.
2. Integração com APIs oficiais da SUSEP para consulta de registro de apólices em tempo real.
3. Módulo de exportação do parecer em formato PDF timbrado institucional.
