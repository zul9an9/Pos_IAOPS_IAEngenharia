// Provider mock para rodar `promptfoo eval` offline (sem chave de API / sem
// egress externo). Devolve as saídas JÁ CURADAS dos CP01/CP02/CP06, escolhidas
// pelas variáveis do caso. Serve para exercitar o MOTOR DE ASSERTS de verdade.
// NÃO substitui um run com provider real: latency ~ms e cost 0 aqui, então os
// asserts latency/cost passam trivialmente e só ganham sentido contra a API real.

const NOTA1 = `ALERTA: Sentinel - autoscaler do sentinel-api atingiu o limite máximo de réplicas (60/60)
IMPACTO: fila de ingestão do Relay crescendo ~2k msgs/min e CPU do sentinel-api em 88%, risco de atraso no alerting em tempo real
HIPÓTESE INICIAL: tenant stark-industries passou a enviar ~4x o volume baseline após onboarding de nova região, saturando as réplicas atuais
AÇÃO IMEDIATA: aumentar manualmente o teto de réplicas do autoscaler do sentinel-api
ESCALAR PARA: @sentinel-core se a fila do Relay não estabilizar após o aumento`;

const NOTA2 = `ALERTA: Relay - taxa de rejeição de ingestão em 6% por 8min
IMPACTO: ingestão do tenant wakanda-systems sendo rejeitada, risco de perda de telemetry desse tenant
HIPÓTESE INICIAL: deploy das 02:55 saturou o buffer de ingestão do Relay
AÇÃO IMEDIATA: avaliar rollback do deploy das 02:55 ou aumento emergencial do buffer
ESCALAR PARA: @relay-core se a rejeição não cair após a ação`;

const NOTA3 = `ALERTA: Forge - lag do consumer em 9min e subindo
IMPACTO: batch forge-batch-ingest atrasado, Sentinel começando a atrasar dashboards a jusante
HIPÓTESE INICIAL: falha do job anterior deixou lote acumulado, sobrecarregando o processamento atual
AÇÃO IMEDIATA: reprocessar/reiniciar o forge-batch-ingest priorizando o backlog acumulado
ESCALAR PARA: @data-platform se o lag continuar subindo após o reprocessamento`;

const POD1 = `Pod: sentinel-api-7d9c8b6f4-h4m2t
Causa provável: OOMKilled. O limite de memória do container é 512Mi, mas o log mostra o heap subindo de 410Mi (ao carregar o cache de alertas) até 498Mi com "high GC pressure", culminando em "out of memory, shutting down process". O processo está estourando o próprio limite de memória sob carga normal de startup, não é um pico anômalo isolado.
Ação recomendada: Aumentar o limite de memória do deployment (ex.: para 768Mi–1Gi) como mitigação imediata, e abrir investigação sobre o tamanho do cache de alertas carregado no startup.`;

const POD2 = `Pod: sentinel-api-7d9c8b6f4-zzp10
Causa provável: ImagePullBackOff. O evento mostra "manifest unknown" ao tentar puxar a tag sentinel-api:2.9.2 do registry. A imagem com essa tag não existe no registry (não é problema de rede ou de credencial).
Ação recomendada: Verificar se o build/push da versão 2.9.2 foi concluído no CI. Se não foi, fazer rollback do deployment para a tag 2.9.1.

Pod: sentinel-ingest-8f7a9c5b-4dkqm
Causa provável: Pending por falta de recurso. O evento "FailedScheduling" mostra "0/6 nodes are available: 6 Insufficient cpu" — o pod pede 2 CPUs e nenhum node tem essa capacidade livre no momento.
Ação recomendada: Verificar ocupação de CPU dos nodes e escalar o node pool (adicionar node), ou revisar se o request de 2 CPU é necessário.`;

const POD3 = `Todos os pods do namespace estão saudáveis: nenhum em CrashLoop, ImagePull ou Pending. O único restart registrado (sentinel-worker, 1 restart há 3 dias) é antigo e isolado, sem recorrência. Nenhuma ação necessária.`;

const NETPOL = `apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: sentinel-prod
spec:
  podSelector: {}            # aplica a TODOS os pods do namespace
  policyTypes:
    - Ingress
    - Egress
  # sem blocos ingress/egress = nega toda entrada e toda saída por padrão.
  # As liberações vêm, de forma aditiva, na policy específica abaixo.
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sentinel-netpol
  namespace: sentinel-prod
spec:
  podSelector:
    matchLabels:
      app: sentinel          # aplica só aos pods do Sentinel
  policyTypes:
    - Ingress
    - Egress
  ingress:
    # ingress 1: consumo de eventos vindo do Relay (relay-prod, app=relay)
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: relay-prod
          podSelector:                      # MESMO item => AND (pod app=relay DENTRO de relay-prod)
            matchLabels:
              app: relay
    # ingress 2: tráfego do API gateway da plataforma (edge, app=api-gateway)
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: edge
          podSelector:
            matchLabels:
              app: api-gateway
  egress:
    # egress 1: consulta ao warehouse Postgres do Forge (forge-prod, app=forge, 5432/TCP)
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: forge-prod
          podSelector:
            matchLabels:
              app: forge
      ports:
        - protocol: TCP
          port: 5432
    # egress 2: busca no Cerebro / Elasticsearch (cerebro-prod, app=cerebro, 9200/TCP)
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: cerebro-prod
          podSelector:
            matchLabels:
              app: cerebro
      ports:
        - protocol: TCP
          port: 9200
    # egress 3: resolução de DNS interno (kube-system, k8s-app=kube-dns, 53 UDP+TCP)
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53`;

class MockProvider {
  constructor(options) {
    this.providerId = (options && options.id) || 'mock';
    this.config = (options && options.config) || {};
  }
  id() { return this.providerId; }

  async callApi(prompt, context) {
    const v = (context && context.vars) || {};
    let output = '';

    if (v.alerta_cru) {
      const a = String(v.alerta_cru);
      if (a.includes('autoscaler')) output = NOTA1;
      else if (a.includes('ingest reject')) output = NOTA2;
      else output = NOTA3;
    } else if (v.snapshot) {
      const s = String(v.snapshot);
      if (s.includes('h4m2t') && s.includes('OOMKilled')) output = POD1;
      else if (s.includes('zzp10')) output = POD2;
      else output = POD3;
    } else if (v.manifesto_permissivo) {
      output = NETPOL;
    }

    // cost: 0 e tokenUsage zerado => assert cost passa (trivialmente) no mock.
    return { output, cost: 0, tokenUsage: { total: 0, prompt: 0, completion: 0 } };
  }
}

module.exports = MockProvider;
