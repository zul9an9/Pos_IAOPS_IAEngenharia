# baseline-compliance Specification

## Purpose
Lê o `baseline.yaml` declarado do parque, compara-o localmente, regra a regra, com o inventário coletado de um host e reporta o veredito, a severidade e o motivo de cada regra, junto com o código de saída geral do processo.

## Requirements

### Requirement: Parser Mínimo de Baseline
O sistema SHALL parsear o `baseline.yaml` usando um parser YAML escrito para este projeto, em vez de depender de uma biblioteca YAML de uso geral, e SHALL rejeitar explicitamente qualquer construção YAML que não saiba interpretar, em vez de ignorá-la ou interpretá-la mal em silêncio. Valores booleanos SHALL ser aceitos somente como os literais `true` e `false`. O subconjunto suportado é: mapeamentos em bloco, listas em bloco, escalares, comentários e flow style de uma linha (`[a, b]` e `{chave: valor, outra: [x, y]}`, com valores escalares ou listas de escalares).

#### Scenario: Construções conhecidas são parseadas
- **QUANDO** o `baseline.yaml` usa apenas construções que o parser suporta
- **ENTÃO** todas as regras do arquivo são carregadas com seu valor esperado e sua severidade

#### Scenario: Mapeamento em linha com listas é suportado
- **QUANDO** o `baseline.yaml` usa `servicos: {ativos: [ssh, chrony], proibidos: [telnet.socket]}` em uma linha
- **ENTÃO** o parser o lê como um mapeamento com duas listas de escalares

#### Scenario: Flow style aninhado ou multilinha é rejeitado
- **QUANDO** o `baseline.yaml` contém um mapeamento em linha dentro de outro mapeamento ou lista em linha, ou um flow style que ocupa mais de uma linha
- **ENTÃO** o baseline é tratado como inválido, com a construção e a linha nomeadas

#### Scenario: Construção desconhecida é rejeitada
- **QUANDO** o `baseline.yaml` contém uma construção YAML que o parser não suporta
- **ENTÃO** a ferramenta se recusa a prosseguir com esse baseline e o reporta como baseline inválido, em vez de adivinhar seu significado

#### Scenario: Booleano ambíguo é rejeitado
- **QUANDO** o `baseline.yaml` usa `yes`, `no`, `on` ou `off` como valor esperado de uma regra booleana
- **ENTÃO** o baseline é tratado como inválido, e não interpretado como `true`/`false`

### Requirement: Baseline Inválido é Falha de Execução
Um `baseline.yaml` que não possa ser parseado ou seja inválido SHALL ser tratado como falha de execução, e não como um host com zero regras aplicáveis.

#### Scenario: Arquivo de baseline malformado
- **QUANDO** o `baseline.yaml` fornecido não pode ser parseado ou falha na validação estrutural
- **ENTÃO** a ferramenta sai com o código de falha de execução e uma mensagem que identifica o baseline como o problema

### Requirement: Validação da Versão do Baseline
O sistema SHALL validar o campo `versao` do `baseline.yaml` antes de interpretar qualquer regra. O conjunto de versões suportadas hoje é `{1}` (inteiro). Versão ausente, desconhecida ou futura SHALL ser falha de execução, e a ferramenta MUST NOT interpretar de forma otimista um baseline cuja versão não conhece.

#### Scenario: Versão suportada
- **QUANDO** o `baseline.yaml` declara `versao: 1`
- **ENTÃO** a ferramenta prossegue para interpretar as regras

#### Scenario: Versão ausente
- **QUANDO** o `baseline.yaml` não contém o campo `versao`
- **ENTÃO** a ferramenta sai com código `2` e uma mensagem que informa que a versão do baseline está ausente, sem avaliar nenhuma regra

#### Scenario: Versão desconhecida
- **QUANDO** o campo `versao` contém um valor que não pertence ao conjunto suportado e não é uma versão maior que a suportada (por exemplo, texto ou valor não inteiro)
- **ENTÃO** a ferramenta sai com código `2` e uma mensagem que informa que a versão do baseline é desconhecida, sem avaliar nenhuma regra

