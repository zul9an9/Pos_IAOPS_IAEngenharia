# ADR-0004 — A comparação com o baseline acontece localmente, nunca no host

| | |
|---|---|
| **Status** | Aceito |
| **Data da decisão** | 2026-09-20 (change `vm-inventory-drift`) |
| **Origem** | `design.md` D4; brainstorm D5 |
| **Relacionados** | [ADR-0003](ADR-0003-sessao-ssh-unica-script-posix-via-stdin.md), [ADR-0007](ADR-0007-contrato-de-dados-baseline-comparacao-e-saidas.md) |

## Contexto

O host é a fonte dos **fatos**, e a plataforma é a fonte do **padrão** (o baseline). Misturar as
duas coisas no host faria a ferramenta confiar em algo já julgado por ele, e exigiria levar o
baseline até lá. A invariante de **só leitura** não pode ser violada por uma evolução futura da
lógica de comparação.

## Decisão

A única função do script remoto é responder "o que é verdade neste host, agora, até onde um usuário
sem privilégio consegue ver". O **baseline nunca é enviado ao host nem avaliado nele**. A comparação
roda inteiramente no lado local (`compliance.py`), que só lê o objeto `Inventario` já coletado e
**nunca** volta a falar com o host. Mudanças na lógica de comparação nunca tocam o script remoto.

## Alternativas consideradas

| Alternativa | Por que foi rejeitada |
|---|---|
| **Avaliar contra o baseline remotamente** (subir o baseline e rodar a comparação num script remoto) | Exigiria gravar o baseline no host (viola a só-leitura) ou enviá-lo por pipe para uma **segunda passagem remota** (viola a decisão de conexão única e cria uma segunda coisa que pode ficar defasada entre execuções). Também faria a ferramenta confiar no que o host devolve já julgado |

## Consequências

**Positivas**

- O host é mera fonte de fatos, e a ferramenta (informada pelo baseline) é a única fonte do que é
  "correto".
- A comparação é **determinística** e testável sem host: mesmo inventário e mesmo baseline dão o
  mesmo veredito.
- A evolução do motor de comparação não afeta a superfície remota nem a garantia de só leitura.

**Negativas e riscos aceitos**

- O coletor precisa trazer valores crus suficientes para toda regra do baseline (por exemplo, o
  endereço de vínculo e o processo dono de cada porta, e não só o número). Um fato que a coleta não
  produz torna a regra `nao_verificado` (ADR-0006).

## Verificação

- `tests/test_compliance.py::ComparacaoLocalTest` (tarefa 6.4): com um dublê de transporte, o teste
  **falha** se a etapa de conformidade tentar falar com o host.
- `tests/test_compliance.py::DeterminismoTest` (tarefa 6.3).
