# Ticket 02 — Triagem no cluster, e duas skills disputando o mesmo pedido

**Status:** concluído. Fases A (fluxo manual), B (skill), C (triagem, comparação e matriz em
duas rodadas) e D (curadoria).

## Resultado em uma tabela

| Pedido do ticket | Resultado | Onde |
|---|---|---|
| Triagem dos 3 chamados, com a causa | 3/3 causas certas, iguais às da triagem manual, com 6 a 7 chamadas de leitura cada | `execucoes/` |
| Comparação com × sem skill | 4/4 × 2/4 causas · US$ 0,58 × 1,28 · 127 s × 284 s · 26 × 80 chamadas · **0 × 8 escritas** | `medicao/ANALISE.md` §1–3 |
| Matriz de roteamento | Rodada 1: 19/20, sem atropelo entre as skills; frases 5 (mal formulada) e 7 (ambígua) geraram ajustes. Rodada 2: 3/3 nas duas, com o comportamento esperado. 0 escritas em 26 sessões | `medicao/ANALISE.md` §4 |
| Curadoria | o que o método fixou, o que ficou com o agente, como se garantiu que não escreve | `curadoria.md` |

| Fase | O quê | Estado | Saída |
|---|---|---|---|
| A1 | Subir o cluster e os 3 chamados; triar à mão com `k.py` (só leitura, tudo registrado) | ✅ | `fluxo-de-origem/logs/` |
| B | Escrever a skill a partir do fluxo | ✅ | `skill/metacortex-triagem/` |
| C1 | Rodar a skill nos 3 chamados (causa de cada um) | ✅ | `execucoes/` |
| C2 | Comparação com e sem skill (3 chamados + caso limite) | ✅ | `medicao/ANALISE.md`, `medicao/resultados-rodada1/` |
| C3 | Matriz de roteamento, rodada 1, e ajustes | ✅ | `medicao/ANALISE.md` §4 |
| C4 | Matriz, rodada 2 (frases 5 e 7) | ✅ | `medicao/ANALISE.md` §4, `medicao/resultados-rodada2/` |
| D | Curadoria | ✅ | `curadoria.md` |

## Ambiente do laboratório (e a triagem que veio antes da triagem)

Windows com Docker Desktop (WSL2), 8 GB de RAM na máquina, **kind v0.33.0** e Kubernetes
**v1.37.0**.

Subir o cluster foi, por si só, uma triagem em camadas:
1. O `kind create cluster` falhava em `wait-control-plane`. O primeiro suspeito foi memória:
   o Docker tinha cerca de 3,8 GB. O `.wslconfig` foi para 5 GB com swap, e **a falha
   continuou**.
2. O k3d subia os containers, mas o k3s morria. O **log do servidor** mostrou a causa real:
   `kubelet is configured to not run on a host using cgroup v1`. As versões recentes do
   Kubernetes recusam cgroup v1.
3. A correção foi `kernelCommandLine = cgroup_no_v1=all` no `.wslconfig`, mais `wsl --update`.
   O Docker passou a reportar `CgroupVersion 2`, e **o kind subiu em 16 segundos**.

O sintoma apontava para uma camada (memória) e a causa estava em outra (versão de cgroup do
kernel). O método que a skill empacota diz o mesmo: quem decide o caminho é a evidência, não o
sintoma declarado.

## Origem da skill

- **De qual fluxo nasceu.** Da triagem manual dos três chamados, feita no cluster com o `k.py`:
  um kubectl que recusa escrita e registra comando, saída e raciocínio. Os logs estão em
  `fluxo-de-origem/logs/`:
  - chamado 0 (foto inicial);
  - chamados 1, 2 e 3, cada um com sintoma, notas de raciocínio, comandos com saída, causa,
    "funcionando ao lado" e fim.
- **Como foi conduzida.** A triagem foi feita **em par**: o operador rodou os comandos e
  escreveu as conclusões, e o Claude, sem dar a causa, apontou que tipo de fonte consultar a
  cada passo. As notas de correção nos logs (texto de modelo gravado por engano e depois
  corrigido) foram mantidas.
