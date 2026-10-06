# Relatório Técnico Final de Conclusão de Curso
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
| **Integrantes** | Edcarlos Cardôso de Farias · Eric Narciso Pimentel dos Santos |
| **Data da Entrega** | 06 de Outubro de 2026 |
| **Status da Avaliação** | 100% dos requisitos atendidos · 182/182 Testes Automatizados Aprovados (Linux: PASS · Windows 11: PENDING REAL VALIDATION) |

---

## 1. Resumo Executivo

O **InsurMinds Apólice Analyzer** é uma plataforma inteligente concebida como ferramenta de **análise e comparação assistida de apólices de seguro de Responsabilidade Civil de Diretores e Administradores (D&O)**. Desenvolvido como Trabalho de Conclusão de Curso no âmbito do programa *InsurMinds* do **Instituto de Inteligência Artificial Aplicada (I2A2)**, o sistema aborda o desafio de processar, estruturar e confrontar contratos securitários complexos que tipicamente contêm de 30 a 80 páginas de linguagem jurídica e financeira densa.

A solução estrutura suas etapas sob o padrão de **Pipeline Multi-Agente Orientado a Estados**, modelado formalmente via Grafos de Estados Finitos com **LangGraph**. Para a execução interativa na interface do MVP em Streamlit, o sistema emprega *runners* procedurais integrados que orquestram os agentes de forma determinística, permitindo controle granular de etapas, callbacks visuais e atualização progressiva de progresso em tempo real. O fluxo abrange **6 agentes inteligentes** especializados com estrita segregação de responsabilidades: *Reception Agent*, *Extractor Agent*, *Identifier Agent*, *Structurer Agent*, *Comparator Agent* e *Reporter Agent*.

O sistema suporta ingestão multimodal resiliente, abrangendo documentos em formato **PDF digital**, **PDF escaneado** e imagens nos formatos **PNG**, **JPG** e **JPEG**, todos validados criptograficamente por cabeçalhos binários (*magic bytes*). A extração combina processamento vetorial direto em memória via `pdfplumber` para textos digitais e rotas multimodais via **Google Gemini 2.0 Flash Lite Vision** ou motor local **PyMuPDF + Tesseract OCR 5.x** para arquivos rasterizados.

Para restringir a estrutura das respostas e reduzir erros de formatação em tarefas de IA generativa, a plataforma implementa **Structured Output** apoiado em esquemas do **Pydantic v2** (`ApoliceDAO`), modelado em estrita observância à regulamentação da SUSEP (Circular nº 637/2021, Ramo 0378). Essa abordagem impõe conformidade de tipos e viabiliza validação estrita de dados, embora não garanta por si só a veracidade semântica das informações extraídas. A confiabilidade semântica é assegurada pelas regras analíticas de validação e pela rastreabilidade proporcionada pelo contrato `EvidenceItem`. Em paralelo, o sistema disponibiliza um **Modo de Contingência Determinístico 100% offline**, operando por meio de heurísticas canônicas pré-calibradas, o que assegura funcionamento mesmo na ausência de chaves de API externa ou conectividade com a internet.

Um diferencial de governança e auditoria da solução é o princípio da **rastreabilidade ponta a ponta**: cada inferência, dado estruturado e divergência identificada é vinculada a um objeto canônico de proveniência (`EvidenceItem`), registrando número da página, trecho textual literal (*snippet*), método de extração e grau de confiança analítica. O motor de comparação (`core/diff_engine.py`) opera de forma determinística, calculando um **Score Global de Similaridade** fundamentado no Índice de Jaccard ponderado sobre os conjuntos de coberturas, exclusões e conformidade de parâmetros escalares.

A interface do usuário, desenvolvida em **Streamlit**, adota o padrão estético corporativo *Dark Obsidian*, oferecendo 6 páginas principais de navegação lateral além de uma visão dedicada de detalhe documental com *drawer* interativo de evidências. A qualidade e estabilidade de software são atestadas por uma suíte de **182 testes automatizados aprovados (0 falhas, 0 erros)** em ambiente Linux homologado. Em ambiente Windows 11, o suporte técnico encontra-se preparado em código, com o status formal mantido como **PENDING REAL VALIDATION** devido a uma ocorrência de parsing/encoding no script de inicialização do Windows PowerShell 5.1 durante a fase de validação física em máquina real.

---

## 2. Introdução

A contratação e gestão de apólices de seguro corporativo de linhas financeiras no Brasil, em especial o ramo de Responsabilidade Civil de Diretores e Administradores (D&O), representam uma das tarefas mais sensíveis da governança de grandes empresas, multinacionais e companhias de capital aberto. O crescimento das demandas societárias, ações civis públicas, litígios concorrenciais e investigações regulatórias conduzidas por órgãos como Comissão de Valores Mobiliários (CVM), Banco Central do Brasil (BACEN), Conselho Administrativo de Defesa Econômica (CADE) e agências setoriais elevou a relevância estratégica dessas apólices.

Contudo, a análise comparativa entre propostas de diferentes seguradoras continua a ser um processo essencialmente manual, custoso e propenso a falhas humanas de interpretação. Documentos com dezenas de páginas, terminologia polissêmica e condições especiais dispersas criam assimetrias informacionais que dificultam a tomada de decisão por corretores, consultores jurídicos e comitês de risco.

O presente projeto propõe enfrentar esse gargalo por meio da aplicação rigorosa de técnicas avançadas de Engenharia de Dados, Inteligência Artificial Generativa e Sistemas Multi-Agente. Longe de pretender substituir o julgamento humano especializado, o **InsurMinds Apólice Analyzer** posiciona-se como uma ferramenta de **análise assistida e auditoria contratual**. O sistema transforma documentos brutos em conhecimento canônico estruturado, destaca discrepâncias objetivas e fundamenta cada conclusão na própria evidência textual da apólice, preservando integralmente a autonomia decisória dos profissionais responsáveis.

---

## 3. Contexto e Problema de Negócio

### 3.1 A Natureza e a Complexidade do Seguro D&O
O seguro D&O (*Directors and Officers Liability Insurance*) destina-se a garantir a proteção do patrimônio pessoal de administradores, diretores, conselheiros de administração e fiscais quando responsabilizados civil, administrativa ou trabalhista por atos de gestão praticados no exercício de suas funções corporativas.

Diferentemente de seguros massificados (como automóvel ou vida), as apólices D&O caracterizam-se por alta complexidade contratual:
1. **Estrutura Tripartite de Garantias:**
   - **Side A:** Proteção direta aos administradores para perdas e custos de defesa em situações nas quais a sociedade empresária não pode ou não tem autorização legal/estatutária para indenizá-los diretamente (por exemplo, insolvência corporativa ou vedações legais). Geralmente contratada sem aplicação de franquia.
   - **Side B:** Reembolso corporativo (*Company Reimbursement*) à sociedade tomadora caso esta tenha adiantado ou indenizado previamente os custos e perdas de seus administradores.
   - **Side C:** Cobertura conferida à própria entidade jurídica (*Entity Coverage*) exclusivamente para demandas judiciais ou administrativas decorrentes de transações com valores mobiliários (*securities claims*).
   - **Side A DIC (*Difference in Conditions*):** Cláusula de garantia adicional e independente que atua em excesso ou na insuficiência das coberturas primárias, preenchendo lacunas de insolvência ou recusas injustificadas de cobertura.
2. **Condições Particulares e Endossos:** Apólices reais combinam Condições Gerais padronizadas com dezenas de endossos customizados (ex.: cobertura para penhora online, despesas de publicidade para mitigação de crise de imagem, custas de extradição, severabilidade de declarações e adiantamento emergencial de honorários).
3. **Prazos Temporais Complexos:** Definição da data de retroatividade (marco a partir do qual atos pretéritos desconhecidos passam a ser amparados), período de notificação de sinistros e prazos complementares/suplementares de reclamação.

### 3.2 O Gargalo Operacional e de Governança
A rotina tradicional de subscrição, cotação e auditoria de contratos de D&O impõe severas barreiras operacionais:
- **Sobrecarga de Tempo:** Confrontar duas propostas detalhadas de 40 a 80 páginas demanda extenso trabalho minucioso de analistas seniores e advogados corporativos, sujeito a fadiga cognitiva e dispersão.
- **Risco de Omissão Crítica:** Detalhes redacionais sutis — como a exigência de decisão judicial transitada em julgado para exclusão de dolo *versus* mera imputação inicial, ou limites subliminares para investigações preliminares — passam frequentemente despercebidos.
- **Falta de Padronização e Rastreabilidade:** Relatórios comparativos manuais costumam ser redigidos em planilhas ou memórias de cálculo heterogêneas, sem vínculo rastreável à página ou cláusula do contrato original, dificultando auditorias de conformidade posteriores.

