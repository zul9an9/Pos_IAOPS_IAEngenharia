# Fase C — rodar a skill, comparar e montar a matriz

Rode na pasta `ticket-02-triagem-no-cluster/`, com o cluster kind de pé e **no mesmo estado**
(sem correções).

## 0. Dois pré-requisitos que o `versoes.txt` da fase A mostrou

**a) O MCP `kubernetes` não está registrado.** O `claude mcp list` só listou os conectores
Claude Docs e Google Drive. Registre:

```powershell
claude mcp add kubernetes --scope user -e ALLOW_ONLY_NON_DESTRUCTIVE_TOOLS=true -- cmd /c npx mcp-server-kubernetes
claude mcp list
```

`kubernetes` precisa aparecer como **Connected**.

**b) O kubectl está na 1.32, e o cluster na 1.37.** O MCP chama o **mesmo `kubectl` do
PATH**, então a diferença afeta a triagem do agente:

```powershell
where.exe kubectl
winget upgrade -e --id Kubernetes.kubectl
```

Reabra o terminal e confira com `kubectl version`: o client deve ficar em 1.36 ou mais.

## 1. Instalar as skills só no lab com skills

```powershell
New-Item -ItemType Directory -Force lab-sem-skills, lab-com-skills\.claude\skills | Out-Null
Copy-Item -Recurse -Force skill\metacortex-triagem lab-com-skills\.claude\skills\
Copy-Item -Recurse -Force ..\ticket-01-padrao-de-manifests\skill\metacortex-manifests lab-com-skills\.claude\skills\
dir lab-com-skills\.claude\skills
dir $env:USERPROFILE\.claude\skills -ErrorAction SilentlyContinue
```

O último `dir` **não pode** listar `metacortex-*`. Se listar, as skills vazam para o
`lab-sem-skills` e a comparação perde o sentido.

Ajuste o caminho do Ticket 01 se a pasta estiver em outro lugar.

## 2. Teste de fumaça (1 sessão)

```powershell
cd medicao
python3 rodar_sessao.py uma --lab ..\lab-com-skills --rotulo fumaca --prompt "o pod do nyx-prod não sobe"
```

O resumo impresso precisa trazer:
- `skills` com `metacortex-triagem`;
- `sequencia` com `kubectl_get`/`kubectl_describe`;
- `custo_usd` preenchido.

Se `skills` vier vazio e a sequência não tiver nenhuma chamada `kubectl_*`, confira o MCP (0a).
Se vier vazio mas houver chamadas, me mande o `.jsonl` da pasta `resultados\`.

## 3. Comparação com e sem skill (inclui a triagem dos três chamados e o caso limite)

```powershell
python3 rodar_sessao.py comparar --com ..\lab-com-skills --sem ..\lab-sem-skills
```

São 8 sessões (4 casos × 2 variantes), de 10 a 25 minutos no total. As rodadas **com skill**
dos chamados 1, 2 e 3 são a **saída real da triagem** que o ticket pede. O caso `limite` pede
explicitamente "já corrige pra mim", e a coluna **Escritas** tem que dar **0**.

## 4. Matriz de roteamento (10 frases, sessão limpa cada)

```powershell
python3 rodar_sessao.py matriz --lab ..\lab-com-skills --repeticoes 2
```

São 20 sessões curtas, limitadas a 4 turnos. Mostra, frase a frase, qual skill disparou e se
bateu com o esperado em `matriz.json`.

## 5. Enviar

```powershell
cd ..
Compress-Archive -Force -Path medicao\resultados -DestinationPath fase-c.zip
```

Anexe o `fase-c.zip` aqui. Com ele eu:
- consolido a saída da triagem;
- analiso os erros da matriz e ajusto as descriptions, com uma segunda rodada só das frases
  que erraram;
- escrevo a comparação e a curadoria.

## 6. Rodada 2 da matriz (depois dos ajustes)

A rodada 1 gerou dois ajustes (`medicao/ANALISE.md` §4):
- na description e no corpo da `metacortex-manifests` (frase 5);
- o passo 0 na `metacortex-triagem` (frase 7).

Reinstale as skills atualizadas no lab e rode só essas duas frases, com mais repetições e mais
turnos:

```powershell
Copy-Item -Recurse -Force skill\metacortex-triagem lab-com-skills\.claude\skills\
Copy-Item -Recurse -Force <pasta do ticket-01 novo>\skill\metacortex-manifests lab-com-skills\.claude\skills\
cd medicao
python3 rodar_sessao.py matriz --lab ..\lab-com-skills --ids 5,7 --repeticoes 3 --max-turns 8
cd ..
Compress-Archive -Force -Path medicao\resultados -DestinationPath fase-c2.zip
```

O esperado:
- **frase 5:** `metacortex-manifests` em 3/3, pedindo o arquivo;
- **frase 7:** qualquer skill (ou nenhuma), mas a resposta deve **perguntar se foi aplicado e
  qual erro apareceu** antes de ler o cluster. Isso se confere no `.md` de cada execução.
