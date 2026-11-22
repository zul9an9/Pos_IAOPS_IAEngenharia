# ADR-0001 — Python 3 com HTML servido localmente

| | |
|---|---|
| **Status** | Aceito |
| **Data da decisão** | 2026-09-27 (change `add-cluster-dashboard`) |
| **Origem** | `design.md` D1; `CURADORIA.md` §3.1. Constava do prompt do `/opsx:propose` como decisão já tomada pelo autor (D1) |
| **Relacionados** | [ADR-0002](ADR-0002-cliente-oficial-do-kubernetes.md), [ADR-0005](ADR-0005-somente-leitura-em-tres-camadas.md) |

## Contexto

O painel precisa mostrar quatro tabelas largas e filtráveis (pods com fase, prontos, reinícios e
motivo; deployments; services; eventos) mais os namespaces, numa ferramenta de **uma pessoa**, que
roda na máquina de quem opera durante um chamado. Python é a linguagem que o time já usa nos outros
tickets, e tem o cliente oficial do Kubernetes com a autenticação de kubeconfig completa (ADR-0002).

## Decisão

1. **Python 3 (3.12+)**, com o HTML **gerado no servidor**, servido por `http.server` da biblioteca
   padrão, **ligado fixo em `127.0.0.1`**. O endereço não é configurável: só a porta é parâmetro.
2. O servidor aceita **só GET**. Qualquer outro método recebe `405`.
3. **Todo texto externo** passa por `html.escape(..., quote=True)`, que cobre corpo e atributos.
   As mensagens de evento são texto controlado por terceiros. O escape acontece num **único ponto**:
   o renderizador recebe só texto cru e é a única parte que monta HTML.
4. Sem build de frontend. O único script da página é o de busca, estático.

## Alternativas consideradas

| Alternativa | O que se ganha | Por que foi rejeitada |
|---|---|---|
| **Go** | Binário único, fácil de distribuir. O `client-go` é equivalente em capacidade | Acrescenta uma segunda linguagem e toolchain para uma ferramenta de uma pessoa, sem ganho de comportamento |
| **TUI no terminal** | Abre mais rápido e dispensa navegador | Quatro tabelas largas e filtráveis mais eventos cabem mal numa largura fixa, e uma tela de terminal não vira anexo de chamado com a mesma facilidade |

## Consequências

**Positivas**

- Tabelas largas cabem no navegador que já está aberto, e a página pode ser capturada e colada no
  chamado.
- Sem build de frontend e sem dependência de servidor web além da biblioteca padrão.
- O servidor local é pequeno o bastante para a garantia "só `127.0.0.1`, só GET" ser auditável.

**Negativas e riscos aceitos**

- **Distribuição:** exige Python 3.12+ e um venv, sem binário único. O empacotamento ficou adiado
  (PRD, Q2).
- Não há autenticação do próprio painel. A fronteira de confiança é "quem tem shell nesta máquina já
  tem o kubeconfig", e o painel não cria uma fronteira nova.

## Verificação

- `tests/test_servidor.py`: `test_escuta_somente_em_127_0_0_1`, `test_endereco_nao_e_configuravel`,
  `test_conexao_por_outra_interface_e_recusada`, `test_metodos_que_nao_sao_get_recebem_405_sem_coleta`.
- `tests/test_render.py`: `test_mensagem_de_evento_com_script_sai_escapada`,
  `test_aspas_em_atributo_nao_encerram_o_atributo`, `test_namespace_digitado_e_escapado_ao_reapresentar`.
- Laboratório (registro 8.10): `netstat` mostra `127.0.0.1:8765`, e a conexão ao IP da rede local é
  recusada com `ConnectionRefusedError`.
