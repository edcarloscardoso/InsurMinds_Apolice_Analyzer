# Wireframe 02 — Nova Análise

## Objetivo
Iniciar uma comparação com o mínimo de fricção.

## Estrutura

```text
NOVA ANÁLISE

Documento A
┌─────────────────────────────────────┐
│ Arraste o PDF ou selecione arquivo │
└─────────────────────────────────────┘

Documento B
┌─────────────────────────────────────┐
│ Arraste o PDF ou selecione arquivo │
└─────────────────────────────────────┘

Tipo documental: D&O

[ Iniciar análise ]
```

## Processamento

Mostrar:

```text
✓ Documento recebido
✓ Conteúdo extraído
✓ Estrutura contratual identificada
✓ Evidências localizadas
◉ Comparação em andamento
```

## Regras
- Não mostrar “Agente 1/2/3/4” como linguagem principal.
- Mostrar mensagens de tarefa.
- Não inventar metadados antes do processamento.
- Erros devem ser compreensíveis.

## Componentes
UploadDropzone, DocumentCard, ProcessingState, PrimaryButton, ErrorState.
