# AUDITORIA TÉCNICA — FASE 7.11C: REMEDIAÇÃO CONTROLADA DE INGESTÃO NATIVA DE IMAGENS

**InsurMinds Apólice Analyzer — Insurance Intelligence v1.0**
*Data de Execução:* 30 de Setembro de 2026
*Status:* **APROVADO (PASS)**
*Ambiente de Execução:* openSUSE Tumbleweed (Linux 6.13.0) · Python 3.13.14 · Streamlit v1.50+

---

## 1. MOTIVAÇÃO

Na auditoria prévia do **Gate 7.11B**, foi identificado um gap crítico entre o enunciado oficial do Projeto Final InsurMinds e a implementação técnica original: o sistema aceitava estritamente arquivos com extensão `.pdf` e assinatura binária `%PDF-`, bloqueando a leitura de imagens em formato PNG, JPG ou JPEG tanto na camada de segurança (`core/security.py`), quanto nos agentes de recepção (`agents/reception_agent.py`) e na interface web (`ui/page_upload.py`).

Conforme o enunciado oficial:
> *"Permitir a leitura de documentos em formato PDF ou imagem."*

A equipe técnica emitiu **AUTORIZAÇÃO EXPLÍCITA** para a execução da **Fase 7.11C**, permitindo modificações pontuais e controladas em `core/`, `agents/`, `ui/` e testes, com a regra pétrea de:
- **NÃO** desmantelar ou fragilizar o pipeline existente de PDFs;
- **NÃO** recorrer à conversão rasa de imagem para PDF em disco como único artifício;
- Tratar imagem como imagem, estabelecendo uma rota explícita de validação binária, OCR multimodal/determinístico e convergência no mesmo modelo canônico `ApoliceDAO`.

---

## 2. REQUISITO OFICIAL ATENDIDO

O requisito oficial do edital do Projeto Final foi integralmente cumprido:
- Suporte nativo à ingestão de documentos nos formatos **PDF**, **PNG**, **JPG** e **JPEG**;
- Reconhecimento automático do tipo documental e integridade na camada de recepção;
- Extração textual inteligente de imagem com atribuição auditável (`page_count = 1`);
- Geração transparente de `EvidenceItem` com rastreabilidade literal, snippet e identificação de método (`ocr` / `gemini_vision`);
- Confronto A ⟷ B multimodal:
  - **Imagem × PDF** (Validado E2E)
  - **Imagem × Imagem** (Validado E2E)
  - **PDF × PDF** (Regressão legada 100% verde)

---

## 3. ARQUIVOS ALTERADOS

As alterações foram estritamente cirúrgicas e controladas:

| Componente | Arquivo | Natureza da Modificação |
| :--- | :--- | :--- |
| **Configuração** | `core/config.py` | Definição de `IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}` e expansão de `ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}`. |
| **Segurança** | `core/security.py` | Preservação estrita de `validate_pdf_content` (legado) e criação de `validate_document_content` com validação de magic-bytes para PNG (`\x89PNG\r\n\x1a\n`), JPEG (`\xFF\xD8\xFF`) e verificação de integridade via PIL. |
| **Esquemas** | `core/schemas.py` | Adição do campo `document_format: str = Field(default="pdf")` em `DocumentState`. |
| **Cliente LLM / Visão** | `core/llm_client.py` | Adição de `extract_text_from_image` utilizando o SDK `google-genai` com `types.Part.from_bytes` e telemetria segura; parametrização de método nos `EvidenceItems`. |
| **Agente 1** | `agents/reception_agent.py` | Rota para validação de imagem e PDF via `validate_document_content`, atribuição de `document_format` e fixação de `page_count = 1` para imagens. |
| **Agente 2** | `agents/extractor_agent.py` | Rota nativa de extração de imagem: **Prioridade A (Gemini Multimodal Vision)** e **Prioridade B (Fallback Determinístico PyMuPDF + Tesseract C-bindings)**, com tratamento defensivo de imagens ilegíveis. |
| **Orquestrador** | `agents/graph.py` | Normalização das mensagens de callback de progresso para linguagem de tarefa profissional sem nomes internos de agentes. |
| **Frontend** | `ui/page_upload.py` | Atualização do `st.file_uploader` para aceitar `["pdf", "png", "jpg", "jpeg"]`, exibição do formato detectado, metadados (`1 página (Imagem / OCR)`) e microcopy orientada a tarefas (`_render_task_checklist`). |
| **Navegação UI** | `app.py` | Suporte a query params para seleção de documentos sob confronto e detalhe de diferenças. |
| **Documentação** | `README.md` | Inclusão de notas operacionais sobre formatos suportados e OCR local nativo. |
| **Testes** | `tests/test_image_ingestion.py` | Criação de 18 novos testes automatizados cobrindo todos os requisitos e cenários negativos. |