A proposta do InsurMinds Apólice Analyzer é mitigar esse gargalo através da automação inteligente do ciclo de ingestão, extração e confronto, proporcionando expressiva agilidade na preparação documental, reduzindo o esforço manual de triagem e conferindo transparência absoluta por meio de evidências textuais auditáveis.

---

## 4. Objetivos

### 4.1 Objetivo Geral
Projetar, construir, validar e documentar um Produto Mínimo Viável (MVP) em nível de *Release Candidate* para análise e comparação assistida de apólices de seguro D&O, integrando processamento de documentos multimodal, modelagem de estados multi-agente inspirada em LangGraph com execução procedural interativa, modelos de linguagem com Structured Output e um motor de confronto determinístico auditável.

### 4.2 Objetivos Específicos
1. **Engenharia de Ingestão:** Implementar pipeline capaz de receber documentos em PDF (digitais e escaneados) e imagens (PNG, JPG, JPEG), aplicando validação de integridade por *magic bytes* e controle de idempotência por hashing criptográfico.
2. **Extração Híbrida e Resiliente:** Desenvolver rota de extração vetorial direta via `pdfplumber` e rotas de visão computacional (Gemini Vision e PyMuPDF + Tesseract OCR), mantendo metadados de paginação.
3. **Modelagem de Dados Canônica:** Estruturar as entidades do domínio securitário no modelo Pydantic v2 `ApoliceDAO`, garantindo compatibilidade com a taxonomia da Circular SUSEP nº 637/2021 (Ramo 0378).
4. **Arquitetura Multi-Agente:** Modelar os estados do pipeline através de Grafos de Estados Finitos (LangGraph) e implementar execução modular no MVP com controle procedural e isolamento de responsabilidades entre recepção, extração, identificação, estruturação, comparação e geração de relatório.
5. **Rastreabilidade e Evidências:** Associar a cada inferência documental um objeto `EvidenceItem` com página de origem, citação textual (*snippet*), método de extração e grau de confiança analítica.
6. **Comparação Determinística:** Desenvolver motor analítico de confronto de cláusulas e formulação matemática do Score de Similaridade Composto via Coeficiente de Jaccard ponderado.
7. **Modo de Contingência Autônomo:** Garantir operação 100% offline através de heurísticas determinísticas, eliminando dependências externas obrigatórias para execução do sistema.
8. **Interface Corporativa:** Desenvolver aplicação web em Streamlit no tema *Dark Obsidian*, com 6 páginas de navegação intuitiva e visualização de evidências.
9. **Garantia de Qualidade e Governança:** Consolidar suíte de testes automatizados com 182 testes aprovados, auditando segurança, persistência, regras de negócio e portabilidade multiplataforma.

---

## 5. Requisitos do Sistema

### 5.1 Requisitos Funcionais (RF)
A tabela a seguir apresenta os requisitos funcionais mapeados a partir do *Product Requirements Document* (PRD) oficial e homologados no Release Candidate:

| ID | Nome do Requisito | Descrição Técnica e Critério de Aceite | Situação |
|---|---|---|:---:|
| **RF01** | **Upload e Validação de Documentos** | Suporte a arquivos PDF, PNG, JPG e JPEG. Validação mandatória de cabeçalho binário (*magic bytes*). Limite configurável de 50 MB por arquivo. Higienização contra *Directory Traversal*. Deduplicação via hash MD5. Barra de progresso visual. | **PASS** |
| **RF02** | **Extração Multimodal Híbrida** | Extração primária via `pdfplumber` para documentos digitais. Detecção de densidade textual e chaveamento para rota multimodal (Gemini 2.0 Flash Lite Vision) ou OCR local (PyMuPDF + Tesseract 5.x) para scans e imagens. | **PASS** |
| **RF03** | **Identificação e Estruturação D&O** | Identificação semântica de seções contratuais (Condições Gerais, Coberturas Básicas e Adicionais, Exclusões, Franquias/POS, Retroatividade, Âmbito Territorial). Mapeamento canônico no modelo Pydantic v2 `ApoliceDAO` (Ramo SUSEP 0378). | **PASS** |
| **RF04** | **Armazenamento e Idempotência** | Persistência relacional em banco de dados SQLite local (`apolices.db`). Idempotência garantida pela chave primária MD5: reenvios do mesmo arquivo recuperam os dados sem reprocessamento. | **PASS** |
| **RF05** | **Comparação Analítica e Gaps** | Confronto determinístico campo a campo entre duas apólices estruturadas. Cálculo do Score Global de Similaridade (Jaccard ponderado). Separação de coberturas exclusivas da Apólice A, exclusivas da Apólice B e coberturas comuns. | **PASS** |
| **RF06** | **Parecer Executivo e Rastreabilidade** | Geração de parecer narrativo técnico em Português (PT-BR) com suporte de IA ou contingência determinística. Ancoragem de cada achado no contrato `EvidenceItem`. Exportação em Markdown (`.md`) e JSON estruturado. | **PASS** |
| **RF07** | **Interface Reativa Multipage** | Interface gráfica construída em Streamlit com 6 páginas principais no menu lateral (`Início`, `Nova análise`, `Comparações`, `Documentos`, `Relatórios`, `Configurações`) e subvisão de `Detalhe`. *Drawer* interativo de evidências. | **PASS** |

### 5.2 Requisitos Não-Funcionais (RNF)

| ID | Categoria | Especificação e Validação Técnica | Situação |
|---|---|---|:---:|
| **RNF01** | **Performance** | Extração vetorial direta em memória sem sobrecarga de rede ou OCR para textos digitais, assegurando processamento local fluido de documentos e execução ágil das regras analíticas. | **PASS** |
| **RNF02** | **Usabilidade** | Fluxo de ponta a ponta completável em poucos passos intuitivos. Identidade visual executiva com tokens centralizados (`ui/tokens.py`). Comunicação em Português do Brasil. | **PASS** |
| **RNF03** | **Confiabilidade e Resiliência** | Arquitetura com dupla rota de execução. Operação 100% autônoma offline na ausência de chaves de API externa. Tratamento estrito de exceções por agente impedindo travamentos gerais (*zero-crash*). | **PASS** |
| **RNF04** | **Segurança e Higiene de Dados** | Chaves lidas exclusivamente via variáveis de ambiente (`os.getenv`). `.env` e `.db` isolados no `.gitignore`. Proteção comprovada contra *Path Traversal* e *SQL Injection*. Zero segredos no repositório. | **PASS** |
| **RNF05** | **Portabilidade Cross-Platform** | Compatibilidade estrutural Linux e Windows 11 baseada em `pathlib.Path`, scripts dedicados e resolução dinâmica de caminhos de OCR (`core/config.py`). | **Linux: PASS**<br>**Win 11: PENDING** |

---

## 6. Fundamentação Teórica e Tecnológica

### 6.1 O Marco Regulatório da SUSEP para o Seguro D&O
No Brasil, o seguro de D&O é regido pelas diretrizes da **Circular SUSEP nº 637, de 27 de julho de 2021**, que consolidou as regras para a estruturação de seguros de responsabilidade civil para diretores e administradores de pessoas jurídicas (Ramo SUSEP 0378).

A norma estabelece princípios fundamentais que orientaram a modelagem do sistema:
- **Inadmissibilidade de Cobertura para Atos Dolosos:** É expressamente vedada a indenização securitária decorrente de atos ilícitos praticados com dolo por parte dos segurados. Todavia, a prática de mercado exige que a exclusão de dolo somente se consume após **decisão judicial ou arbitral transitada em julgado**, impondo à seguradora o dever de adiantar custos de defesa até a referida condenação definitiva. O InsurMinds Apólice Analyzer foi calibrado para mapear essa sutileza contratual específica.
- **Princípio da Severabilidade (*Severability Clause*):** Estabelece que as declarações, conhecimentos ou condutas de um administrador segurado não devem prejudicar os direitos de outros administradores de boa-fé. A presença ou ausência dessa cláusula é um dos pontos focais da matriz de comparação.
- **Tipologia de Coberturas Adicionais:** A Circular 637/2021 autoriza a inclusão de garantias específicas, tais como custos de defesa em investigações preliminares, responsabilidade por poluição e danos ambientais, custos de extradição, gestão de crise e indisponibilidade de bens/penhora online.

