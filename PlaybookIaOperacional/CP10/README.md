# Aegis Playbook — testes de prompt em produção contínua (CP10)

Cada prompt da biblioteca tem seu conjunto promptfoo, e um pipeline em GitHub Actions roda a suíte a
cada alteração, **barrando regressão**.

## Estrutura
```
.github/
  workflows/playbook-eval.yml   # o pipeline (PR: prompts alterados; push/noturno: suíte inteira)
  scripts/gate.mjs              # a POLÍTICA de gate (fonte única da decisão pass/fail)
prompts/
  promptfooconfig.yaml          # agregador p/ o comentário before/after da action oficial
  postmortem/  prompt.txt + promptfooconfig.yaml   # determinístico + juiz
  triagem/     prompt.txt + promptfooconfig.yaml   # saída estruturada (is-json + javascript)
  comunicado/  prompt.txt + promptfooconfig.yaml   # qualidade/tom -> juiz
docs/
  GATE_STRATEGY.md              # estratégia + justificativa comparando alternativas
  EVIDENCE.md                   # evidência de execução real (verde e vermelho)
```

## Convenção para cobrir um prompt novo
Crie `prompts/<nome>/` com `prompt.txt` e um `promptfooconfig.yaml` contendo:
determinísticos (`contains`, `is-json`, `regex`, `javascript`) como **trava dura** e, quando o valor
exigir julgamento, um `llm-rubric` com `threshold: 0.75` como **trava suave**. O pipeline passa a
cobri-lo automaticamente — nada mais a configurar.

## Rodar local sem gastar token
Troque o `providers` do config por `[ echo ]`, deixe só os asserts determinísticos e rode
`npx promptfoo eval -c prompts/<nome>/promptfooconfig.yaml` — é o *smoke test* usado no EVIDENCE.md.

## Setup no GitHub
1. `Settings > Secrets and variables > Actions`: adicione `OPENAI_API_KEY` e `ANTHROPIC_API_KEY`.
2. O `GITHUB_TOKEN` é automático; o workflow já pede `permissions: pull-requests: write`.
3. Abra um PR editando um `prompt.txt` para ver o comentário before/after e o check do gate.
