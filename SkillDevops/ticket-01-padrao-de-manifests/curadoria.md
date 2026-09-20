# Curadoria da skill `metacortex-manifests`

## 1. Onde passa a linha entre script e instrução

O critério foi uma pergunta feita a cada regra: **a resposta é a mesma para qualquer manifesto,
olhando só o YAML?** Se sim, a regra é mecânica. Se depende de saber o que a aplicação faz, é
contextual. Várias regras do padrão têm as duas metades, e cada metade foi para o seu lado.

| Tipo | Regras | Quem confere |
|---|---|---|
| Mecânica que o Trivy já cobre | 2.1 (presença), 3.2, 3.6, 3.1 (`:latest`) | `trivy config`, a mesma varredura que S&C roda no pipeline, traduzida pelo script |
| Mecânica que só a Metacortex sabe | 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.3, 2.4, 2.5, 3.4 (presença), 3.5, 3.7, 3.3 (literal, ConfigMap, comentário, Secret versionado) | `conferir.py` |
| Híbrida | 2.2 (tem probe? / o endpoint existe e não checa banco?), 2.1 (tem limite? / o valor fica entre 1,5x e 2x do consumo?), 3.3 (tem literal? / quais variáveis a app lê e quais são sensíveis?), 3.2 (FS read-only? / onde a app escreve?), 3.4 (token desmontado? / a app fala com a API?) | o script acusa a metade mecânica e emite "revisar"; o SKILL.md resolve a outra |
| Só contextual | 2.6 (SIGTERM, drenagem, PID 1) | instrução |

**Regra de ouro: não reimplementar o Trivy.** O script não verifica securityContext, requests e
limits nem acesso ao host: só traduz os IDs KSV para a numeração do padrão. O mapa foi levantado
rodando o Trivy, não suposto. A exceção é o `:latest`: o script só o verifica quando o Trivy não
está disponível, para não deixar uma regra *proibida* sem cobertura.

**A prova de que a metade contextual não é opcional** está em
`execucoes/02-conferencia-nyx/variante-exemplo-do-padrao/`. O manifesto do nyx foi corrigido
seguindo à risca o exemplo "certo" da regra 3.3 (`DATABASE_URL` via `secretKeyRef`) e passou na
conferência mecânica com **0 falhas**. Mesmo assim, o kube-news não conectaria no banco, porque
não lê essa variável. Nenhum script pega isso; só abrir o projeto.

**Conflitos com o catálogo do Trivy.** Só um ficou suprimido, em `scripts/trivyignore` com
justificativa: o KSV-0125, falso positivo de registry "não confiável" para
`registry.metacortex.io`. Nos manifests gerados, é o **único** achado cru do Trivy. Se o Trivy do
pipeline de S&C não tiver o registry interno configurado como confiável, ele acusa isso em todo
manifesto do parque, e vale levar ao Seraph. Checks do catálogo que o padrão não pede (seccomp,
hostIPC, hostPath, GID) aparecem como **informativo**: não são suprimidos e não barram.

## 2. O que ficou no corpo do SKILL.md

Ficou o que o agente usa em **toda** execução:
- os limites (não aplicar, não inventar, não escrever credencial, não incluir Namespace);
- o regime de severidade e exceção do padrão, que decide o veredito;
- o roteiro dos dois modos;
- o **checklist de leitura do projeto**, que é o conhecimento que o script não tem;
- o formato de saída;
- a prioridade "quebra funcional antes de desvio de padrão".

Essa prioridade é a lição mais importante da conferência do nyx. Das 25 falhas, três derrubam o
cliente mesmo depois de "passar": o nome rejeitado pela API, o Service sem endpoint e a
variável que o código não lê. Um relatório plano esconderia isso entre achados de securityContext.

## 3. O que virou arquivo consultado sob demanda

| Arquivo | Quando é aberto | Por que não está no corpo |
|---|---|---|
| `references/padrao.md` | para citar o texto e a severidade de uma regra, ou o mapa Trivy→regra | o script já aplica as regras; o texto só é preciso para explicar |
| `references/decisoes.md` | quando a leitura esbarra em: sem endpoint de saúde, migração no start, banco junto, diretórios graváveis | só alguns projetos caem nisso (o fake-shop cai em todos; o nyx em nenhum) |
| `assets/modelo-app.yaml` | só no modo escrita | a conferência não precisa |
| `scripts/conferir.py`, `scripts/trivyignore` | executados, nunca lidos | código não precisa entrar no contexto para funcionar |

