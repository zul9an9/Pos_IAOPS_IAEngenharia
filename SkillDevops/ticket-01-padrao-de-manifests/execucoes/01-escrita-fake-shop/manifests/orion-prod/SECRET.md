# Secret `orion-fake-shop-db` — não versionado (regra 3.3)

Criado fora do Git, antes do primeiro apply, por quem opera o cliente orion. Leva os quatro
rótulos da regra 1.3, como todo objeto:

```bash
kubectl -n orion-prod create secret generic orion-fake-shop-db \
  --from-literal=username=ecommerce \
  --from-literal=password="$(openssl rand -base64 24)"
kubectl -n orion-prod label secret orion-fake-shop-db \
  app.kubernetes.io/name=orion-fake-shop-db app.kubernetes.io/instance=orion-prod \
  app.kubernetes.io/part-of=orion app.kubernetes.io/managed-by=platform
```

Chaves consumidas: `username` (DB_USER, POSTGRES_USER) e `password` (DB_PASSWORD, POSTGRES_PASSWORD).
O namespace `orion-prod` é provisionado pelo Construct (regra 1.2) e não faz parte deste diretório.
