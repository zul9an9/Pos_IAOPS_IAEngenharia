# Checkpoint 02 — Nota de Triagem Padronizada

## Contexto

Prompt parametrizável que transforma um alerta cru do Sentinel em uma nota de
triagem padronizada, para que qualquer plantonista escreva (e o próximo
plantão leia) no mesmo formato. Ensina o padrão via **few-shot**, embutindo
os três exemplos de formato do time como referência dentro do próprio prompt.

## 1. Prompt parametrizável

```
Contexto: Você é o assistente do plantão de operações da Aegis. Sua tarefa é
transformar um alerta cru do sistema de observabilidade Sentinel em uma nota
de triagem padronizada, para que o próximo plantonista entenda o incidente
sem precisar reprocessar o alerta original.

Ação: A partir do alerta cru fornecido, produza uma nota com exatamente
estes cinco campos, nesta ordem, um por linha:
ALERTA: <sistema e sintoma, resumido em uma frase>
IMPACTO: <quem/o que é afetado e a extensão>
HIPÓTESE INICIAL: <causa mais provável, com base no que o alerta indica>
AÇÃO IMEDIATA: <ação de mitigação que já pode ser tomada agora>
ESCALAR PARA: <handle no formato @time, conforme mapeamento abaixo>

Mapeamento de escalonamento (fixo, não varia por alerta):
- Alertas de Relay    -> @relay-core
- Alertas de Forge    -> @data-platform
- Alertas de Cerebro  -> @search-infra
- Alertas de Sentinel -> @sentinel-core
Se o alerta envolver mais de um sistema, escale para o time do sistema que
disparou o alerta (indicado entre colchetes no início do alerta cru, ex.
"[Relay]"), não para quem foi apenas impactado.

Restrições:
- A nota inteira deve ter no máximo 8 linhas.
- Não invente números, horários ou nomes que não estejam no alerta cru.
- Se a causa não estiver clara a partir do alerta, marque a hipótese como
  tal (ex.: "possível X, a confirmar") em vez de afirmar com certeza.

Exemplos do padrão esperado — isto é referência de FORMATO. Não são o
alerta a processar, apenas mostram como a nota final deve se parecer:

ALERTA: Relay - taxa de rejeição de ingestão acima de 2% por 5min
IMPACTO: ingestão de telemetry degradada para ~12% dos tenants
HIPÓTESE INICIAL: deploy do Relay às 09:14 reduziu o buffer de ingestão
AÇÃO IMEDIATA: rollback iniciado via Argo CD
ESCALAR PARA: @relay-core se a rejeição não cair em 10min

ALERTA: Forge - lag de ingestão acima de 15min
IMPACTO: dashboards do Sentinel atrasados para todos os tenants
HIPÓTESE INICIAL: pico de volume do tenant acme-corp saturou o consumer
AÇÃO IMEDIATA: aumento manual de partições do consumer do Relay
ESCALAR PARA: @data-platform se lag não estabilizar em 20min

ALERTA: Cerebro - latência de busca p99 acima de 4s
IMPACTO: investigação de incidentes lenta para o time interno
HIPÓTESE INICIAL: reindexação noturna não concluiu antes do horário comercial
AÇÃO IMEDIATA: pausar reindexação e priorizar shard quente
ESCALAR PARA: @search-infra se p99 não cair em 15min

Alerta cru a processar:
{{alerta_cru}}
```

Parâmetro: `{{alerta_cru}}` — único valor variável entre execuções.

## 2. Execução

**Modelo usado:** Claude (Sonnet). Justificativa: tarefa de extração +
formatação estrita, com baixo risco de ambiguidade — prioriza aderência
exata ao formato (crítico porque este prompt será testado por regex no
Checkpoint 08) sobre criatividade.

### Entrada 1

Alerta cru:
```
2026-05-12 14:02:09 UTC [Sentinel] autoscaler hit max replicas (60/60) on sentinel-api,
queue depth on Relay growing 2k/min, CPU avg 88%, tenant stark-industries
sending 4x baseline volume after onboarding new region
```