## 4. O que decidi não empacotar

- **O Bloco 4 inteiro (4.1 a 4.8).** O próprio padrão diz que ele foi escrito "para quem está
  chegando" e que "quem já opera pode pular". Ele descreve Pod, ReplicaSet, Deployment, Service,
  port/targetPort, Endpoints, ConfigMap/Secret e probes, e o modelo já sabe tudo isso. Carregar
  o bloco em toda ativação gastaria contexto sem mudar nenhuma decisão. Nada da essência se
  perdeu:
  - a distinção readiness/liveness (4.8) já está na regra 2.2, que é o que a revisão cobra;
  - "Secret é base64, não criptografia" (4.7) já está na 3.3;
  - o comportamento do Endpoints ausente em vez de vazio (4.6) é útil, mas é do **Ticket 04**
    (dashboard), não da escrita ou conferência de manifesto;
  - "NodePort é usado na borda" (4.4) é uma descrição, não uma regra, e por isso a skill não
    restringe o tipo de Service.
- **Validação de schema (kubeconform, `kubectl --dry-run=server`).** Foi usada no fluxo, mas não
  entrou. O ferramental do time é o Trivy, e o dry-run de servidor exige credencial de cluster,
  justamente a porta que a skill mantém fechada. Fica como recomendação de pipeline.
- **Cálculo de requests e limits.** A 2.1 pede limite de memória entre 1,5x e 2x o *consumo
  observado*, e o manifesto não tem essa informação. A skill exige que os valores existam e
  obriga o relatório a declarar se vieram de métrica ou são iniciais. Cortar sem medir é o que
  gera o Chamado 1 do Ticket 02.
- **Verificar se a tag existe no registry.** Isso é olhar o mundo, não o arquivo; é território
  da skill de triagem do Ticket 02. A fronteira é o que evita que as duas disputem o mesmo pedido.
- **Validar exceções.** Elas vivem no PR, com aprovação de S&C e prazo, e o script não enxerga
  PR. A skill identifica quando uma falha precisa de exceção e escreve o pedido; não finge que a
  exceção existe.
- **Corrigir o código do cliente.** `secret_key` hardcoded, cartão e CVV gravados em texto,
  `sequelize.sync` no boot, falta de tratamento de SIGTERM e entrypoint sem `set -e` saem como
  recomendação.
- **NetworkPolicy, topologySpread e seccomp como exigência.** Não estão no padrão. O seccomp foi
  mantido no modelo por custo zero, mas o script não o exige.

## 5. Permissões que a skill pede

Declaradas em `allowed-tools`:

| Permissão | Para quê | Limite |
|---|---|---|
| `Read`, `Grep`, `Glob` | ler manifests e o código do projeto | mínimo para a metade contextual |
| `Write`, `Edit` | modo escrita: gerar ou corrigir manifests | o diretório de destino é restrição de instrução (`allowed-tools` não limita caminho) |
| `Bash(python3 *conferir.py*)` | rodar o script empacotado | só esse script |
| `Bash(trivy config*)` | o script chama o Trivy; o agente pode ver a saída crua | só `config`: sem scan de imagem nem de cluster |
| `Bash(git clone*)` | trazer o projeto a partir da URL | única saída de rede prevista |

O que a skill **não** pede, de propósito:
- `kubectl` com qualquer verbo, inclusive leitura: o cluster é da triagem;
- Bash livre;
- acesso a credencial.

## 6. A description e a convivência com a skill de triagem

A description diz o que a skill faz e **o que ela não faz**: diagnosticar objetos rodando e
explicar conceitos. Esse "não" antecipa o Ticket 02, em que uma segunda skill ocupa o mesmo
território (Kubernetes, YAML, coisa quebrada). Pedidos como "esse manifesto não sobe no cluster"
são ambíguos entre as duas, e a matriz de roteamento vai testar essa fronteira.

## 7. O que mudou quando o padrão oficial chegou

