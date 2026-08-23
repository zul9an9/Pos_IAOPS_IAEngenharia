// Alvo (mock): devolve a análise de causa-raiz em três níveis de qualidade,
// escolhidos por context.vars.variant. Serve para exercitar o GATE (juiz) de
// verdade offline, sem chave de API.

const GOLD = `Linha do tempo: às 02:00 o job de reindex (task 88123) inicia, previsto para ~90min (fim ~03:30). Às 08:02 ainda roda, 38% concluído; heap em 61%, p99 850ms. Entre 08:14 e 09:12 os GCs "old" crescem (heap 3.1gb->5.9gb). 08:41 o IndexingMemoryController faz throttle no shard 7. 09:58 o circuit breaker dispara a 96%, a busca estoura o timeout de 5s e o cache hit cai para 29%. Às 10:00 o reindex ainda está em 41%.

Causa-raiz: a causa-raiz é o job de reindexação (task 88123) NÃO ter concluído no tempo esperado — previsto para ~90min, ainda em 41% mais de 7h depois. Esse job competindo por heap e threadpool de escrita com o tráfego normal é o evento que desencadeia todo o resto.

Cadeia causal: reindex atrasado mantém o heap sob pressão sustentada por horas -> GCs "old" longos e ineficazes -> throttle de indexação -> circuit breaker de memória dispara a 96% -> bulks rejeitados e buscas estourando o timeout de 5s. A queda do cache hit de 71% para 29% é CONSEQUÊNCIA da pressão de memória (eviction acelerada), não uma causa independente; do mesmo modo, indexed_docs subindo é o reindex somado ao tráfego, não carga externa nova.

Ação recomendada: pausar ou cancelar a task 88123 imediatamente para liberar heap e aliviar o circuit breaker — normaliza busca e escrita em minutos, sem mudança de infraestrutura. Depois, reagendar o reindex para janela de menor tráfego ou em lotes menores, e rever se jvm_heap: 8g comporta reindex + tráfego simultâneos (revisão de capacidade posterior, não emergência).

Limites do diagnóstico: os dados NÃO explicam por que o reindex, historicamente de ~90min, está demorando mais de 7h nesta execução — não há evidência de aumento de volume, degradação de hardware ou mudança de schema. Também não é possível confirmar, só com estes artefatos, se cerebro-node-3 é o único nó afetado ou se o cluster inteiro está sob a mesma pressão.`;

const SYMPTOM = `A causa-raiz é o circuit breaker de memória, que disparou a 96% e provocou os timeouts de busca e a rejeição dos bulks. Junto disso, a latência p99 subiu para mais de 5s e o cache hit despencou para 29%, degradando a experiência de busca.

Ação recomendada: aumentar o heap da JVM e reiniciar o nó cerebro-node-3 para limpar o circuit breaker e restabelecer o serviço. O cluster aparenta precisar de mais memória para aguentar a carga.`;

const FABRICATED = `Causa-raiz: a reindexação (task 88123) saturou o heap, o que levou ao circuit breaker a 96%, aos timeouts de busca e à queda do cache. A queda do cache hit é consequência da pressão de memória, não uma causa separada.

O reindex atrasou porque o volume de dados do tenant dobrou nesta madrugada, exigindo reprocessar o dobro de documentos.

Ação recomendada: refazer o cluster com o dobro de heap (16g) e reconstruir todos os shards do zero, para garantir que a degradação não se repita.`;

class Target {
  constructor(o) { this.providerId = (o && o.id) || 'target'; }
  id() { return this.providerId; }
  async callApi(prompt, context) {
    const v = ((context && context.vars) || {}).variant || 'gold';
    const out = v === 'symptom' ? SYMPTOM : v === 'fabricated' ? FABRICATED : GOLD;
    return { output: out, cost: 0, tokenUsage: { total: 0, prompt: 0, completion: 0 } };
  }
}
module.exports = Target;
