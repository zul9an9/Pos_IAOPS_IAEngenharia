# Delta de Spec

## Purpose

Conecta-se a exatamente um host alvo por SSH como usuário sem privilégio e produz um inventário estruturado, pontual, da configuração real desse host, sem instalar, gravar nem modificar nada nele.

## ADDED Requirements

### Requirement: Um Único Host por Execução
O sistema SHALL aceitar exatamente um host alvo (endereço, usuário, caminho da chave privada) por execução e MUST NOT aceitar nem iterar sobre uma lista de hosts.

#### Scenario: Um host processado por execução
- **QUANDO** a ferramenta é invocada com um endereço, um usuário e um caminho de chave privada
- **ENTÃO** ela conecta a esse único host e produz exatamente um resultado de inventário para ele

### Requirement: Conexão SSH pelo Cliente do Sistema
O sistema SHALL falar com o host alvo invocando o cliente `ssh` do sistema operacional como subprocesso, com `BatchMode=yes`, `IdentitiesOnly=yes` (para que somente a chave informada em `-i` seja oferecida, e nunca uma identidade do agente SSH ou uma chave padrão do operador) e um `ConnectTimeout` explícito, e MUST NOT vincular nem invocar nenhuma biblioteca cliente SSH em processo. A chave privada SHALL ser passada ao subprocesso `ssh` apenas como caminho de arquivo, por meio de `-i`.

#### Scenario: Conexão não interativa com espera limitada
- **QUANDO** o host alvo está inalcançável ou não responde
- **ENTÃO** a tentativa de conexão falha após o `ConnectTimeout` configurado, em vez de travar ou pedir algo de forma interativa

#### Scenario: Só a chave informada é oferecida
- **QUANDO** o operador informa uma chave que o host não aceita, mas existe um agente SSH ou uma chave padrão que o host aceitaria
- **ENTÃO** a autenticação é rejeitada, porque só a chave de `-i` é oferecida, e a ferramenta reporta autenticação rejeitada

#### Scenario: Nenhuma biblioteca SSH no processo de coleta
- **QUANDO** a ferramenta estabelece uma conexão
- **ENTÃO** a conexão é feita disparando o binário `ssh` do sistema como subprocesso, e nenhuma implementação do protocolo SSH roda dentro do processo da própria ferramenta

### Requirement: Verificação da Chave do Host
O sistema SHALL executar o `ssh` com `StrictHostKeyChecking=yes` por padrão, de modo que, em `BatchMode`, um host cuja chave não consta no `known_hosts` do operador seja recusado. Afrouxar essa política SHALL exigir uma flag explícita do operador (`--aceitar-host-novo`), que só pode resultar em `StrictHostKeyChecking=accept-new`. O sistema MUST NOT usar `StrictHostKeyChecking=no` nem `UserKnownHostsFile=/dev/null`, e MUST NOT aceitar uma chave de host que difere da registrada, com ou sem a flag.

#### Scenario: Host desconhecido é recusado por padrão
- **QUANDO** o host alvo tem uma chave que não consta no `known_hosts` do operador e a flag `--aceitar-host-novo` não foi informada
- **ENTÃO** a conexão é recusada, nenhum inventário é produzido, o processo sai com código `2` e a mensagem diz que a chave do host é desconhecida

#### Scenario: Flag explícita aceita apenas host novo
- **QUANDO** o operador informa `--aceitar-host-novo` e o host alvo é desconhecido
- **ENTÃO** a conexão prossegue com `StrictHostKeyChecking=accept-new`

#### Scenario: Chave de host alterada é recusada mesmo com a flag
- **QUANDO** a chave apresentada pelo host difere da registrada no `known_hosts`, com ou sem `--aceitar-host-novo`
- **ENTÃO** a conexão é recusada, o processo sai com código `2` e a mensagem diz que a chave do host foi alterada

### Requirement: Garantia de Somente Leitura
O sistema SHALL executar no host alvo apenas comandos que leem estado. Ele MUST NOT instalar pacotes, gravar arquivos, iniciar/parar/habilitar/desabilitar serviços, nem alterar de qualquer outro modo o estado do host alvo. O único rastro tolerado no host é o registro de login da própria sessão SSH (por exemplo, a linha de sessão do `sshd` em log ou journal), que é efeito esperado de toda conexão e não constitui violação.

#### Scenario: A coleta repetida é idempotente
- **QUANDO** o mesmo host é coletado duas vezes seguidas, sem mudança de configuração entre elas
- **ENTÃO** todo fato coletado é idêntico entre as duas execuções, exceto o timestamp da coleta