A v1 foi feita contra um padrão reconstruído, porque o anexo não estava disponível. Quando o
oficial chegou, o **método** sobreviveu inteiro: a divisão script/instrução, o Trivy antes do
script, os dois modos, o checklist de leitura e o Bloco 4 fora. O **conteúdo** mudou muito.

| Mudança | Itens |
|---|---|
| Removidos: inventados na v1, ausentes do padrão | prefixo do cliente no nome; rótulos `component` e `metacortex.io/{cliente,ambiente}`; réplicas ≥ 2 em stg; `topologySpreadConstraints`; regra de migração; seccomp; hostIPC e hostPath; NetworkPolicy obrigatória; Service só ClusterIP; registry por cliente; tag obrigatoriamente semver; exceção por anotação |
| Invertidos | **2.1**: a v1 dispensava limite de CPU e suprimia o KSV-0011; o padrão exige. **3.2**: a v1 tratava UID > 10000 como informativo; o padrão mostra `runAsUser: 10001`, e o Postgres saiu do UID 70 |
| Novos | 1.6 (nome de container); 2.4 (strategy em prod); 2.6 (grace period e SIGTERM); 3.3 em ConfigMap e **comentário** (o script passou a varrer o texto cru); semântica da 1.3 (`instance` = instalação, `managed-by` em `platform\|argocd\|helm`) |
| Estruturais | três severidades (a v1 tinha só falha); exceção obrigatória via PR com S&C e prazo; proibido sem exceção; o Namespace é criado pelo Construct e saiu dos manifests; `owner` passou de obrigatório a recomendado |

O que isso ensina, e que alimenta o Tema 2 do desafio: uma skill construída sobre suposições
passava na própria conferência com 0 falhas e estava errada em mais de uma dezena de pontos. **O script garante
consistência com o padrão que ele conhece, não com o padrão verdadeiro.** Por isso o catálogo
fica isolado (numeração oficial, uma função por regra, um mapa KSV) e é o único lugar a mudar
quando o wiki mudar. A próxima revisão do wiki deve disparar uma revisão da skill.

## 8. Limitações conhecidas

- **A 3.3 é heurística.** A varredura do texto cru pega URL com `usuario:senha` em qualquer lugar,
  inclusive comentário. A detecção por nome de variável (`PASS`, `SECRET`, `TOKEN`...) tem falso
  positivo e falso negativo. A metade contextual ("quais variáveis são sensíveis") continua
  obrigatória.
- **Autoavaliação.** As execuções foram feitas pela mesma sessão que escreveu a skill. O guia de
  criação de skills trata isso como teste de sanidade. A avaliação em sessão limpa entra na
  matriz do Ticket 02.
- **Nada foi aplicado em cluster.** A compatibilidade com UID 10001 e FS read-only só se prova no
  Ticket 04.
- **Trivy com checks embutidos.** O bundle atualizado estava bloqueado pela rede do container. O
  mapa KSV deve ser revisado contra o Trivy do pipeline de S&C.

## 9. Ajustes feitos por causa das execuções

| Quando | O que apareceu | Ajuste |
|---|---|---|
| v1, teste no nyx | `:latest` acusado duas vezes (Trivy e script) | o script cede ao KSV-0013 quando o Trivy roda |
| v1, escrita | âncora YAML reaproveitada entre documentos `---`, o que é inválido | rótulos explícitos por recurso |
| v1, captura | o código de saída registrado era o do `echo`, não o do script | recaptura com `rc=$?` imediato |
| v2, escrita | Postgres com 1 réplica em prod barra a 2.3 | exceção declarada com opções e custos (decisões D4), sem contornar |
| v2, conferência | o exemplo "certo" da 3.3 passaria sem falhas e quebraria o kube-news | variante de controle registrada como evidência |
| Ticket 02, matriz de roteamento | "esse manifesto está no padrão da casa?" sem arquivo: numa das 2 sessões limpas o agente procurou YAML no disco antes de carregar a skill | description passou a dizer "…ou está no padrão — mesmo que o arquivo ainda não tenha sido enviado (carregue a skill antes de procurar o arquivo)"; corpo ganhou "Se o manifesto não veio junto" |
| v2, conferência | readiness e liveness no mesmo destino no Postgres | o script avisa ("revisar") em vez de barrar; o `references/decisoes.md` §3 explica por que é aceitável quando o processo é o próprio banco |
