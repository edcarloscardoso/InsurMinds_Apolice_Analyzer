# AUDITORIA FASE 7.9 — IMPLEMENTAÇÃO DO “ASSISTENTE CONTEXTUAL” — COPILOTO DE LEITURA, NÃO CHATBOT GENÉRICO
**Projeto:** InsurMinds Apólice Analyzer — Insurance Intelligence v1.0
**Data:** 30/09/2026
**Status:** APROVADO (PASS)

---

## 1. OBJETIVO DA FASE 7.9

Adicionar ao frontend um **Assistente Contextual** do InsurMinds Apólice Analyzer que auxilie o profissional de seguros (analista, subscritor, corretor, jurídico ou visitante) a compreender a análise contratual D&O atualmente aberta, sem criar uma segunda camada analítica independente e sem transformar a aplicação em um chatbot conversacional genérico.

- **Princípio Central:** *“O assistente explica o contexto disponível; o documento continua sendo a fonte.”*
- **Base de Dados Exclusiva:** Responde estritamente a partir do contexto já carregado em memória/banco:
  - Comparação atual (`ComparisonResult`);
  - Diferenças entre campos contratuais (`FieldDiff`);
  - Relações e equivalências semânticas (`SemanticMatchItem`);
  - Evidências documentais literais e números de página (`EvidenceItem`);
  - Metadados dos documentos em confronto A/B (`ApoliceDAO`);
  - Síntese estruturada do relatório (`relatorio_markdown`).
- **Governança de IA:**
  - Exibição compulsória do aviso legal: *"Assistência por IA: Respostas são geradas a partir do contexto documental disponível e devem ser revisadas pelo profissional responsável. O texto contratual permanece sendo a fonte primária."*;
  - Indicação explícita em caso de ausência de prova: *"Não há evidência documental disponível para sustentar esta resposta."*;
  - Separação mandatória entre a transcrição literal da fonte primária (em `IBM Plex Mono`) e a interpretação contextual para o perfil.

---

## 2. AUDITORIA DO MECANISMO DE IA / LLM DISPONÍVEL

Antes de qualquer implementação, foi auditado o pipeline de inteligência artificial em `core/llm_client.py` e `agents/`:
1. **Mecanismos Existentes:** O sistema possui prompts e chamadas para extração estruturada de campos via Gemini (`extract_policy_fields`), identificação semântica de cláusulas (`analyze_semantic_matches`) e redação do parecer executivo (`generate_comparative_report`).
2. **Inexistência de Endpoint Conversacional:** NÃO existe no backend congelado qualquer endpoint REST ou WebSocket para diálogo em tempo real ou chat multi-turn.
3. **Decisão Arquitetural Estrita:**
   - Em estrito cumprimento à regra crítica de governança ("Se NÃO houver mecanismo seguro e já existente para conversação contextual: NÃO criar backend novo; NÃO criar endpoint novo; NÃO fingir que existe IA conversacional; implementar o shell contextual e ações orientativas somente sobre os dados já disponíveis"), implementou-se um **Copiloto de Leitura Contextual** determinístico e estruturado;
   - As ações e sugestões de leitura exploram profundamente a árvore de evidências documentais já auditadas pelo pipeline, sem simular LLM inexistente e com total integridade factual.

---

## 3. ARQUIVOS CRIADOS / ALTERADOS

### Criados:
1. `ui/components/context_assistant.py`:
   - Componente principal do Assistente Contextual (`render_context_assistant` e `get_assistant_context`);
   - Mapeamento dinâmico de contexto por tela (`Comparação`, `Detalhe da Diferença`, `Relatório`, `Biblioteca / Documentos`, `Início / Workspace`);
   - Formatadores factuais: `format_difference_summary`, `format_scope_changes`, `format_review_items`, `format_clause_explanation`, `format_clause_diff_ab`, `format_clause_evidence`, `format_report_summary`, `format_report_findings`, `format_library_summary`, `format_library_comparisons`, `format_workspace_guide`;
   - Renderização limpa via `render_html` evitando anomalias de parsing CommonMark.
2. `tests/test_fase7_9_assistant.py`:
   - 19 testes automatizados cobrindo detecção de contexto, ações contextuais por tela, os 5 perfis corporativos, ausência de evidências, disclaimer de governança e neutralidade de vocabulário.
3. `scripts/qa_fase7_9.py`:
   - Script de QA visual automatizado utilizando Chrome CDP headless com 12 cenários em 1440x900, 1366x768 e 1024x768.
4. `docs/audits/FASE_7_9_ASSISTENTE_CONTEXTUAL.md`:
   - Este documento formal de auditoria e conformidade.