#### Scenario: Nenhum comando mutante é emitido
- **QUANDO** o script de coleta roda no host alvo
- **ENTÃO** ele não contém nenhum comando que crie, apague ou modifique arquivo, pacote, estado de serviço ou configuração nesse host

#### Scenario: Estado do host inalterado após a coleta
- **QUANDO** o estado do host (lista de unidades systemd ativas dos tipos service e socket, `/proc/swaps`, portas em escuta por `ss -ltn` e o conteúdo e a data de modificação do `authorized_keys`) é capturado antes e depois de uma coleta
- **ENTÃO** as duas capturas são idênticas, e o registro de login da sessão SSH da própria coleta não é considerado diferença

### Requirement: Coleta por Script em Conexão Única
O sistema SHALL reunir todo o inventário de um host enviando um único script de shell POSIX por stdin dentro de uma única sessão SSH, interpretado por `sh -s` (e não por `bash`), e esse script SHALL devolver um único documento JSON contendo todos os fatos coletados com valores crus.

#### Scenario: Uma conexão por host
- **QUANDO** um host é coletado
- **ENTÃO** exatamente uma sessão SSH é aberta para obter o inventário completo, e não uma conexão por dado

#### Scenario: Script portável para POSIX sh
- **QUANDO** o script de coleta é executado por `sh -s`, inclusive em um host cujo `/bin/sh` é `dash`
- **ENTÃO** ele roda sem depender de nenhum recurso exclusivo do `bash`

#### Scenario: Retrato coerente de um único instante
- **QUANDO** o inventário inclui fatos que de outro modo poderiam ser lidos com instantes de diferença (por exemplo, portas em escuta e estado do swap)
- **ENTÃO** todos os fatos vêm da mesma execução única do script, de modo que descrevem o host no mesmo instante

### Requirement: Dados de Identificação
O sistema SHALL reportar, para todo host coletado: o endereço usado para conectar, o hostname reportado pelo próprio host e o timestamp do instante da coleta.

#### Scenario: A identificação está sempre presente
- **QUANDO** uma coleta termina, com sucesso ou parcialmente
- **ENTÃO** o resultado inclui o endereço de conexão, o hostname reportado pelo host e o timestamp da coleta

### Requirement: Dados de Sistema Operacional e Kernel
O sistema SHALL reportar a distribuição do SO do host (o identificador do sistema, em minúsculas, como `ubuntu`), a versão da distribuição e a versão do kernel em execução.

#### Scenario: Distribuição e kernel capturados
- **QUANDO** uma coleta termina em um host alcançável
- **ENTÃO** o resultado inclui o identificador da distribuição, a versão da distribuição e a versão do kernel, conforme reportados pelo host

### Requirement: Inventário de Serviços
O sistema SHALL reportar os serviços ativos do host, distinguindo unidades systemd `.service` de unidades `.socket`, e SHALL reportar o estado ativo de cada unidade.

#### Scenario: Unidades service e socket distinguidas
- **QUANDO** o host tem unidades `.service` e `.socket` ativas
- **ENTÃO** o resultado lista cada unidade com seu tipo (`service` ou `socket`) e seu estado (`active`), de modo que as duas nunca sejam confundidas

### Requirement: Dados de Swap
O sistema SHALL reportar se o swap está habilitado no host e, quando estiver, o seu tamanho.

#### Scenario: Estado do swap capturado
- **QUANDO** o host tem swap habilitado
- **ENTÃO** o resultado reporta o swap como habilitado e inclui o seu tamanho

#### Scenario: Swap desabilitado é reportado explicitamente
- **QUANDO** o host não tem swap configurado
- **ENTÃO** o resultado reporta o swap como desabilitado, em vez de omitir o campo

### Requirement: Dados de Portas em Escuta
O sistema SHALL reportar cada porta em estado de escuta no host, incluindo o seu endereço de vinculação (bind address) e o processo dono.

#### Scenario: Porta em escuta com dono capturada
- **QUANDO** um processo no host está escutando em uma porta
- **ENTÃO** o resultado inclui o endereço de vinculação dessa porta e a identidade do processo dono

### Requirement: Dados de Chaves SSH Autorizadas
O sistema SHALL reportar as chaves SSH autorizadas para login do usuário que estabeleceu a conexão, cada uma com um atributo identificador (como comentário ou fingerprint). O escopo é o conjunto de chaves autorizadas legível por esse usuário sem privilégio, e o resultado SHALL declarar esse escopo.

#### Scenario: Chaves autorizadas enumeradas
- **QUANDO** o usuário que conectou tem uma ou mais chaves SSH autorizadas configuradas
- **ENTÃO** o resultado lista cada chave com um atributo identificador, sem expor o material completo da chave além do necessário para identificá-la

