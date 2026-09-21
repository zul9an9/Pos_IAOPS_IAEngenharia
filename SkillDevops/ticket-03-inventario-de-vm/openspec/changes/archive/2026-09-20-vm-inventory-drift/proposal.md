# Proposal

## Why

O parque de VMs não tem hoje uma forma barata de responder "este host está como deveria estar?". Cada desvio de configuração (swap desabilitado, porta exposta sem necessidade, login de root liberado, chave SSH esquecida) só é descoberto quando já virou incidente. É preciso uma ferramenta que entre em um host por SSH, levante o retrato real da máquina e compare esse retrato com o baseline declarado da plataforma, apontando cada desvio e sua gravidade — sem exigir acesso privilegiado e sem alterar nada do lado do host.

## What Changes

- Nova ferramenta de linha de comando, em Python 3 (stdlib apenas), que roda na máquina de quem opera.
- Recebe endereço, usuário e caminho de chave privada de uma única VM; conecta via subprocesso do cliente `ssh` do sistema (`BatchMode=yes`, `ConnectTimeout`, `IdentitiesOnly=yes` para que só a chave de `-i` seja oferecida, `StrictHostKeyChecking=yes` por padrão), nunca via biblioteca SSH em processo — a chave nunca é lida pelo nosso código, só referenciada por caminho no `-i`.
- Host desconhecido é recusado por padrão (exit 2); afrouxar exige flag explícita do operador (`--aceitar-host-novo`, que só aceita hosts *novos* — chave de host alterada continua sendo recusada).
- Envia por stdin, em uma única conexão, um script de shell POSIX (executado com `sh -s`) que coleta todo o inventário do host de uma vez e devolve JSON com valores crus e marcações explícitas de "não lido" (campos que exigiriam privilégio).
- Inventário coletado: identificação (endereço de conexão, hostname reportado, instante da coleta), SO (distribuição e versão), kernel, serviços ativos (distinguindo unit `.service` de `.socket`, com o estado), swap (habilitado/tamanho), portas em escuta (bind address + processo dono), chaves SSH autorizadas do usuário que conectou (com identificação), configuração efetiva de login de root no SSH, e sincronização de tempo (mecanismo e estado).
- Parser YAML mínimo, escrito para este projeto, que lê o `baseline.yaml` do parque e recusa explicitamente qualquer construção que não saiba interpretar (nunca interpreta baseline de forma parcial e silenciosa). O baseline carrega um campo `versao`; versão ausente, desconhecida ou futura é falha de execução, nunca interpretação otimista.
- Layout do `baseline.yaml` (versionado pelo enunciado do ticket, não é livre): `versao`, `aplica_a`, `esperado` (grupos com regras: `so`, `kernel`, `servicos`, `swap`, `portas_em_escuta`, `chaves_ssh`, `ssh`, `ntp`) e `severidade` (listas *invertidas*: cada nível `critico`/`alto`/`medio` lista os ids das regras). O id de uma regra é o caminho pontilhado dentro de `esperado` (ex.: `portas_em_escuta.somente_rede_interna`). Severidade é um conjunto fechado (`critico`, `alto`, `medio`): outro valor, ou regra de `esperado` sem severidade declarada, é baseline inválido (exit 2).
- Motor de comparação local: para cada regra do baseline, produz uma entrada com regra, valor esperado, valor encontrado e veredito. Três vereditos possíveis: `conforme`, `desvio` (carregando a severidade que a própria regra do baseline declara) e `nao_verificado` (com motivo — falta de privilégio na coleta, ou a coleta simplesmente não produz o fato que a regra referencia). A semântica de comparação é definida por tipo de regra (lista presente/ausente, versão mínima numérica, portas por endereço público/interno, booleano, emissor de chave), nunca por igualdade textual genérica.
- Saídas: o relatório é escrito em stdout por padrão (Markdown para leitura humana pelo plantão; `--formato json` para consumo automático) e, opcionalmente, em arquivo (`--saida-json`, `--saida-markdown`). Mensagens de erro vão só para stderr.
- Formato do JSON (consumido pelo Roster, definido pelo enunciado): `{"host": {endereco, hostname, coletado_em}, "inventario": {so, kernel, servicos, swap, portas_em_escuta, chaves_ssh, ssh, ntp}, "conformidade": [{regra, esperado, encontrado, veredito, severidade (só em desvio), motivo (só em nao_verificado)}], "resumo": {conforme, desvio, nao_verificado, por_severidade: {critico, alto, medio}}}`. Campo não lido no inventário é `null` (nunca `[]`, `0`, `false` ou `""`), e o motivo viaja na entrada de `conformidade` (`encontrado: null` + `motivo`).
- Formato do Markdown (feito para o plantão, mostra primeiro o que exige ação): título `# Inventário — <hostname> (<endereco>)`, linha `Coletado em <data> · baseline v<versao>`, seção **Desvios** (tabela Severidade | Regra | Esperado | Encontrado, ordenada crítico > alto > médio), seção **Não verificado** (tabela Regra | Motivo) e seção **Conforme** (nomes das regras separados por ` · `). O inventário completo fica no JSON.
- Códigos de saída do processo: `0` sem desvios, `1` com pelo menos um desvio, `2` para falha de execução (host inalcançável, host desconhecido, chave recusada, baseline inválido, uso incorreto) — falha de execução nunca é confundida com host conforme.
- Duas invariantes de segurança/confiabilidade: (1) a ferramenta é só-leitura no host remoto — nenhum comando de escrita, instalação ou correção é executado, e duas execuções seguidas contra o mesmo host produzem o mesmo veredito por regra, variando apenas o instante da coleta (o único rastro tolerado no host é o registro de login da própria sessão SSH); (2) o **conteúdo** da chave privada nunca aparece em stdout, stderr, arquivo de saída ou mensagem de erro, em nenhum caminho de falha. O **caminho** da chave pode aparecer em mensagens de erro no stderr (é dado digitado pelo operador e necessário para diagnóstico, não é segredo), mas não nos relatórios JSON/Markdown, que circulam fora da máquina do operador.

