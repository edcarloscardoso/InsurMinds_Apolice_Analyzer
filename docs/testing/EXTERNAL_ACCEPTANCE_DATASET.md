# Guia de Aceitação e Homologação — Corpus Externo D&O

**InsurMinds Apólice Analyzer — Plataforma de Inteligência em Apólices de Seguros**
*Documento de Referência Técnica e Operacional de Homologação (Fase 8.0A)*

---

## 1. Visão Geral e Finalidade

Este documento detalha o protocolo de acesso, governança, verificação criptográfica e estratégia de testes com o **corpus externo de documentos de Seguro D&O** (*Directors & Officers Liability*).

O objetivo principal desta infraestrutura de testes é permitir a homologação cega (*holdout testing*), validação de robustez e aferição de capacidades de extração, estruturação e comparação analítica em documentos contratuais autênticos e de alta complexidade do mercado segurador brasileiro, **sem acoplar ou inflar o repositório base da aplicação**.

---

## 2. Localização e Natureza do Corpus

O corpus externo foi compilado a partir de fontes públicas e domínios oficiais das seguradoras, estando alocado em um diretório fora do workspace do projeto:

* **Diretório Canônico na Estação de Homologação:**
  `/caminho/para/dataset_do`
* **Status do Corpus no Projeto:**
  **Externo e Opcional**. Os arquivos PDF e derivados **NÃO** fazem parte da instalação padrão do repositório Git, evitando o gigantismo do repositório (os 15 PDFs contratuais somam centenas de megabytes e 941 páginas).
* **Workspace do Projeto:**
  `/caminho/para/InsurMinds_Apolice_Analyzer`

> [!IMPORTANT]
> **Regra Fundamental de Governança:**
> Sob nenhuma hipótese os PDFs externos devem ser copiados, movidos ou comitados no workspace do projeto. A aplicação e seus scripts de homologação interagem com o corpus através de leitura referencial parametrizada.

---

## 3. Configuração de Ambiente (`INSURMINDS_EXTERNAL_TEST_DIR`)

Para garantir que o código seja 100% portável entre máquinas de desenvolvimento, servidores de homologação e pipelines de CI/CD, o caminho absoluto do corpus externo **não deve ser hardcodado** nas rotinas operacionais da aplicação.

### 3.1. Variável de Ambiente Oficial

A plataforma utiliza a variável de ambiente:

```bash
export INSURMINDS_EXTERNAL_TEST_DIR="/caminho/para/dataset_do"
```

### 3.2. Exemplos de Configuração

#### No Linux / macOS (Bash / Zsh):
```bash
# Temporário na sessão atual
export INSURMINDS_EXTERNAL_TEST_DIR="/caminho/para/dataset_do"

# Permanente no ~/.bashrc ou ~/.zshrc
echo 'export INSURMINDS_EXTERNAL_TEST_DIR="/caminho/para/dataset_do"' >> ~/.bashrc
source ~/.bashrc
```

#### No Windows (PowerShell):
```powershell
$env:INSURMINDS_EXTERNAL_TEST_DIR = "C:\caminho\para\dataset_do"
```

### 3.3. Comportamento de Resolução e Fallback

O runner oficial `scripts/discover_external_dataset.py` implementa a seguinte precedência de resolução:
1. Argumento explícito de linha de comando: `--corpus-dir <caminho>`;
2. Variável de ambiente `INSURMINDS_EXTERNAL_TEST_DIR`;
3. Detecção automática de fallback local (`dataset_do/`) para conveniência nesta estação de trabalho, emitindo aviso de não-portabilidade se a variável de ambiente estiver ausente;
4. Falha controlada com erro explicativo se o corpus não for localizado.

---

## 4. Estrutura Canônica do Corpus Externo

O diretório `dataset_do/` possui organização temática e auditável:

```
dataset_do/
├── README.md                          # Documentação e contexto da coleta oficial
├── documentos/                        # 15 PDFs contratuais padronizados (DO001 a DO015)
├── por_seguradora/                    # Espelhos organizados por companhia seguradora
│   ├── AIG_Brasil/
│   ├── Berkley_Brasil/
│   ├── Chubb/
│   ├── EZZE_Seguros/
│   └── Sompo_Seguradora/
├── metadados/                         # Catálogos estruturados e somas de verificação
│   ├── catalogo.json                  # Catálogo completo estruturado
│   ├── catalogo.csv                   # Catálogo tabular
│   ├── sha256.txt                     # Hashes SHA-256 de referência
│   └── tabela_fontes.md               # Rastreabilidade de links públicos oficiais
├── evidencias/                        # 15 arquivos Markdown com proveniência de cada PDF
├── documentos_complementares/         # Condições anexas / variantes (DO013, DO014, DO015)
├── materiais_comerciais/              # Folder comercial (não-contratual, descartado do pipeline)
├── materiais_regulatorios/            # Norma SUSEP (Circular 541/2016)
├── referencias_academicas/            # TCC acadêmico UnB sobre D&O
└── derivados_para_teste_ocr/          # Cópia rasterizada sintética para estresse de OCR
```

---

## 5. Como Reproduzir o Inventário e o Manifesto

Para auditar o acervo, verificar a integridade criptográfica dos arquivos e gerar o manifesto canônico de aceitação:

```bash
# Com a variável configurada
export INSURMINDS_EXTERNAL_TEST_DIR="/caminho/para/dataset_do"
./.venv/bin/python3 scripts/discover_external_dataset.py
```

O comando irá:
1. Validar a presença de todos os subdiretórios e catálogos obrigatórios;
2. Calcular os hashes SHA-256 e MD5 dos 15 contratos em `documentos/`;
3. Varrer o diretório `data/` do projeto para atestar que **zero PDFs foram duplicados** no workspace;
4. Inspecionar o banco relacional `data/apolices.db` para mapear documentos previamente processados e identificar arquivos inéditos;
5. Gerar o arquivo estruturado `docs/testing/EXTERNAL_ACCEPTANCE_MANIFEST.json`.

---

## 6. Utilização de Hashes Criptográficos (SHA-256 e MD5)

### 6.1. Integridade e Unicidade Real

> [!NOTE]
> **Regra Anti-Duplicidade:**
> No InsurMinds Apólice Analyzer, o nome do arquivo **não define a novidade do documento**.
> Dois arquivos com nomes diferentes mas o mesmo SHA-256 representam o mesmo documento. Inversamente, dois arquivos com nomes idênticos mas hashes distintos representam versões diferentes.

* **SHA-256 (Padrão de Auditoria):** Usado para verificação de integridade e atestar que nenhum documento do corpus foi copiado para o workspace.
* **MD5 (Padrão de Banco):** Usado como chave primária (`id`) na tabela `apolices` do SQLite (`ApoliceDAO.id`), permitindo correlacionar de forma instantânea se uma apólice ingerida previamente corresponde exatamente ao PDF sob teste.

---

## 7. Diferença Entre Corpus Conhecido e Holdout

Na metodologia de homologação de sistemas de IA e Processamento de Documentos Complexos:

| Conceito | Definição | Documentos na Base Atual | Finalidade |
|---|---|---|---|
| **Corpus Conhecido** (*Known Set*) | Documentos utilizados durante o desenvolvimento das Fases 1 a 7 para calibração de regras, testes de regressão e aferição da UI de demonstração. | 11 documentos (DO001, DO003, DO004, DO005, DO007, DO008, DO009, DO010, DO012, DO013, DO014). | Testes de regressão contínua, benchmarking fixo e demonstração ao vivo. |
| **Corpus Holdout** (*Test Set Inédito*) | Documentos autênticos do mercado que **nunca foram processados no banco de dados**, servindo como avaliação cega da capacidade de generalização da IA. | 4 documentos inéditos (DO002, DO006, DO011, DO015). | Teste cego de homologação, aferição de resiliência e estresse analítico. |

