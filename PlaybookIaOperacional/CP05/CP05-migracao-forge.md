# Checkpoint 05 — Migração do Forge de lote para tempo real

## Contexto 

Cadeia de prompts parametrizáveis (prompt chaining) para conduzir a
migração do Forge — o pipeline de dados da Aegis — do modelo em lote
(cron de 60min) para event-driven, quebrando a decisão em três elos
sequenciais em vez de um único prompt monolítico. Cada elo recebe a
saída do anterior como entrada.

## Por que uma cadeia, e não um único prompt

Testes com um megaprompt único ("diagnostique, planeje e detalhe o
primeiro passo") produziram plano raso e genérico — recomendação de
"adotar CDC + Kafka Streams" sem citar consumidores específicos nem
os pontos frágeis do Forge atual. A cadeia força cada elo a produzir
estrutura utilizável pelo próximo, mantendo o acoplamento com o cenário
real da Aegis.

## 1. Prompts parametrizáveis da cadeia

### Elo 1 — Diagnóstico do estado atual

```
Role: Você é um arquiteto de dados sênior, consultor da Aegis para a
transição do pipeline Forge (hoje em lote) para um modelo orientado a
eventos. Nesta etapa, seu papel é apenas diagnosticar — não propor
migração ainda.

Input:
- {{estado_atual}}: descrição do Forge hoje (ingestão em cron, etapas de
  transformação, destinos, dependências e pontos frágeis)

Steps:
1. Identifique os pontos frágeis estruturais do desenho atual — o que
   torna a migração para eventos necessária, e não apenas desejável.
2. Mapeie os consumidores do Forge e classifique cada um pela sensibilidade
   à latência (quem tolera atraso, quem não tolera).
3. Liste os riscos de continuidade — o que pode quebrar durante a
   transição se não for tratado com cuidado.
4. Aponte pré-condições técnicas para a migração começar (o que precisa
   estar de pé antes de mover a primeira peça).

Expectation: estruture em seções tituladas ("Pontos frágeis",
"Consumidores por sensibilidade", "Riscos de continuidade", "Pré-condições").
Não proponha ainda como migrar — isso é próxima etapa. Seja específico ao
Forge descrito na entrada, sem generalizações.
```

Parâmetro: `{{estado_atual}}`

### Elo 2 — Plano de migração em passos

```
Role: Você é o mesmo arquiteto do passo anterior. Agora, com o diagnóstico
em mãos, seu papel é propor o passo a passo da migração — sem detalhar
implementação ainda, só a sequência de passos e a lógica de cada um.

Input:
- {{diagnostico}}: saída do elo anterior (pontos frágeis, consumidores,
  riscos, pré-condições)
- {{restricoes}}: as restrições explícitas da migração (consumo contínuo
  do Relay, manter dependentes funcionando, nada de big-bang, reversível)

Steps:
1. Proponha uma sequência de passos ordenada, do estado atual (lote) ao
   estado alvo (event-driven). Cada passo precisa: (a) ser reversível
   isoladamente; (b) manter os consumidores identificados no diagnóstico
   funcionando durante o passo; (c) endereçar pelo menos um dos pontos
   frágeis ou riscos do diagnóstico.
2. Para cada passo, identifique explicitamente qual é o critério de
   sucesso que autoriza avançar para o próximo (não avançar por tempo,
   avançar por evidência).
3. Para cada passo, identifique o gatilho de rollback — que sinal indica
   que o passo precisa ser desfeito.

Expectation: uma sequência numerada de passos, cada um com "Objetivo",
"Critério de sucesso", "Gatilho de rollback". A cadeia deve terminar no
estado event-driven pretendido, mas nenhum passo isolado pode ser um
big-bang. Não entre em detalhe de código, tooling ou vendor — isso é a
próxima etapa.
```

Parâmetros: `{{diagnostico}}`, `{{restricoes}}`

### Elo 3 — Detalhamento executável do próximo passo

```
Role: Você é o mesmo arquiteto. Agora, dado o plano completo, detalhe
apenas UM passo — o que o time deve começar a executar primeiro — em nível
de ação concreta, para que engenharia possa iniciar sem ambiguidade.

Input:
- {{plano}}: saída do elo anterior (sequência de passos numerados)
- {{passo_alvo}}: qual passo do plano será detalhado (por padrão, o passo 1)

Steps:
1. Traduza o objetivo do passo escolhido em ações concretas ordenadas
   (o que instrumentar, o que criar em paralelo, o que ligar, o que
   observar).
2. Especifique como o critério de sucesso do passo será medido na prática
   (qual métrica, qual valor, por quanto tempo estável).
3. Especifique como o gatilho de rollback será detectado na prática
   (mesma lógica: métrica, limiar, janela).
4. Aponte que informação você ainda NÃO tem e que precisaria vir do time
   (Bruce Banner, Steve Rogers, Sam Wilson) para reduzir risco desse passo.

Expectation: um plano executável do passo, em seções tituladas ("Ações
ordenadas", "Como medir sucesso", "Como detectar rollback", "Informação a
solicitar ao time"). Nada de código pronto — o nível é de plano de
execução, não de implementação linha a linha.
```

Parâmetros: `{{plano}}`, `{{passo_alvo}}`

## 2. Execução

**Modelo usado (nos três elos):** Claude (Sonnet). Justificativa:
raciocínio arquitetural sequencial com contexto acumulado — cada elo
precisa entender o output estruturado do anterior e produzir estrutura
para o próximo. É o cenário típico onde qualidade de raciocínio pesa mais
que custo, e o número de chamadas por execução completa da cadeia é baixo
(3, não recorrente).

### Elo 1 — Saída

Rodado com `{{estado_atual}}` = o cenário do Forge do checkpoint.

```
Pontos frágeis:
- Job de 60min como unidade indivisível: uma falha invalida uma hora
  inteira de processamento, sem retomada parcial.
- Efeito bola de neve: se um lote falha, o próximo processa o dobro,
  aumentando ainda mais o risco de nova falha — o próprio design amplifica
  incidentes.
- Latência estrutural mínima de ~40min (a duração da transformação em
  Spark), independentemente de urgência do dado — mesmo alertas críticos
  a jusante herdam esse piso.
- Ponto único de execução (o cron): o pipeline inteiro depende de um
  agendador acordar corretamente a cada hora.

Consumidores por sensibilidade:
- Sentinel (alta sensibilidade): lê tabelas agregadas para alerting;
  qualquer atraso do Forge se propaga a alertas.
- Cerebro (média sensibilidade): indexa eventos transformados; atraso
  degrada frescor da busca mas não quebra funcionalidade imediata.
- Relatórios de billing da Pepper (baixa sensibilidade, mas alta
  criticidade em janela específica): rodam de madrugada; toleram muito
  atraso, mas não toleram inconsistência de dado.

Riscos de continuidade:
- Consumidores hoje assumem tabelas particionadas por hora — mudar o
  contrato de escrita (blocos menores, mais frequentes) pode quebrar
  queries que se apoiam nessa granularidade.
- Billing lê de madrugada assumindo que o lote das 23h fechou; se a
  migração alterar o momento de fechamento das partições, os relatórios
  podem ler dados incompletos.
- Steve Rogers construiu as 14 etapas de transformação encadeadas;
  reproduzir a lógica delas em micro-lotes exige entendimento profundo
  do que cada etapa faz — não é refatoração mecânica.

Pré-condições:
- Consumo contínuo do Relay já disponível como capacidade (Relay já é
  event-driven, então isso está atendido pela plataforma).
- Instrumentação de observabilidade do próprio Forge: hoje, como é lote,
  provavelmente não há métricas de lag/latência por evento. Precisam ser
  criadas antes da migração para se saber o que "melhor" ou "pior"
  significa.
- Definição de contrato de leitura com Sentinel, Cerebro e billing — o
  que cada um espera ver e com que granularidade, escrito.
```

### Elo 2 — Saída

Rodado com o diagnóstico do Elo 1 + `{{restricoes}}` = as três restrições
da migração declaradas no checkpoint.

```
Passo 1 — Instrumentar o Forge atual em lote
Objetivo: criar visibilidade de lag por evento, tempo por etapa de
transformação e taxa de falha do job, antes de mudar qualquer
comportamento. Endereça a pré-condição de instrumentação identificada
no diagnóstico.
Critério de sucesso: métricas visíveis no Sentinel por 5 dias úteis
cobrindo um ciclo completo (incluindo pelo menos uma falha ou retry,
para validar que o instrumento captura o cenário ruim).
Gatilho de rollback: nenhum — este passo só adiciona observabilidade,
não muda o pipeline. Se a instrumentação em si degradar o job (custo
inesperado), remover a instrumentação, mas continuar o plano após ajuste.

Passo 2 — Rodar em paralelo um consumer event-driven do Relay em
"modo sombra"
Objetivo: consumir do Relay continuamente e escrever em tabelas de
staging separadas (não as tabelas de produção lidas por Sentinel/
Cerebro/billing). O lote de 1h continua rodando normalmente. Isso valida
o consumo contínuo sem risco para consumidores.
Critério de sucesso: as tabelas de staging convergem para os mesmos
resultados agregados que as tabelas de produção, em uma janela de
comparação de 7 dias, sem divergência acima do tolerado (a definir
com Bruce Banner).
Gatilho de rollback: divergência sistemática entre staging e produção,
ou custo de infraestrutura da execução paralela acima do previsto.
Rollback é simplesmente desligar o consumer sombra — o pipeline em lote
continua íntegro.

Passo 3 — Migrar uma etapa de transformação por vez, do lote para o
event-driven
Objetivo: das 14 etapas em Spark, começar pela mais simples e menos
crítica, reescrevendo-a para operar em micro-lotes contínuos. As demais
13 continuam em lote. Cada etapa migrada é validada isoladamente antes
de avançar para a próxima.
Critério de sucesso por etapa: o output da etapa migrada bate com o
output da etapa equivalente em lote, para o mesmo período de dados,
por 3 dias.
Gatilho de rollback por etapa: divergência de output, ou latência de
processamento da etapa migrada pior que o piso da etapa em lote
(migração precisa melhorar, não degradar).

Passo 4 — Cortar consumidores para as tabelas do pipeline event-driven,
um por um
Objetivo: primeiro o Cerebro (média sensibilidade — degradação seria
visível mas não crítica), depois o Sentinel (alta sensibilidade —
migração mais arriscada), e por último o billing (janela específica de
madrugada, muda o contrato de fechamento).
Critério de sucesso por consumidor: consumidor migrado opera com
paridade funcional por 5 dias úteis, incluindo pelo menos um incidente
ou reprocessamento (para validar o comportamento sob estresse, não só
em caminho feliz).
Gatilho de rollback por consumidor: SLA do consumidor violado no
período, ou queixa de dados incorretos/faltantes reportada por
usuário/time interno. Rollback significa apontar o consumidor de volta
para a tabela em lote (que ainda existe até o passo 5).

Passo 5 — Desligar o pipeline em lote
Objetivo: com todos os consumidores migrados e estáveis por pelo menos
2 semanas, desligar o job de cron e remover as tabelas antigas. Este é
o único passo irreversível do plano — por isso vem por último e depende
de todos os anteriores terem sido validados.
Critério de sucesso: 2 semanas consecutivas com todos os consumidores
operando no pipeline event-driven sem incidente relacionado à migração.
Gatilho de rollback: mesmo depois de desligado, manter as tabelas
antigas por mais 30 dias antes de remover — se algum consumidor precisar
voltar, é possível religar o job manualmente nesse período. Só ao fim
dos 30 dias a migração é considerada "sem volta".
```

### Elo 3 — Saída

Rodado com o plano do Elo 2 + `{{passo_alvo}}` = "Passo 1".

```
Ações ordenadas:
1. Definir as três métricas mínimas do Forge atual em lote:
   (a) duração de cada uma das 14 etapas de transformação;
   (b) tempo entre o momento em que um evento entra no Relay e o momento
       em que aparece nas tabelas de produção do Forge (lag ponta-a-ponta);
   (c) taxa de falha do job por dia e o volume acumulado quando o lote
       seguinte processa "o dobro" (o efeito bola de neve do diagnóstico).
2. Instrumentar o job Spark para emitir essas métricas para o Sentinel —
   idealmente sem tocar na lógica das transformações, adicionando apenas
   pontos de instrumentação nas bordas (início/fim de etapa, ponto de
   escrita).
3. Criar dashboard no Sentinel dedicado ao Forge com essas três métricas,
   e alertas para os thresholds acordados (a definir com Sam Wilson quando
   houver baseline de 3 dias).
4. Rodar por 5 dias úteis coletando baseline, incluindo ativamente
   induzir/observar pelo menos uma falha do job (pode ser um retry
   controlado em ambiente pré-produção que espelhe o volume real).

Como medir sucesso:
As três métricas visíveis no Sentinel de forma contínua por 5 dias
úteis. Sucesso não é "as métricas existem" — é "as métricas mostram
comportamento consistente e explicável" (ex.: o lag pico durante a
janela do reindex do Cerebro é X min, o lag em janela normal é Y min,
com X e Y estáveis). Se as métricas oscilam sem explicação, a
instrumentação ainda não está confiável.

Como detectar rollback:
O único risco deste passo é a instrumentação em si degradar o job — se a
duração do job passar a exceder consistentemente 60min (o que
canibalizaria o próximo ciclo do cron) por causa do custo da
instrumentação, remover a instrumentação, ajustar (amostragem, menos
pontos coletados) e reintroduzir. Rollback aqui é local, não afeta os
consumidores.

Informação a solicitar ao time:
- Bruce Banner: qual é o tolerável de divergência ao comparar staging vs.
  produção (informação necessária para o Passo 2, não para este, mas vale
  já pedir para ganhar tempo). E quais das 14 etapas ele considera "mais
  simples" — para embasar a escolha da primeira etapa a migrar no
  Passo 3.
- Steve Rogers: as 14 etapas têm dependência forte de ordem (é uma
  cadeia rígida) ou algumas podem rodar em paralelo? Isso muda
  radicalmente a estratégia do Passo 3.
- Sam Wilson: qual latência de dashboard é aceitável para o time de
  plantão hoje — para estabelecer o threshold de alerta em (b).
```

## 3. Curadoria

**Técnica escolhida — prompt chaining, e não um megaprompt:** testei um
único prompt gigante ("diagnostique, planeje e detalhe o primeiro passo")
como comparação. Resultado ficou raso: o plano recomendou "adotar CDC +
Kafka Streams" sem citar nenhum dos consumidores específicos do Forge
(Sentinel, Cerebro, billing da Pepper) e sem tocar nas 14 etapas do
Steve Rogers. A cadeia força o modelo a produzir estrutura em cada etapa
e usar essa estrutura na próxima — no output final, o Elo 3 cita
explicitamente o baseline do Elo 1 (efeito bola de neve, as 14 etapas,
os três consumidores) e os critérios do Elo 2. Sem a cadeia, esse
acoplamento se perde.

**Como as fronteiras entre elos foram desenhadas:** cada elo tem um
"não faça" explícito (Elo 1: "não proponha migração"; Elo 2: "não entre em
detalhe de código, tooling ou vendor"; Elo 3: "nada de código pronto").
Sem esses limites, testes preliminares mostraram o Elo 2 refazendo o
diagnóstico do Elo 1 e o Elo 3 tentando escrever pseudocódigo — cada elo
estava "puxando o cobertor" para o próprio escopo, e a cadeia perdia o
benefício da divisão.

**O que precisou de refino:** a primeira versão do Elo 2 pedia apenas
"sequência de passos"; o modelo respondeu com uma lista sem critérios de
avanço nem de reversão, o que quebrava a restrição explícita de "poder
voltar atrás". Adicionar "Critério de sucesso" e "Gatilho de rollback"
como campos obrigatórios por passo transformou a saída — passou a ser um
plano operável, e não um roteiro abstrato. Essa mesma estrutura foi
replicada no Elo 3, garantindo que o passo detalhado carregue os mesmos
dois critérios traduzidos em métricas concretas.

**Observação sobre reusabilidade:** os três elos são parametrizados de
forma que a mesma cadeia serve para outras migrações lote→evento na
Aegis (não só o Forge). O que muda é o conteúdo de `{{estado_atual}}`,
`{{restricoes}}` e `{{passo_alvo}}` — a lógica dos prompts em si é
agnóstica ao sistema específico.
