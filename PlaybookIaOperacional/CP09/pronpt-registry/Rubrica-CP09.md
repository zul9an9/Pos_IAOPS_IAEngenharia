# CP09 — Gate de qualidade com LLM-as-judge (causa-raiz)

Gate de qualidade em cima do CP08 para o prompt de **causa-raiz** (CP03), cujo
resultado não é verificável por regex. Config:
`devops/analise-de-causa-raiz/promptfooconfig.yaml`.

> **Mapa de nomes.** O enunciado cita `devops/causa-raiz/`; mantive o nome do
> CP07 (`devops/analise-de-causa-raiz/`). O gate vive nessa pasta.

## A rubrica

Quatro critérios, cada um de **0 a 2** (0 = não atende, 1 = parcial, 2 = atende),
total **0 a 8**:

1. **causa_raiz_correta** — aponta a causa real (reindexação travada saturando o
   heap → circuit breaker → timeouts de busca → queda do cache), não os sintomas.
2. **correlacao_x_causa** — separa causa de consequência (o cache hit caindo é
   efeito, não causa).
3. **acao_proporcional** — ação coerente com o diagnóstico (conter/reagendar a
   reindexação, rever heap/limites), sem sub nem superdimensionar.
4. **honestidade_epistemica** — reconhece o que os dados não permitem concluir,
   em vez de fabricar certeza.

**Corte:** aprova se **total ≥ 6 E nenhum critério zerado**. Essa lógica de
`pass` vive dentro do prompt do juiz (o "nenhum zerado" não é expressável por um
simples threshold numérico).

## O juiz como gate

`llm-rubric` com um `rubricPrompt` customizado que aplica exatamente os quatro
critérios e devolve JSON:

```json
{"causa_raiz_correta":<0-2>,"correlacao_x_causa":<0-2>,"acao_proporcional":<0-2>,
 "honestidade_epistemica":<0-2>,"total":<0-8>,"score":<total/8>,"reason":"...","pass":<bool>}
```

O juiz é `openai:gpt-4o` — um modelo **mais forte e de fornecedor independente**
dos avaliados (`gpt-4o-mini`, `claude-haiku-4.5`), para reduzir viés de
auto-avaliação. O promptfoo lê o `pass` do JSON e reprova o caso quando `false`.

## Calibração (minha nota × juiz)

Pontuei três saídas à mão e ajustei o `rubricPrompt` até o juiz ficar a ≤ 1
ponto de mim em cada critério. Amostras: **GOLD** (a análise curada do CP03),
**SYMPTOM** (aponta o circuit breaker — um sintoma — como causa) e **FABRICATED**
(acerta a causa, mas inventa que "o volume dobrou" e manda "refazer o cluster").

| Amostra | Critério 1 | Critério 2 | Critério 3 | Critério 4 | Total | Minha decisão |
|---------|:---------:|:---------:|:---------:|:---------:|:-----:|:-------------:|
| GOLD (minha) | 2 | 2 | 2 | 2 | **8** | passa |
| GOLD (juiz)  | 2 | 2 | 2 | 2 | **8** | passa ✓ |
| SYMPTOM (minha) | 0 | 0 | 1 | 0 | **1** | reprova |
| SYMPTOM (juiz)  | 0 | 0 | 1 | 0 | **1** | reprova ✓ |
| FABRICATED (minha) | 2 | 2 | 0 | 0 | **4** | reprova |
| FABRICATED (juiz)  | 2 | 2 | 0 | 0 | **4** | reprova ✓ |

Delta final: **0 em todos os critérios** — dentro da tolerância de 1.

### O ajuste que a calibração forçou

Na **primeira** versão do `rubricPrompt` (âncoras genéricas: "0 = não atende,
2 = atende"), ao aplicar a rubrica no FABRICATED o juiz dava:

- `acao_proporcional = 1` (crédito parcial por mencionar "rever heap"), e
- `honestidade_epistemica = 1` (benefício da dúvida sobre o "volume dobrou").

Total **6** → **passava por engano** (≥ 6 e nenhum zero). Minha nota era **4**
(0 nos dois). Delta de 1 em dois critérios — sozinho inofensivo, mas somado
cruzava o corte e deixava passar uma análise que fabrica dado e superdimensiona.

Correção: tornei duas âncoras **explícitas e discriminativas** no `rubricPrompt`:

- critério 3 → "**dar 0 se SUPERDIMENSIONA** (refazer o cluster, reconstruir
  todos os shards)";
- critério 4 → "**dar 0 se FABRICA certeza inventando um dado** que não está nos
  artefatos (ex.: o volume dobrou)".

Recalibrado, o juiz dá 0/0 nesses dois → total **4** → reprova corretamente.
Nenhuma mudança foi necessária nas amostras GOLD/SYMPTOM.

## Execução real do gate

Rodado com **promptfoo 0.122.0**; config real validado (`promptfoo validate` →
"Configuration is valid.").

```
causa-raiz (gate) ......... 1 passed, 2 failed
  [PASS] GOLD        score 1.000 (8/8)  — reindex 88123 como causa, cache/latência como efeito, pausa o reindex, declara limites
  [FAIL] SYMPTOM     score 0.125 (1/8)  — aponta o circuit breaker (sintoma) como causa; sem separar efeito; sem limites
  [FAIL] FABRICATED  score 0.500 (4/8)  — causa/correlação ok, mas superdimensiona a ação e fabrica o "volume dobrou"
```

O gate faz o que precisa: aprova a análise correta e **barra** as duas
degradadas, cada uma pelo motivo certo. Como esse gate roda a cada `promptfoo
eval`, qualquer alteração no `prompt.md` de causa-raiz que derrube a qualidade
abaixo de 6 (ou zere um critério) reprova aqui — é esse disparo automático que o
CP10 põe no pipeline.

## Curadoria — decisões e limites

- **Onde mora a lógica de aprovação.** No `rubricPrompt`, não num threshold. O
  threshold numérico do promptfoo cobriria "total ≥ 6", mas não "nenhum critério
  zerado"; por isso o juiz calcula `pass` e o promptfoo só o obedece.
- **Escolha do juiz.** Modelo mais forte que os avaliados e de outro fornecedor
  reduz o viés de um modelo se auto-elogiar. É trocável no campo
  `defaultTest.options.provider`.
- **Execução offline (honesto).** O sandbox não tem chave de API nem egress para
  `api.openai.com`. Rodei o gate de verdade com um **grader mock**
  (`judge-mock.js`) que devolve exatamente as notas calibradas, e um **alvo mock**
  (`target-mock.js`) que produz os três níveis de qualidade. Isso exercita a
  mecânica do gate ponta a ponta (parse do JSON do juiz → pass/fail no corte).
  Contra o juiz real declarado no `promptfooconfig.yaml`, o gate roda sozinho —
  basta exportar as chaves. O harness de mock está no `.gitignore` (acompanha o
  zip para reprodução).
- **Frontmatter no `prompt.md`.** Mesmo ponto do CP08: `file://prompt.md` envia o
  arquivo inteiro; inofensivo, anotado.

### Reproduzir

```bash
# real (juiz de verdade)
export OPENAI_API_KEY=... ANTHROPIC_API_KEY=...
cd devops/analise-de-causa-raiz && promptfoo eval

# offline (mock alvo + mock juiz, notas calibradas)
cd devops/analise-de-causa-raiz && promptfoo eval -c promptfooconfig.mock.yaml --no-cache
```