#### Scenario: Versão futura
- **QUANDO** o campo `versao` contém um inteiro maior que a maior versão suportada
- **ENTÃO** a ferramenta sai com código `2` e uma mensagem que informa que o baseline foi escrito para uma versão mais nova da ferramenta, sem avaliar nenhuma regra

### Requirement: Layout do Baseline
O `baseline.yaml` SHALL seguir o layout oficial do enunciado: chaves de raiz `versao`, `aplica_a` (texto não vazio, informativo), `esperado` (mapeamento de grupos, cada grupo um mapeamento de regras) e `severidade` (mapeamento *invertido*: cada nível de severidade lista os ids das regras a que se aplica). O id de uma regra SHALL ser o caminho pontilhado dentro de `esperado` (grupo e regra, ex.: `portas_em_escuta.somente_rede_interna`), e a ordem das regras SHALL ser a de aparição em `esperado`. Qualquer chave de raiz fora dessas quatro, ou a ausência de `aplica_a`, `esperado` ou `severidade`, torna o baseline inválido. O valor `esperado` de cada regra conhecida SHALL ser validado segundo o tipo da regra.

#### Scenario: Layout oficial é carregado
- **QUANDO** o `baseline.yaml` traz `versao`, `aplica_a`, `esperado` e `severidade` no layout oficial
- **ENTÃO** cada folha de `esperado` vira uma regra com id pontilhado (`so.versao_minima`, `servicos.ativos`, `swap.habilitado` etc.), o valor esperado declarado e a severidade obtida das listas de `severidade`

#### Scenario: Chave de raiz desconhecida ou ausente
- **QUANDO** o baseline tem uma chave de raiz desconhecida (por exemplo o antigo `regras`), ou não tem `aplica_a`, `esperado` ou `severidade`
- **ENTÃO** o baseline é inválido e a ferramenta sai com código `2`, nomeando a chave

#### Scenario: Valor esperado de tipo errado
- **QUANDO** o valor esperado de uma regra conhecida não tem o tipo exigido (por exemplo `swap.habilitado: sim`, ou `so.versao_minima: jammy`)
- **ENTÃO** o baseline é inválido e a ferramenta sai com código `2`, nomeando a regra

#### Scenario: Regra desconhecida com severidade é aceita
- **QUANDO** `esperado` contém uma regra que a ferramenta não conhece e ela tem severidade declarada
- **ENTÃO** o baseline é válido e essa regra será avaliada como `nao_verificado`

### Requirement: Severidades Fechadas
O sistema SHALL aceitar como severidade apenas `critico`, `alto` e `medio`. É baseline inválido (exit 2): uma chave de `severidade` fora desse conjunto; uma regra de `esperado` sem severidade declarada; uma regra listada em mais de um nível; e um id listado em `severidade` que não existe em `esperado`.

#### Scenario: Severidade fora do conjunto
- **QUANDO** `severidade` contém uma chave como `baixo`, `critica` ou `urgente`
- **ENTÃO** o baseline é inválido e a ferramenta sai com código `2`, nomeando a severidade desconhecida

#### Scenario: Regra sem severidade declarada
- **QUANDO** uma regra de `esperado` não aparece em nenhuma lista de `severidade`
- **ENTÃO** o baseline é inválido e a ferramenta sai com código `2`, nomeando a regra sem severidade

#### Scenario: Regra em dois níveis
- **QUANDO** o mesmo id aparece em duas listas de `severidade`
- **ENTÃO** o baseline é inválido e a ferramenta sai com código `2`, nomeando a regra

#### Scenario: Id de severidade sem regra
- **QUANDO** uma lista de `severidade` contém um id que não existe em `esperado` (por exemplo por erro de digitação)
- **ENTÃO** o baseline é inválido e a ferramenta sai com código `2`, nomeando o id

#### Scenario: Severidade válida
- **QUANDO** toda regra de `esperado` aparece em exatamente uma das listas `critico`, `alto` ou `medio`
- **ENTÃO** a severidade de cada regra é a do nível em que ela aparece

### Requirement: Comparação Local
O sistema SHALL realizar a comparação entre os fatos coletados do host e o baseline inteiramente na máquina que executa a ferramenta. O host alvo MUST NOT ser consultado de novo, nem alterado, como parte da etapa de comparação.

