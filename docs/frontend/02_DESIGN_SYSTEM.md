# InsurMinds — Design System: Insurance Intelligence v1.0

## 1. Princípio visual

### Insurance Intelligence

O produto deve transmitir:

**confiança + precisão + eficiência + rastreabilidade.**

Não deve parecer um laboratório de IA ou um dashboard cyberpunk.

Evitar:
- neon dominante;
- glassmorphism pesado;
- excesso de efeitos;
- estética “tech demo”.

Buscar:
- ambiente corporativo;
- leitura documental;
- clareza;
- alta densidade controlada;
- hierarquia visual.

---

## 2. Paleta

| Token | Valor | Uso |
|---|---|---|
| Primary Navy | `#12304A` | navegação, headings |
| Primary Blue | `#2864C7` | ações principais |
| Secondary Teal | `#0B8A84` | informação/estado positivo |
| Success | `#197B5C` | confirmado |
| Attention | `#F59E0B` | atenção |
| Critical | `#D94A4A` | alteração crítica |
| Background | `#F5F7FA` | canvas |
| Surface | `#FFFFFF` | cartões |
| Border | `#D9E1E8` | divisórias |
| Text | `#1F2A35` | texto principal |
| Muted | `#6B7785` | texto secundário |

### Regra

**Cor tem função semântica.**

Não usar vermelho, verde ou âmbar apenas como decoração.

---

## 3. Tipografia

### Interface
**Inter**

- H1: 24/32 Semibold
- H2: 20/28 Semibold
- H3: 16/24 Semibold
- Body: 14/22 Regular
- Caption: 12/18 Regular

### Evidência

**IBM Plex Mono**

Usar para:
- snippets;
- trechos contratuais;
- identificadores técnicos;
- contexto documental.

---

## 4. Layout

Prioridade:
- desktop 1440×900;
- notebook 1366×768;
- tablet em uma coluna quando necessário;
- mobile fora da prioridade do MVP.

### Shell

Sidebar persistente + topbar + área de conteúdo.

A sidebar deve ser compacta.

---

## 5. Espaçamento

Base recomendada:
- 4 px — microespaçamento;
- 8 px — compactação;
- 12 px — interno;
- 16 px — padrão;
- 24 px — blocos;
- 32 px — seções;
- 48 px — grandes divisões.

Manter uma escala consistente.

---

## 6. Componentes

Inventário principal:

- AppShell
- Sidebar
- TopBar
- Breadcrumb
- ProfileSelector
- DocumentCard
- DocumentHeader
- MetricCard
- StatusBadge
- SemanticBadge
- DifferenceCard
- ComparisonMatrix
- EvidencePanel
- EvidenceSnippet
- FilterBar
- TabNavigation
- ProcessingState
- EmptyState
- SuccessState
- WarningState
- ErrorState
- AssistantPanel
- ReportHeader

---

## 7. Semantic Badges

Mapeamento de dados internos para interface:

| Interno | Rótulo |
|---|---|
| `semantic_equivalent` | Equivalente |
| `different` | Diferente |
| `broader` | Escopo ampliado |
| `narrower` | Escopo reduzido |
| `changed_scope` | Escopo alterado |
| `changed_condition` | Condição alterada |
| `changed_limit` | Limite alterado |

O usuário nunca deve ser obrigado a entender os identificadores internos.

---

## 8. Diferença

Um `DifferenceCard` deve conter:
- tipo;
- nome;
- documento A;
- página A;
- documento B;
- página B;
- resumo;
- ação.

Modelo:

```text
CONDIÇÃO ALTERADA

Inadimplemento do prêmio

A — pág. 26
B — pág. 28

A condição contratual foi modificada entre as versões.

[Ver análise]
[Ver evidência]
```

---

## 9. Evidência

O `EvidencePanel` deve destacar:

- fonte;
- página;
- snippet literal;
- contexto;
- método quando relevante.

Regra:

> **Evidência é fonte. IA é interpretação.**

Nunca fabricar snippet, página ou referência.

---

## 10. Confiança

Não exibir “95% de certeza” como linguagem principal.

Interface:
- Evidência forte;
- Evidência moderada;
- Revisão recomendada.

Detalhamento técnico:
> Confiança da análise: 0.xx

A confiança não substitui evidência.

---

## 11. Estados

### Empty
“Não há análises disponíveis.”

### Loading
“Processando documentos...”

### Success
“Análise concluída.”

### Partial
“Documento processado, mas alguns campos não foram identificados.”

### Error
“Não foi possível concluir a análise deste documento.”

### Fallback
“Modo de contingência ativo — análise utilizando regras determinísticas.”

---

## 12. Cards

Características:
- fundo branco;
- borda discreta;
- raio moderado;
- sombra muito leve;
- hierarquia tipográfica clara.

Não transformar cada informação em card.

Cards devem existir onde ajudam a agrupar significado.

---

## 13. Tabelas

Usar para:
- biblioteca;
- dados repetitivos;
- comparações estruturadas.

Evitar tabelas gigantes na tela principal.

Na tela central, priorizar cards de diferença.

---

## 14. Ícones

Preferir ícones lineares, discretos e consistentes.

Não utilizar emojis como estrutura principal da UI.

Emojis podem aparecer em conteúdo de onboarding ou pequenos elementos expressivos, mas não devem sustentar a semântica crítica.

---

## 15. IA

O visual da IA deve ser discreto.

Evitar:
- chatbot ocupando grande parte da tela;
- animações exageradas;
- “thinking” decorativo.

Preferir:
- “Interpretação assistida”;
- “Perguntar sobre esta análise”;
- painel contextual.

---

## 16. Princípios

1. Corporate, not futuristic.
2. Evidence first.
3. Progressive disclosure.
4. Minimal cognitive load.
5. IA discreta.
6. Informação hierarquizada.
7. Documento é fonte; modelo é intérprete.
