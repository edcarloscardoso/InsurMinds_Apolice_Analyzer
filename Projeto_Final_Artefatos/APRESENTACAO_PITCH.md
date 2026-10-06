# Roteiro de Demonstração & Pitch Deck (5 Minutos)
**InsurMinds Apólice Analyzer · Apresentação Final da Banca I2A2**<br>
*Instituto de Inteligência Artificial Aplicada — I2A2 (2026)*

---

| Metadado | Informação |
|---|---|
| **Projeto** | InsurMinds Apólice Analyzer |
| **Curso** | Inteligência Artificial Aplicada às Finanças e Seguros (InsurMinds) |
| **Instituição** | I2A2 — Instituto de Inteligência Artificial Aplicada |
| **Equipe** | Seguros Connect |
| **Integrantes** | Edcarlos Cardôso de Farias · Eric Narciso Pimentel dos Santos |
| **Data da Entrega** | 06 de Outubro de 2026 |
| **Duração Total** | 5 Minutos (Apresentação Oral / Gravação de Vídeo) |
| **Status do MVP** | Homologado em Linux (182/182 testes) · Windows 11: PENDING REAL VALIDATION |

---

## 1. O Problema de Negócio e de Pesquisa (0:00 – 0:45 min)

- **Complexidade do Domínio:** Apólices do ramo de Responsabilidade Civil de Diretores e Administradores (D&O) são documentos extensos, redigidos em linguagem jurídica e descentralizados entre condições gerais, especiais, exclusões, definições e cláusulas particulares.
- **Insuficiência da Busca Textual Direta:** Comparações simples por palavras-chave são ineficazes, pois termos idênticos (ex.: "custos de defesa") podem conter condições divergentes, enquanto redações diferentes podem tratar de garantias equivalentes.
- **Gargalos Operacionais:** O processo exige extração de dados em arquivos heterogêneos (PDFs digitais, escaneados e imagens), padronização em uma estrutura única de comparação e, sobretudo, exatidão na explicitação do trecho e da página que justificam cada diferença apontada.

---

## 2. A Solução Proposta (0:45 – 1:30 min)

- **Proposta de Valor:** O InsurMinds Apólice Analyzer é um MVP focado na análise e comparação assistida de apólices D&O.
- **Fluxo Contínuo de Processamento:** A solução articula um pipeline estruturado em 5 etapas principais:
  $$\text{Documento} \longrightarrow \text{Extração e OCR} \longrightarrow \text{Conhecimento Estruturado} \longrightarrow \text{Comparação Analítica} \longrightarrow \text{Diferenças e Evidências}$$
- **Escopo Assistido:** O sistema atua estritamente como ferramenta de apoio ao analista, subscritor ou corretor, sem a pretensão de substituir a avaliação jurídica ou realizar subscrições autônomas.

---

## 3. Arquitetura do Sistema e Pipeline Multiagente (1:30 – 2:30 min)

- **Arquitetura em Camadas:** Organizada em Apresentação (Streamlit), Orquestração, Agentes, Domínio (Pydantic / Regras) e Persistência (SQLite).
- **Modelo Conceitual vs. Execução Prática:** O fluxo de estados foi formalmente modelado em grafos via LangGraph, mas executado na interface do Streamlit por meio de *runners* procedurais para garantir controle previsível do progresso visual.
- **Pipeline Distribuído em 6 Agentes Especializados:**
  1. **Reception Agent:** Valida o arquivo por assinatura binária (*magic bytes*), calcula hashes e garante idempotência no banco de dados.
  2. **Extractor Agent:** Gerencia as rotas de extração (PDF digital via `pdfplumber`; PDF escaneado/imagem via OCR/Gemini Vision com fallback para `PyMuPDF` / `Tesseract`).
  3. **Identifier Agent:** Mapeia seções estratégicas de D&O (coberturas, exclusões, limites, franquias, retroatividade, jurisdição).
  4. **Structurer Agent:** Normaliza os dados extraídos no modelo canônico (`ApoliceDAO`) e associa as evidências documentais.
  5. **Comparator Agent:** Confronta os dados normalizados aplicando regras de negócio e classificações semânticas.
  6. **Reporter Agent:** Sintetiza os achados em pareceres explicativos e permite exportação em JSON e Markdown.