#### Scenario: A comparação usa apenas fatos já coletados
- **QUANDO** o relatório de conformidade é produzido
- **ENTÃO** ele é derivado do inventário já coletado na sessão SSH única, sem nenhuma interação adicional com o host

### Requirement: Uma Entrada de Conformidade por Regra do Baseline
O sistema SHALL produzir exatamente uma entrada de conformidade por regra declarada no baseline, cada uma contendo o identificador da regra, o valor esperado, o valor encontrado no host e um veredito.

#### Scenario: Toda regra é contabilizada
- **QUANDO** o baseline declara N regras
- **ENTÃO** o relatório de conformidade contém exatamente N entradas, uma por regra, cada uma nomeando essa regra

### Requirement: Modelo de Três Vereditos
O veredito de cada entrada de conformidade SHALL ser exatamente um entre: `conforme` (o host atende à expectativa do baseline), `desvio` (o host não atende, carregando a severidade que o baseline atribui àquela regra) ou `nao_verificado` (a regra não pôde ser avaliada, carregando um motivo). O que significa "atender" depende do tipo da regra, conforme o requisito "Semântica de Comparação por Tipo de Regra". A severidade SHALL constar somente em entradas `desvio`, e o motivo somente em entradas `nao_verificado`, que SHALL ter o valor encontrado `null`.

#### Scenario: Valor que atende é conforme
- **QUANDO** o valor encontrado no host atende à expectativa do baseline para uma regra, segundo a semântica do tipo dessa regra
- **ENTÃO** o veredito dessa regra é `conforme`

#### Scenario: Valor que não atende é desvio com severidade
- **QUANDO** o valor encontrado no host não atende à expectativa do baseline para uma regra, segundo a semântica do tipo dessa regra
- **ENTÃO** o veredito dessa regra é `desvio` e carrega a severidade que o baseline declara para essa regra

#### Scenario: Fato não lido é nao_verificado com motivo
- **QUANDO** uma regra depende de um fato do host que a coleta marcou como não lido (por exemplo, por privilégio insuficiente)
- **ENTÃO** o veredito dessa regra é `nao_verificado` e inclui o motivo pelo qual o fato não pôde ser verificado, e esse veredito nunca é reportado como `conforme`

