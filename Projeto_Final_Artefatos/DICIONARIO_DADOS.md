# Dicionário de Dados Canônico & Especificação de Schemas
**InsurMinds Apólice Analyzer · Projeto Final I2A2**

---

## 1. Modelo Canônico: `ApoliceDAO` (Pydantic v2)

Este modelo representa uma apólice de seguro D&O completamente estruturada e validada.

| Campo | Tipo | Obrigatoriedade | Descrição | Exemplo |
|---|---|---|---|---|
| `id` | `str` | Opcional (PK) | Hash MD5 hexadecimal do arquivo PDF original. | `"e4d909c290d0fb1ca068ffaddf22cbd0"` |
| `nome_arquivo` | `str` | Obrigatório | Nome original do documento PDF ingerido. | `"apolice_do_allianz.pdf"` |
| `data_processamento` | `str` | Obrigatório | Carimbo de data/hora no padrão ISO-8601. | `"2026-09-04T16:00:00"` |
| `numero_apolice` | `str` | Opcional | Número identificador de registro da apólice. | `"01.0775.000458/01"` |
| `segurado` | `str` | Opcional | Razão social da empresa tomadora do seguro. | `"TechCorp Brasil Inovações S.A."` |
| `seguradora` | `str` | Opcional | Razão social da seguradora emissora da proposta. | `"Allianz Global Corporate & Specialty"` |
| `vigencia_inicio` | `str` | Opcional | Data de início de vigência no formato DD/MM/AAAA. | `"01/01/2026"` |
| `vigencia_fim` | `str` | Opcional | Data de término de vigência no formato DD/MM/AAAA. | `"01/01/2027"` |
| `premio_total` | `str` | Opcional | Valor total do prêmio pago pelo segurado. | `"R$ 120.000,00"` |
| `limite_responsabilidade` | `str` | Opcional | Limite Máximo de Garantia (LMG) agregado. | `"R$ 10.000.000,00"` |
| `franquia` | `str` | Opcional | Franquia / Retenção aplicável a sinistros. | `"R$ 50.000,00"` |
| `coberturas` | `List[str]` | Obrigatório (Default `[]`) | Lista com as coberturas básicas e adicionais ativas. | `["Side A", "Side B", "Penhora Online"]` |
| `exclusoes` | `List[str]` | Obrigatório (Default `[]`) | Lista com as cláusulas expressas de exclusão. | `["Atos Dolosos", "Poluição Ambiental"]` |
| `clausulas_especiais` | `List[str]` | Obrigatório (Default `[]`) | Endossos e cláusulas particulares do contrato. | `["Cláusula de Severabilidade de Dolo"]` |
| `retroatividade` | `str` | Opcional | Data limite ou período de retroatividade. | `"01/01/2023 (3 anos)"` |
| `territorio` | `str` | Opcional | Âmbito geográfico de validade das garantias. | `"Brasil e Jurisdição Mundial (exceto EUA/Canadá)"` |
| `legislacao_aplicavel` | `str` | Opcional | Jurisdição e foro eleito no contrato. | `"Legislação Brasileira, Foro de São Paulo/SP"` |
| `cod_ramo` | `str` | Opcional (Default `"0378"`) | Código de 4 dígitos do ramo na SUSEP. | `"0378"` |
| `ramo_descricao` | `str` | Opcional | Descrição oficial do ramo SUSEP. | `"Responsabilidade Civil D&O"` |
| `tipo_movimento` | `str` | Opcional (Default `"101"`) | Código oficial de movimentação FIP SUSEP (101 a 108). | `"101"` |
| `tipo_movimento_descricao` | `str` | Opcional | Descrição da operação do documento. | `"Emissão de Apólice"` |
| `metodo_extracao` | `str` | Obrigatório | Método utilizado (`pdfplumber`, `gemini_vision` ou `mock_fallback`). | `"pdfplumber"` |
| `confianca_extracao` | `float` | Obrigatório | Grau de confiança estatística (0.0 a 1.0). | `0.95` |
| `campos_nao_encontrados`| `List[str]` | Obrigatório (Default `[]`) | Campos que não puderam ser localizados no PDF. | `[]` |

---

## 2. Modelo: `ComparisonResult`

Representa o resultado consolidado do confronto entre duas apólices estruturadas.