---

## 4. Uso Estratégico de Inteligência Artificial (2:30 – 3:15 min)

- **Structured Output e Pydantic:** Uso de modelos de linguagem (Google Gemini 2.0 Flash Lite) vinculados a schemas rígidos do Pydantic, assegurando respostas tipadas e prontas para persistência no banco SQLite.
- **Arquitetura Resiliente (Dual Mode):**
  - **Modo Online:** Utiliza a API do Gemini para interpretação multimodal e apoio na redação do parecer.
  - **Modo Offline / Contingência:** Garante o funcionamento contínuo através de regras determinísticas e heurísticas locais (`PyMuPDF`, `Tesseract`, `pdfplumber`), impedindo que a ausência de chave ou conexão interrompa o sistema.
- **Diretriz de Governança:** A IA atua como intérprete e organizadora, mantendo o documento original como única fonte primária da verdade.

---

## 5. Diferencial Técnico e Rastreabilidade (3:15 – 3:45 min)

- **Rastreabilidade por `EvidenceItem`:** Cada dado extraído ou divergência identificada vincula-se obrigatoriamente a uma estrutura contendo a página, trecho literal (*snippet*), método de extração e grau de confiança analítica (0.0 a 1.0).
- **Modelo Canônico `ApoliceDAO`:** Padroniza atributos heterogêneos de diferentes seguradoras em uma representação única (limites, franquias, vigência, garantias, exclusões, foro e processo SUSEP).
- **Classificação Semântica de Diferenças:** O motor classifica as relações entre cláusulas em categorias qualitativas (*equivalente*, *diferente*, *escopo ampliado/reduzido*, *condição alterada*, *limite alterado*). Utiliza também o Índice de Jaccard como métrica auxiliar de similaridade estrutural, evitando usá-lo como parecer decisório.

---

## 6. Metodologia de Testes e Homologação (3:45 – 4:30 min)

- **Validação Multi-Camadas:** Testes unitários, de integração, de interface e de aceitação com documentos reais.
- **Suíte de Testes Automatizada:** Atingiu **182 testes aprovados** sem nenhuma falha ou erro em ambiente Linux (`pytest` executado em 238,65s).
- **Validação com Corpus Real:** Avaliação realizada sobre documentos públicos de grandes seguradoras do mercado brasileiro (**AIG Brasil**, **Berkley Brasil**, **Chubb**, **EZZE** e **Sompo**), com testes de comparação nos pares homologados (*Sompo v1.2 × Sompo v1.5* e *Chubb OPD 2024 × Chubb OPD 2025*).
- **Transparência Acadêmica de Ambiente:** A homologação no Linux foi concluída com 100% de êxito. Em Windows 11, o status foi registrado como **PENDING REAL VALIDATION** devido a um problema de encoding/parsing no script de configuração PowerShell 5.1 (`setup_windows.ps1`).

---

## 7. Principais Resultados e Conclusão (4:30 – 5:00 min)

- **Requisitos Cumpridos:** Atendimento integral com status PASS aos 7 requisitos funcionais (RF01 a RF07), abrangendo desde o upload seguro até a interface multipágina em Streamlit.
- **Limitações Reconhecidas:** Dependência da qualidade de imagem no OCR, escopo atualmente calibrado para o ramo D&O e ausência de testes em apólices privadas com prêmios e limites reais negociados.
- **Conclusão para a Banca:** O projeto entrega um MVP consistente, estável e auditável para o contexto acadêmico, demonstrando como a IA Generativa pode ser integrada ao setor de seguros com rigor técnico, governança e rastreabilidade total.