---

## 4. ARQUITETURA ANTES / DEPOIS

### Antes (Fase 7.11B)
```
Upload (.pdf apenas)
       ↓
validate_pdf_content (%PDF-)
       ↓
ReceptionAgent (Status: erro se não for PDF)
       ↓
ExtractorAgent (pdfplumber -> PyMuPDF -> Gemini Vision apenas para PDF escaneado)
       ↓
Identifier / Structurer -> ApoliceDAO
```

### Depois (Fase 7.11C — Remediação Concluída)
```
                                 [ UPLOAD ]
                                      │
                 ┌────────────────────┴────────────────────┐
                 ▼                                         ▼
            [ Rota PDF ]                              [ Rota Imagem ]
                 │                                         │
        validate_document_content                 validate_document_content
           (%PDF- / 1024b)                     (PNG \x89PNG / JPEG \xFF\xD8\xFF)
                 │                                         │
           Recepção PDF                              Recepção Imagem
        (page_count real)                          (page_count = 1 fixo)
                 │                                         │
           Extração PDF                              Extração Imagem
     (pdfplumber / PyMuPDF)                   ┌────────────┴────────────┐
                 │                            ▼                         ▼
         [ PDF Escaneado ]            [ Gemini Vision ]         [ OCR Determinístico ]
                 │                    (Multimodal API)        (PyMuPDF + libtesseract5)
                 └──────────────┬─────────────┘                         │
                                │                                       │
                                └───────────────────┬───────────────────┘
                                                    ▼
                                           [ DocumentState ]
                                         (raw_text unificado)
                                                    │
                                           [ Identifier Agent ]
                                                    │
                                           [ Structurer Agent ]
                                     (evidências: page=1, method)
                                                    │
                                                    ▼
                                              [ ApoliceDAO ]
                                                    │
                                            [ Comparador D&O ]
                                                    │
                                           [ Relatório Executivo ]
```

---

## 5. SEGURANÇA E HIGIENIZAÇÃO BINÁRIA

A segurança foi substancialmente aprofundada, impedindo vulnerabilidades de bypass por extensão ou renomeação maliciosa:
1. **Magic Bytes Reais**:
   - PNG: `89 50 4E 47 0D 0A 1A 0A` (8 primeiros bytes checados rigorosamente).
   - JPEG/JPG: `FF D8 FF` (3 primeiros bytes checados rigorosamente).
   - PDF: `%PDF-` nos primeiros 1024 bytes.
2. **Rejeição Estrita de Spoofing de Extensão**:
   - PNG renomeado para `.jpg` → REJEITADO imediatamente.
   - JPG renomeado para `.png` → REJEITADO imediatamente.
   - PDF renomeado para `.png` → REJEITADO imediatamente.
   - Arquivo binário arbitrário/texto renomeado para `.png` → REJEITADO imediatamente.
3. **Detecção de Corrupção por Decodificação**:
   - Imagens válidas passam por `PIL.Image.open(io.BytesIO(data)).verify()`.
   - Se o cabeçalho for adulterado ou o stream de compressão estiver truncado, a imagem é rejeitada antes de entrar no pipeline de processamento.