### Requirement: Configuração Efetiva de Login de Root no SSH
O sistema SHALL tentar determinar a configuração *efetiva* do servidor SSH para login de root (isto é, o valor resolvido em tempo de execução, e não apenas uma linha extraída de um arquivo de configuração).

#### Scenario: Valor efetivo obtido quando o privilégio permite
- **QUANDO** o usuário da coleta tem privilégio suficiente para consultar a configuração efetiva do daemon SSH
- **ENTÃO** o resultado reporta o valor efetivo de login de root conforme lido do daemon

#### Scenario: Marcado como não lido quando o privilégio é insuficiente
- **QUANDO** o usuário da coleta não tem o privilégio necessário para consultar a configuração efetiva do daemon SSH
- **ENTÃO** o resultado marca esse campo como não lido, com o motivo, em vez de adivinhar a partir de um arquivo de configuração ou omiti-lo em silêncio

### Requirement: Dados de Sincronização de Tempo
O sistema SHALL reportar se o host tem um mecanismo de sincronização de tempo ativo e qual é o mecanismo.

#### Scenario: Mecanismo ativo identificado
- **QUANDO** o host tem um serviço de sincronização de tempo em execução
- **ENTÃO** o resultado reporta que a sincronização está ativa e nomeia o mecanismo

### Requirement: Marcação de Campo Não Lido
Todo campo que o script de coleta não consiga ler — mais comumente por privilégio insuficiente do usuário que conecta — SHALL ser marcado explicitamente como não lido na saída, distinguível de um campo cujo valor real é vazio, zero ou desabilitado.

#### Scenario: Não lido é distinto de vazio
- **QUANDO** um campo não pode ser lido porque o usuário que conecta não tem privilégio
- **ENTÃO** a saída o marca como não lido, com um motivo, e essa marcação nunca é a mesma representação de um valor legitimamente vazio ou desabilitado

### Requirement: Confidencialidade da Chave Privada
O sistema SHALL tratar a chave privada como credencial. Ele MUST NOT ler o conteúdo da chave privada para dentro do seu próprio processo (pode apenas verificar a existência do caminho, sem abrir o arquivo), e o **conteúdo** da chave MUST NOT aparecer na saída padrão, no erro padrão, em arquivo de saída, em log nem em qualquer mensagem de erro, em qualquer caminho de falha. O **caminho** da chave privada pode aparecer em mensagens de erro no stderr, pois é um dado digitado pelo operador e necessário para diagnosticar erro de digitação ou de permissão; ele MUST NOT aparecer nos relatórios JSON e Markdown (em stdout ou em arquivo), porque esses circulam fora da máquina do operador. O texto de stderr do subprocesso `ssh` SHALL ser reescrito em categorias fixas de falha e nunca repassado cru.

#### Scenario: Chave rejeitada pelo host
- **QUANDO** o host alvo rejeita a chave privada fornecida
- **ENTÃO** o erro reportado explica que a autenticação falhou, sem imprimir o conteúdo da chave, material da chave ou passphrase

#### Scenario: Falha inesperada durante a conexão
- **QUANDO** o subprocesso SSH falha por qualquer motivo (rede, autenticação, protocolo)
- **ENTÃO** nenhuma saída capturada, linha de log, mensagem de exceção ou arquivo de saída emitido pela ferramenta contém o conteúdo da chave privada

#### Scenario: Caminho da chave só em mensagem de erro
- **QUANDO** o arquivo da chave privada não existe ou não é acessível
- **ENTÃO** a mensagem de erro no stderr pode citar o caminho informado pelo operador, e nenhum relatório JSON ou Markdown contém esse caminho

### Requirement: Reporte de Falha de Conexão com o Host
O sistema SHALL detectar quando o host alvo está inalcançável, a chave do host não é confiável ou a autenticação falha, e SHALL reportar isso como uma falha distinta e legível, que descreve o que ocorreu, sem stack trace cru e sem ser reportada como se a coleta tivesse tido sucesso.

#### Scenario: Host inalcançável
- **QUANDO** o host alvo não responde dentro do tempo limite de conexão
- **ENTÃO** a ferramenta reporta que o host estava inalcançável, em uma mensagem que diz o que aconteceu, e não produz um resultado de inventário como se o host tivesse respondido

#### Scenario: Autenticação rejeitada
- **QUANDO** o host alvo rejeita a autenticação SSH
- **ENTÃO** a ferramenta reporta que a autenticação falhou, em uma mensagem que diz o que aconteceu, sem stack trace cru
