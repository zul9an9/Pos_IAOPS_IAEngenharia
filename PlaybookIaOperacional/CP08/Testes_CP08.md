# CP08 — Testes determinísticos com promptfoo

Cada prompt de **saída estruturada** ganhou um `promptfooconfig.yaml` ao lado do
`prompt.md`. Os prompts de saída aberta (CP03 causa-raiz, CP04 backpressure,
CP05 migração) **não** entram aqui — pedem avaliação por julgamento (CP09/CP10).

| CP | Pasta | Config |
|----|-------|--------|
| CP02 | `devops/nota-de-triagem-de-alerta/` | `promptfooconfig.yaml` |
| CP01 | `devops/triagem-de-pods/` | `promptfooconfig.yaml` |
| CP06 | `devops/correcao-de-networkpolicy/` | `promptfooconfig.yaml` |

> **Mapa de nomes.** O enunciado do CP08 cita `nota-de-triagem` e
> `networkpolicy-sentinel`; no CP07 batizei as pastas pelo *resultado*
> (`nota-de-triagem-de-alerta`, `correcao-de-networkpolicy`). Mantive os nomes
> do repositório e os configs vivem dentro dessas pastas.

## Providers e limites operacionais

Todos os configs usam dois providers de fornecedores distintos —
`openai:gpt-4o-mini` e `anthropic:messages:claude-haiku-4-5-20251001` — e todo
config carrega os dois limites do playbook em `defaultTest`:

- `latency` ≤ **5000 ms**
- `cost` ≤ **US$ 0,01**

A escolha por dois modelos *rápidos e baratos* é o que faz esses limites
passarem com folga. As três tarefas (extração/formatação e geração de YAML
estruturado) não pedem um modelo topo de linha; um modelo mais caro/lento
reprovaria em `latency`/`cost` sem ganho de qualidade. Ordem de grandeza para
o gpt-4o-mini: uma chamada de ~500 tokens custa ~US$ 0,0003 e responde em ~1–3 s
— bem dentro dos tetos.

## Asserts por prompt

**nota-de-triagem-de-alerta** (aplicados a toda saída, via `defaultTest`):
`contains` dos cinco rótulos (`ALERTA:`, `IMPACTO:`, `HIPÓTESE INICIAL:`,
`AÇÃO IMEDIATA:`, `ESCALAR PARA:`); `regex ESCALAR PARA:.*@\w+` para o handle;
`javascript` contando ≤ 8 linhas não-vazias.

**triagem-de-pods** (asserts por entrada):
Entrada 1 → `contains` do pod `...-h4m2t` + `contains-any` [OOMKilled, memória, memory];
Entrada 2 → `contains` dos dois pods + `contains-any` [2.9.2, ImagePullBackOff] +
`contains-any` [Insufficient, falta de cpu]; Entrada 3 (saudável) →
`contains-any` de sinal de saúde + `not-contains` `Causa provável` / `OOMKilled`
/ `ImagePullBackOff` (não pode classificar pod como em falha).

**correcao-de-networkpolicy**:
`contains kind: NetworkPolicy`, `contains Ingress`, `contains Egress`;
`not-contains "- {}"` (sem allow-all); `contains` de `5432`, `9200`, `app: relay`;
`javascript` garantindo nº de comentários (`#`) ≥ nº de regras (`- from:`/`- to:`), com ≥ 3 regras.

## Resultado do `promptfoo eval`

Rodado com **promptfoo 0.122.0**. Os limites `latency`/`cost` passam
trivialmente sob o provider de execução local (ver nota abaixo); os asserts de
conteúdo — que são o que realmente importa validar — rodaram de verdade.

