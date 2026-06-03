
# Justificativa — onde cada elemento R-I-S-E aparece

# [ROLE]:
Role aparece no bloco  
define um SRE sênior com perfil específico (8+ anos, foco em runbooks, padrão de comandos copiáveis). Isso ancora o tom (instrucional, sem prosa) e a profundidade técnica (limits/requests, HPA, OOMKilled como vocabulário esperado, não explicado). Sem esse Role, o modelo tende a produzir um runbook didático com explicações longas, o que aumenta o MTTR em vez de reduzi-lo.

$ [INPUT]: 
Input aparece no bloco 
entrega todo o contexto operacional do Chronos — namespace, número de réplicas, parâmetros do HPA, dependências, ferramentas disponíveis, canal e SLA de escalação. Esse bloco é o que evita que o modelo invente componentes (ex.: sugerir Datadog quando o ambiente usa Grafana) ou comandos para ferramentas indisponíveis. O Input também restringe o escopo: o runbook produzido só usa kubectl, aws cli e argocd cli, exatamente o que o plantão tem na mão.

# [STEPS]: 
Steps aparece no bloco 
prescreve a estrutura do runbook em 9 seções obrigatórias e na ordem certa — triagem antes de diagnóstico, diagnóstico antes de mitigação, escalação com critério objetivo, encerramento com condição mensurável, pós-incidente. Cada passo dentro do Steps já antecipa o que deve existir na saída (ex.: passo 4 exige verificar profundidade da fila SQS via aws cli). Isso transforma o prompt em uma planta arquitetônica do output e elimina a variabilidade do passo 6 (mitigação), forçando escolha de uma entre três ações com critério.

# [EXPECTATION]: 
Expectation aparece no bloco 
define o formato (Markdown), o estilo dos comandos (blocos bash com placeholders em <>), e — mais importante — proíbe ambiguidade ("verificar se está ok" não é aceito), exige thresholds numéricos em escalação/encerramento e proíbe passos opcionais sem critério de entrada. Essa é a parte que ataca diretamente o problema relatado (variância de 30–40 min): sem Expectation forte, o modelo produziria um runbook plausível mas igualmente ambíguo ao que existe na cabeça das pessoas hoje.
Em síntese: Role garante voz e profundidade, Input garante aderência ao ambiente real, Steps garante completude e ordem, Expectation garante que cada passo seja executável por qualquer plantonista sem consultar quem conhece o sistema — que era exatamente o pedido da Lorraine.

