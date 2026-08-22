# Checkpoint 01 — Triagem de Pods (Sentinel / SRE) - CP01_triagem_de_pods.md

## Contexto

Prompt parametrizável para triagem rápida da saúde dos pods do cluster onde
o Sentinel está hospedado. Recebe um snapshot já coletado pelo plantonista
(kubectl get pods + describe + logs) e devolve a causa provável de cada pod
problemático, cruzando as três fontes — não apenas repetindo o `Reason` do
`describe`.

## 1. Prompt parametrizável

```
Role: Você é um SRE senior especialista em Kubernetes, atuando como apoio de
triagem para o plantão da Aegis. Sua análise será lida por um plantonista sob
pressão, então precisa ser direta e confiável.

Input: {{snapshot}} — bloco de texto contendo a saída de `kubectl get pods`,
o `kubectl describe pod` dos pods relevantes e trechos de log das aplicações.

Steps:
1. Liste os pods presentes no snapshot e identifique quais NÃO estão em estado
   saudável (saudável = Running, READY completo, sem CrashLoop e sem restart
   recente e recorrente).
2. Para cada pod problemático, cruze as três fontes disponíveis — STATUS,
   Events (describe) e logs — para determinar a causa provável. Não é
   suficiente repetir o Reason do describe (ex.: "OOMKilled" ou
   "ImagePullBackOff"); explique o mecanismo por trás, citando o dado do log
   ou do evento que sustenta essa conclusão.
3. Para cada pod problemático, recomende a próxima ação concreta que o
   plantonista deve tomar agora (não uma investigação genérica).
4. Se, após a análise, nenhum pod estiver problemático, declare isso de forma
   explícita e inequívoca. Não classifique nenhum pod como "atenção" ou
   "monitorar" nesse caso — se está saudável, diga que está saudável.

Expectation: Devolva a saída neste formato:
- Se houver pod(s) problemático(s): um bloco por pod, com os campos
  "Pod:", "Causa provável:" e "Ação recomendada:".
- Se não houver problema: uma única linha confirmando que todos os pods
  estão saudáveis, sem listar pod por pod.
Não devolva JSON. Não repita o dump bruto do kubectl. Escreva para leitura
rápida durante um plantão, não para um relatório.
```

Parâmetro: `{{snapshot}}` — único valor variável entre execuções.

## 2. Execução

**Modelo usado:** Claude (Sonnet). Justificativa: tarefa de raciocínio causal
sobre texto estruturado (logs/eventos), sem necessidade de tool use ou geração
de código — o critério que pesa aqui é qualidade de leitura de log e custo por
token, não throughput ou latência agressiva.

### Entrada 1 — pod reiniciando

```
Pod: sentinel-api-7d9c8b6f4-h4m2t
Causa provável: OOMKilled. O limite de memória do container é 512Mi, mas o
log mostra o heap subindo de 410Mi (ao carregar o cache de alertas) até
498Mi com "high GC pressure", culminando em "out of memory, shutting down
process". O processo está estourando o próprio limite de memória sob carga
normal de startup, não é um pico anômalo isolado.
Ação recomendada: Aumentar o limite de memória do deployment (ex.: para
768Mi–1Gi) como mitigação imediata, e abrir investigação sobre o tamanho do
cache de alertas carregado no startup — ele já consome ~80% do limite antes
mesmo de o serviço estabilizar.
```

### Entrada 2 — pods que não sobem

```
Pod: sentinel-api-7d9c8b6f4-zzp10
Causa provável: ImagePullBackOff. O evento mostra "manifest unknown" ao
tentar puxar a tag sentinel-api:2.9.2 do registry. Isso indica que a imagem
com essa tag não existe no registry (não é um problema de rede ou de
credencial, é a tag não publicada).
Ação recomendada: Verificar se o build/push da versão 2.9.2 foi concluído no
pipeline de CI. Se não foi, fazer rollback do deployment para a tag 2.9.1
(que está rodando com sucesso no outro pod) até o build ser corrigido.

Pod: sentinel-ingest-8f7a9c5b-4dkqm
Causa provável: Pending por falta de recurso. O evento "FailedScheduling"
mostra "0/6 nodes are available: 6 Insufficient cpu" — o pod pede 2 CPUs e
nenhum node do cluster tem essa capacidade livre no momento.
Ação recomendada: Verificar ocupação de CPU dos nodes e, se não houver
margem, escalar o node pool (adicionar node) ou revisar se o request de 2
CPU é realmente necessário para esse pod. Não é um problema de imagem ou
config da aplicação — é capacidade do cluster.
```

### Entrada 3 — tudo saudável

```
Todos os pods do namespace estão saudáveis: nenhum em CrashLoop, ImagePull
ou Pending. O único restart registrado (sentinel-worker, 1 restart há 3
dias) é um evento antigo e isolado, sem recorrência — não caracteriza
problema ativo. Nenhuma ação necessária.
```

## 3. Curadoria

Framework escolhido: **RISE** (Role, Input, Steps, Expectation). A tarefa tem
exatamente essa forma — papel fixo (SRE de triagem), input único bem definido
(o snapshot), sequência de passos de raciocínio que precisa ser forçada
(senão o modelo atalha para o `Reason` bruto do describe), e uma expectativa
de formato rígida (necessária porque este prompt será testado com asserts de
regex no Checkpoint 08 — formato solto aqui quebraria os testes mais adiante).

O que precisou de refino: a primeira versão do Step 2 era vaga ("identifique
a causa"), e na prática o modelo só repetia o campo `Reason` do `describe` —
não cumpria o requisito de cruzar status + eventos + logs. Também foi
necessário blindar o Step 4 contra respostas em cima do muro (ex.: "parece
estável, mas vale monitorar") — o checkpoint exige reconhecimento explícito
do caso saudável, sem hedge.

Nota sobre dados sensíveis: este snapshot não trouxe identificador de
cliente/tenant (diferente do CP03, que traz nome de tenant nos logs) — não
houve decisão de sanitização a tomar aqui.