### 6.2 Modelagem de Estados (LangGraph) e Execução Procedural no MVP
Pipelines complexos de processamento documental beneficiam-se da formalização de estados e fronteiras modulares. A arquitetura do sistema adota o framework **LangGraph** para modelar conceitualmente as máquinas de estado (`DocumentState` e `ComparisonState`) através de Grafos de Estados Finitos (*StateGraph*).

Nesse paradigma conceitual:
- O estado global de processamento é modelado como contratos Pydantic imutáveis por etapa.
- Cada agente funciona como um nó (*node*) que recebe o estado, executa sua transformação e emite um delta de atualização.
- As arestas (*edges*) representam transições de estado (tais como *Cache Hit*, erro de validação ou seleção de rota de extração).

Na implementação prática da interface interativa do MVP, a execução em runtime é conduzida por executores procedurais integrados ao ciclo de vida do **Streamlit**. Essa abordagem desacoplada permite acionar os agentes sequencialmente, fornecendo callbacks visuais, atualizações dinâmicas da barra de progresso e tratamento direto de exceções na tela, sem depender exclusivamente da execução contínua assíncrona do grafo em tempo de execução web.

### 6.3 IA Generativa Multimodal e Structured Outputs
O emprego de Modelos de Linguagem de Grande Porte (LLMs) multimodais permite a interpretação de cláusulas contratuais complexas e a leitura visual de documentos digitalizados. Contudo, saídas em texto livre sujeitam-se a erros de formatação JSON e inconsistências de schema.

Para mitigar tais falhas estruturais, a plataforma utiliza **Structured Output** via SDK oficial `google-genai` com o modelo **Google Gemini 2.0 Flash Lite**. O contrato Pydantic `ApoliceDAO` é fornecido como esquema estrito, restringindo a saída do modelo à gramática definida e reduzindo drasticamente erros de decodificação e parsing.

É crucial destacar, todavia, que o Structured Output atua sobre a sintaxe e a tipagem dos dados, **não assegurando por si só a veracidade semântica** das informações extraídas. A mitigação de alucinações semânticas e a confiabilidade dos dados repousam na validação por regras de domínio e, fundamentalmente, na rastreabilidade proporcionada pelo contrato `EvidenceItem`, que ancora cada dado ao trecho literal do documento de origem para verificação humana.

### 6.4 Teoria dos Conjuntos e Coeficiente de Similaridade de Jaccard
A mensuração quantitativa de equivalência entre dois contratos extensos requer rigor matemático. O sistema emprega o **Índice de Jaccard**, métrica estatística clássica para comparação de similaridade e diversidade entre conjuntos finitos:

$$J(A, B) = \frac{|A \cap B|}{|A \cup B|}$$

Aplicado separadamente sobre os conjuntos de coberturas contratuais ($C_A, C_B$) e cláusulas de exclusão ($E_A, E_B$), o coeficiente varia de $0.0$ (disjunção total) a $1.0$ (identidade completa de conjuntos). Quando combinado a uma métrica de conformidade escalar ($S_{\text{escalar}}$) para valores numéricos e prazos, o índice produz um indicador consistente de convergência contratual.

### 6.5 Engenharia de Evidências e Rastreabilidade Documental
No setor securitário e financeiro, a explicabilidade de sistemas baseados em inteligência artificial é imperativo regulatório e deontológico. O sistema implementa o paradigma de **Ancoragem Probatória**: nenhuma informação estruturada é admitida na camada analítica sem o preenchimento obrigatório de sua tupla de evidência (página de origem, trecho literal citável, técnica de extração e grau de confiança analítica). Essa abordagem facilita a auditoria técnica e a validação pelos analistas, permitindo conferir a procedência de qualquer dado diretamente no documento original.

---

## 7. Arquitetura do Sistema

A arquitetura do InsurMinds Apólice Analyzer foi concebida sob o padrão de **Camadas Desacopladas com Modelagem de Estados Multi-Agente**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       CAMADA DE APRESENTAÇÃO (STREAMLIT UI)                 │
│   [Início]   [Nova análise]   [Comparações]   [Documentos]   [Relatórios]   │
│                 └── Visão de Detalhe com Drawer de Evidências               │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Eventos / Invocação Procedural
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│             CAMADA DE ORQUESTRAÇÃO (MODELAGEM LANGGRAPH + RUNNERS)          │
│                                                                             │
│  [ Reception ] ──► [ Extractor ] ──► [ Identifier ] ──► [ Structurer ]      │
│        │                 │                                     │            │
│    Cache Hit        Branch OCR                            Salva no SQLite   │
│   (Pula Etapa)    (Gemini/Tess)                                             │
│                                                                             │
│          [ Comparator Agent ] ──────────────► [ Reporter Agent ]            │
│       (Diff Determinístico + Jaccard)       (Síntese Narrativa + Evidências)│
└──────────────────────┬──────────────────────────────────────┬───────────────┘
                       │                                      │
                       ▼                                      ▼
