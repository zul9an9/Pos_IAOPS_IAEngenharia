# Inventário — DESKTOP-ENKOORK (172.29.2.241)

Coletado em 2026-09-20T22:24:26Z · baseline v1

## Desvios

| Severidade | Regra | Esperado | Encontrado |
|---|---|---|---|
| critico | `swap.habilitado` | false | true |
| critico | `portas_em_escuta.somente_rede_interna` | [9100] | [{"enderecos": [], "porta": 9100}] |
| alto | `servicos.ativos` | ["ssh", "containerd", "node_exporter", "chrony"] | {"ativos": ["chrony.service", "ssh.service"], "ausentes_ou_inativos": ["containerd.service", "node_exporter.service"]} |

## Não verificado

| Regra | Motivo |
|---|---|
| `ssh.login_de_root` | fato 'ssh_login_root' não lido pela coleta: sshd -T falhou (privilégio insuficiente para ler a configuração efetiva) |

## Conforme

so.distribuicao · so.versao_minima · kernel.versao_minima · servicos.proibidos · portas_em_escuta.publicas_permitidas · chaves_ssh.emitidas_por · ntp.sincronizado
