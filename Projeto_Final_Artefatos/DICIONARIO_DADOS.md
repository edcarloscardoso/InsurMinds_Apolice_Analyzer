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