┌──────────────────────────────────────┐  ┌───────────────────────────────────┐
│     CAMADA DE DOMÍNIO & REGRAS       │  │    CAMADA DE PERSISTÊNCIA RELAC.  │
│  • core/schemas.py (Pydantic v2)     │  │  • SQLite (apolices.db)           │
│  • core/diff_engine.py               │  │  • Tabela 'apolices' (PK: MD5)    │
│  • core/llm_client.py                │  │  • Tabela 'comparacoes'           │
│  • core/security.py                  │  │  • Transações ACID Parametrizadas │
│  • core/config.py                    │  │  • Migração DDL Automática        │
└──────────────────────────────────────┘  └───────────────────────────────────┘
```

### 7.1 Módulos do Sistema
- `agents/`: Implementação isolada de cada agente inteligente e definição dos grafos canônicos em `graph.py`.
- `core/`: Núcleo de regras analíticas, esquemas tipados, cliente de LLM, infraestrutura de banco de dados, resolução de OCR e segurança.
- `ui/`: Interface reativa dividida em páginas modulares, sistema de estilos CSS customizados e design tokens centralizados.
- `data/`: Gerador de apólices sintéticas e diretório local para persistência do banco relacional.
- `tests/`: Suíte de 182 testes automatizados cobrindo todas as camadas da aplicação.
- `scripts/`: Ferramentas de automação e scripts de inicialização para ambientes Linux e Windows.

---

## 8. Pipeline Multi-Agente e Orquestração

O pipeline do InsurMinds modela dois grafos conceituais de estados: o **Pipeline de Documento (`DocumentState`)** e o **Pipeline de Comparação (`ComparisonState`)**, estruturados formalmente em `agents/graph.py` com o LangGraph. Durante a operação interativa na interface do usuário, a invocação ocorre de forma procedural e controlada, etapa a etapa, viabilizando feedback visual em tempo real ao usuário.

### 8.1 Agente 1 — Reception Agent (`agents/reception_agent.py`)
- **Função:** Ponto de entrada e custódia da segurança do pipeline.
- **Operações Realizadas:**
  1. Inspeciona os primeiros bytes do arquivo para validação de integridade por *magic bytes* (`%PDF-`, `\x89PNG`, `\xFF\xD8\xFF`), bloqueando arquivos maliciosos renomeados.
  2. Valida o limite máximo de tamanho de upload (padrão de 50 MB, configurável).
  3. Higieniza o nome do arquivo impedindo vetores de ataque de *Directory Traversal* (`../`).
  4. Calcula os hashes criptográficos **MD5** e **SHA-256**.
  5. Consulta o banco relacional SQLite: caso o hash MD5 já conste cadastrado, sinaliza *Cache Hit* no `DocumentState`. O pipeline desvia imediatamente para o término com reaproveitamento integral dos dados previamente estruturados, poupando processamento e consumo de API.

### 8.2 Agente 2 — Extractor Agent (`agents/extractor_agent.py`)
- **Função:** Extração de texto preservando a numeração de páginas e contexto estrutural.
- **Roteamento Inteligente:**
  - **Documentos Digitais:** Aciona `pdfplumber` para extração vetorial direta do texto e bounding-boxes de tabelas.
  - **Avaliação de Densidade:** Calcula a média de caracteres por página. Se a média for inferior a 100 caracteres/página (indicativo de documento escaneado ou imagem encapsulada), ativa o ramo multimodal.
  - **Ramo Multimodal:** Se `GOOGLE_API_KEY` estiver ativa, envia as páginas renderizadas para o Gemini 2.0 Flash Lite Vision. Caso contrário (operação offline), aplica rasterização a 300 DPI via `PyMuPDF` (`fitz`) e executa o motor local Tesseract OCR com dicionário de português.

### 8.3 Agente 3 — Identifier Agent (`agents/identifier_agent.py`)
- **Função:** Segmentação semântica e categorização das seções contratuais de D&O.
- **Operações Realizadas:**
  - Identifica e delimita os blocos textuais relativos a: Condições Gerais, Limites Financeiros (LMG, Sublimites e Franquias/POS), Quadro de Coberturas Básicas e Adicionais, Rol de Riscos Excluídos, Cláusulas Particulares, Prazos de Retroatividade e Âmbito Territorial/Jurisdição.
  - Alinha as seções encontradas à taxonomia regulatória da Circular SUSEP 637/2021.

### 8.4 Agente 4 — Structurer Agent (`agents/structurer_agent.py`)
- **Função:** Normalização canônica, validação de tipos e persistência relacional.
- **Operações Realizadas:**
  - Instancia o modelo `ApoliceDAO` (Pydantic v2).
  - Normaliza valores monetários no padrão financeiro brasileiro (BRL), percentuais de franquia e formatos de datas (DD/MM/AAAA).
  - Gera os objetos `EvidenceItem` associando cada campo à sua respectiva evidência documental.
  - Persiste atomicamente a apólice no banco de dados local `apolices.db`.

### 8.5 Agente 5 — Comparator Agent (`agents/comparator_agent.py`)
- **Função:** Confronto analítico determinístico entre duas apólices estruturadas.
- **Operações Realizadas:**
  - Carrega as entidades canônicas da Apólice A e da Apólice B.
  - Aciona o motor analítico `core/diff_engine.py`, avaliando divergências campo a campo em dados escalares e calculando a sobreposição de listas de coberturas e exclusões.
  - Calcula o Score Global de Similaridade (0% a 100%).
  - Identifica assimetrias contratuais e compila o objeto `ComparisonResult`.

### 8.6 Agente 6 — Reporter Agent (`agents/reporter_agent.py`)
- **Função:** Síntese executiva e redação do parecer técnico em linguagem natural.
- **Operações Realizadas:**
  - Gera síntese narrativa técnica em Português (PT-BR) fundamentada nos fatos apurados pelo `ComparisonResult`.
  - Aponta discrepâncias materiais com indicação direta dos trechos de evidência documental.
  - Opera via Gemini 2.0 (modo online) ou via sintetizador determinístico baseado em templates técnicos (modo offline).
  - Persiste o parecer na tabela `comparacoes` do SQLite e disponibiliza opções de download em Markdown e JSON estruturado.

---

## 9. Extração Multimodal e OCR

O subsistema de extração foi projetado para assegurar máxima fidelidade textual e resiliência operacional diante da variedade de documentos recebidos pelo mercado segurador:

```
                      [ Documento de Entrada ]
                      (PDF, PNG, JPG ou JPEG)
                                 │
                                 ▼
                     Validação de Magic Bytes
                     (%PDF-, \x89PNG, \xFF\xD8\xFF)
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
       [ PDF Digital Nativo ]        [ Imagem / PDF Escaneado ]
                 │                               │
                 ▼                               ▼
      Extração Vetorial Direta              Condição de
           (pdfplumber)                      Execução
      • Texto e tabelas                  ┌───────┴───────┐
      • 100% offline                     ▼               ▼
      • Custo zero de API          [ Com Chave ]   [ Sem Chave ]
                                         │               │
                                         ▼               ▼
                                   Google Gemini   PyMuPDF + Tess.
                                     2.0 Vision       OCR Local
```

### 9.1 Formatos de Entrada Suportados
1. **PDFs Digitais Nativos:** Documentos gerados eletronicamente pelas seguradoras, contendo texto selecionável e vetores tipográficos. Processados diretamente via `pdfplumber`.
2. **PDFs Escaneados:** Documentos impressos e digitalizados, nos quais o texto está encapsulado como imagem rasterizada. O sistema detecta a baixa densidade textual (<100 caracteres por página) e aciona automaticamente a rota visual.
3. **Imagens Rasterizadas (PNG, JPG, JPEG):** Fotografias de apólices, capturas de tela ou cópias digitalizadas em formato de imagem avulsa.

### 9.2 Resolução de Ambiente para Tesseract OCR
Para viabilizar portabilidade e funcionamento local sem intervenção manual, o módulo `core/config.py` implementa mecanismos automatizados:
- **`resolve_tessdata_dir()`:** Realiza busca ativa de diretórios `tessdata` no Linux (`/usr/share/tessdata`, `/usr/share/tesseract-ocr/tessdata`) e no Windows (`C:\Program Files\Tesseract-OCR\tessdata`, diretórios de `%LOCALAPPDATA%` ou caminhos indicados por variáveis de ambiente `TESSDATA_PREFIX` e `TESSERACT_CMD`).
- **`get_ocr_language()`:** Inspeciona o diretório `tessdata` localizado e valida se o modelo de linguagem em Português (`por.traineddata`) está presente. Em caso afirmativo, configura o OCR para `por+eng`; caso contrário, adota fallback transparente para `eng`.

---

## 10. Estruturação dos Dados e Modelagem Canônica

Todos os dados manipulados pelo InsurMinds trafegam sob contratos tipados compilados em **Pydantic v2**, proporcionando coerção de tipos, validação de limites e serialização segura.

### 10.1 O Modelo Canônico `ApoliceDAO`
O objeto `ApoliceDAO` (`core/schemas.py`) compreende 25+ atributos canônicos:

```python
class ApoliceDAO(BaseModel):
    # Identificação & Rastreabilidade
    id: Optional[str] = None  # Hash MD5 (Chave Primária)
    nome_arquivo: str
    data_processamento: str

    # Metadados Contratuais
    numero_apolice: Optional[str] = None
    processo_susep: Optional[str] = None
    segurado: Optional[str] = None
    seguradora: Optional[str] = None
    vigencia_inicio: Optional[str] = None
    vigencia_fim: Optional[str] = None

    # Parâmetros Financeiros
    premio_total: Optional[str] = None
    limite_responsabilidade: Optional[str] = None  # LMG Agregado
    franquia: Optional[str] = None                 # POS / Deductible

    # Coberturas e Exclusões (D&O Side A/B/C e Adicionais)
    coberturas: List[str] = Field(default_factory=list)
    exclusoes: List[str] = Field(default_factory=list)
    clausulas_especiais: List[str] = Field(default_factory=list)

    # Escopo Territorial e Temporal
    retroatividade: Optional[str] = None
    territorio: Optional[str] = None
    legislacao_aplicavel: Optional[str] = None

    # Classificação Regulatória SUSEP
    cod_ramo: Optional[str] = "0378"
    ramo_descricao: Optional[str] = "Responsabilidade Civil D&O"
    tipo_movimento: Optional[str] = "101"
    tipo_movimento_descricao: Optional[str] = "Emissão de Apólice"
    document_type: Optional[str] = "unknown"

    # Auditoria de Extração e Evidências
    metodo_extracao: str = "pdfplumber"
    confianca_extracao: float = 1.0
    campos_nao_encontrados: List[str] = Field(default_factory=list)
    conflitos_extracao: Dict[str, List[str]] = Field(default_factory=dict)
    evidencias: Dict[str, EvidenceItem] = Field(default_factory=dict)