Nota gerada:
```
ALERTA: Sentinel - autoscaler do sentinel-api atingiu o limite máximo de réplicas (60/60)
IMPACTO: fila de ingestão do Relay crescendo ~2k msgs/min e CPU do sentinel-api em 88%, risco de atraso no alerting em tempo real
HIPÓTESE INICIAL: tenant stark-industries passou a enviar ~4x o volume baseline após onboarding de nova região, saturando as réplicas atuais
AÇÃO IMEDIATA: aumentar manualmente o teto de réplicas do autoscaler do sentinel-api
ESCALAR PARA: @sentinel-core se a fila do Relay não estabilizar após o aumento
```

### Entrada 2

Alerta cru:
```
2026-05-13 03:11:00 UTC [Relay] ingest reject rate 6% for 8min, tenant wakanda-systems,
buffer saturated after deploy 02:55
```

Nota gerada:
```
ALERTA: Relay - taxa de rejeição de ingestão em 6% por 8min
IMPACTO: ingestão do tenant wakanda-systems sendo rejeitada, risco de perda de telemetry desse tenant
HIPÓTESE INICIAL: deploy das 02:55 saturou o buffer de ingestão do Relay
AÇÃO IMEDIATA: avaliar rollback do deploy das 02:55 ou aumento emergencial do buffer
ESCALAR PARA: @relay-core se a rejeição não cair após a ação
```

### Entrada 3

Alerta cru:
```
2026-05-13 11:40:22 UTC [Forge] consumer lag 9min and climbing, batch forge-batch-ingest
delayed after previous job failure, downstream Sentinel starting to lag
```

Nota gerada:
```
ALERTA: Forge - lag do consumer em 9min e subindo
IMPACTO: batch forge-batch-ingest atrasado, Sentinel começando a atrasar dashboards a jusante
HIPÓTESE INICIAL: falha do job anterior deixou lote acumulado, sobrecarregando o processamento atual
AÇÃO IMEDIATA: reprocessar/reiniciar o forge-batch-ingest priorizando o backlog acumulado
ESCALAR PARA: @data-platform se o lag continuar subindo após o reprocessamento
```

Todas as 3 saídas: 5 campos na ordem correta, handle `@algo` presente,
nota com no máximo 8 linhas.

## 3. Curadoria

**Decisão de método:** ensinei o formato por **few-shot** (embutindo os 3
exemplos de nota-padrão dentro do próprio prompt), em vez de só descrever a
regra em texto (zero-shot). Testei as duas abordagens: a zero-shot variava a
ordem dos campos e ocasionalmente fundia IMPACTO e HIPÓTESE numa única linha.
A few-shot ficou consistente nas três execuções. O custo dessa escolha é um
prompt mais longo (mais tokens por chamada) — aceitável aqui porque o volume
de chamadas desse prompt específico é baixo (um alerta por vez, sob
demanda), diferente de um prompt que rodaria em lote com custo agregado alto.

**Risco mitigado:** o próprio checkpoint avisa que há duas listas de
exemplos no material (formato de saída vs. alertas crus). Ao embutir os
exemplos de formato no prompt, havia risco de o modelo tentar "responder" a
esses exemplos como se fossem o alerta de entrada. Resolvido rotulando-os
explicitamente como "referência de FORMATO... não são o alerta a
processar" — sem essa marcação, um teste preliminar mostrou o modelo
comentando sobre o alerta do exemplo (Relay) em vez de processar o
`{{alerta_cru}}` real fornecido.

**Assunção registrada:** o mapeamento `Sentinel -> @sentinel-core` não veio
nos 3 exemplos originais do time (que cobrem apenas Relay, Forge e Cerebro).
Foi inferido por padrão de nomenclatura para cobrir a Entrada 1, que é um
alerta originado no Sentinel — fica registrado como suposição a validar
com o time, não como dado confirmado.

