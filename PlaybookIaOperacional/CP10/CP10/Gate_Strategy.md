# CP10 — Estratégia de gate e justificativa estendida

O pipeline (`.github/workflows/playbook-eval.yml`) roda a suíte promptfoo a cada alteração e
**reprova o build quando um prompt regride**. Este documento fixa a regra do gate e justifica cada
decisão de desenho contra pelo menos duas alternativas, apontando o que se ganha e o que se perde.

Antes das decisões, a regra em uma frase:

> **Reprova o build** quando (a) qualquer assert **determinístico** falha, ou (b) a **mediana** de
> N julgamentos do LLM-as-judge, por caso de teste, fica **abaixo do threshold** (0.75). O
> comentário *before/after* da action oficial é informativo para o revisor humano — não é o gate.

---

## Decisão 1 — Quem decide pass/fail: a action oficial ou um script próprio

A `promptfoo/promptfoo-action@v1` foi feita para rodar o eval e **postar o comparativo
before/after no PR**. Ela é ótima como camada de visualização, mas o *build-failing* preciso — com
threshold e tratamento de flutuação — é justamente a parte que o enunciado deixa em aberto.

- **Alternativa A — deixar a action ser o gate (exit code dela).**
  *Ganha:* zero código próprio; um passo só. *Perde:* a decisão fica presa ao comportamento embutido
  da action; não dá para expressar "mediana-de-N ≥ 0.75", nem separar trava dura de trava suave, nem
  versionar o threshold junto do repo. O gate vira uma caixa-preta.
- **Alternativa B — só `promptfoo eval` com exit code nativo.**
  *Ganha:* simples, o próprio promptfoo já sai não-zero quando um assert falha. *Perde:* perde o
  comentário rico no PR e continua sem controle fino sobre o juiz (um único run flaky derruba o build).
- **Escolhido — as duas camadas, com fonte única de verdade no `gate.mjs`.**
  A action roda no PR **só para o comentário** (camada 1). O gate real (camada 2) roda
  `promptfoo eval ... || true` — o eval **sempre** vai até o fim e escreve o JSON — e o
  `.github/scripts/gate.mjs` lê esse JSON e é o **único** ponto que decide `exit 0/1`. *Ganha:*
  visualização humana + decisão de máquina auditável e versionada. *Perde:* ~70 linhas de script para
  manter. Trade aceitável: a lógica de gate é justamente o que precisa ficar explícito e testável.

---

## Decisão 2 — O que reprova: só determinístico, ou também nota do juiz

Esta é a decisão central e a de mais caminhos defensáveis.

- **Alternativa A — só asserts determinísticos reprovam.**
  *Ganha:* 100% reproduzível, custo zero de token, nunca dá falso-vermelho. *Perde:* cega para tudo
  que não é verificável por regra — tom, ausência de alucinação, aderência ao pedido. Metade da razão
  de existir do playbook (qualidade de resposta) fica fora do gate.
- **Alternativa B — juiz reprova por threshold absoluto em um único run.**
  *Ganha:* captura qualidade. *Perde:* um juiz não-determinístico **reprova o build por flutuação** —
  a mesma resposta tira 0.78 num run e 0.71 no próximo. Build vermelho intermitente destrói a
  confiança no CI mais rápido do que qualquer regressão real.
- **Alternativa C — juiz só como *advisory* (nunca reprova, só comenta).**
  *Ganha:* zero flutuação no gate. *Perde:* na prática ninguém segura merge por um comentário; a
  regressão de qualidade passa. É "ter o teste e ignorar o resultado".
- **Escolhido — trava dura determinística + trava suave por juiz com mediana-de-N.**
  Asserts determinísticos (`contains`, `is-json`, `regex`, `javascript`…) reprovam na hora — são
  baratos e não flutuam, então carregam o máximo possível do gate. O juiz (`llm-rubric`) cobre só o
  que exige julgamento e reprova apenas quando a **mediana de N=3 runs** fica abaixo de 0.75.
  *Ganha:* pega regressão de qualidade sem reprovar por tremor de um julgamento isolado (ver Decisão
  3). *Perde:* 3× o custo de token nos casos com juiz, e um threshold que é escolha de engenharia, não
  verdade absoluta. Por isso o threshold e o N ficam versionados no `env` do workflow, revisáveis em PR.

**Regra de ouro herdada dos estudos de certificação:** empurrar o máximo de cobertura para o lado
determinístico e reservar o juiz só para o que genuinamente precisa de julgamento — é mais barato,
mais estável e mais fácil de auditar.

---

## Decisão 3 — Flutuação do juiz: como impedir falso-vermelho

- **Alternativa A — threshold absoluto, run único.** Já descartada na Decisão 2: flaky.
- **Alternativa B — comparação relativa ao base (regressão = queda vs versão anterior além de uma
  margem).** É o espírito do before/after da action. *Ganha:* mede exatamente "piorou em relação à
  versão anterior", que é a definição de regressão do enunciado. *Perde:* precisa de um baseline
  estável e persistido; ruído do juiz aparece nos **dois** lados da comparação e a margem vira outro
  número mágico. Bom para o comentário humano, arriscado como gate automático.