### Requirement: Semântica de Comparação por Tipo de Regra
O sistema SHALL avaliar cada regra conforme a semântica do seu tipo, definida abaixo, e MUST NOT comparar valores por igualdade textual genérica. Em todos os casos, a entrada de conformidade SHALL registrar o valor esperado e o valor encontrado; em caso de `desvio`, o valor encontrado SHALL identificar o que causou o desvio (itens ausentes, itens presentes, portas ou chaves ofensoras). Nos tipos abaixo, se o fato de que a regra depende foi marcado como não lido pela coleta, o veredito é `nao_verificado` com motivo, conforme o modelo de três vereditos. Um "endereço interno" é: loopback (`127.0.0.0/8`, `::1`), RFC1918 (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local (`169.254.0.0/16`, `fe80::/10`) ou ULA (`fc00::/7`). Todo endereço curinga (`0.0.0.0`, `::`, `*`) e todo endereço fora dessas faixas é um "endereço público".

#### Scenario: servicos.ativos — todos presentes e ativos
- **QUANDO** a regra `servicos.ativos` lista unidades (nome sem sufixo significa unidade `.service`; uma unidade `.socket` precisa ser nomeada com o sufixo `.socket`) e todas estão presentes e ativas no host
- **ENTÃO** o veredito é `conforme`

#### Scenario: servicos.ativos — alguma ausente ou inativa
- **QUANDO** pelo menos uma unidade listada em `servicos.ativos` não está presente e ativa no host
- **ENTÃO** o veredito é `desvio` com a severidade da regra, e o valor encontrado lista as unidades ausentes ou inativas

#### Scenario: servicos.proibidos — nenhuma presente
- **QUANDO** nenhuma das unidades listadas em `servicos.proibidos` está ativa no host
- **ENTÃO** o veredito é `conforme`

#### Scenario: servicos.proibidos — alguma presente
- **QUANDO** pelo menos uma unidade listada em `servicos.proibidos` está ativa no host
- **ENTÃO** o veredito é `desvio` com a severidade da regra, e o valor encontrado lista as unidades proibidas presentes

#### Scenario: so.distribuicao — distribuição igual à esperada
- **QUANDO** a regra `so.distribuicao` espera `ubuntu` e a distribuição reportada pelo host (o identificador do sistema, sem diferenciar maiúsculas de minúsculas) é `ubuntu`
- **ENTÃO** o veredito é `conforme`

#### Scenario: so.distribuicao — distribuição diferente
- **QUANDO** a distribuição reportada pelo host é diferente da esperada (por exemplo `debian`)
- **ENTÃO** o veredito é `desvio` com a severidade da regra, e o valor encontrado é a distribuição reportada

#### Scenario: Versão mínima é comparada numericamente, não como texto
- **QUANDO** as regras `so.versao_minima` ou `kernel.versao_minima` são avaliadas
- **ENTÃO** as versões são comparadas componente a componente como números inteiros (por exemplo, `6.10` é maior que `6.9`, e `24.04` é maior ou igual a `22.04`), e nunca como strings; no kernel, apenas o prefixo numérico da versão participa da comparação (`5.15.0-101-generic` é comparado como `5.15.0`)

#### Scenario: Versão igual ou superior à mínima é conforme
- **QUANDO** a versão encontrada no host é numericamente igual ou superior à versão mínima do baseline
- **ENTÃO** o veredito é `conforme`

#### Scenario: Versão inferior à mínima é desvio
- **QUANDO** a versão encontrada no host é numericamente inferior à versão mínima do baseline
- **ENTÃO** o veredito é `desvio` com a severidade da regra

#### Scenario: Versão encontrada ilegível
- **QUANDO** a versão reportada pelo host não pode ser interpretada como sequência numérica de componentes
- **ENTÃO** o veredito é `nao_verificado` com o motivo, e nunca `conforme`

#### Scenario: Versão mínima ilegível no baseline
- **QUANDO** o valor esperado de `so.versao_minima` ou `kernel.versao_minima` no baseline não é uma sequência numérica de componentes
- **ENTÃO** o baseline é inválido e a ferramenta sai com código `2`

#### Scenario: portas_em_escuta.publicas_permitidas — nenhuma porta pública além das listadas
- **QUANDO** toda porta em escuta vinculada a endereço público está na lista de `portas_em_escuta.publicas_permitidas`
- **ENTÃO** o veredito é `conforme`; portas vinculadas somente a endereço interno não afetam essa regra

#### Scenario: portas_em_escuta.publicas_permitidas — porta pública não listada
- **QUANDO** existe pelo menos uma porta em escuta vinculada a endereço público que não está na lista
- **ENTÃO** o veredito é `desvio` com a severidade da regra, e o valor encontrado lista as portas públicas não permitidas com seus endereços

#### Scenario: portas_em_escuta.somente_rede_interna — porta em endereço interno
- **QUANDO** uma porta listada em `portas_em_escuta.somente_rede_interna` (por exemplo, `9100`) existe e todas as suas vinculações são a endereços internos
- **ENTÃO** o veredito é `conforme`

#### Scenario: portas_em_escuta.somente_rede_interna — porta em endereço público
- **QUANDO** uma porta listada em `portas_em_escuta.somente_rede_interna` (por exemplo, `9100`) está vinculada a `0.0.0.0` (ou a qualquer outro endereço público), mesmo que também esteja vinculada a um endereço interno
- **ENTÃO** o veredito é `desvio` com a severidade da regra, e o valor encontrado mostra o endereço público da vinculação

#### Scenario: portas_em_escuta.somente_rede_interna — porta inexistente
- **QUANDO** uma porta listada em `portas_em_escuta.somente_rede_interna` não está em escuta no host
- **ENTÃO** o veredito é `desvio` com a severidade da regra, porque a regra exige que a porta exista e esteja vinculada a endereço interno

#### Scenario: Regras booleanas
- **QUANDO** as regras `swap.habilitado`, `ssh.login_de_root` ou `ntp.sincronizado` são avaliadas
- **ENTÃO** o valor esperado (`true`/`false`) é comparado ao estado booleano encontrado: para `swap.habilitado`, swap ativo é `true`; para `ntp.sincronizado`, sincronização de tempo ativa é `true`; para `ssh.login_de_root`, o valor efetivo `no` é `false` e qualquer outro valor efetivo (incluindo `yes`, `prohibit-password` e `forced-commands-only`) é `true`

#### Scenario: Login de root por chave conta como habilitado
- **QUANDO** o baseline espera `ssh.login_de_root: false` e a configuração efetiva do daemon é `prohibit-password`
- **ENTÃO** o veredito é `desvio` com a severidade da regra

#### Scenario: chaves_ssh.emitidas_por — todas as chaves compatíveis
- **QUANDO** toda chave autorizada coletada tem identificação (comentário) cujo trecho após o último `@` é igual ao emissor declarado em `chaves_ssh.emitidas_por` (por exemplo, `platform@metacortex-platform` para o emissor `metacortex-platform`), e não há nenhuma chave autorizada sem identificação
- **ENTÃO** o veredito é `conforme`; um conjunto sem nenhuma chave autorizada também é `conforme`, pois não há chave que contrarie a regra

#### Scenario: chaves_ssh.emitidas_por — chave sem identificação compatível
- **QUANDO** pelo menos uma chave autorizada não tem identificação ou tem identificação cujo emissor difere do declarado
- **ENTÃO** o veredito é `desvio` com a severidade da regra, e o valor encontrado lista cada chave ofensora pela identificação ou fingerprint, sem expor o material completo da chave

#### Scenario: Escopo da regra de chaves
- **QUANDO** `chaves_ssh.emitidas_por` é avaliada
- **ENTÃO** ela considera as chaves autorizadas do usuário que estabeleceu a conexão, que é o conjunto que a coleta sem privilégio consegue ler, e o relatório declara esse escopo

### Requirement: Regra sem Fato Coletado é nao_verificado
Uma regra do baseline que referencia um fato que a coleta não produz (regra que a ferramenta não sabe avaliar, ou fato fora do inventário coletado) SHALL receber o veredito `nao_verificado` com um motivo que diga que a coleta não produz esse fato, e MUST NOT receber `conforme` em nenhuma hipótese.

#### Scenario: Fato que a coleta não produz
- **QUANDO** o baseline contém uma regra cujo fato não faz parte do que a coleta produz
- **ENTÃO** a entrada de conformidade dessa regra tem veredito `nao_verificado` e o motivo informa que a coleta não produz o fato referenciado, e a regra continua contando como uma entrada do relatório

#### Scenario: Fato não coletado nunca é conforme
- **QUANDO** qualquer regra não pode ser avaliada por falta do fato correspondente, seja por ele não ser produzido pela coleta ou por ter sido marcado como não lido
- **ENTÃO** o veredito nunca é `conforme` e nunca é `desvio`, e a distinção entre "não produzido pela coleta" e "não lido" aparece no motivo

### Requirement: Comparação Determinística
Dados o mesmo inventário coletado e o mesmo baseline, a comparação SHALL produzir o mesmo veredito para cada regra ao longo de execuções repetidas.

#### Scenario: Mesmas entradas, mesmos vereditos
- **QUANDO** o motor de conformidade é executado duas vezes com um inventário coletado idêntico e um baseline idêntico
- **ENTÃO** o veredito e a severidade de cada regra são idênticos entre as duas execuções

### Requirement: Saída de Relatório em JSON
O sistema SHALL emitir um relatório JSON adequado ao consumo automatizado pelo Roster, no formato do enunciado: um objeto com as chaves `host` (`endereco`, `hostname`, `coletado_em`), `inventario` (`so` com `distribuicao` e `versao`; `kernel` com `versao`; `servicos`, lista de `nome`, `tipo` e `estado`; `swap` com `habilitado` e `tamanho`; `portas_em_escuta`, lista de `porta`, `bind` e `processo`; `chaves_ssh`, lista de `identificacao`; `ssh` com `login_de_root`; `ntp` com `sincronizado` e `mecanismo`), `conformidade` (lista com uma entrada por regra: `regra`, `esperado`, `encontrado`, `veredito`, e `severidade` somente em `desvio`, `motivo` somente em `nao_verificado`) e `resumo` (`conforme`, `desvio`, `nao_verificado` e `por_severidade` com `critico`, `alto` e `medio`). Um campo do inventário que a coleta não leu SHALL ser `null`, e MUST NOT ser representado por `[]`, `0`, `false` ou `""`; o motivo SHALL constar na entrada de `conformidade` da regra correspondente, com `encontrado` igual a `null`.

#### Scenario: O JSON é legível por máquina e segue o formato
- **QUANDO** uma execução termina (com ou sem desvios)
- **ENTÃO** a ferramenta emite um documento JSON, parseável por um parser JSON padrão, com exatamente as chaves de topo `host`, `inventario`, `conformidade` e `resumo`, cada uma com a estrutura acima

#### Scenario: Projeção do inventário
- **QUANDO** a coleta leu todos os fatos
- **ENTÃO** `servicos[].nome` traz o nome da unidade sem o sufixo, `servicos[].tipo` é `service` ou `socket` e `servicos[].estado` é o estado ativo; `swap.tamanho` é um inteiro em bytes; `chaves_ssh[].identificacao` é o comentário da chave (ou o fingerprint, se não há comentário); `ssh.login_de_root` é booleano; `ntp.mecanismo` é o nome do mecanismo ou `"nenhum"`

#### Scenario: Swap desabilitado é lido, não nulo
- **QUANDO** o host não tem swap
- **ENTÃO** o inventário traz `swap.habilitado` igual a `false` e `swap.tamanho` igual a `0`, distintos de `null`

#### Scenario: Campo não lido é null com motivo na conformidade
- **QUANDO** a coleta não conseguiu ler o fato `ssh.login_de_root` (por privilégio insuficiente)
- **ENTÃO** `inventario.ssh.login_de_root` é `null` e a entrada `ssh.login_de_root` de `conformidade` tem `veredito` `nao_verificado`, `encontrado` `null` e `motivo` preenchido, sem chave `severidade`

#### Scenario: Severidade só em desvio e motivo só em nao_verificado
- **QUANDO** o relatório contém entradas `conforme`, `desvio` e `nao_verificado`
- **ENTÃO** somente as entradas `desvio` têm a chave `severidade`, e somente as `nao_verificado` têm a chave `motivo`

#### Scenario: Resumo por severidade conta apenas desvios
- **QUANDO** o relatório tem, por exemplo, dois desvios `critico`, um `alto` e nenhum `medio`
- **ENTÃO** `resumo` traz `desvio` igual a `3`, e `por_severidade` igual a `{"critico": 2, "alto": 1, "medio": 0}`, e as contagens de `conforme`, `desvio` e `nao_verificado` somam o número de regras

### Requirement: Saída de Relatório em Markdown
O sistema SHALL emitir um relatório Markdown adequado à leitura humana pelo plantão, que mostra primeiro o que exige ação: o título `# Inventário — <hostname> (<endereco>)`; a linha `Coletado em <data> · baseline v<versao>`; a seção `## Desvios`, uma tabela `Severidade | Regra | Esperado | Encontrado` ordenada por severidade decrescente (crítico, alto, médio), preservando a ordem do baseline dentro do mesmo nível; a seção `## Não verificado`, uma tabela `Regra | Motivo`; e a seção `## Conforme`, com os nomes das regras conformes separados por ` · `. O inventário completo SHALL ficar somente no relatório JSON.

#### Scenario: Estrutura do Markdown
- **QUANDO** uma execução termina (com ou sem desvios)
- **ENTÃO** o Markdown tem o título com hostname e endereço, a linha com a data da coleta e a versão do baseline, e as três seções `Desvios`, `Não verificado` e `Conforme`, nessa ordem

#### Scenario: Desvios ordenados por severidade
- **QUANDO** há desvios `medio`, `critico` e `alto`
- **ENTÃO** a tabela de desvios lista primeiro os `critico`, depois os `alto` e por fim os `medio`

#### Scenario: Seção sem itens
- **QUANDO** não há nenhuma regra em uma das três categorias
- **ENTÃO** a seção correspondente continua presente e indica que não há itens, em vez de ser omitida

#### Scenario: Conforme como lista simples
- **QUANDO** há regras conformes
- **ENTÃO** a seção `Conforme` lista os nomes das regras separados por ` · `, sem tabela

### Requirement: Destino das Saídas
O sistema SHALL escrever o relatório em stdout por padrão e SHALL permitir gravá-lo em arquivo por meio de flags. `--formato {markdown,json}` escolhe o relatório enviado ao stdout (padrão: `markdown`); `--saida-json <arquivo>` e `--saida-markdown <arquivo>` gravam o respectivo relatório em arquivo, e podem ser usadas juntas para obter os dois formatos numa única execução. Mensagens de erro e de diagnóstico SHALL ir somente para o stderr, de modo que o stdout contenha apenas o relatório. Os relatórios MUST NOT conter o caminho nem o conteúdo da chave privada. Se um arquivo de saída não puder ser gravado, a execução SHALL falhar com código `2`.

#### Scenario: Padrão é stdout
- **QUANDO** a ferramenta é executada sem `--formato` e sem flags de arquivo
- **ENTÃO** o relatório Markdown é escrito no stdout e nenhum arquivo é criado

#### Scenario: Escolha do formato em stdout
- **QUANDO** a ferramenta é executada com `--formato json`
- **ENTÃO** o stdout contém somente o documento JSON, parseável por um parser JSON padrão

#### Scenario: Gravação em arquivo
- **QUANDO** a ferramenta é executada com `--saida-json` e/ou `--saida-markdown`
- **ENTÃO** o relatório correspondente é gravado no arquivo indicado, e os dois formatos podem ser obtidos numa única execução

#### Scenario: Arquivo de saída não gravável
- **QUANDO** o caminho de um arquivo de saída não pode ser gravado
- **ENTÃO** a ferramenta sai com código `2` e uma mensagem no stderr que diz que o arquivo de saída não pôde ser gravado

#### Scenario: Relatórios não expõem a chave
- **QUANDO** qualquer relatório (stdout ou arquivo) é gerado
- **ENTÃO** ele não contém o conteúdo nem o caminho da chave privada

### Requirement: Contrato do Código de Saída do Processo
O sistema SHALL sair com o código `0` quando o host tem zero entradas `desvio`, sair com o código `1` quando o host tem pelo menos uma entrada `desvio`, e sair com o código `2` quando a execução falhou (host inalcançável, host desconhecido, chave rejeitada, baseline inválido, arquivo de saída não gravável ou invocação incorreta). Entradas `nao_verificado` sozinhas MUST NOT provocar o código de saída `1`.

#### Scenario: Host totalmente conforme sai com zero
- **QUANDO** toda regra do baseline é avaliada como `conforme` ou `nao_verificado`, sem nenhum `desvio`
- **ENTÃO** o processo sai com o código `0`

#### Scenario: Qualquer desvio sai com um
- **QUANDO** pelo menos uma regra do baseline é avaliada como `desvio`
- **ENTÃO** o processo sai com o código `1`

#### Scenario: Falha de execução sai com dois
- **QUANDO** o host está inalcançável, o host é desconhecido, a chave é rejeitada, o baseline é inválido, um arquivo de saída não pode ser gravado ou a ferramenta é invocada incorretamente
- **ENTÃO** o processo sai com o código `2`, e isso nunca é reportado da mesma forma que um host conforme

### Requirement: Mensagem de Falha de Execução
Quando o processo sai com o código de falha de execução, a ferramenta SHALL imprimir, no stderr, uma mensagem que diga o que ocorreu em linguagem simples, sem stack trace cru nem texto interno de exceção, e sem expor o conteúdo da chave privada.

#### Scenario: Motivo claro da falha
- **QUANDO** a execução falha por qualquer motivo (host inalcançável, host desconhecido, chave rejeitada, baseline inválido, arquivo de saída não gravável, uso incorreto)
- **ENTÃO** a mensagem impressa nomeia qual desses ocorreu, em linguagem utilizável por um operador, sem stack trace cru e sem conteúdo da chave privada
