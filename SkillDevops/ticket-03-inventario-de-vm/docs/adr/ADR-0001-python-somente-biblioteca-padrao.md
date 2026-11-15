# ADR-0001 — Python 3, somente biblioteca padrão

| | |
|---|---|
| **Status** | Aceito |
| **Data da decisão** | 2026-09-20 (change `vm-inventory-drift`) |
| **Origem** | `design.md` D1; brainstorm D1 |
| **Relacionados** | [ADR-0002](ADR-0002-cliente-ssh-do-sistema-chave-so-caminho.md), [ADR-0005](ADR-0005-parser-yaml-minimo-e-versao-do-baseline.md) |

## Contexto

O `vminv` é uma CLI pontual e de baixo tráfego, que roda na máquina de quem opera contra uma VM por
invocação. A equipe de infraestrutura que a mantém é **só Python**. A fatia 1 não tem perfil de
desempenho que justifique uma linguagem compilada: o gargalo é I/O de rede contra um host, não CPU.
Além disso, a ferramenta manipula, indiretamente, uma credencial de cliente/produção (a chave
privada), e qualquer dependência de terceiros nesse caminho é superfície de risco.

## Decisão

Implementar em **Python 3, usando somente a biblioteca padrão** (mais o binário `ssh` do sistema,
ver ADR-0002). Não há `requirements.txt`. O requisito é Python 3.10+.

## Alternativas consideradas

| Alternativa | Por que foi rejeitada |
|---|---|
| **Go** | Adiciona uma segunda linguagem e uma etapa de compilação e release a uma equipe que não constrói nem distribui binários Go, para uma ferramenta cujo gargalo não é CPU. A vantagem do binário único não compensa |
| **Python + `paramiko`** | (1) Adiciona uma dependência de terceiros, e sua dependência transitiva de criptografia, a um caminho sensível de credencial. (2) Faz os bytes da chave privada serem parseados e mantidos pelo nosso próprio processo, em vez de entregues, como caminho, ao binário `ssh` do sistema, que é bem auditado. Também exigiria um `pip install` na máquina de quem opera |
| **Shell puro** | Começa simples e degrada rápido na formatação do JSON e no tratamento de erro (alternativa levantada no brainstorm) |

## Consequências

**Positivas**

- Zero dependências novas de runtime além da stdlib e do `ssh`: nada para instalar, atualizar ou
  auditar.
- A equipe mantém a ferramenta na linguagem que já domina.

**Negativas e riscos aceitos**

- Sem biblioteca SSH em processo, a ferramenta depende do cliente `ssh` do SO estar no `PATH` e
  precisa classificar o desfecho do subprocesso (ver ADR-0002).
- Sem PyYAML, a leitura do baseline exige um parser próprio, com os custos descritos no ADR-0005.
- Distribuição: exige Python 3.10+ na máquina do operador, sem binário único.

## Verificação

- `tests/test_transport.py::test_nenhuma_biblioteca_ssh_importada_pelo_pacote`.
- Ausência de `requirements.txt` no projeto.
