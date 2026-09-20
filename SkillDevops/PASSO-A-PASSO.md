# Passo a passo — Fase A (rodar na sua máquina)

Os comandos servem para PowerShell e bash; onde há diferença, as duas formas aparecem. Rode tudo
a partir da pasta `ticket-02-triagem-no-cluster/`.

## 0. Pré-requisitos

- Docker Desktop (ou Docker Engine) rodando
- `kind` e `kubectl` no PATH
- Node.js (para o `npx` do mcp-server-kubernetes)
- Python 3
- Claude Code (`claude --version`)

## 1. Cluster local

```bash
kind create cluster --name metacortex-lab
kubectl config use-context kind-metacortex-lab
kubectl get nodes
```

As imagens dos chamados são públicas e servem x86_64 e ARM, então nada precisa ser construído.

## 2. Subir os três chamados, com o defeito, e esperar

```bash
kubectl apply -f ambiente/
```

**Espere 5 minutos** antes de triar. Os sintomas precisam de tempo para aparecer (reinícios,
back-off). Não corrija nada: o cluster fica nesse estado até o fim do ticket.

Guarde a foto do estado inicial:

```bash
python fluxo-de-origem/k.py --chamado 0 inicio "foto do estado inicial do cluster"
python fluxo-de-origem/k.py --chamado 0 get pods -A -o wide
python fluxo-de-origem/k.py --chamado 0 get deploy,svc,endpoints -n nyx-prod
python fluxo-de-origem/k.py --chamado 0 get deploy,svc,endpoints -n orion-stg
python fluxo-de-origem/k.py --chamado 0 get deploy,svc,endpoints -n nyx-stg
```

## 3. Registrar o MCP em modo não destrutivo (escopo do usuário)

bash / macOS / Linux:
```bash
claude mcp add kubernetes --scope user -e ALLOW_ONLY_NON_DESTRUCTIVE_TOOLS=true -- npx mcp-server-kubernetes
```

Windows (PowerShell), onde o `npx` precisa do `cmd /c`:
```powershell
claude mcp add kubernetes --scope user -e ALLOW_ONLY_NON_DESTRUCTIVE_TOOLS=true -- cmd /c npx mcp-server-kubernetes
```

Confira com `claude mcp list`: o servidor `kubernetes` deve aparecer como conectado.

> O **modo não destrutivo não é somente leitura**. Ele bloqueia delete, mas mantém `kubectl_apply`,
> `kubectl_create`, `kubectl_patch`, `kubectl_scale`, `kubectl_rollout` e `exec_in_pod`. Verificado
> no código-fonte do servidor (commit `0340ab6`). Ele fica assim de propósito: o ticket exige que a
> triagem não escreva "nem quando o agente tem permissão", e o harness conta toda tentativa de escrita.

## 4. Os dois laboratórios (a única diferença entre eles é a skill)

```bash
mkdir -p lab-sem-skills lab-com-skills/.claude/skills
cp -r ../ticket-01-padrao-de-manifests/skill/metacortex-manifests lab-com-skills/.claude/skills/
```
Windows:
```powershell
New-Item -ItemType Directory -Force lab-sem-skills, lab-com-skills\.claude\skills | Out-Null
Copy-Item -Recurse ..\ticket-01-padrao-de-manifests\skill\metacortex-manifests lab-com-skills\.claude\skills\
```

**Importante:** não deixe essas skills em `~/.claude/skills` (escopo do usuário). Se estiverem lá,
elas vazam para o `lab-sem-skills` e a comparação perde o sentido. A skill de triagem só entra no
`lab-com-skills` na fase C.

## 5. Fase A1 — triagem manual com o `k.py` (é daqui que a skill nasce)

Para cada chamado, trie **só pelo cluster**, partindo do sintoma que o cliente declarou. Use o
`k.py` no lugar do `kubectl`: ele grava tudo e recusa escrita. A cada passo, registre **por que**
escolheu o próximo comando; isso é o método que a skill vai empacotar. Quando achar a causa,
registre e **pare**.

```bash
python fluxo-de-origem/k.py --chamado 1 inicio "cliente nyx: a API do kube-news em nyx-prod reinicia sozinha"
python fluxo-de-origem/k.py --chamado 1 nota "começo por onde? por quê?"
python fluxo-de-origem/k.py --chamado 1 get pods -n nyx-prod
#   ... (describe, logs --previous, get events --sort-by=.lastTimestamp, get endpoints, etc.)
python fluxo-de-origem/k.py --chamado 1 causa "<camada> — <causa> — <evidência>"
python fluxo-de-origem/k.py --chamado 1 fim
```

Faça o mesmo com:
- `--chamado 2`: "cliente orion: a loja do fake-shop em orion-stg parou depois de uma publicação
  do Loom; a tag foi anunciada, o deploy foi aplicado, mas o pod nunca trocou";
- `--chamado 3`: "cliente nyx: o kube-news em nyx-stg responde 503 para quem chama de fora".

Anote também **o que está funcionando ao lado** (banco de pé, outras réplicas, etc.). O ticket
diz que é isso que separa triagem de chute. Honestidade de método: você já viu os YAML no
enunciado. Trie pelo cluster mesmo assim, e registre numa nota se algum passo foi guiado por esse
conhecimento prévio.

## 6. Fase A2 — como o agente tria SEM método (linha de base)

```bash
cd medicao
python rodar_sessao.py uma --lab ../lab-sem-skills --rotulo base-chamado-1 --prompt "Chamado do cliente nyx: a API do kube-news em nyx-prod reinicia sozinha. Faz a triagem e me diz a causa."
python rodar_sessao.py uma --lab ../lab-sem-skills --rotulo base-chamado-2 --prompt "Chamado do cliente orion: a loja do fake-shop em orion-stg parou depois de uma publicação do Loom. Faz a triagem e me diz a causa."
python rodar_sessao.py uma --lab ../lab-sem-skills --rotulo base-chamado-3 --prompt "Chamado do cliente nyx: o kube-news em nyx-stg responde 503 para quem chama de fora. Faz a triagem e me diz a causa."
```

Cada execução grava em `medicao/resultados/`:
- `.jsonl`: o transcript cru;
- `.json`: o resumo (sequência de ferramentas, tentativas de escrita, custo, tempo, turnos,
  tokens);
- `.md`: a resposta final.

Confira no primeiro `.json` se `custo_usd` e `sequencia` vieram preenchidos. Se vierem vazios, a
sua versão do CLI mudou o formato do stream-json; me mande o `.jsonl` e eu ajusto o parser.

## 7. O que me mandar para a fase B

1. `fluxo-de-origem/logs/` inteiro (chamado-0 a chamado-3);
2. `medicao/resultados/` (os três `base-chamado-*`);
3. a saída de `kind version`, `kubectl version`, `claude --version` e `claude mcp list`.

Com isso eu escrevo a skill de triagem a partir do **seu** fluxo e do que o agente sem método fez
de diferente.
