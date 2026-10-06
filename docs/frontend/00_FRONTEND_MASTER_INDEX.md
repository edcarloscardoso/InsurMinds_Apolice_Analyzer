# InsurMinds — Frontend Source of Truth

## 1. Propósito

Esta pasta contém a documentação oficial de produto, UX, Design System e implementação do frontend do InsurMinds — Apólice Analyzer.

Ela deve ser consultada antes de qualquer alteração relevante na camada de interface.

## 2. Estrutura

```text
docs/frontend/
├── 00_FRONTEND_MASTER_INDEX.md
├── 01_PRODUCT_UX_SPEC.md
├── 02_DESIGN_SYSTEM.md
├── 03_ANTIGRAVITY_HANDOFF.md
└── wireframes/
    ├── 01_workspace.md
    ├── 02_nova_analise.md
    ├── 03_comparacao.md
    ├── 04_detalhe_diferenca.md
    ├── 05_biblioteca.md
    └── 06_relatorio.md
```

## 3. Ordem de leitura

1. `01_PRODUCT_UX_SPEC.md` — visão do produto, público, personas, jobs-to-be-done e arquitetura de experiência.
2. `02_DESIGN_SYSTEM.md` — linguagem visual, tokens, componentes, estados e regras de interface.
3. `03_ANTIGRAVITY_HANDOFF.md` — contrato de implementação e limites técnicos.
4. `wireframes/` — especificação de cada tela.

## 4. Regra arquitetural

O frontend é uma camada de apresentação sobre a engenharia analítica existente.

O princípio é:

> **Uma inteligência analítica. Diferentes perspectivas profissionais. Uma evidência rastreável.**

A persona altera a forma de apresentação. Não altera os resultados analíticos.

## 5. Backend Freeze

O backend analítico permanece congelado.

Qualquer necessidade de alteração em `core/`, no pipeline, nos schemas ou no banco exige análise de impacto e aprovação explícita antes da implementação.

## 6. MVP de identidade

O MVP não possui autenticação real.

O “perfil de trabalho” é uma preferência de sessão:
- Analista de Seguros
- Subscritor / Underwriter
- Corretor de Seguros
- Jurídico / Compliance
- Explorar como visitante

Não simular nomes de usuários ou contas inexistentes.

## 7. Princípio de linguagem

A interface deve falar a linguagem do profissional de seguros.

Evitar:
- jargão técnico de LLM;
- “a IA decidiu”;
- notas de qualidade;
- recomendações de contratação.

Preferir:
- alteração identificada;
- diferença encontrada;
- evidência localizada;
- interpretação assistida;
- revisão recomendada.

## 8. Tarefas futuras

Após aprovação dos documentos deste diretório:
- implementação frontend;
- QA visual;
- QA E2E;
- preparação para pitch e demonstração.