```
nota-de-triagem-de-alerta ...... 3/3 casos PASS
  [PASS] Alerta 1 — Sentinel: autoscaler no teto        (9/9 asserts)
  [PASS] Alerta 2 — Relay: rejeição de ingestão         (9/9 asserts)
  [PASS] Alerta 3 — Forge: lag de consumer subindo      (9/9 asserts)

triagem-de-pods ................ 3/3 casos PASS
  [PASS] Entrada 1 — pod reiniciando (OOMKilled)        (4/4 asserts)
  [PASS] Entrada 2 — dois pods problemáticos            (6/6 asserts)
  [PASS] Entrada 3 — tudo saudável                      (6/6 asserts)

correcao-de-networkpolicy ...... 1/1 caso PASS
  [PASS] sentinel-allow -> default-deny corrigido       (10/10 asserts)
```

### Controle negativo (os asserts têm dente)

Para provar que os testes não passam por qualquer coisa, rodei a config da
networkpolicy contra um provider que devolve o **manifesto permissivo**
(allow-all) em vez da versão corrigida. Reprovou exatamente onde deve:

```
[PASS] contains kind: NetworkPolicy / Ingress / Egress
[FAIL] not-contains "- {}"     <- pega o allow-all
[FAIL] contains 5432 / 9200    <- egress de Forge/Cerebro ausente
[FAIL] contains app: relay     <- ingress do Relay ausente
[FAIL] javascript (regras>=3 e comentários>=regras)
=> 1 failed (100%)
```

## Curadoria — o que ajustei

1. **Assert `javascript` não aceita `return` no topo.** A primeira versão usava
   `return output.split(...)...` e o promptfoo reprovou com *"Unexpected token
   'return'"* — ele avalia o valor como **expressão**, não corpo de função.
   Corrigi para expressão pura na nota
   (`output.split("\n").filter(l => l.trim().length > 0).length <= 8`) e, na
   networkpolicy, para uma expressão booleana direta com os dois `match(...)`
   (a tentativa intermediária com IIFE também falhou por ser lida como função).
   Arrow function *dentro* de callback (`filter(l => ...)`) funciona; o que não
   pode é `return`/IIFE no nível de topo.

2. **Nenhum ajuste foi necessário nos prompts.** As saídas curadas do CP01/02/06
   já satisfazem os asserts — o que confirma que o formato rígido definido lá
   atrás (rótulos fixos, comentário por regra, caso saudável explícito) era
   testável como planejado. O único trabalho de correção foi nos **testes**, não
   nos prompts.

3. **`latency`/`cost` sob execução local.** O `promptfoo eval` foi rodado neste
   ambiente com um **provider mock** (`mock-provider.js`) que devolve as saídas
   já curadas do CP01/02/06 — porque o sandbox não tem chave de API nem egress
   para `api.openai.com`. Isso exercita o motor de asserts de conteúdo de
   verdade, mas os asserts `latency`/`cost` passam trivialmente (mock responde
   em ~ms e reporta custo 0). Contra os providers reais declarados no
   `promptfooconfig.yaml`, esses dois limites voltam a ter sentido — e a escolha
   de gpt-4o-mini + claude-haiku-4.5 foi feita justamente para caber neles.

4. **Frontmatter no `prompt.md`.** O `file://prompt.md` envia o arquivo inteiro,
   incluindo o frontmatter YAML do CP07. Com o mock isso é irrelevante (a saída
   é canônica). Num run com provider real, o modelo recebe o bloco de metadados
   antes das instruções — inofensivo na prática, mas se incomodar dá para
   apontar o config para um corpo sem frontmatter. Ponto anotado, não bloqueia.

## Como reproduzir offline

O harness de mock (`mock-provider.js`, `mock-provider-bad.js`,
`promptfooconfig.mock.yaml`, `promptfooconfig.negctl.yaml`) fica fora do
versionamento (`.gitignore`) mas acompanha o zip. Para rodar contra os
**providers reais**, exporte as chaves e rode o config versionado:

```bash
export OPENAI_API_KEY=...  ANTHROPIC_API_KEY=...
cd devops/nota-de-triagem-de-alerta && promptfoo eval        # usa promptfooconfig.yaml
```

Para reproduzir o run offline (mock, sem chaves):

```bash
cd devops/nota-de-triagem-de-alerta && promptfoo eval -c promptfooconfig.mock.yaml --no-cache
```
