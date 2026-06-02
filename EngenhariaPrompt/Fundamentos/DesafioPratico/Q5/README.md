
# Justificativa B-A-B
ElementoOnde aparece no promptO que fazBeforeBloco [BEFORE]: manifest original colado + lista explícita dos 6 problemas identificadosAncora o modelo na realidade atual, sem ambiguidade sobre o ponto de partidaAfterBloco [AFTER]: 8 requisitos numerados com exemplos concretos de valoresDefine o estado-alvo com precisão suficiente para o modelo não inventar critériosBridgeBloco [BRIDGE]: instrução de reescrita + comentários inline + entrega do Secret separadoÉ o "como chegar lá" — transforma os dois estados em uma tarefa executável com formato de saída definido
A eficácia do framework aqui está em não deixar nenhum gap implícito: o Before nomeia os problemas, o After especifica as soluções, e o Bridge instrui o modelo a conectar cada decisão técnica à sua justificativa via comentário — o que torna o output auditável por qualquer engenheiro que revisar o PR.Você disse: [BEFORE] Tenho um Kubernetes Deployment legado que foi escrito há três anos e nunca foi atualizado.

# Justificativa Modelo Claude Sonnet (claude-sonnet-4-20250514)
— Equilíbrio ideal entre raciocínio técnico e custo para geração de YAML estruturado com comentários.