**Fora de escopo desta fatia (fatia 1)**: múltiplos hosts por execução, correção automática de desvios, descoberta de hosts, integração com qualquer API da plataforma.

## Critérios de aceite

1. **Host conforme sai sem desvio**: contra o host do laboratório, com um baseline reduzido contendo apenas regras que esse host cumpre, a ferramenta sai com código `0` e todas as entradas do relatório são `conforme`.
2. **Lacuna de privilégio é honesta**: contra o mesmo host, a regra `ssh.login_de_root` é reportada `nao_verificado` (com motivo), nunca `conforme` nem `desvio`.
3. **Execução repetida devolve o mesmo retrato**: duas execuções seguidas concordam em todos os vereditos, diferindo apenas no instante da coleta.
4. **Falha de execução nunca parece conformidade**: host inalcançável, host desconhecido, chave recusada e baseline inválido saem com código `2` e mensagem clara.
5. **Desvios reais com a severidade do baseline**: contra o laboratório, com o baseline oficial do enunciado (que produz desvios reais no host: serviços `containerd`/`node_exporter` ausentes, swap habilitado, porta 9100 ausente), a ferramenta sai com código `1`, cada desvio carrega a severidade que o baseline declara, `resumo.por_severidade` bate com os desvios e `ssh.login_de_root` continua `nao_verificado`.

## Capabilities

### New Capabilities
- `inventory-collection`: conexão SSH read-only a um host (com política explícita de verificação de chave do host), execução de um script de coleta POSIX em uma única sessão, e produção de um retrato estruturado do host (com campos marcados como não lidos quando a coleta não teve privilégio suficiente), sem nunca expor o conteúdo da chave privada usada na conexão.
- `baseline-compliance`: leitura e validação de um `baseline.yaml` do parque (layout oficial `versao`/`aplica_a`/`esperado`/`severidade`, com severidades fechadas) através de um parser YAML mínimo próprio, comparação regra a regra do retrato coletado contra o baseline com semântica definida por tipo de regra, classificação de cada regra em `conforme` / `desvio` (com severidade) / `nao_verificado` (com motivo), emissão de relatório em JSON (formato do Roster) e Markdown (estrutura para o plantão), em stdout ou arquivo, e definição dos códigos de saída do processo (0 sem desvio, 1 com desvio, 2 falha de execução).

### Modified Capabilities
(nenhuma — projeto greenfield, sem specs existentes)

## Impact

- Novo código: uma base de código Python 3 (stdlib apenas) neste repositório, sem dependências externas (paramiko e Go descartados — ver design.md).
- Nenhum sistema remoto é modificado; o único efeito colateral em um host alvo é a leitura via SSH com o usuário informado (mais o registro de login da própria sessão SSH, rastro esperado).
- Artefato de configuração do parque: `baseline.yaml`, cujo layout oficial (incluindo `versao`, `aplica_a`, `esperado` e `severidade`), severidades fechadas e semântica de comparação por tipo de regra este projeto passa a interpretar e validar.
- Ambiente de validação: Ubuntu 26.04 em WSL2, acessível em `orpheu@172.29.2.241:22` com usuário comum e chave ed25519 (`platform@metacortex-platform`); já confirmado que `sshd -T` falha sem privilégio nesse host, portanto a regra `ssh.login_de_root` nasce `nao_verificado` nesse ambiente — comportamento esperado, não bug. A chave do host de laboratório precisa estar no `known_hosts` do operador antes da validação (a política padrão recusa host desconhecido).