- **O que o fluxo ensinou e virou método:**
  - sempre começar pelo estado dos pods e anotar o que está saudável ao lado;
  - escolher o ramo pela **assinatura**, não pelo sintoma: CrashLoop/OOMKilled leva à camada
    do container, ImagePullBackOff com 0 restarts à imagem, pods 1/1 com cliente sem acesso ao
    caminho do tráfego;
  - os três momentos de cruzar fontes:
    - motivo numa fonte e descarte da alternativa em outra (`describe` + `logs --previous`
      vazio);
    - fonte principal que perdeu a informação (eventos só com back-off → status do container);
    - defeito num vínculo entre objetos (seletor × rótulos);
  - parar quando houver camada, o quê e evidência.
- **O que a leitura do código do MCP acrescentou.** O `kubectl_get` em JSON **resume listas**
  e descarta READY, RESTARTS, rótulos e endpoints, exatamente os sinais que resolveram os três
  chamados. A skill obriga `output: wide` em listas e o objeto completo por nome para campos
  específicos.
- **Ferramenta.** Claude (claude.ai, Claude Opus 5) para conduzir a triagem, ler o código do
  mcp-server-kubernetes e escrever a skill, seguindo a anatomia do guia `skill-creator`
  (frontmatter, corpo curto, `references/` sob demanda).

## Estrutura

```
ticket-02-triagem-no-cluster/
├── README.md
├── PASSO-A-PASSO.md          # fase A
├── FASE-C.md                 # fase C (rodar, comparar, matriz)
├── ambiente/                 # os 3 chamados, verbatim do ticket
├── fluxo-de-origem/
│   ├── k.py                  # kubectl somente leitura que registra comando, saída e raciocínio
│   ├── logs/chamado-0..3.md  # a triagem manual
│   └── versoes.txt
├── skill/metacortex-triagem/
│   ├── SKILL.md
│   └── references/
│       ├── assinaturas.md    # assinatura → leitura → segunda fonte (com a origem de cada ramo)
│       └── mcp-leitura.md    # como chamar as ferramentas de leitura e o que o resumo JSON esconde
├── execucoes/                # saída real da triagem com a skill (3 chamados + limite)
├── curadoria.md
└── medicao/
    ├── ANALISE.md            # comparação, caso limite e matriz, com o que mudou
    ├── resultados-rodada1/   # transcripts (.jsonl), resumos (.json), respostas (.md), evidências do limite
    ├── resultados-rodada2/   # matriz, frases 5 e 7, depois dos ajustes
    ├── rodar_sessao.py       # sessões limpas do Claude Code + análise do transcript
    ├── matriz.json           # 10 frases, classe e roteamento aceito
    └── comparacao.json       # 3 chamados + caso limite, com critério objetivo de causa certa
```

## Achados até aqui

1. **"Modo não destrutivo" não é "somente leitura".** No código do servidor (commit
   `0340ab6`), esse modo remove só delete, uninstall, cleanup, node management e
   `kubectl_generic`. Ficam liberados `kubectl_apply`, `kubectl_create`, `kubectl_patch`,
   `kubectl_scale`, `kubectl_rollout` (incluindo `restart` e `undo`), helm install/upgrade,
   `port_forward` e **`exec_in_pod`**. Por isso o limite "triagem lê, nunca escreve" tem de vir
   do método, e a fase C mede isso no caso `limite`, com o agente tendo permissão real de
   escrita.
2. **O braço resume demais.** O `kubectl_get` em JSON devolve só nome e status calculado. Um
   Deployment sem réplica pronta nem traz `readyReplicas`. Sem saber disso, o agente não vê
   RESTARTS, `0/N` nem endpoints vazios.
3. **O MCP usa o `kubectl` do PATH.** A diferença de versão (client 1.32 × server 1.37) afeta
   a triagem do agente, e não só a manual.
4. **Endpoints está depreciado** (aviso no chamado 3). É irrelevante para a triagem de hoje,
   mas é a decisão que o Ticket 04 pede para registrar.
