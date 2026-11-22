# ADR-0002 — Cliente `ssh` do sistema via subprocesso, com a chave passada só como caminho

| | |
|---|---|
| **Status** | Aceito |
| **Data da decisão** | 2026-09-20 (change `vm-inventory-drift`) |
| **Origem** | `design.md` D2; brainstorm D2 e D8 |
| **Relacionados** | [ADR-0001](ADR-0001-python-somente-biblioteca-padrao.md), [ADR-0003](ADR-0003-sessao-ssh-unica-script-posix-via-stdin.md), [ADR-0008](ADR-0008-identitiesonly-yes.md) |

## Contexto

A chave privada é uma **credencial de cliente/produção**. O requisito do ticket é que o seu
**conteúdo** nunca apareça em stdout, stderr, arquivo de saída, log ou mensagem de erro, em nenhum
caminho de falha. Tudo que aumente a superfície em que a chave é manipulada (parsear, manter em
memória, passar por uma biblioteca) aumenta o risco sem benefício de comportamento, já que o cliente
`ssh` do sistema já faz isso com segurança.

## Decisão

1. A ferramenta **nunca abre nem lê** o arquivo da chave privada. Ela monta o `argv` do binário
   `ssh` do sistema e o executa como **subprocesso**:

   ```
   ssh -i <caminho> -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=<n> \
       -o StrictHostKeyChecking=<política> <usuario>@<host> sh -s
   ```

   O cliente `ssh` faz todo o tratamento de chave e de protocolo no próprio processo. A ferramenta
   pode fazer `stat` no caminho, para dizer "arquivo não encontrado" com clareza, mas nunca o abre.
   **Nunca** é passado `-v`.
2. **Política de `StrictHostKeyChecking`:** o padrão é `yes`. Em `BatchMode` o `ssh` não pode
   perguntar nada, então host desconhecido é **recusado**, e a execução termina com exit 2 e uma
   mensagem própria. Afrouxar exige a flag explícita `--aceitar-host-novo`, que mapeia para
   `accept-new`: aceita apenas hosts **novos**, e chave de host **alterada** continua recusada. A
   ferramenta **nunca** usa `StrictHostKeyChecking=no` e **nunca** usa `UserKnownHostsFile=/dev/null`:
   o `known_hosts` padrão do operador é sempre respeitado.
3. O **stderr do subprocesso é capturado e reescrito** em categorias fixas de falha (inalcançável,
   chave do host, autenticação recusada, outra), e nunca repassado cru.
4. O **caminho** da chave pode aparecer nas mensagens de erro do stderr da própria ferramenta (por
   exemplo, "chave privada não encontrada em `<caminho>`"), porque é um dado que o operador digitou,
   não é segredo, e permite diagnosticar erro de digitação ou de permissão. **Não** pode aparecer
   nos relatórios JSON e Markdown, que circulam fora da máquina do operador e revelariam a
   estrutura de diretórios dele.

## Alternativas consideradas

| Alternativa | Por que foi rejeitada |
|---|---|
| **Biblioteca SSH em processo** (`paramiko` ou similar) | Ver ADR-0001. Além disso, com uma biblioteca, as **nossas** mensagens de exceção em Python poderiam embutir estado relacionado à chave (por exemplo, um erro de decriptação com bytes da chave), a menos que fossem cuidadosamente higienizadas. A fronteira do subprocesso torna essa classe de vazamento estruturalmente mais difícil, porque a chave nunca entra no nosso espaço de endereçamento |
| **`StrictHostKeyChecking=no`** ou `UserKnownHostsFile=/dev/null` | Desligaria a verificação de identidade do host, abrindo a porta para interceptação |

## Consequências

**Positivas**

- O requisito de confidencialidade se reduz a: o stderr do subprocesso é reclassificado, e o
  conteúdo da chave nunca é visto pelo nosso processo.
- A ferramenta herda `known_hosts` e a configuração do cliente `ssh` do operador.

**Negativas e riscos aceitos**

- É preciso separar o stderr do cliente do erro do comando remoto e fixar `BatchMode=yes` e
  `ConnectTimeout`, para não travar pedindo senha.
- **Classificar o desfecho do `ssh` é frágil** entre versões e locales do OpenSSH. Mitigação: o
  **status de saída vem primeiro** (255 para falhas de conexão ou autenticação), o texto é apoio
  para as subcategorias, e há sempre uma categoria "outra falha", para que um caso não reconhecido
  ainda saia com exit 2 e uma mensagem decente.
- Depende de o cliente `ssh` estar no `PATH` (a ausência é falha de execução).
- Há um teto adicional de 120 s para a sessão inteira, porque o `ConnectTimeout` só cobre o
  estabelecimento da conexão.

## Verificação

- `tests/test_transport.py`: `test_chave_so_como_caminho_e_sem_flags_proibidas`,
  `test_status_de_saida_vem_antes_do_texto`, `test_padrao_e_strict_yes`,
  `test_flag_usa_accept_new_e_nunca_no`, `test_host_alterado_recusado_mesmo_com_a_flag`.
- `tests/test_vazamento.py`: `test_conteudo_da_chave_nunca_aparece_em_lugar_nenhum`,
  `test_a_ferramenta_nunca_abre_o_arquivo_da_chave`, `test_o_argv_carrega_o_caminho_e_nunca_o_conteudo`,
  `test_caminho_da_chave_nunca_aparece_em_relatorios`.
- Laboratório: host inalcançável e chave recusada saem com exit 2 (`evidencias-aceite.txt` §4 e §4b).
