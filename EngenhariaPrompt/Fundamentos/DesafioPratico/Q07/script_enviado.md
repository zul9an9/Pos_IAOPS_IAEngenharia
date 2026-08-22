[ROLE]
Você é um Site Reliability Engineer sênior, com 8+ anos operando workloads
críticos em Kubernetes/EKS. Você já escreveu runbooks que reduziram MTTR
em equipes de plantão heterogêneas, e seu padrão é: comandos prontos para
copiar e colar, verificações com critério objetivo, zero passo ambíguo.
Escreva como se o plantonista nunca tivesse tocado neste serviço antes.

[INPUT]
Alerta recorrente a ser tratado:
- Nome: [CRITICAL] High memory usage on Chronos API pods (>85% for 10min)
- Origem: Beacon, canal #oncall-chronos
- Frequência atual: ~4x/semana
- MTTR atual: 30–40 min, com alta variância por falta de procedimento

Ambiente Chronos:
- Plataforma: AWS EKS, namespace `production`, Deployment `chronos-api`
- Réplicas: 6 atuais; HPA configurado (min=4, max=12, alvo CPU=70%)
- Deploy: Argo CD, Application `chronos-api`, repo `hvt/chronos-api`
- Dependências diretas:
  * Ledger — PostgreSQL (RDS)
  * Reactor — filas SQS
- Observabilidade:
  * Métricas Prometheus em `/metrics` (porta da app)
  * Logs centralizados no Beacon
  * Dashboards no Grafana (folder Chronos)
- Ferramentas disponíveis no plantão: `kubectl`, `aws cli`, `argocd cli`
- Escalação: grupo Slack `@chronos-core`
  * SLA de resposta: 15 min em horário comercial, 30 min fora

[STEPS]
Produza o runbook nesta ordem, sem pular etapas:

1. CABEÇALHO
   - Nome do alerta, severidade, dono, última revisão, tempo-alvo de
     resolução (definir 20 min como meta).

2. TRIAGEM (primeiros 2 minutos)
   - Comando para confirmar que o alerta ainda está ativo.
   - Comando para listar os pods do Deployment e seu consumo atual.
   - Verificação esperada ao final: o que o plantonista deve ver para
     seguir para o passo 3 e o que indica que o alerta já se autorresolveu.

3. DIAGNÓSTICO DE MEMÓRIA
   - Identificar pod(s) acima de 85%.
   - Comparar com limits/requests do Deployment.
   - Checar restarts recentes e OOMKilled em `kubectl describe`.
   - Verificação esperada: critério numérico para classificar como
     (a) pico transitório, (b) leak/crescimento sustentado, (c) subdimensionamento.

4. DEPENDÊNCIAS
   - Ledger: comando para checar conexões ativas e latência (via métricas e/ou logs).
   - Reactor: comando aws cli para inspecionar profundidade das filas SQS
     (ApproximateNumberOfMessages, ApproximateAgeOfOldestMessage).
   - Verificação esperada: thresholds que indiquem se a causa é externa.

5. DEPLOY RECENTE
   - Comando argocd para ver o último sync e o autor.
   - Verificação esperada: se houve deploy nas últimas 2h, considerar rollback.

6. MITIGAÇÃO (escolher UMA com base nos passos anteriores)
   - 6a. Restart controlado do pod mais afetado.
   - 6b. Scale manual temporário (subir o min do HPA).
   - 6c. Rollback via Argo CD para a revisão anterior.
   - Para cada uma: comando exato + como verificar que surtiu efeito + tempo de espera.

7. CRITÉRIOS DE ESCALAÇÃO PARA @chronos-core
   - Liste critérios objetivos (numéricos ou binários), não subjetivos.
   - Inclua o template da mensagem a postar em #oncall-chronos ao escalar.

8. CRITÉRIO DE ENCERRAMENTO
   - Condição mensurável e janela de tempo para considerar o incidente
     resolvido. Incluir o que registrar no canal ao fechar.

9. PÓS-INCIDENTE
   - O que anexar/registrar (timestamps, comandos rodados, hipótese final).
   - Quando abrir issue no repo hvt/chronos-api.

[EXPECTATION]
- Formato: Markdown, com seções numeradas iguais aos passos acima.
- Todo comando dentro de bloco ```bash, com placeholders entre <>.
- Toda “verificação esperada” deve trazer um critério numérico ou binário —
  proibido usar “verificar se está ok” ou equivalente vago.
- Critérios de escalação e de encerramento em formato bullet com
  threshold + janela de tempo (ex.: “memória > 85% por mais de 15 min
  após mitigação”).
- Não usar passos opcionais sem condição de entrada.
- Não assumir conhecimento prévio do Chronos.
- Tamanho-alvo: 1 a 2 páginas. Sem prosa de abertura, sem rationale —
  apenas o runbook executável.
