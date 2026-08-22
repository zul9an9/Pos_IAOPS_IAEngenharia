---
nome: Nota de Triagem de Alerta
descricao: Converte um alerta cru do Sentinel em nota de triagem padronizada de cinco campos para o plantão.
versao: 1.0.0
tags: [observabilidade, plantao, alertas, padronizacao, incidentes]
inputs:
  - nome: alerta_cru
    descricao: "O alerta bruto emitido pelo Sentinel, incluindo o sistema de origem entre colchetes (ex.: `[Relay]`)."
---

# Nota de Triagem de Alerta

## Objetivo

Transformar um alerta cru do Sentinel numa nota de triagem padronizada de cinco campos (ALERTA, IMPACTO, HIPÓTESE INICIAL, AÇÃO IMEDIATA, ESCALAR PARA), para que qualquer plantonista escreva e o próximo plantão leia no mesmo formato. O padrão é ensinado por few-shot embutido no próprio prompt.

## Quando usar

- Ao receber um alerta bruto do Sentinel que precisa virar nota legível para o handoff.
- Para padronizar a comunicação entre plantões, sem depender do estilo de cada plantonista.
- Quando o roteamento correto do escalonamento (@time) importa e precisa seguir o mapeamento fixo.

## Exemplo de uso

**Entrada (`{{alerta_cru}}`):** `[Sentinel] autoscaler hit max replicas (60/60) on sentinel-api, queue depth on Relay growing 2k/min, tenant stark-industries sending 4x baseline`.

**Saída (trecho):**
```
ALERTA: Sentinel - autoscaler do sentinel-api atingiu o limite máximo de réplicas (60/60)
IMPACTO: fila de ingestão do Relay crescendo ~2k msgs/min, risco de atraso no alerting
HIPÓTESE INICIAL: tenant stark-industries enviando ~4x o baseline após onboarding de região
AÇÃO IMEDIATA: aumentar manualmente o teto de réplicas do autoscaler
ESCALAR PARA: @sentinel-core se a fila do Relay não estabilizar
```

## Limitações conhecidas

- O mapeamento `Sentinel -> @sentinel-core` foi inferido por padrão de nomenclatura (os exemplos originais do time cobriam só Relay, Forge e Cerebro) — validar com o time antes de tratar como confirmado.
- O few-shot embutido aumenta o número de tokens por chamada; aceitável por ser um alerta por vez, sob demanda.
- Processa um único alerta por execução; não faz correlação entre múltiplos alertas.