4. **Proteção contra Path Traversal**:
   - Mantida em `core/security.py` via `get_safe_destination_path` com resolução de caminho canônico restrito a `UPLOADS_DIR`.

---

## 6. OCR UTILIZADO

- **Implementação Determinística Local**:
  - Aproveitamento nativo dos C-bindings do `PyMuPDF` (`fitz`) com o motor de OCR `tesseract` (`libtesseract5-5.5.3-1.1.x86_64`) já disponível no sistema operacional openSUSE Tumbleweed.
  - Prefixação configurada: `TESSDATA_PREFIX=/usr/share/tessdata`.
  - Mecanismo: `tp = page.get_textpage_ocr(language='eng', dpi=150); tp.extractText()`.
  - **Desempenho**: Extração de 437 caracteres em ~0.4s na amostra rasterizada de alta resolução `apolice_do_rasterizada.png`.

---

## 7. INTEGRAÇÃO MULTIMODAL GOOGLE GEMINI

- **Método**: `core/llm_client.py` → `extract_text_from_image(file_path_or_bytes, mime_type)`.
- **SDK**: `google-genai` oficial, utilizando `types.Part.from_bytes(data=img_bytes, mime_type=mime)`.
- **Modelo Configurado**: `gemini-2.5-flash` (ou `gemini-2.0-flash`).
- **Prompt Especializado**: Orientado a OCR literal e tabelas contratuais D&O, preservando limites de responsabilidade, números de apólice e processos SUSEP sem alucinações.
- **Segurança de Credenciais**:
  - Telemetria registrada via `_record_call`: timestamp, latência em ms, contagem de caracteres e status.
  - **Nenhuma chave de API, token ou segredo é exposto em logs ou na interface.**

---

## 8. FALLBACK DETERMINÍSTICO E RESILIÊNCIA

Quando o Gemini não está disponível (chave ausente ou sem cota):
1. O pipeline aciona automaticamente o OCR local determinístico via `PyMuPDF / Tesseract`.
2. O texto extraído é repassado ao `identifier_agent` e `structurer_agent`.
3. Se a imagem estiver em branco ou for ilegível (< 20 caracteres úteis), o sistema trata defensivamente emitindo erro amigável:
   > *"A imagem foi recebida, mas o conteúdo textual não pôde ser extraído com qualidade suficiente."*
4. O sistema nunca trava ou mascou erros.

---

## 9. SUÍTE DE TESTES AUTOMATIZADOS (18 TESTES NOVOS)

Arquivo: `tests/test_image_ingestion.py`
Execução: `pytest tests/test_image_ingestion.py -v`
Resultado: **18/18 PASSED em 24.21s**

