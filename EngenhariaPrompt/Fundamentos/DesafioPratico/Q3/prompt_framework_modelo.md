# Síntese: o T-A-G 
funciona como um funil — a Task delimita o universo de dados (CSV, meta, restrição de SLA), a Action define as análises a executar sobre esses dados (priorização, cronograma, riscos), e o Goal molda a forma final do entregável (idioma, tom, estrutura, público). Cada pilar elimina uma classe de ambiguidade diferente, resultando em um relatório que pode ir direto da resposta do modelo para a mesa da diretoria.

# modelo: Opus 4.6

Justificativas técnicas para esta escolha:

Raciocínio financeiro encadeado: o modelo precisa cruzar 12 linhas de custo, calcular % individuais sobre o total, somar economias parciais e validar que a meta de 15% é atingida — cadeia longa de dependência lógica onde Opus se diferencia.
Planejamento multi-variável: o cronograma precisa respeitar dependências entre ações (ex.: rightsizing antes de desligar on-demand), algo que exige raciocínio de segunda ordem.
Tom executivo para diretoria: Opus mantém consistência de registro formal em documentos longos melhor que modelos menores.

# [TASK]
Você recebeu o breakdown de custos AWS do último mês consolidado
no CSV abaixo. O custo total mensal é USD 41.800. A meta da
diretoria (definida por Goldie) é reduzir 15% do custo cloud
(≈ USD 6.270/mês) até o fim do próximo trimestre, sem degradar
nenhum SLA vigente.

CSV de entrada:
servico,categoria,custo_mensal_usd,uso_medio_pct,observacao
EC2 reservada,compute,4200,72,contrato de 1 ano
EC2 on-demand,compute,8200,45,workloads variaveis
EKS,compute,6700,58,3 clusters
RDS PostgreSQL,databases,8200,62,multi-AZ
ElastiCache Redis,databases,2100,40,cluster de producao
S3 Standard,storage,3100,,5 buckets principais
EBS gp3,storage,1600,68,volumes de producao
CloudWatch Logs,observability,2800,,retencao de 90 dias
CloudWatch Metrics,observability,900,,
Data Transfer Out,network,1900,,trafego entre regioes
NAT Gateway,network,1200,,3 gateways ativos
Lambda,compute,900,30,~12M invocacoes/mes

# [ACTION]
Analise cada linha de custo e produza um relatório executivo para
Goldie com as seguintes entregas:

1. TABELA DE OPORTUNIDADES priorizada por impacto (maior economia
   primeiro), contendo para cada ação:
   - Serviço afetado
   - Ação proposta (descrição concreta, não genérica)
   - Economia estimada em USD/mês e em % da conta total
   - Esforço de implementação: Baixo / Médio / Alto
   - Riscos ou pré-requisitos de cada ação

2. SOMA DAS ECONOMIAS para confirmar que o pacote atinge ≥ 15%.

3. CRONOGRAMA DE EXECUÇÃO trimestral (3 meses), distribuindo as
   ações em sprints quinzenais com dependências e responsável
   sugerido (SRE, DevOps, FinOps, Plataforma).

4. MAPA DE RISCOS consolidado: para cada risco identificado,
   probabilidade (alta/média/baixa), impacto no SLA e mitigação
   proposta.

5. Considere como estratégias válidas: Savings Plans, Spot/Graviton,
   rightsizing, lifecycle policies S3, redução de retenção de logs,
   consolidação de NAT Gateways, compressão de tráfego, reserved
   nodes para Redis/RDS — mas só inclua o que se justificar pelos
   dados.

# [GOAL]
O entregável final é um plano de execução pronto para aprovação da
diretoria. Formato:
- Linguagem em português BR, tom executivo e direto.
- Todas as tabelas em Markdown.
- Seções claramente separadas: RESUMO EXECUTIVO → OPORTUNIDADES
  → CRONOGRAMA → MAPA DE RISCOS → PRÓXIMOS PASSOS.
- Inclua um parágrafo de resumo executivo no topo com: custo atual,
  meta de redução, economia total projetada e nível de confiança
  (conservador / moderado / agressivo).