### Alterados:
1. `ui/components/app_shell.py`:
   - Inclusão do acionador discreto `[🧠 Assistente]` / `[✕ Fechar]` na barra superior (`TopBar`) e botão de alternância no menu lateral (`Sidebar`);
   - Gerenciamento de abertura/fechamento através de `st.session_state["context_assistant_open"]`.
2. `ui/components/__init__.py`:
   - Exportação pública de `render_context_assistant` e `get_assistant_context`.
3. `ui/styles.py`:
   - Adição de tokens e regras CSS para o painel contextual (`.im-assistant-panel`, `.im-assistant-header`, `.im-assistant-context-bar`, `.im-assistant-box`, `.im-assistant-gov-box`).
4. `app.py`:
   - Renderização retrátil do `render_context_assistant` logo abaixo da TopBar quando o estado estiver ativo, acompanhando a tela atual sem abandonar a navegação principal.

---

## 4. COMPONENTES DO DESIGN SYSTEM UTILIZADOS

| Componente / Token | Origem | Finalidade no Assistente |
| :--- | :--- | :--- |
| `render_html` | `ui.styles` | Renderização livre de erros de código indentado (CommonMark) |
| `COLORS` | `ui.tokens` | Paleta institucional (Primary Navy `#1E3A8A`, Light Navy `#2B6CB0`, Slate Gray `#64748B`, Neutral Gray `#F8FAFC`) |
| `TYPOGRAPHY` | `ui.tokens` | Inter para microcopy e IBM Plex Mono para citações literais e evidências |
| `RADIUS` & `SHADOWS` | `ui.tokens` | Elevações e bordas corporativas sem estilos cyberpunk/glassmorphism |
| `render_semantic_badge` | `ui.components.badges` | Identificação visual de equivalências e relações semânticas |
| `navigate_to` | `ui.navigation` | Navegação cruzada fluida para aprofundamento na evidência ou retorno |

---

## 5. DADOS REAIS UTILIZADOS NO TESTE E QA

A funcionalidade foi validada com os contratos reais D&O já processados no repositório:

1. **Chubb 2024 × Chubb 2025 (`DO_005` × `DO_014`):**
   - **Cláusulas Auditadas:** 9 cláusulas confrontadas;
   - **Divergências Identificadas:** 4 alterações de escopo (*Custos de Defesa*, *Cobertura Side A*, *Investigações Regulatórias e Administrativas*, *Atos Dolosos e Fraude*);
   - **Evidências Literais:** Apresentação fiel com citação direta de página (ex: pág. 35 para Custos de Defesa, pág. 17 para Cobertura Side A);
   - **Diferença A/B:** Demonstração simétrica entre a versão emitida e as condições gerais de oferta pública.

2. **Sompo 2024 × Sompo 2025 (`DO_010` × `DO_012`):**
   - **Cláusulas Auditadas:** 6 cláusulas mapeadas;
   - **Confronto:** Equivalências semânticas e variações nas condições de *Inadimplemento do Prêmio*, *Defesa e Acordos* e *Garantias Pessoais*;
   - **Adaptação de Perfis:** Testado com sucesso nos 5 perfis profissionais (Analista, Subscritor, Corretor, Jurídico e Visitante).

---

## 6. FLUXOS E INTERAÇÕES TESTADOS

1. **Acionamento Discreto e Retrátil:**
   - Botão `[🧠 Assistente]` na barra superior e no menu lateral;
   - Abertura sem encobrir a visão global ou interromper a análise;
   - Fechamento imediato pelo botão `[✕ Fechar Assistente]`.
2. **Contextualização Dinâmica por Tela:**
   - **Na Comparação:** Sugestões para resumir diferenças gerais, explicar alterações de escopo e listar itens para revisão do perfil;
   - **No Detalhe da Diferença:** Contexto específico da cláusula selecionada, resumo do impacto A → B e exibição da evidência auditável com citação literal;
   - **No Relatório:** Síntese da estrutura do parecer, achados analíticos e pontos pendentes de homologação;
   - **Na Biblioteca:** Inventário dos documentos armazenados e atalhos para comparações salvas.
3. **Navegação de Continuidade:**
   - O assistente permite transição direta entre o resumo contextual e a auditoria minuciosa (`Auditar Cláusula #1 ➔`), retorno à comparação (`Voltar à Comparação Geral`) ou consulta ao dossiê.
4. **Respeito aos 5 Perfis de Trabalho:**
   - Adaptação de microcopy sem alterar dados, métricas, scores ou textos legais.

