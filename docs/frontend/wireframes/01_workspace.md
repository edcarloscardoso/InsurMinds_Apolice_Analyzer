# Wireframe 01 — Workspace / Início

## Objetivo
Responder rapidamente: “O que está acontecendo no meu trabalho?”

## Estrutura

```text
┌──────────────────────────────────────────────────────────────┐
│ INSURMINDS                         Perfil de trabalho ▾      │
├──────────────┬───────────────────────────────────────────────┤
│ Início       │ Seu workspace                                │
│ + Nova       │                                               │
│ análise      │ [Análises] [Documentos] [Diferenças]         │
│ Comparações  │ [Evidências]                                 │
│ Documentos   │                                               │
│ Relatórios   │ [ + Nova análise ]                            │
│ Config.      │                                               │
│              │ Análises recentes                             │
│              │ Documento A | Documento B | Diferenças | ... │
└──────────────┴───────────────────────────────────────────────┘
```

## Prioridade por perfil

### Analista
Diferenças → evidências → documentos.

### Subscritor
Alterações de condição/escopo/limite → diferenças.

### Corretor
Comparações recentes → A/B → exclusivas.

### Jurídico
Alterações → evidências → documentos.

## Componentes
AppShell, Sidebar, TopBar, MetricCard, DifferencePreview, RecentAnalyses.

## Estados
Empty, Success, Loading e Error.