```

### 10.2 Modelos Auxiliares do Domínio
- **`EvidenceItem`:** Entidade atômica de proveniência com página, trecho, método e grau de confiança analítica.
- **`FieldDiff`:** Registro atômico de divergência em campo escalar com classificação padronizada (`igual`, `diferente`, `valor`, `ausente_em_A`, `ausente_em_B`, etc.).
- **`ComparisonResult`:** Entidade agregada contendo a lista completa de diffs, decomposição de coberturas/exclusões exclusivas e comuns, score de similaridade e metadados.
- **`SemanticMatchItem`:** Registro de correspondência semântica entre cláusulas com classificação relacional (`semantic_equivalent`, `broader`, `narrower`, `changed_scope`).

---

## 11. Comparação Analítica e Motor de Confronto

O motor de comparação (`core/diff_engine.py`) opera inteiramente através de algoritmos determinísticos em Python puro, proporcionando execução ágil em memória, reprodutibilidade matemática e ausência de custos operacionais externos.

### 11.1 Normalização Prévia de Dados
Antes da comparação, os valores escalares passam por procedimentos de normalização:
- **Moedas e Valores:** Remoção de símbolos de moeda (`R$`, `US$`), pontos de milhar e conversão de vírgulas decimais, permitindo confrontar equivalências numéricas reais independentemente de variações tipográficas.
- **Datas:** Normalização para o padrão ISO (AAAA-MM-DD) ou DD/MM/AAAA para validação de períodos de vigência e marcos de retroatividade.
- **Textos:** Higienização de espaços redundantes, caracteres invisíveis e padronização de caixa (*case folding*).

### 11.2 Formulação Matemática do Score de Similaridade
A aderência global entre as duas propostas contratuais é calculada através de uma média ponderada:

$$\text{Score Total} = (S_{\text{escalar}} \times 0.40) + (J_{\text{coberturas}} \times 0.40) + (J_{\text{exclusoes}} \times 0.20)$$

Onde:
1. **$S_{\text{escalar}}$:** Proporção de campos escalares equivalentes em relação ao total de campos avaliados (LMG, Franquia/POS, Prêmio, Vigência, Retroatividade, Território, Foro):
   $$S_{\text{escalar}} = \frac{\sum_{i=1}^{N} \mathbb{I}(\text{campo}_{A,i} \equiv \text{campo}_{B,i})}{N}$$
2. **$J_{\text{coberturas}}$:** Coeficiente de Similaridade de Jaccard sobre os conjuntos de cláusulas de cobertura:
   $$J_{\text{coberturas}} = \frac{|C_A \cap C_B|}{|C_A \cup C_B|}$$
3. **$J_{\text{exclusoes}}$:** Coeficiente de Jaccard sobre os conjuntos de cláusulas de exclusão:
   $$J_{\text{exclusoes}} = \frac{|E_A \cap E_B|}{|E_A \cup E_B|}$$

### 11.3 Identificação de Assimetrias Críticas de D&O
Além do cálculo numérico, o motor aplica regras especializadas de domínio securitário:
- Alerta para assimetria na presença de *Side A DIC* (diferencial relevante em coberturas executivas).
- Verificação de exigência de trânsito em julgado para exclusão de atos dolosos.
- Checagem da abrangência da retroatividade (retroatividade ilimitada *versus* retroatividade fixada em data estrita).
- Identificação de restrições de extraterritorialidade (exclusão de litígios sob foro dos Estados Unidos ou Canadá).

---

## 12. Evidências e Rastreabilidade Documental

A confiabilidade do InsurMinds decorre da sua capacidade de auditar cada afirmação analítica até sua origem no documento original.

### 12.1 O Objeto `EvidenceItem`
Cada atributo extraído é acompanhado de uma instância de `EvidenceItem`:

| Atributo | Tipo | Descrição |
|---|---|---|
| `page` | `int` | Número da página inicial da evidência no documento original (1-indexed). |
| `page_end` | `Optional[int]` | Número da página final para cláusulas que se estendem por múltiplos fólios. |
| `section` | `Optional[str]` | Identificador da seção, cláusula ou artigo correspondente. |
| `snippet` | `Optional[str]` | Citação textual literal extraída do contrato que fundamenta o dado. |
| `method` | `str` | Rota técnica de extração (`pdfplumber`, `llm`, `heuristic`, `ocr`, `normalized`). |
| `confidence` | `float` | Grau de confiança analítica atribuído à extração (0.0 a 1.0, não constituindo probabilidade estatística calibrada). |

### 12.2 Experiência de Auditoria no Frontend
Na tela de Comparações, o usuário tem acesso ao **Drawer de Evidências**. Ao clicar em qualquer divergência identificada na matriz, uma gaveta lateral é aberta exibindo:
- O rótulo e os valores comparados;
- O número exato da página da Apólice A e da Apólice B;
- O *snippet* textual destacado em caixa de realce visual;
- O método de extração e o grau de confiança analítica atribuído.

Essa funcionalidade permite ao corretor ou advogado conferir o texto literal da cláusula de maneira imediata e contextualizada, sem a necessidade de folhear manualmente apólices com dezenas de páginas.

---

## 13. Inteligência Artificial Generativa e Estratégia de Fallback

A plataforma opera sob uma arquitetura de **Dupla Rota Transparente**:

```
                              [ Solicitação de Análise ]
                                          │
                                          ▼
                             Existe GOOGLE_API_KEY ativa?
                                          │
                        ┌─────────────────┴─────────────────┐
                        ▼ SIM                               ▼ NÃO / OFFLINE
          [ Rota IA Generativa ]               [ Rota Determinística Local ]
          • Google Gemini 2.0 Flash Lite       • Heurísticas SUSEP (Circ. 637/2021)
          • Structured Output Pydantic v2      • Regex e Tokenização Canônica
          • Multimodal Vision para Scans       • PyMuPDF + Tesseract OCR Local
          • Parecer Narrativo Contextual       • Síntese Paramétrica Estruturada
                        │                                   │
                        └─────────────────┬─────────────────┘
                                          ▼
                           Objeto Canônico ApoliceDAO
                           (Mesma Estrutura e Interface)
```

### 13.1 Modo IA Generativa (com Google Gemini 2.0)
- Utiliza o SDK oficial `google-genai` com o modelo `gemini-flash-lite-latest`.
- A extração estruturada opera via *Structured Output*, impondo conformidade com o schema Pydantic v2 e reduzindo erros de sintaxe e chaveamento.
- A rota visual processa imagens e documentos digitalizados mantendo a interpretação contextual de layouts e tabelas.
- O parecer executivo é gerado com linguagem técnica, contextualizando os achados para corretores e executivos.

### 13.2 Modo de Contingência Determinístico (Offline)
- O sistema inclui um banco abrangente de expressões regulares e dicionários de termos canônicos calibrados especificamente para apólices D&O sob regulação da SUSEP.
- Quando nenhuma chave de API é fornecida, ou na ocorrência de interrupções de conexão, o sistema migra automaticamente para o modo determinístico.
- A aplicação é capaz de inicializar, processar documentos, extrair dados, realizar comparações e emitir relatórios estruturados sem qualquer dependência de nuvem ou internet.
- A saída estruturada produzida é compatível com o schema canônico `ApoliceDAO`, com indicação transparente do método de extração utilizado (`method: "heuristic"`).

---

## 14. Interface de Usuário (Streamlit e Design Dark Obsidian)

A interface gráfica foi desenhada para atender aos padrões estéticos e ergonômicos adequados para profissionais do mercado financeiro e securitário.

### 14.1 O Sistema de Design *Dark Obsidian*
- **Fundos Estruturados:** Fundo predominante em *Deep Midnight Navy* (`#0A192F` a `#0F172A`), reduzindo o cansaço visual em jornadas prolongadas de análise contratual.
- **Elevação Visual:** Cartões analíticos em *Slate* escuro (`#1E293B`) com bordas sutis e sombras suaves.
- **Cores Semânticas de Risco Securitário:**
  - 🟢 **Verde Esmeralda (`#10B981` / `#065F46`):** Convergências contratuais, cláusulas equivalentes e garantias amparadas.
  - 🟡 **Âmbar Ouro (`#F59E0B` / `#92400E`):** Discrepâncias de valores, assimetrias de franquia e limites financeiros divergentes.
  - 🔴 **Vermelho Rubi (`#EF4444` / `#991B1B`):** Lacunas materiais de cobertura (*gaps* de cobertura presentes em uma proposta e ausentes em outra) e riscos excluídos.
- **Acentos Executivos:** Toques de *Dourado de Resseguro* (`#C5A059`) e *Azul Royal Analítico* (`#0284C7`) para indicadores e botões de ação principal.