| Campo | Tipo | Descrição |
|---|---|---|
| `apolice_a_id` | `str` | ID hash da Apólice A. |
| `apolice_b_id` | `str` | ID hash da Apólice B. |
| `apolice_a_nome` | `str` | Nome de exibição / seguradora da Apólice A. |
| `apolice_b_nome` | `str` | Nome de exibição / seguradora da Apólice B. |
| `data_comparacao` | `str` | Carimbo ISO-8601 da data de realização do confronto. |
| `score_similaridade` | `float` | Pontuação ponderada de 0 a 100%. |
| `diffs` | `List[FieldDiff]` | Lista detalhada de divergências campo a campo. |
| `coberturas_exclusivas_a` | `List[str]` | Cláusulas de garantia presentes apenas na Apólice A. |
| `coberturas_exclusivas_b` | `List[str]` | Cláusulas de garantia presentes apenas na Apólice B. |
| `coberturas_comuns` | `List[str]` | Cláusulas equivalentes contratadas em ambas as apólices. |
| `exclusoes_exclusivas_a` | `List[str]` | Riscos excluídos unicamente no contrato A. |
| `exclusoes_exclusivas_b` | `List[str]` | Riscos excluídos unicamente no contrato B. |
| `exclusoes_comuns` | `List[str]` | Riscos excluídos em ambas as propostas. |

---

## 3. Modelo: `FieldDiff`

| Campo | Tipo | Descrição |
|---|---|---|
| `campo` | `str` | Identificador canônico do atributo. |
| `rotulo` | `str` | Rótulo amigável em português para exibição em tabelas. |
| `valor_apolice_a` | `Optional[str]` | Valor extraído na primeira apólice. |
| `valor_apolice_b` | `Optional[str]` | Valor extraído na segunda apólice. |
| `ha_diferenca` | `bool` | Flag booleana indicando se há discrepância. |
| `tipo_diferenca` | `str` | Classificação (`"igual"`, `"valor"`, `"ausente_a"`, `"ausente_b"`, `"ambos_ausentes"`). |

---

## 4. Modelo: `SinistroItem` (Auditoria Contábil FIP SUSEP)

Representa um registro individual de sinistro ou movimentação de provisão técnica (PSL).

| Campo | Tipo | Descrição |
|---|---|---|
| `numero_sinistro` | `str` | Identificador único do sinistro. |
| `numero_apolice` | `str` | Número da apólice contratual vinculada. |
| `segurado` | `str` | Razão social da empresa segurada. |
| `seguradora` | `str` | Razão social da seguradora emissora. |
| `cod_ramo` | `str` | Código de 4 dígitos do ramo na SUSEP (`0378`, `0351`, etc.). |
| `ramo_nome` | `str` | Descrição por extenso do ramo. |
| `tipo_mov` | `str` | Código de movimentação SUSEP (`101` a `108`). |
| `saldo_anterior` | `float` | Saldo contábil da reserva no início do período (R$). |
| `saldo_atual` | `float` | Saldo contábil atualizado da reserva no fechamento (R$). |
| `delta_variacao` | `float` | Variação monetária líquida (`saldo_atual - saldo_anterior`). |
| `status_sinistro` | `str` | Situação regulatória (`Avisado`, `Sob Regulação`, `Liquidado`, `Judicializado`). |
| `causa_sinistro` | `str` | Descrição técnica do fato gerador para justificativa perante auditoria. |

---

## 5. Modelo: `AuditoriaVarianceReport`

Consolidação da ponte de variação contábil e justificativa executiva para SUSEP e auditores externos.

| Campo | Tipo | Descrição |
|---|---|---|
| `periodo_referencia` | `str` | Mês/Ano de competência contábil (ex: `08/2026`). |
| `total_anterior_geral` | `float` | Saldo inicial agregado da carteira (R$). |
| `total_atual_geral` | `float` | Saldo final agregado da carteira (R$). |
| `delta_global` | `float` | Variação líquida global de provisão (R$). |
| `delta_global_percentual` | `float` | Variação percentual global do período (%). |
| `ramo_maior_ofensor` | `RamoVarianceSummary` | Ramo SUSEP que mais contribuiu para a oscilação da provisão. |
| `sinistro_maior_ofensor` | `SinistroItem` | Sinistro de maior materialidade individual da carteira. |
| `variacao_por_ramo` | `List[RamoVarianceSummary]` | Distribuição das variações por Ramo SUSEP. |
| `justificativa_auditoria_markdown` | `str` | Nota explicativa formal gerada para envio à SUSEP/Auditoria. |