---

## 8. Seleção Preliminar de Candidatos a Holdout

A partir da análise estrutural do corpus e do manifesto gerado, foram selecionados 4 candidatos individuais e 2 pares comparativos:

### 8.1. Candidatos Individuais
1. **Documento Longo & Variante da Seguradora:**
   `DO002` — *DO_AIG_CONDICOES_GERAIS_AIGGO_2025_002.pdf* (AIG Brasil, 72 páginas, 2 tabelas).
   *Justificativa:* Testa a estabilidade do particionamento por janelas de contexto (*chunking*) e extração em documentos volumosos. Inédito no banco SQLite.
2. **Seguradora Diferente & Produto Especializado:**
   `DO006` — *DO_CHUBB_CONDICOES_GERAIS_FUNDOS_INVESTIMENTO_2024_006.pdf* (Chubb, 64 páginas).
   *Justificativa:* Produto voltado a Fundos de Investimentos, com taxonomia e definições de segurados substancialmente distintas de empresas comuns. Inédito no banco SQLite.
3. **Versão Diferente & Gradiente Temporal:**
   `DO011` — *DO_SOMPO_CONDICOES_GERAIS_V1_3_2024_011.pdf* (Sompo Seguradora, 46 páginas, 3 tabelas).
   *Justificativa:* Versão v1.3 (outubro/2024) que fecha o intervalo evolutivo entre v1.2 (DO010) e v1.4 (DO013), permitindo checagem fina de variações contratuais intermediárias. Inédito no banco SQLite.
4. **Documento Compacto & Teste de Imagem/OCR:**
   `DO015` — *DO_EZZE_CONDICOES_COMPLEMENTARES_RISCOS_AMBIENTAIS_2021_015.pdf* (EZZE Seguros, 11 páginas).
   *Justificativa:* Documento enxuto e anexo (Riscos Ambientais), inédito no banco SQLite. Ideal para homologação ponta a ponta da nova rota de ingestão de imagens (PNG/JPG) e OCR, dispondo de espelho rasterizado em `derivados_para_teste_ocr/`.

### 8.2. Pares Comparativos Recomendados
* **HOLDOUT_PAIR_01 (Cross-Insurer Cego):** `DO006` (Chubb Fundos) vs `DO002` (AIG AIGGO).
  *Objetivo:* Avaliar a capacidade do `ComparatorAgent` e do `DiffEngine` de confrontar duas apólices complexas de seguradoras distintas, ambas inéditas para o sistema.
* **HOLDOUT_PAIR_02 (Evolução Temporal Intra-Insurer):** `DO010` (Sompo v1.2) vs `DO011` (Sompo v1.3).
  *Objetivo:* Avaliar a precisão semântica na identificação de alterações de redação em cláusulas regulatórias consecutivas da mesma seguradora.

---

## 9. Isolamento dos Resultados de Homologação

Para cumprir rigorosamente o critério de **não contaminação do banco oficial de demonstração** (`data/apolices.db`):
* Todas as execuções de testes de homologação deverão ser direcionadas para diretórios temporários ou de rascunho:
  `scratch/external_acceptance/`
* Quando os testes de ingestão da Fase 8 forem executados, o banco de dados de teste poderá ser apontado de forma isolada através da variável:
  `export DB_PATH="scratch/external_acceptance/homologacao.db"`
  garantindo total isolamento e preservação dos dados de demonstração.

---

## 10. Conclusão da Fase 8.0A

Com a conclusão da Fase 8.0A, o InsurMinds Apólice Analyzer possui:
* Infraestrutura de homologação externa totalmente mapeada e referenciada;
* Manifesto JSON formal com hashes SHA-256 e status de ineditismo;
* Runner automatizado de auditoria (`scripts/discover_external_dataset.py`);
* Zero cópias de arquivos no workspace e zero contaminação do banco relacional principal.
