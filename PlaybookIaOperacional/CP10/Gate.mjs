#!/usr/bin/env node
// gate.mjs — política de gate do playbook Aegis.
// Regra de decisão (separada do provider de exibição da action):
//   1) TRAVA DURA: qualquer assert determinístico que falhe reprova o build.
//   2) TRAVA SUAVE (juiz): por caso de teste, agrega os N repeats por MEDIANA
//      e reprova só se a mediana < threshold. A mediana absorve a flutuação
//      não-determinística de um único run do LLM-as-judge.
// Uso: node gate.mjs <results.json> [--judge-threshold=0.75] [--min-judge-runs=3]

import fs from 'node:fs';

const args = process.argv.slice(2);
const file = args.find(a => !a.startsWith('--'));
const opt = Object.fromEntries(args.filter(a => a.startsWith('--'))
  .map(a => a.replace(/^--/, '').split('=')));
const JUDGE_THRESHOLD = Number(opt['judge-threshold'] ?? 0.75);
const MIN_JUDGE_RUNS  = Number(opt['min-judge-runs'] ?? 1);

const DETERMINISTIC = new Set([
  'contains','icontains','not-contains','equals','regex','not-regex',
  'is-json','contains-json','starts-with','levenshtein','is-valid-openai-function-call',
  'javascript','python','contains-all','contains-any','is-sql'
]);
const isJudge = t => /^(llm-rubric|g-eval|model-graded|answer-relevance|factuality|similar|context-|moderation)/.test(t);

const median = xs => {
  const s = [...xs].sort((a,b)=>a-b); const m = s.length>>1;
  return s.length % 2 ? s[m] : (s[m-1]+s[m])/2;
};

const data = JSON.parse(fs.readFileSync(file, 'utf8'));
const results = data.results?.results ?? [];

let hardFailures = [];            // asserts determinísticos reprovados
const judgeByCase = new Map();    // chave do caso -> [scores]

for (const r of results) {
  const caseKey = JSON.stringify(r.vars ?? {});
  for (const c of r.gradingResult?.componentResults ?? []) {
    const type = c.assertion?.type ?? '';
    if (DETERMINISTIC.has(type)) {
      if (!c.pass) hardFailures.push({ caseKey, type, value: c.assertion?.value, reason: c.reason });
    } else if (isJudge(type)) {
      const score = typeof c.score === 'number' ? c.score : (c.pass ? 1 : 0);
      if (!judgeByCase.has(caseKey)) judgeByCase.set(caseKey, []);
      judgeByCase.get(caseKey).push(score);
    }
  }
}

let judgeFailures = [];
for (const [caseKey, scores] of judgeByCase) {
  if (scores.length < MIN_JUDGE_RUNS) {
    judgeFailures.push({ caseKey, reason: `repeats insuficientes: ${scores.length} < ${MIN_JUDGE_RUNS}` });
    continue;
  }
  const med = median(scores);
  if (med < JUDGE_THRESHOLD) {
    judgeFailures.push({ caseKey, median: med.toFixed(3), scores: scores.map(s=>s.toFixed(2)) });
  }
}

console.log(`Gate Aegis :: threshold-juiz=${JUDGE_THRESHOLD}  min-runs=${MIN_JUDGE_RUNS}`);
console.log(`  asserts determinísticos reprovados: ${hardFailures.length}`);
console.log(`  casos de juiz abaixo da mediana:     ${judgeFailures.length}`);
for (const f of hardFailures) console.log(`  [DET-FAIL] ${f.type}=${JSON.stringify(f.value)} :: ${f.reason}`);
for (const f of judgeFailures) console.log(`  [JUIZ-FAIL] mediana=${f.median ?? '-'} scores=${JSON.stringify(f.scores ?? [])} ${f.reason ?? ''}`);

if (hardFailures.length || judgeFailures.length) {
  console.error('\n❌ GATE REPROVADO — regressão detectada.');
  process.exit(1);
}
console.log('\n✅ GATE APROVADO.');
