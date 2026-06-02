# [BEFORE]
Tenho um Kubernetes Deployment legado que foi escrito há três anos e nunca foi atualizado. Ele tem vários problemas críticos de segurança e disponibilidade:
yamlapiVersion: apps/v1
kind: Deployment
metadata:
  name: chronos-api
  namespace: production
spec:
  replicas: 1
  selector:
    matchLabels:
      app: chronos-api
  template:
    metadata:
      labels:
        app: chronos-api
    spec:
      containers:
      - name: api
        image: chronos-api:latest
        ports:
        - containerPort: 8080
        env:
        - name: DB_PASSWORD
          value: "P@ssw0rd2023!"
        - name: JWT_SECRET
          value: "hvt-jwt-prod-secret"
Os problemas identificados são: réplica única (zero alta disponibilidade), imagem com tag latest (não reproduzível), credenciais hardcoded no manifest (violação de segurança), ausência de resource requests e limits, ausência de liveness e readiness probes, e container rodando potencialmente como root.

# [AFTER]
Preciso de uma versão modernizada desse manifest que atenda ao padrão atual de produção da empresa, com obrigatoriamente:

Alta disponibilidade: mínimo 3 réplicas com podAntiAffinity para distribuição entre nodes
Imagem versionada: substituir latest por um placeholder explícito como chronos-api:1.0.0
Secrets externalizados: variáveis sensíveis referenciadas via secretKeyRef, sem nenhum valor literal no manifest
Resource requests e limits: valores realistas para uma API (ex: 256Mi/500m requests, 512Mi/1000m limits)
Liveness probe: verifica se o processo está vivo (ex: HTTP GET /healthz)
Readiness probe: verifica se o pod está pronto para receber tráfego (ex: HTTP GET /ready)
SecurityContext não-root: runAsNonRoot: true, runAsUser: 1000, readOnlyRootFilesystem: true, allowPrivilegeEscalation: false
RollingUpdate strategy com maxUnavailable: 0 para deploy sem downtime

# [BRIDGE]
Reescreva o manifest acima aplicando todas as mudanças listadas. Para cada seção modificada, adicione um comentário inline # explicando brevemente o motivo da mudança. Ao final, inclua um bloco separado com o manifest do Secret do Kubernetes que deve acompanhar este Deployment. Não remova nenhuma funcionalidade existente; apenas modernize e adicione o que falta.

