name: playbook-eval

# Dispara em toda alteração:
#  - pull_request: valida SÓ os prompts alterados (rápido, barato, com before/after e comentário no PR)
#  - push na main:  rede de segurança pós-merge
#  - schedule:      suíte INTEIRA toda madrugada, fora do caminho crítico do dev
on:
  pull_request:
    paths:
      - 'prompts/**'
      - '.github/workflows/promptfoo.yml'
      - '.github/scripts/gate.mjs'
  push:
    branches: [main]
    paths:
      - 'prompts/**'
  schedule:
    - cron: '0 6 * * *'   # 06:00 UTC ~ 03:00 America/Sao_Paulo
  workflow_dispatch: {}

concurrency:
  group: playbook-eval-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read
  pull-requests: write   # necessário para o comentário do before/after no PR

jobs:
  eval:
    runs-on: ubuntu-latest
    env:
      # thresholds do gate ficam versionados aqui, não escondidos no script
      JUDGE_THRESHOLD: '0.75'
      MIN_JUDGE_RUNS: '3'
      # chaves ficam em Settings > Secrets and variables > Actions (nunca no YAML)
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    steps:
      - uses: actions/checkout@v5
        with:
          fetch-depth: 0   # preciso do histórico para o diff PR e para o before/after

      - uses: actions/setup-node@v4
        with:
          node-version: '24'   # a action oficial exige Node >= 22.22.0

      # Cache do promptfoo: reaproveita respostas de LLM entre runs => menos token, menos tempo
      - name: Cache promptfoo
        uses: actions/cache@v4
        with:
          path: ~/.cache/promptfoo
          key: ${{ runner.os }}-promptfoo-${{ hashFiles('prompts/**') }}
          restore-keys: ${{ runner.os }}-promptfoo-

      # ── Camada 1 (só no PR): comentário before/after via action oficial ─────────
      # Serve ao HUMANO revisor. NÃO é o gate: é visualização da regressão relativa.
      - name: Comentário before/after no PR
        if: github.event_name == 'pull_request'
        uses: promptfoo/promptfoo-action@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          prompts: 'prompts/**/prompt.*'
          config: 'prompts/promptfooconfig.yaml'
          cache-path: ~/.cache/promptfoo

      # ── Descobre O QUE avaliar ──────────────────────────────────────────────────
      # PR  -> só as pastas de prompt alteradas (barato)
      # push/schedule/manual -> a biblioteca inteira (rede de segurança)
      - name: Selecionar configs a avaliar
        id: select
        run: |
          set -euo pipefail
          if [ "${{ github.event_name }}" = "pull_request" ]; then
            base="${{ github.event.pull_request.base.sha }}"
            changed=$(git diff --name-only "$base"...HEAD | grep '^prompts/.*/' || true)
            dirs=$(echo "$changed" | sed -n 's#\(prompts/[^/]*\)/.*#\1#p' | sort -u)
          else
            dirs=$(find prompts -mindepth 1 -maxdepth 1 -type d | sort)
          fi
          configs=$(for d in $dirs; do [ -f "$d/promptfooconfig.yaml" ] && echo "$d/promptfooconfig.yaml"; done)
          echo "Configs selecionadas:"; echo "${configs:-<nenhuma>}"
          { echo 'configs<<EOF'; echo "$configs"; echo 'EOF'; } >> "$GITHUB_OUTPUT"

      # ── Camada 2: o GATE de verdade ─────────────────────────────────────────────
      # Roda o eval (sempre até o fim, || true) e deixa gate.mjs ser a ÚNICA decisão.
      - name: Rodar suíte + aplicar gate
        run: |
          set -euo pipefail
          mkdir -p results
          fail=0
          while IFS= read -r cfg; do
            [ -z "$cfg" ] && continue
            name=$(echo "$cfg" | sed 's#/#_#g')
            echo "::group::eval $cfg"
            npx promptfoo@0.122.0 eval -c "$cfg" \
              --repeat "${MIN_JUDGE_RUNS}" \
              --output "results/${name}.json" \
              --cache || true
            echo "::endgroup::"
            node .github/scripts/gate.mjs "results/${name}.json" \
              --judge-threshold="${JUDGE_THRESHOLD}" \
              --min-judge-runs="${MIN_JUDGE_RUNS}" || fail=1
          done <<< "${{ steps.select.outputs.configs }}"
          exit $fail

      - name: Publicar resultados como artefato
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: promptfoo-results
          path: results/
          retention-days: 14