- **Escolhido — mediana de N=3 runs contra threshold fixo.** A mediana é robusta a um outlier: um
  run que despenca não move a mediana (evidência no `EVIDENCE.md`, Caso A: scores 0.90/0.55/0.85 →
  mediana 0.85 → **aprova**). Só reprova quando a piora é **persistente** (Caso B: 0.40/0.50/0.72 →
  mediana 0.50 → **reprova**). *Ganha:* estabilidade sem abrir mão de pegar regressão real. *Perde:*
  custo 3×. Mitigado restringindo N=3 aos poucos prompts com juiz e aos poucos casos por prompt.
  *(Alternativa de reforço: subir para N=5 no run noturno, onde tempo/custo não estão no caminho
  crítico do dev.)*

---

## Decisão 4 — Escopo por execução: suíte inteira vs. só o que mudou

- **Alternativa A — suíte inteira a cada PR.**
  *Ganha:* nunca deixa passar regressão cruzada (um prompt que quebra por causa de um fixture/rubrica
  compartilhada). *Perde:* cada PR paga o custo da biblioteca inteira em tempo e token; conforme a
  biblioteca cresce, o PR fica lento e caro, e o dev começa a evitar o CI.
- **Alternativa B — só os prompts alterados, sempre.**
  *Ganha:* PR rápido e barato — custo proporcional ao diff. *Perde:* uma mudança em recurso
  compartilhado (rubrica, provider default, template incluído) pode regredir um prompt **não** tocado
  no diff, e esse escapa até produção.
- **Escolhido — híbrido por gatilho.** No `pull_request`, avalia **só as pastas de prompt alteradas**
  (o passo *Selecionar configs* faz `git diff base...HEAD`). No `push` para `main` e no `schedule`
  noturno, avalia a **biblioteca inteira**. *Ganha:* PR barato e rápido no caminho crítico; a rede de
  segurança da suíte completa roda pós-merge e toda madrugada, fora do caminho do dev, pegando
  regressões cruzadas com atraso de no máximo um dia. *Perde:* uma regressão cruzada pode entrar na
  `main` e só ser pega no push/noturno — não em produção, mas depois do merge. Trade consciente:
  troca-se um pouco de imediatismo por um CI que as pessoas de fato usam.

---

## Decisão 5 — Custo de chamar modelo a cada PR

- **Alternativa A — sem cache, modelo caro como juiz, suíte inteira.** O pior caso: todo PR reexecuta
  tudo. Rejeitada por custo.
- **Alternativa B — `echo`/mock nos PRs, modelo real só no noturno.** *Ganha:* PR custa zero token.
  *Perde:* o juiz — a parte que exige modelo — fica fora do gate do PR; regressão de qualidade só
  aparece de madrugada. Bom para *smoke test* local (é o que uso no `EVIDENCE.md`), fraco como gate de PR.
- **Escolhido — combinação de quatro alavancas:** (1) **cache** do promptfoo via `actions/cache`
  (chaveado por `hashFiles('prompts/**')`) reaproveita respostas idênticas entre runs; (2) **escopo
  por diff** no PR (Decisão 4) já corta a maior parte do custo; (3) o juiz roda num modelo de custo
  moderado, não no maior; (4) `concurrency` com `cancel-in-progress` mata runs obsoletos quando chega
  push novo no mesmo PR. *Ganha:* custo de PR proporcional ao diff e amortizado pelo cache. *Perde:* o
  cache pode mascarar não-determinismo (uma resposta cacheada não reexpõe flutuação); por isso o run
  **noturno usa `--no-cache` implícito via N=3** e revalida a biblioteca inteira do zero.

---

## Decisão 6 — Onde guardam as chaves dos provedores

- **Alternativa A — chave no YAML / no código.** Nunca. Segredo em repositório vaza no primeiro fork
  ou log. Descartada de saída.
- **Alternativa B — *repository secrets*.** *Ganha:* simples, um lugar só (`Settings > Secrets and
  variables > Actions`), referenciado como `${{ secrets.OPENAI_API_KEY }}`. *Perde:* todo workflow do
  repo enxerga o segredo; sem escopo por ambiente nem *required reviewers*.
- **Alternativa C — *environment secrets* / OIDC para cofre externo.** *Ganha:* escopo por ambiente,
  aprovação manual, rotação central, credencial de curta duração via OIDC (sem chave estática).
  *Perde:* setup mais pesado, justificável quando há produção/custo alto.
- **Escolhido — *repository secrets* agora, com o caminho para *environment secrets* documentado.**
  Para um playbook em consolidação, repository secrets (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) são o
  equilíbrio certo entre segurança e atrito. O `GITHUB_TOKEN` usado pelo comentário no PR é o token
  efêmero automático do Actions, com `permissions: pull-requests: write` — nunca uma PAT pessoal.
  *Quando* o gasto de token virar material, migra-se o job para um `environment` protegido com
  aprovação e, idealmente, OIDC.

---

## Ponte para o que vem depois

O que foi automatizado aqui — suíte versionada, gate como código com fonte única de decisão, escopo
por gatilho, segredos em secrets — é a base das automações seguintes. Um agente que **proponha**
mudanças de prompt precisa exatamente deste gate para que suas sugestões só entrem se não regredirem:
o pipeline deixa de ser só um freio de regressão humana e passa a ser o **contrato de qualidade** que
qualquer autor de mudança (pessoa ou agente) tem que satisfazer.