### 14.2 Estrutura das 6 Telas Oficiais no Menu Lateral
A navegação lateral (`ui/navigation.py`) organiza a experiência do usuário em 6 páginas principais:

1. **Início (Workspace):** Dashboard consolidado apresentando métricas de apólices cadastradas no SQLite, status operacional dos agentes e ferramenta rápida de seleção para comparação entre duas apólices.
2. **Nova análise (Upload):** Área de arrastar e soltar arquivos (PDF, PNG, JPG, JPEG) com verificação de tamanho, exibição de magic bytes e timeline dinâmica exibindo em tempo real o progresso dos agentes do pipeline.
3. **Comparações:** Matriz comparativa campo a campo com filtros por categoria, scorecards de divergência, painel de coberturas exclusivas e acionamento do *drawer* de evidências documentais.
4. **Documentos (Biblioteca):** Catálogo geral de apólices processadas e salvas no banco relacional, com filtros de busca, estatísticas e botão para visualização da ficha completa de **Detalhe da Apólice**.
5. **Relatórios:** Emissão do parecer executivo narrativo com destaques dos principais pontos de atenção e botões de exportação em Markdown (`.md`) e JSON estruturado.
6. **Configurações:** Painel de controle para auditoria do ambiente, verificação de chaves de API, diagnóstico do motor de OCR e monitoramento do banco de dados local.

Além das 6 páginas oficiais, a aplicação disponibiliza a subvisão de **Detalhe da Apólice** (`ui/page_detail.py`), que exibe a ficha cadastral integral de um documento individual e suas evidências, e um módulo de apoio à **Auditoria Contábil** (`ui/page_accounting.py`), dedicado à conciliação de provisões técnicas (PSL) e variação de sinistros conforme normas da SUSEP.

---

## 15. Camada de Persistência Relacional

O sistema adota o banco de dados relacional embarcado **SQLite 3** (`data/apolices.db`), gerenciado através da classe `DatabaseManager` (`core/database.py`). A escolha elimina a dependência de serviços externos de banco de dados, simplificando a implantação local e garantindo integridade transacional ACID.

### 15.1 Esquema Relacional e Tabelas

```
┌────────────────────────────────────────────────────────┐
│                        apolices                        │
├────────────────────────────────────────────────────────┤
│ PK  id                          TEXT  (Hash MD5)       │
│     nome_arquivo                TEXT                   │
│     data_processamento          TEXT  (ISO-8601)       │
│     segurado                    TEXT                   │
│     seguradora                  TEXT                   │
│     numero_apolice              TEXT                   │
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
│     metodo_extracao             TEXT                   │
│     confianca_extracao          REAL                   │
│     campos_nao_encontrados_json TEXT  (JSON Array)     │
│     dados_completos_json        TEXT  (Payload Apolice)│
│     evidencias_json             TEXT  (Payload Evid.)  │
│     created_at                  TIMESTAMP              │
└───────────────────────────┬────────────────────────────┘
                            │ 1
                            │
                            │ N
┌───────────────────────────▼────────────────────────────┐
│                      comparacoes                       │
├────────────────────────────────────────────────────────┤
│ PK  id                          TEXT  (idA_idB)        │
│ FK  apolice_a_id                TEXT                   │
│ FK  apolice_b_id                TEXT                   │
│     score_similaridade          REAL  (0.0 a 100.0)    │
│     data_comparacao             TEXT  (ISO-8601)       │
│     resultado_json              TEXT  (ComparisonRes.) │
│     relatorio_markdown          TEXT  (Parecer Final)  │
│     created_at                  TIMESTAMP              │
└────────────────────────────────────────────────────────┘
```

### 15.2 Idempotência e Segurança
- **Controle Estrito de Idempotência:** A chave primária da tabela `apolices` é definida pelo hash MD5 do arquivo binário. O envio repetido de um mesmo documento é interceptado, recuperando o registro previamente persistido e prevenindo duplicações.
- **Proteção contra SQL Injection:** 100% das instruções SQL executadas utilizam consultas estritamente parametrizadas com marcadores `?`, isolando dados e neutralizando ataques de injeção.
- **Migração DDL Automática:** Ao ser instanciado, o `DatabaseManager` verifica a existência das tabelas e colunas, aplicando migrações incrementais de forma transparente caso novas colunas (como `evidencias_json`) sejam adicionadas ao schema.

---

## 16. Estratégia de Validação e Corpus de Testes

A integridade do InsurMinds Apólice Analyzer foi assegurada por meio de uma estratégia de testes em múltiplos níveis, integrando dados sintéticos controlados e documentos reais de mercado.

### 16.1 Base Sintética Homologada (`data/sample_policies/`)
Para viabilizar a validação determinística do pipeline sem violar acordos de confidencialidade (NDAs) ou a Lei Geral de Proteção de Dados (LGPD), o projeto conta com um gerador programático (`data/generate_samples.py`) baseado na biblioteca `ReportLab`. O gerador produz três apólices D&O de alta fidelidade:
1. **Allianz Global Corporate & Specialty (`apolice_do_allianz.pdf`):** LMG de R$ 10.000.000,00, franquia de R$ 50.000,00 (Side A isento), cobertura para investigação regulatória e severabilidade de declarações.
2. **Chubb Seguros Brasil S.A. (`apolice_do_chubb.pdf`):** LMG de R$ 5.000.000,00, franquia de R$ 100.000,00, inclusão de Side A DIC e cobertura de custos de defesa para danos ambientais.
3. **AIG Seguros Brasil S.A. (`apolice_do_aig.pdf`):** LMG de R$ 15.000.000,00, franquia de R$ 75.000,00, retroatividade ilimitada e âmbito territorial mundial com extensão para jurisdição norte-americana (SEC).

### 16.2 Corpus Externo de Apólices Reais e Holdout de Aceitação
Para validar a robustez contra documentos de mercado não-sintéticos, a aplicação suporta a conexão opcional de um dataset externo por meio da variável de ambiente `INSURMINDS_EXTERNAL_TEST_DIR`.

O corpus externo efetivamente homologado e utilizado para avaliação no projeto compreende apólices e condições gerais de seguro D&O das seguintes companhias:
- **AIG Brasil**
- **Berkley Brasil**
- **Chubb**
- **EZZE**
- **Sompo**

Para os procedimentos de validação comparativa e demonstrações do motor de confronto, foram homologados especificamente os seguintes pares reais:
- **Sompo Seguros D&O v1.2 × Sompo Seguros D&O v1.5**
- **Chubb OPD 2024 × Chubb OPD 2025**

Outras seguradoras eventualmente citadas no contexto de mercado servem apenas como referências conceituais do setor, não integrando o corpus de testes homologado no projeto.

---

## 17. Testes e Resultados

A validação automatizada da solução foi executada através do framework `pytest`. A suíte é composta por 25 arquivos de teste especializados cobrindo testes unitários, testes de integração de agentes, segurança da informação e fluxos de ponta a ponta.

### 17.1 Resultados da Bateria Canônica
A execução oficial dos testes automatizados no ambiente Linux homologado apresentou os seguintes números consolidados:

```bash
.venv/bin/pytest tests/ -q
```

**Resultado:**
```text
........................................................................ [ 39%]
........................................................................ [ 79%]
......................................                                   [100%]
182 passed in 238.65s (0:03:58)
```

- **Total de Testes:** 182
- **Testes Aprovados:** 182 (100% dos testes aprovados)
- **Falhas (*Failures*):** 0
- **Erros (*Errors*):** 0
- **Regressões:** 0

### 17.2 Distribuição dos Testes por Módulo
A tabela a seguir discrimina as áreas cobertas pela suíte automatizada:

| Área de Teste | Arquivos Principais | Escopo da Validação | Status |
|---|---|---|:---:|
| **Schemas e Contratos** | `test_schemas.py` | Validação estrita do Pydantic v2, serialização de `ApoliceDAO`, `EvidenceItem` e integridade de tipos. | **PASS** |
| **Segurança e Higiene** | `test_security.py` | Higienização de nomes, neutralização de *Path Traversal* e validação binária de *magic bytes*. | **PASS** |
| **Persistência Relacional** | `test_database.py` | Operações CRUD, integridade transacional, migração de esquemas DDL e controle de idempotência via MD5. | **PASS** |
| **Motor de Comparação** | `test_diff_engine.py`<br>`test_fase4_*.py` | Normalização escalar, Similaridade de Jaccard, decomposição de coberturas e detecção de assimetrias. | **PASS** |
| **Ingestão Multimodal** | `test_image_ingestion.py`<br>`test_fase2_extraction.py` | Ingestão e parsing de PDF digital, PDF escaneado, PNG, JPG e JPEG com validação de DPI. | **PASS** |
| **Pipeline Multi-Agente** | `test_pipeline_integration.py`<br>`test_fase5_*.py` | Execução integrada dos grafos `DocumentState` e `ComparisonState`. | **PASS** |
| **Interface e Navegação** | `test_fase6_ui.py`<br>`test_fase7_*.py` | Roteamento das 6 páginas oficiais, rendering de componentes e *drawer* de evidências. | **PASS** |
| **Resiliência e Hardening** | `test_fase5_2_hardening.py` | Operação em modo de contingência offline, arquivos corrompidos e ausência de variáveis de ambiente. | **PASS** |
| **Dataset Externo** | `test_discover_external_dataset.py` | Descoberta dinâmica e ingestão segura de apólices reais em diretórios externos. | **PASS** |

---

## 18. Homologação Cross-Platform

A garantia de portabilidade entre diferentes sistemas operacionais é um requisito relevante de engenharia de software para soluções corporativas. O projeto adotou diretrizes estruturais para viabilizar execução em **Linux** e **Windows 11**.

### 18.1 Matriz de Homologação Atual