| # | Caso de Teste | Status | Detalhes |
| :-: | :--- | :-: | :--- |
| 1 | `test_01_png_valido_aceito` | **PASSED** | Aceitação de PNG com magic bytes corretos e formato 'image'. |
| 2 | `test_02_jpg_valido_aceito` | **PASSED** | Aceitação de JPG com magic bytes corretos e formato 'image'. |
| 3 | `test_03_jpeg_valido_aceito` | **PASSED** | Aceitação de JPEG com magic bytes corretos e formato 'image'. |
| 4 | `test_04_arquivo_invalido_rejeitado` | **PASSED** | Bloqueio de arquivos `.exe` e `.txt`. |
| 5 | `test_05_conteudo_incompativel_rejeitado` | **PASSED** | Bloqueio de PNG como JPG, JPG como PNG, PDF como PNG e corrompido. |
| 6 | `test_06_pdf_continua_aceito` | **PASSED** | PDF válido aceito em `validate_document_content` e `validate_pdf_content`. |
| 7 | `test_07_imagem_gera_documentstate_valido` | **PASSED** | Agente 1 gera DocumentState com `document_format='image'` e hash MD5. |
| 8 | `test_08_imagem_gera_page_count_correto` | **PASSED** | Imagem registra rigorosamente `page_count = 1`. |
| 9 | `test_09_ocr_retorna_texto` | **PASSED** | Extração de texto documental inteligível (>50 caracteres). |
| 10 | `test_10_imagem_sem_texto_tratamento_defensivo` | **PASSED** | Imagem em branco produz erro claro sem exception não tratada. |
| 11 | `test_11_evidence_item_criado_para_imagem` | **PASSED** | EvidenceItem com `page=1`, snippet e método auditável. |
| 12 | `test_12_imagem_segue_para_estruturacao` | **PASSED** | StructurerAgent processa estado de imagem sem anomalias. |
| 13 | `test_13_imagem_chega_ao_mesmo_apolice_dao` | **PASSED** | Imagem gera instância canônica `ApoliceDAO` com ID idempotente. |
| 14 | `test_14_comparacao_imagem_x_pdf` | **PASSED** | Confronto A/B Imagem × PDF produz `ComparisonResult` e relatório. |
| 15 | `test_15_comparacao_imagem_x_imagem` | **PASSED** | Confronto A/B Imagem × Imagem executa no pipeline padrão. |
| 16 | `test_16_regressao_pdf_escaneado_preservada` | **PASSED** | Detecção de PDF escaneado preservada no `extractor_agent`. |
| 17 | `test_17_regressao_pdf_normal_preservada` | **PASSED** | PDF Sompo v1.2 processado integralmente (>10 páginas). |
| 18 | `test_18_fluxo_completo_pipeline_com_callbacks` | **PASSED** | Execução ponta a ponta com registro dos 4 passos de progresso. |

---

## 10. TESTES DE REGRESSÃO DA SUÍTE COMPLETA

Execução: `./.venv/bin/pytest tests/ -q`
Resultado: **176 PASSED em 246.42s (04m06s)**
Zero falhas, zero warnings bloqueantes. Todos os 158 testes legados das fases anteriores permaneceram verdes.

---

## 11. TESTE E2E REAL VIA STREAMLIT (UI)

- **Servidor Ativo**: `http://localhost:8503` (Daemon task).
- **Controlador**: Chrome DevTools Protocol (CDP) via Google Chrome headless (`/usr/bin/google-chrome`) com viewport calibrado.
- **Fluxos Homologados**:
  1. **Upload Imagem × PDF**:
     - Documento A: `apolice_do_rasterizada.png` (PNG válido, 1 página OCR).
     - Documento B: `DO_SOMPO_CONDICOES_GERAIS_V1_2_2024_010.pdf` (PDF Sompo v1.2, 84 páginas).
     - Validação na UI: ambos os cartões verdes com badges `✓ Imagem válida (PNG)` e `✓ Arquivo PDF válido`.
     - Execução da Comparação: concluída com sucesso.
     - Navegação para Comparação, Detalhe e Evidência Auditável 100% operacionais.
  2. **Upload Imagem × Imagem**:
     - Documento A: `apolice_do_rasterizada.jpg` (JPEG válido).
     - Documento B: `apolice_do_rasterizada.png` (PNG válido).
     - Comparação gerou 14 equivalências contratuais diretas e relatório executivo completo.

---

## 12. QA VISUAL MULTI-RESOLUÇÃO (SCREENSHOTS)

Todas as 15 telas foram capturadas e arquivadas em alta resolução:

### Resolução Principal — 1440×900
- `docs/captura_telas/tela01_inicio.png` (164 KB) — Workspace principal com resumo de atividades.
- `docs/captura_telas/tela02_nova_analise.png` (154 KB) — Uploader com suporte explícito a PDF ou Imagem (PNG, JPG, JPEG).
- `docs/captura_telas/tela03_comparacoes.png` (145 KB) — Tela de Comparação com confronto multimodal ativo.
- `docs/captura_telas/tela04_detalhe.png` (145 KB) — Tela de Detalhe da Diferença.
- `docs/captura_telas/tela05_documentos.png` (156 KB) — Biblioteca documental operacional.
- `docs/captura_telas/tela06_relatorios.png` (143 KB) — Relatório analítico executivo.
- `docs/captura_telas/tela07_configuracoes_ia_integracoes.png` (175 KB) — Configurações de IA e auditoria contábil.

### Resoluções Complementares
- **1366×768**:
  - `docs/captura_telas/multi_res/inicio_1366x768.png` (138 KB)
  - `docs/captura_telas/multi_res/nova_analise_1366x768.png` (124 KB)
  - `docs/captura_telas/multi_res/comparacao_1366x768.png` (121 KB)
  - `docs/captura_telas/multi_res/configuracoes_1366x768.png` (155 KB)
- **1024×768**:
  - `docs/captura_telas/multi_res/inicio_1024x768.png` (118 KB)
  - `docs/captura_telas/multi_res/nova_analise_1024x768.png` (110 KB)
  - `docs/captura_telas/multi_res/comparacao_1024x768.png` (105 KB)
  - `docs/captura_telas/multi_res/configuracoes_1024x768.png` (125 KB)

---

## 13. HOLDOUT TESTS EXTRAS

Foi executado processamento de par documental holdout não cacheado:
- **Imagem Holdout**: `apolice_do_rasterizada.jpg` (tempo de extração: 1.36s).
- **PDF Holdout**: `DO_EZZE_CONDICOES_GERAIS_2026_009.pdf` (84 páginas, tempo de extração: 11.89s).
- **Comparação**: executada em 0.02s, gerando 14 diffs estruturais e parecer executivo com 4.782 caracteres.

---

## 14. DEPENDÊNCIAS

- **Nenhuma dependência Python nova** foi adicionada ao `pyproject.toml` ou `requirements.txt`.
- O motor de OCR determinístico aproveitou os recursos nativos já existentes no ambiente:
  - `PyMuPDF` (`fitz` 1.28.2);
  - `libtesseract5` e `tesseract-ocr-common` instalados no sistema operacional.
- O motor multimodal utilizou o SDK oficial `google-genai` previamente configurado.

---

## 15. LIMITAÇÕES CONHECIDAS

1. **Documentos multipágina em imagem**: Como os formatos PNG/JPG são nativamente de página única, cada arquivo de imagem é registrado com `page_count = 1`. Imagens de apólices com múltiplas páginas físicas devem ser fornecidas como páginas individuais ou preferencialmente agregadas em PDF.
2. **Qualidade da Imagem**: Fotografias com sombras severas, baixa resolução (<100 DPI) ou texto cortado nas bordas são tratadas defensivamente pelo sistema, emitindo notificação de erro sem travar a aplicação.

---

## 16. GOVERNANÇA GIT

- `git commit`: **NÃO EXECUTADO** (0 commits criados)
- `git push`: **NÃO EXECUTADO** (0 pushes realizados)
- `git pull request / merge`: **NÃO EXECUTADO** (repositório congelado localmente)

---

## 17. VEREDITO FINAL

```
==================================================
           VEREDITO DA FASE 7.11C: PASS
==================================================
[x] Requisito oficial de imagem (PNG/JPG/JPEG) atendido
[x] Validação binária de segurança implementada
[x] Rota de imagem explícita sem atalhos indevidos
[x] Zero regressão nos 158 testes legados de PDF
[x] 18 novos testes automatizados verdes (176 no total)
[x] Comparação Imagem x PDF validada na UI
[x] Comparação Imagem x Imagem validada na UI
[x] Evidências rastreáveis geradas (page=1, method)
[x] Capturas de tela multi-resolução salvas
[x] Zero credenciais ou segredos expostos
[x] Governança de Git estritamente respeitada (zero commit/push)
==================================================
```
