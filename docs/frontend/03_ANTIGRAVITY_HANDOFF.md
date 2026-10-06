# InsurMinds — Antigravity Frontend Handoff v1.0

## 1. Finalidade

Este documento é o contrato operacional para implementação do frontend.

Antes de alterar a UI, ler:
1. `docs/frontend/00_FRONTEND_MASTER_INDEX.md`
2. `docs/frontend/01_PRODUCT_UX_SPEC.md`
3. `docs/frontend/02_DESIGN_SYSTEM.md`
4. wireframes correspondentes

---

## 2. REGRA ABSOLUTA — BACKEND FREEZE

A implementação deve ser **frontend only**.

Não modificar, salvo aprovação explícita:
- `core/schemas.py`
- `core/diff_engine.py`
- `core/llm_client.py`
- `core/document_chunker.py`
- `core/consolidation.py`
- pipeline dos agentes;
- banco/estrutura analítica;
- contratos de dados.

Se uma necessidade de UI parecer exigir alteração do backend:
1. parar;
2. explicar a necessidade;
3. indicar impacto;
4. aguardar aprovação.

---

## 3. Dados disponíveis

A camada de apresentação deve consumir os dados existentes.

### Documento
`ApoliceDAO`

### Diferença
`FieldDiff`

### Comparação
`ComparisonResult`

### Correspondência semântica
`SemanticMatchItem`

### Evidência
`EvidenceItem`

Não criar campos contratuais fictícios apenas para preencher a UI.

---

## 4. Tradução de dados

A UI é responsável por adaptar linguagem técnica.

Exemplo:

```text
changed_condition
        ↓
Condição alterada
```

Não alterar o valor interno.

---

## 5. Perfil de trabalho

O MVP utiliza sessão frontend.

Perfis:
- Analista de Seguros
- Subscritor / Underwriter
- Corretor
- Jurídico / Compliance
- Visitante

O perfil pode modificar:
- ordenação;
- prioridade;
- filtros;
- densidade;
- linguagem.

Nunca modificar:
- resultado;
- evidência;
- classificação;
- conteúdo contratual.

---

## 6. Autenticação

Não implementar login no MVP.

Não inventar:
- nome;
- empresa;
- cargo;
- conta;
- permissões.

Futuro login é responsabilidade de outra fase.

---

## 7. Mapeamento por tela

### Início
Usar:
- dados agregados existentes;
- comparações persistidas;
- documentos persistidos.

### Nova análise
Usar:
- upload existente;
- pipeline existente;
- estados de processamento existentes.

### Comparação
Usar:
- `ComparisonResult`;
- `FieldDiff`;
- `SemanticMatchItem`;
- evidências.

### Detalhe
Usar:
- `FieldDiff`;
- `evidence_a`;
- `evidence_b`;
- relações semânticas.

### Biblioteca
Usar:
- `ApoliceDAO`;
- metadados disponíveis;
- persistência existente.

### Relatório
Usar:
- resultado da comparação;
- dados existentes;
- relatório persistido/gerado.

---

## 8. Regras de evidência

A interface deve preservar:
- página;
- snippet;
- origem;
- método;
- confiança;
- contexto, quando disponível.

Nunca:
- inventar evidência;
- criar página;
- alterar snippet;
- apresentar ausência como dado conhecido.

Quando inexistente:
> “Não identificado no documento.”

---

## 9. Regras de semântica

As sete relações canônicas devem permanecer intactas:

- semantic_equivalent
- different
- broader
- narrower
- changed_scope
- changed_condition
- changed_limit

A UI somente traduz.

---

## 10. Score

O score de similaridade é **indicador auxiliar**.

Não exibir como:
- nota;
- ranking;
- qualidade;
- recomendação;
- “melhor apólice”.

Não usar o score para reordenar alterações substantivas.

---

## 11. Assistente

O assistente é contextual.

Pode:
- resumir diferenças;
- explicar cláusula;
- listar alterações;
- responder usando a análise.

Não pode:
- inventar fatos;
- substituir evidências;
- recomendar contratação;
- decidir juridicamente;
- decidir subscrição.

---

## 12. Responsividade

Prioridade:
1. 1440×900
2. 1366×768
3. tablet

Mobile é secundário no MVP.

---

## 13. Processo de implementação

Para cada tela:

1. ler wireframe;
2. mapear dados;
3. implementar apresentação;
4. não alterar core;
5. testar;
6. capturar screenshot;
7. revisar visualmente;
8. documentar resultado.

---

## 14. QA

A cada alteração frontend:
- executar testes;
- verificar imports;
- iniciar Streamlit;
- validar navegação;
- testar estados;
- conferir visual.

Nenhum commit automático.

Nenhum push automático.

---

## 15. Critérios de aceite

### Produto
- fluxo compreensível;
- linguagem profissional;
- informação relevante em primeiro plano;
- quatro perfis funcionalmente diferenciados na apresentação.

### Visual
- design corporativo;
- hierarquia clara;
- sem excesso de efeitos;
- evidências legíveis;
- responsividade adequada.

### Integridade
- backend preservado;
- nenhum dado inventado;
- sem alteração semântica feita pela UI;
- evidências preservadas.

### Governança
- zero commit;
- zero push;
- zero PR;
- zero merge.

---

## 16. Regra de decisão

Quando houver conflito:

**função > estética**

**clareza > densidade**

**evidência > interpretação**

**backend preservado > conveniência de implementação**

**julgamento humano > recomendação automática**

---

## 17. Mantra

> **Uma inteligência analítica.
> Quatro perspectivas profissionais.
> Uma evidência rastreável.**
