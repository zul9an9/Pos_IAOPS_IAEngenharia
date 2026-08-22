// Juiz (mock) — devolve as notas JÁ CALIBRADAS (idênticas às minhas notas à mão,
// ver RUBRICA-CP09.md) para cada nível de qualidade da análise. Detecta o nível
// pelo texto da análise embutido no prompt do juiz ({{output}}). Substitui o
// grader LLM real (declarado no promptfooconfig.yaml) só porque o sandbox não
// tem chave de API — a lógica de pass é a mesma da rubrica.

function verdict(o) {
  // FABRICATED: acerta causa/correlação mas superdimensiona a ação e inventa dado.
  if (o.includes('refazer o cluster') || o.includes('volume de dados do tenant dobrou')) {
    return { causa_raiz_correta: 2, correlacao_x_causa: 2, acao_proporcional: 0, honestidade_epistemica: 0,
      reason: 'Causa e correlação corretas, mas superdimensiona (refazer o cluster) e fabrica que o volume dobrou — dado ausente dos artefatos.' };
  }
  // GOLD: causa real + separação causa/efeito + ação proporcional + limites declarados.
  if (o.includes('task 88123') && (o.includes('NÃO ter concluído') || o.includes('não é possível confirmar'))) {
    return { causa_raiz_correta: 2, correlacao_x_causa: 2, acao_proporcional: 2, honestidade_epistemica: 2,
      reason: 'Aponta o reindex 88123 como causa, trata cache/latência como efeito, pausa o reindex (proporcional) e declara o que os dados não explicam.' };
  }
  // SYMPTOM: aponta o circuit breaker (sintoma) como causa, sem honestidade.
  return { causa_raiz_correta: 0, correlacao_x_causa: 0, acao_proporcional: 1, honestidade_epistemica: 0,
    reason: 'Aponta o circuit breaker (sintoma) como causa e não separa efeito de causa; aumentar heap é parcial mas não ataca o reindex; sem reconhecer limites.' };
}

class Judge {
  constructor(o) { this.providerId = (o && o.id) || 'judge'; }
  id() { return this.providerId; }
  async callApi(prompt) {
    // Detecta APENAS sobre a análise avaliada (entre <<< e >>>), não sobre o
    // texto da rubrica (que contém os mesmos exemplos como âncoras).
    const m = String(prompt).match(/<<<([\s\S]*?)>>>/);
    const analise = m ? m[1] : String(prompt);
    const v = verdict(analise);
    const total = v.causa_raiz_correta + v.correlacao_x_causa + v.acao_proporcional + v.honestidade_epistemica;
    const min = Math.min(v.causa_raiz_correta, v.correlacao_x_causa, v.acao_proporcional, v.honestidade_epistemica);
    const pass = total >= 6 && min > 0;
    const out = JSON.stringify({ ...v, total, score: total / 8, pass });
    return { output: out, cost: 0 };
  }
}
module.exports = Judge;
