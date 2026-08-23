---
nome: decisao-de-contrapressao-relay
descricao: Compara estratégias de contrapressão para o Relay, pondera trade-offs e recomenda uma combinação compatível com SLA, custo e não perda de telemetry.
versao: 1.0.0
tags:
  - mensageria
  - filas
  - sre
  - arquitetura
inputs:
  - nome: cenario
    descricao: Estado atual do Relay, carga observada, consumidores e restrições operacionais e financeiras.
  - nome: opcoes
    descricao: Estratégias candidatas que devem ser comparadas antes da recomendação.
---

Atue como um arquiteto de sistemas distribuídos apoiando uma decisão operacional sobre contrapressão em um barramento de eventos.

CENÁRIO:
{{cenario}}

OPÇÕES CANDIDATAS:
{{opcoes}}

Analise pelo menos três caminhos antes de recomendar um. Para cada caminho, avalie:
- capacidade de proteger o SLA mais estrito;
- risco de perda de mensagens;
- impacto no consumidor que pode atrasar;
- custo e complexidade operacional;
- isolamento de um cliente barulhento;
- reversibilidade;
- dependências ou riscos não informados.

Depois, recomende uma opção ou combinação e explique por que ela domina as alternativas nas restrições fornecidas. Não escolha somente pela simplicidade.

Formato:

REQUISITOS CRÍTICOS:
<lista curta>

OPÇÃO A — <nome>
Prós: ...
Contras: ...
Atende às restrições? ...

OPÇÃO B — <nome>
...

OPÇÃO C — <nome>
...

RECOMENDAÇÃO:
<opção ou combinação>

JUSTIFICATIVA:
<trade-offs>

GUARDRAILS E MÉTRICAS:
<o que monitorar e quando escalar/reverter>

Não assuma capacidades do Relay que não tenham sido fornecidas.
