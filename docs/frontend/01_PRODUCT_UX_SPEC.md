# InsurMinds — Product UX Specification v1.0

## 1. Posicionamento

**InsurMinds — Apólice Analyzer**

Ferramenta profissional para análise e comparação de documentos de seguros, com foco inicial em D&O.

### Proposta de valor

> **Reduzir o trabalho manual de análise contratual, destacar alterações relevantes e mostrar a evidência documental que sustenta cada conclusão.**

### Assinatura

> **Compare. Entenda. Comprove.**

O sistema é um copiloto de análise. O julgamento profissional permanece humano.

---

## 2. Público-alvo

Profissionais que trabalham com seguros e documentos contratuais:

1. Analista de Seguros
2. Subscritor / Underwriter
3. Corretor de Seguros
4. Jurídico / Compliance

A interface deve atender diferentes prioridades sem criar quatro aplicações.

---

## 3. Personas

### 3.1 Analista de Seguros

**Job to be Done:** descobrir rapidamente o que mudou entre documentos.

Prioridade:
1. diferenças;
2. cláusulas;
3. evidências;
4. metadados.

Perguntas:
- O que mudou?
- Qual cláusula?
- Qual página?
- É alteração de texto, condição, escopo ou limite?
- Onde está a prova?

### 3.2 Subscritor / Underwriter

**Job to be Done:** identificar alterações contratuais que merecem avaliação técnica.

Prioridade:
1. condições;
2. escopo;
3. limites;
4. novas cláusulas;
5. evidências.

A interface pode indicar:
- alteração contratual identificada;
- revisão recomendada;
- exige análise humana.

Não atribuir automaticamente “risco alto/baixo” sem regra de negócio formal.

### 3.3 Corretor

**Job to be Done:** comparar alternativas e diferenças entre documentos.

Prioridade:
1. A × B;
2. exclusivas A;
3. exclusivas B;
4. alterações;
5. equivalências.

### 3.4 Jurídico / Compliance

**Job to be Done:** revisar alterações com rastreabilidade documental.

Prioridade:
1. texto A/B;
2. evidência;
3. página;
4. contexto;
5. interpretação assistida.

---

## 4. Perfil de trabalho

A UI deve usar o termo **Perfil de trabalho**, não “persona”.

Opções:
- Analista de Seguros
- Subscritor / Underwriter
- Corretor de Seguros
- Jurídico / Compliance
- Explorar como visitante

O perfil muda:
- ordem dos blocos;
- filtros padrão;
- prioridade visual;
- linguagem;
- densidade.

Não muda:
- conteúdo analítico;
- relações semânticas;
- evidências;
- resultados do motor.

---

## 5. Autenticação

### MVP

Não implementar login.

O backend atual não possui arquitetura de identidade de usuário persistente. O perfil de trabalho deve ser mantido apenas na sessão do frontend.

Não usar nomes fictícios como “Bom dia, Ana”.

Preferir:
- “Bem-vindo ao InsurMinds”
- “Seu workspace”

### Futuro

Login, organização, permissões e workspaces persistentes ficam para versão futura.

---

## 6. Arquitetura de informação

Navegação principal:

- Início
- Nova análise
- Comparações
- Documentos
- Relatórios
- Configurações

A área “Auditoria Contábil”, caso permaneça tecnicamente no projeto, não deve competir com o fluxo principal de D&O.

---

## 7. Jornada principal

```text
Entrada
  ↓
Perfil de trabalho
  ↓
Workspace
  ↓
Nova análise
  ↓
Upload A + B
  ↓
Processamento
  ↓
Comparação
  ↓
Alterações relevantes
  ↓
Detalhe
  ↓
Evidência
  ↓
Relatório
```

A sequência cognitiva central é:

> **O que mudou? → Como mudou? → Onde está a prova?**

---

## 8. Telas

### 8.1 Início / Workspace

Objetivo: mostrar panorama do trabalho.

Elementos:
- resumo de análises;
- documentos;
- diferenças relevantes;
- evidências;
- CTA “Nova análise”;
- análises recentes.

### 8.2 Nova análise

Objetivo: iniciar comparação.

Elementos:
- documento A;
- documento B;
- tipo documental D&O;
- iniciar análise;
- progresso compreensível.

O processamento deve usar linguagem de tarefa:
- Documento recebido
- Conteúdo extraído
- Estrutura identificada
- Evidências localizadas
- Comparação em andamento

### 8.3 Workspace de comparação

É a tela central.

Objetivo:
> **O que mudou?**

Deve mostrar:
- documentos A/B;
- seguradora;
- versão/data quando disponível;
- tipo documental;
- SUSEP quando disponível;
- diferenças;
- alterações relevantes;
- equivalências;
- evidências.

### 8.4 Detalhe da diferença

Objetivo:
> **Permitir compreender e comprovar uma diferença.**

Estrutura:
- título;
- classificação;
- texto A;
- texto B;
- páginas;
- interpretação assistida;
- evidência;
- contexto.

### 8.5 Biblioteca

Objetivo:
> gerenciar documentos disponíveis.

Recursos:
- busca;
- filtro por seguradora;
- ano;
- tipo;
- páginas;
- documentos relacionados.

### 8.6 Relatório

Objetivo:
> transformar a análise em artefato profissional.

Seções:
- identificação;
- resumo executivo;
- alterações relevantes;
- diferenças;
- coberturas;
- exclusões;
- evidências;
- metodologia;
- limitações.

---

## 9. Progressiva divulgação

Três níveis:

### Nível 1 — Executivo
**O que aconteceu?**

### Nível 2 — Analítico
**Como aconteceu?**

### Nível 3 — Auditoria
**Onde está a prova?**

Detalhes técnicos do LLM ficam recolhidos.

---

## 10. Papel da IA

A IA não é o protagonista visual.

O sistema deve apresentar o resultado, não o modelo.

Pode haver:

> **Interpretação assistida**

e um painel:

> Como a análise foi construída?

com:
- regras estruturais;
- ontologia D&O;
- evidência documental;
- análise semântica assistida por IA.

---

## 11. Linguagem

Evitar:
- “A IA decidiu”
- “Melhor apólice”
- “Compra recomendada”
- “Certeza”
- “Risco alto” sem regra de negócio

Preferir:
- alteração identificada;
- diferença encontrada;
- evidência localizada;
- interpretação assistida;
- revisão recomendada.

---

## 12. Critérios de experiência

A interface deve permitir que um profissional:
- compreenda o objetivo sem treinamento;
- localize alterações relevantes rapidamente;
- veja a comparação A/B;
- abra a evidência;
- compreenda a origem da interpretação;
- navegue sem excesso de informação;
- mantenha o julgamento profissional.