---

## 7. EVIDÊNCIAS DE QA VISUAL E RESPONSIVIDADE

Executado script automatizado via CDP (`scripts/qa_fase7_9.py`) gravando screenshots nas seguintes resoluções e estados:

| Arquivo de Screenshot | Resolução | Tela / Ação Validada |
| :--- | :--- | :--- |
| `fase7_9_01_compare_closed_1440.png` | 1440×900 | Comparação aberta com Assistente inicialmente fechado |
| `fase7_9_02_assistant_open_compare_1440.png` | 1440×900 | Assistente aberto na Comparação exibindo contexto A×B e resumo inicial |
| `fase7_9_03_assistant_open_compare_1366.png` | 1366×768 | Responsividade em notebook corporativo com proporções perfeitas |
| `fase7_9_04_assistant_open_compare_1024.png` | 1024×768 | Responsividade compacta sem quebra de layout ou sobreposição |
| `fase7_9_05_action_escopo_1440.png` | 1440×900 | Ação executada: "Explicar alterações de escopo" |
| `fase7_9_06_action_revisao_1440.png` | 1440×900 | Ação executada: "Mostrar itens para revisão profissional" |
| `fase7_9_07_assistant_in_detalhe_1440.png` | 1440×900 | Assistente ativo na tela de Detalhe da Diferença (Cláusula #1) |
| `fase7_9_08_detalhe_evidencia_1440.png` | 1440×900 | Ação executada: "Mostrar a evidência relacionada" (trechos literais em monospace) |
| `fase7_9_09_back_to_compare_1440.png` | 1440×900 | Navegação assistida de retorno à Comparação Geral |
| `fase7_9_10_assistant_in_relatorio_1440.png` | 1440×900 | Assistente integrado e contextual na tela de Relatório Executivo |
| `fase7_9_11_assistant_in_documentos_1440.png` | 1440×900 | Assistente contextual na Biblioteca de Documentos |
| `fase7_9_12_assistant_closed_again_1440.png` | 1440×900 | Fechamento bem-sucedido restaurando o shell padrão |

---

## 8. TESTES AUTOMATIZADOS EXECUTADOS

Execução completa da suíte de testes do projeto via `pytest`:

```bash
./.venv/bin/pytest tests/ -q
```

**Resultado:**
- **153 passed in 218.76s (0:03:38)**
- Total de 134 testes anteriores preservados + 19 novos testes específicos da Fase 7.9 em `tests/test_fase7_9_assistant.py` (**100% GREEN**).

---

## 9. CONFORMIDADE COM A GOVERNANÇA DE CÓDIGO E GIT

- [x] **Backend 100% Congelado:** Nenhuma alteração realizada em `core/` ou `agents/`;
- [x] **Banco de Dados Preservado:** Zero novas tabelas, colunas, migrations ou esquemas;
- [x] **Sem Lógica Fictícia:** Nenhuma simulação de IA conversacional não existente;
- [x] **Sem Usuários Fictícios:** Nenhum mock de login, autenticação ou autorização inventado;
- [x] **Integridade do Git:**
  - **Zero commit;**
  - **Zero push;**
  - **Zero PR;**
  - **Zero merge.**

---

## 10. CHECKLIST DE CRITÉRIO DE ACEITE

- [x] Assistente é contextual
- [x] Assistente não domina a interface
- [x] Contexto vem da análise atual
- [x] Não cria nova lógica de comparação
- [x] Não altera resultados
- [x] Não inventa evidências
- [x] Evidência pode ser aberta
- [x] Interpretação é distinguida da fonte
- [x] Sem recomendação de compra
- [x] Sem decisão automática de risco
- [x] Sem parecer jurídico automático
- [x] Sem usuário fictício
- [x] Sem banco novo
- [x] Sem backend novo
- [x] Persona altera apenas apresentação
- [x] Comparação validada
- [x] Detalhe validado
- [x] Relatório validado
- [x] Biblioteca validada
- [x] 1440×900
- [x] 1366×768
- [x] 1024×768
- [x] Sompo
- [x] Chubb
- [x] 134/134 testes ou superior (153/153 obtidos)
- [x] `core/` intacto
- [x] `agents/` intacto
- [x] zero commit
- [x] zero push
- [x] zero PR
- [x] zero merge

---

## 11. CONCLUSÃO

A implementação do **Assistente Contextual (Copiloto de Leitura D&O)** cumpriu 100% das diretrizes do Insurance Intelligence Design System, da especificação funcional e da governança técnica estrita.

**Resultado da Avaliação: PASS**
