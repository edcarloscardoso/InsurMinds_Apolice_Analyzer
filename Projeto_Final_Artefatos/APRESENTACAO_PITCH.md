# Roteiro de Demonstração & Pitch Deck (5 Minutos)
**InsurMinds Apólice Analyzer · Apresentação Final da Banca I2A2**

---

## 🎯 1. O Problema (Minuto 0:00 – 1:00)
- **Cenário:** O seguro D&O (Directors & Officers) protege o patrimônio pessoal de conselheiros e diretores de empresas contra reclamações e investigações regulatórias.
- **A Dor:** Apólices D&O possuem entre 30 e 80 páginas em linguagem jurídica densa. Comparar duas propostas exige de 3 a 5 horas de trabalho especializado de corretores seniores e advogados.
- **Impacto:** Erros na análise de cláusulas como *Side A DIC*, franquias de penhora online ou retroatividade podem deixar administradores desprotegidos em sinistros multimilionários.

---

## 💡 2. A Solução InsurMinds (Minuto 1:00 – 2:00)
- Uma plataforma inteligente baseada em **IA Generativa (Google Gemini 2.0 Flash)** e **Orquestração Multi-Agente (LangGraph)**.
- **Pipeline de 6 Agentes Especializados:**
  1. *Reception Agent:* Valida integridade e garante idempotência por hashing criptográfico.
  2. *Extractor Agent:* Extrai texto nativo com fallback OCR de visão multimodal para PDFs escaneados.
  3. *Identifier Agent:* Segmenta as cláusulas semânticas da apólice.
  4. *Structurer Agent:* Converte em esquemas contratuais canônicos Pydantic.
  5. *Comparator Agent:* Confronta os dados determinísticos e calcula o Score de Similaridade de Jaccard.
  6. *Reporter Agent:* Gera um parecer executivo narrativo com recomendações estratégicas em segundos.

---

## 🚀 3. Demonstração Prática ao Vivo (Minuto 2:00 – 4:00)
1. **Upload / Amostras:**
   - Clicar em *"⚡ Carregar Apólices de Demonstração"*.
   - Acompanhar a timeline em tempo real dos 4 agentes processando as apólices da Allianz, Chubb e AIG.
2. **Biblioteca de Apólices:**
   - Exibir o catálogo com os limites, prêmios e coberturas já salvos no banco SQLite.
   - Selecionar **Allianz** e **Chubb** para o confronto.
3. **Matriz Comparativa & Gap Analysis:**
   - Mostrar o Scorecard de Similaridade (ex: **78.4%**).
   - Destacar as bandeiras visuais na tabela (Diferença no LMG: R$ 10M vs R$ 5M; Franquias: R$ 50k vs R$ 100k).
   - Apresentar as coberturas exclusivas detectadas (Allianz com *Investigação Regulatória*; Chubb com *Side A DIC*).
4. **Parecer Executivo:**
   - Exibir o parecer gerado pela IA estruturado com Resumo Executivo, Análise de Riscos e Recomendação Final.
   - Demonstrar o download em Markdown e JSON consolidado.

---

## 📈 4. Diferenciais de Engenharia de Dados & Conclusão (Minuto 4:00 – 5:00)
- **Resiliência Zero-Crash:** Provedores de contingência garantem execução mesmo em caso de indisponibilidade de chaves de API externas.
- **Arquitetura de Dados Segura:** Sanitização completa contra Path Traversal, validação de magic bytes e consultas parametrizadas.
- **Próximos Passos:** Suporte a apólices de Riscos Cibernéticos (Cyber) e E&O (Erros e Omissões).