| Componente Técnico | Linux (openSUSE / Ubuntu) | Windows 11 64-bit | Situação Atual e Observações |
|---|:---:|:---:|---|
| **Interpretador Python (≥ 3.10)** | **PASS** | **PENDING** | Validado em Python 3.13.15 no Linux. Suporte a `python.exe` e `py.exe` preparado no Windows. |
| **Instalação Automatizada** | **PASS** | **PENDING** | Linux: `scripts/setup_linux.sh` (PASS). Windows: `scripts/setup_windows.ps1`. |
| **Tratamento de Caminhos** | **PASS** | **PENDING** | 100% implementado com `pathlib.Path`, prevenindo conflitos entre `/` e `\`. |
| **Ingestão PDF (pdfplumber)** | **PASS** | **PENDING** | Dependências compiladas disponíveis em *wheels* pré-compilados para ambas as plataformas. |
| **Ingestão Imagens (PNG/JPG)** | **PASS** | **PENDING** | Validação binária via Pillow agnóstica de sistema operacional. |
| **OCR Local (PyMuPDF + Tesseract)** | **PASS** | **PENDING** | Resolução dinâmica em `core/config.py` para caminhos do UB-Mannheim no Windows. |
| **Google Gemini SDK** | **PASS** | **PENDING** | SDK oficial `google-genai` independente de sistema operacional. |
| **Fallback Determinístico** | **PASS** | **PENDING** | Lógica implementada em Python puro em memória. |
| **Persistência SQLite** | **PASS** | **PENDING** | Biblioteca padrão `sqlite3` com suporte universal a arquivos locais. |
| **Interface Streamlit** | **PASS** | **PENDING** | Streamlit 1.39+ homologado no Linux (HTTP 200). |
| **Suíte de Testes (182 testes)** | **PASS (182/182)** | **PENDING** | Zero falhas no Linux; aguardando conclusão em hardware Windows 11 real. |

### 18.2 Relato da Validação Física no Windows 11
Em conformidade com as regras de governança e integridade técnica do projeto, o suporte ao Windows 11 não é declarado como PASS de forma puramente teórica ou simulada.

Durante a Fase 8.0H, o procedimento de validação física foi iniciado em uma estação de trabalho real com Windows 11. Na execução da etapa preliminar de configuração via **Windows PowerShell 5.1** (a versão clássica nativa que acompanha instalações padrão do Windows), o script de automação (`setup_windows.ps1`) encontrou um **erro de parsing e codificação de caracteres (*encoding*)**, interrompendo o setup antes da criação completa do ambiente e da execução da suíte de testes do `pytest`.

Por essa razão, o status do Windows 11 permanece formalmente registrado como **PENDING REAL VALIDATION**. Essa ocorrência é tratada como uma pendência de portabilidade do setup no PowerShell 5.1. Como proposta de correção futura a ser investigada, planeja-se analisar o salvamento do script com codificação UTF-8 com BOM e avaliar a compatibilidade em ambientes com PowerShell 7 (PowerShell Core), mantendo a transparência documental do projeto.

---

## 19. Segurança e Conformidade (OWASP / Secure Web)

O InsurMinds Apólice Analyzer foi estruturado segundo boas práticas de desenvolvimento seguro (OWASP Top 10 e diretrizes para aplicações web):

1. **Prevenção contra Path Traversal:** O método `core.security.get_safe_destination_path` normaliza caminhos de arquivo e verifica de forma mandatória se o caminho final resolvido reside estritamente contido dentro do diretório sandbox (`data/uploads/`), bloqueando qualquer tentativa de manipulação com `../` ou caminhos absolutos arbitrários.
2. **Inspeção Estrita de Magic Bytes:** O sistema não confia em extensões declaradas pelo usuário. Antes de qualquer processamento, os primeiros bytes do arquivo são confrontados contra as assinaturas binárias canônicas (`%PDF-`, `\x89PNG\r\n\x1a\n`, `\xFF\xD8\xFF`), impedindo o envio de scripts ou binários executáveis disfarçados.
3. **Imunidade a SQL Injection:** Todas as operações com o banco SQLite utilizam consultas parametrizadas com placeholders `?`. Nenhuma variável de entrada é concatenada diretamente em comandos SQL.
4. **Isolamento de Credenciais:** As chaves de API do Google Gemini são acessadas unicamente através de variáveis de ambiente (`os.getenv`). Não há chaves hardcoded no código-fonte, e os arquivos `.env` e `apolices.db` estão estritamente listados no `.gitignore`.
5. **Mitigação de Exaustão de Recursos (DoS):** O tamanho máximo de upload é limitado por padrão em 50 MB, prevenindo sobrecarga excessiva de memória durante operações de parsing.
6. **Segurança de Rede Local:** O servidor Streamlit é configurado por padrão para escutar na interface de *loopback* local (`127.0.0.1`), prevenindo exposição acidental em redes públicas.

---

## 20. Resultados e Discussão Técnica

O desenvolvimento do InsurMinds Apólice Analyzer permitiu avaliar empiricamente a aplicação de IA generativa e sistemas modulares em domínios contratuais complexos:

1. **Eficácia da Modelagem por Estados e Execução Modular:** A segregação do pipeline em agentes com responsabilidade única e estados canônicos trouxe previsibilidade e robustez ao sistema. O controle procedural na interface Streamlit garantiu feedback visual imediato ao analista, enquanto a modelagem formal dos estados permitiu manter o código modular e testável isoladamente.
2. **Redução de Inconsistências Estruturais via Structured Output:** O emprego de Structured Outputs via Pydantic v2 provou ser essencial para restringir a estrutura da resposta e eliminar erros de formato JSON. Em comparações qualitativas com saídas em texto livre, o schema tipado preveniu quebras de deserialização no Pydantic, viabilizando a persistência relacional direta. Ressalta-se, contudo, que a validação estrutural não assegura veracidade semântica; a fidelidade das informações aos termos reais do contrato repousa na ancoragem documental provida pelo `EvidenceItem` e na auditoria assistida pelo usuário.
3. **Relevância do EvidenceItem para Usuários Especialistas:** A disponibilização de citações literais (*snippets*) e numeração exata de páginas transforma a usabilidade da ferramenta. Profissionais regulados necessitam verificar a fonte contratual imediata do achado, conferindo transparência à análise assistida.
4. **Resiliência do Modo de Contingência Offline:** A presença de um modo determinístico baseado na Circular SUSEP 637/2021 assegurou que o sistema permanecesse operacional e apto a demonstrações mesmo em cenários de indisponibilidade de rede ou ausência de chaves de provedores de nuvem.

---

## 21. Limitações do Sistema

1. **Portabilidade Windows 11 Pendente:** Conforme registrado na Seção 18, o script de instalação automática requer investigação de encoding para compatibilidade com o Windows PowerShell 5.1 antes da homologação física definitiva.
2. **Documentos de Baixa Qualidade Gráfica:** PDFs escaneados com resolução inferior a 150 DPI, documentos inclinados (*skewed*) ou com artefatos de digitalização severos podem apresentar redução no grau de confiança analítica da extração de texto via OCR local.
3. **Escopo Setorial Calibrado para D&O:** As regras heurísticas determinísticas e a taxonomia canônica foram calibradas especificamente para apólices de Responsabilidade Civil D&O (Ramo 0378 da SUSEP). O processamento de apólices de outros ramos (como Patrimonial, Automóvel ou Rural) pode ser realizado, porém sem garantia de preenchimento completo de todos os campos específicos.
4. **Caráter Assistido e Limite de Responsabilidade:** O sistema não substitui a assessoria jurídica, a análise atuarial ou a subscrição formal de riscos. Ele opera estritamente como um instrumento auxiliar de leitura e confronto analítico.

---

## 22. Trabalhos Futuros

1. **Investigação e Conclusão da Homologação Windows 11:** Investigar a causa do erro de parsing/encoding observado no Windows PowerShell 5.1, avaliando hipóteses de correção como a adoção de UTF-8 com BOM ou o uso do PowerShell 7, e realizar a execução física da suíte completa de 182 testes na plataforma.
2. **Esteira de CI/CD Multi-Platform:** Configurar automação via GitHub Actions para disparar a execução de testes em matriz paralela contendo *runners* Linux (`ubuntu-latest`) e Windows (`windows-latest`).
3. **Expansão de Domínio para Linhas Financeiras Correlatas:** Ampliar o modelo canônico e as heurísticas para cobrir seguros de **Erros e Omissões (E&O)** e **Seguro de Riscos Cibernéticos (Cyber Insurance)**.
4. **Integração com APIs da SUSEP:** Implementar consulta automatizada ao Sistema de Consulta de Produtos e Apólices da SUSEP para validação de registros de produtos e número de processo em tempo real.
5. **Exportação de Relatórios Institucionais:** Desenvolver gerador de relatórios em formato PDF institucional, incorporando gráficos de similaridade e formatação executiva.
6. **Suporte a Jurisdições Internacionais:** Incluir dicionários canônicos em língua inglesa e espanhola para confronto de apólices emitidas sob direito norte-americano (*Delaware Law*) ou europeu.

---

## 23. Conclusão

O **InsurMinds Apólice Analyzer** consolida os conhecimentos desenvolvidos ao longo do curso de Inteligência Artificial Aplicada às Finanças e Seguros do **I2A2**. O projeto entrega um Produto Mínimo Viável funcional, auditável e aderente às exigências do mercado segurador corporativo.

Aliando a flexibilidade multimodal dos modelos de linguagem à Engenharia de Dados e à Teoria dos Conjuntos, o sistema aborda um gargalo operacional relevante na análise de apólices de D&O. Mais do que uma aplicação de IA generativa, a plataforma destaca-se pela sua governança, evidenciada pela rastreabilidade minuciosa de cada achado (`EvidenceItem`), pela capacidade de operar 100% offline em contingência e pelo compromisso com a integridade científica ao manter documentada com total transparência a situação de validação entre plataformas.

---

## 24. Referências Bibliográficas e Normativas

1. **SUSEP — Superintendência de Seguros Privados.** *Circular nº 637, de 27 de julho de 2021.* Dispõe sobre as regras e os critérios para operação do seguro de responsabilidade civil de diretores e administradores de pessoas jurídicas (D&O). Rio de Janeiro: SUSEP, 2021.
2. **SUSEP — Superintendência de Seguros Privados.** *Circular nº 621, de 12 de fevereiro de 2021.* Dispõe sobre as regras e os critérios para operação dos seguros de danos. Rio de Janeiro: SUSEP, 2021.
3. **LangChain AI.** *LangGraph: Building Language Agents as Graphs.* Disponível em: <https://github.com/langchain-ai/langgraph>. Acesso em: out. 2026.
4. **Pydantic Authors.** *Pydantic: Data validation using Python type hints (v2).* Disponível em: <https://docs.pydantic.dev/>. Acesso em: out. 2026.
5. **Google AI.** *Gemini 2.0 Flash Documentation and Multimodal Vision API.* Disponível em: <https://ai.google.dev/>. Acesso em: out. 2026.
6. **Jaccard, Paul.** *The distribution of the flora in the alpine zone.* New Phytologist, v. 11, n. 2, p. 37-50, 1912.
7. **OWASP Foundation.** *OWASP Top 10: 2021 — The Ten Most Critical Web Application Security Risks.* Disponível em: <https://owasp.org/Top10/>. Acesso em: out. 2026.
8. **Streamlit Inc.** *Streamlit: The fastest way to build and share data apps.* Disponível em: <https://docs.streamlit.io/>. Acesso em: out. 2026.
9. **I2A2 — Instituto de Inteligência Artificial Aplicada.** *Programa de Formação em Inteligência Artificial Aplicada às Finanças e Seguros — InsurMinds.* São Paulo: I2A2, 2026.

---

## 25. Anexos Técnicos

### Anexo I: Tabela Comparativa de Atributos Canônicos (`ApoliceDAO`)

| Atributo | Tipo Pydantic | Descrição Regulamentar | Exemplo Canônico |
|---|---|---|---|
| `id` | `Optional[str]` | Hash MD5 do binário original (Chave Primária). | `"e4d909c290d0fb1ca068ffaddf22cbd0"` |
| `nome_arquivo` | `str` | Nome original do documento submetido. | `"apolice_do_allianz.pdf"` |
| `data_processamento`| `str` | Carimbo ISO-8601 da data/hora da ingestão. | `"2026-10-06T12:00:00"` |
| `numero_apolice` | `Optional[str]` | Número único de apólice ou proposta. | `"01.0775.000458/01"` |
| `processo_susep` | `Optional[str]` | Número do processo regulatório do produto. | `"15414.900458/2021-12"` |
| `segurado` | `Optional[str]` | Razão social da empresa tomadora do seguro. | `"TechCorp Brasil Inovações S.A."` |
| `seguradora` | `Optional[str]` | Nome da sociedade seguradora emissora. | `"Allianz Global Corporate & Specialty"` |
| `vigencia_inicio` | `Optional[str]` | Data de início de cobertura (DD/MM/AAAA). | `"01/01/2026"` |
| `vigencia_fim` | `Optional[str]` | Data de término de cobertura (DD/MM/AAAA). | `"01/01/2027"` |
| `premio_total` | `Optional[str]` | Prêmio total contratado (BRL). | `"R$ 120.000,00"` |
| `limite_responsabilidade` | `Optional[str]` | Limite Máximo de Garantia (LMG agregado).| `"R$ 10.000.000,00"` |
| `franquia` | `Optional[str]` | Franquia ou Participação Obrigatória (POS).| `"R$ 50.000,00"` |
| `coberturas` | `List[str]` | Lista de garantias básicas e adicionais. | `["Side A", "Side B", "Penhora Online"]` |
| `exclusoes` | `List[str]` | Lista de riscos expressamente excluídos. | `["Atos Dolosos", "Poluição Ambiental"]` |
| `clausulas_especiais` | `List[str]` | Endossos particulares e cláusulas específicas.| `["Severabilidade de Declarações"]` |
| `retroatividade` | `Optional[str]` | Marco temporal limite para atos de gestão.| `"01/01/2023 (3 anos)"` |
| `territorio` | `Optional[str]` | Abrangência geográfica e jurisdicional. | `"Brasil e Jurisdição Mundial (exceto EUA)"` |
| `legislacao_aplicavel` | `Optional[str]`| Foro e ordenamento jurídico aplicável. | `"Legislação Brasileira, Foro de SP"` |
| `cod_ramo` | `Optional[str]` | Código oficial do ramo SUSEP. | `"0378"` |
| `metodo_extracao` | `str` | Motor utilizado na extração primária. | `"pdfplumber"` |
| `confianca_extracao`| `float` | Grau numérico de confiança analítica. | `0.95` |

### Anexo II: Comandos Rápidos de Execução e Diagnóstico

```bash
# 1. Diagnóstico Automatizado de Ambiente (8 verificações)
python scripts/validate_environment.py

# 2. Execução da Suíte Completa de Testes Automatizados (182 testes)
pytest tests/ -q

# 3. Inicialização da Aplicação Web Streamlit (Porta 8503)
streamlit run app.py
```
