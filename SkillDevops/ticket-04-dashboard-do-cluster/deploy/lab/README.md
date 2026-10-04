# RBAC do painel no laboratório

Estes comandos são para **quem opera** executar à mão. Eles escrevem no cluster
(aplicam RBAC e pedem token). O painel e os scripts do projeto nunca executam
nada disso.

Os kubeconfigs gerados ficam em arquivos próprios e o seu `~/.kube/config` não
é alterado. Rode tudo no Git Bash, a partir da raiz do projeto, com o contexto
`kind-metacortex-lab` como corrente.

## 1. Aplicar os manifestos

```bash
kubectl apply -f deploy/rbac/clusterrole-somente-leitura.yaml   # papel de exemplo
kubectl apply -f deploy/lab/sem-eventos.yaml                    # cenário 8.5
kubectl apply -f deploy/lab/so-um-namespace.yaml                # cenário 8.9
```

## 2. Gerar um kubeconfig por ServiceAccount

A função abaixo cria `<arquivo>` com um token de 8 horas para a ServiceAccount
informada. O terceiro argumento, opcional, define o `namespace` do contexto.

```bash
gerar_kubeconfig() {  # arquivo serviceaccount [namespace]
  local arquivo="$1" sa="$2" ns="${3:-}"
  local servidor token
  servidor=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
  kubectl config view --minify --raw \
    -o jsonpath='{.clusters[0].cluster.certificate-authority-data}' | base64 -d > "$arquivo.ca"
  token=$(kubectl create token "$sa" -n painel-cluster --duration=8h)
  kubectl config --kubeconfig="$arquivo" set-cluster lab --server="$servidor" \
    --certificate-authority="$arquivo.ca" --embed-certs=true
  kubectl config --kubeconfig="$arquivo" set-credentials "$sa" --token="$token"
  kubectl config --kubeconfig="$arquivo" set-context painel --cluster=lab --user="$sa" \
    ${ns:+--namespace="$ns"}
  kubectl config --kubeconfig="$arquivo" use-context painel
  rm -f "$arquivo.ca"
}

mkdir -p .kubeconfigs-lab
gerar_kubeconfig .kubeconfigs-lab/somente-leitura.yaml painel-cluster
gerar_kubeconfig .kubeconfigs-lab/sem-eventos.yaml     painel-sem-eventos
gerar_kubeconfig .kubeconfigs-lab/so-nyx-prod.yaml     painel-so-nyx-prod nyx-prod
```

## 3. Rodar o painel com um desses kubeconfigs

```bash
KUBECONFIG=.kubeconfigs-lab/sem-eventos.yaml .venv/Scripts/python -m painel_cluster
```

## 4. Remover tudo do laboratório

```bash
kubectl delete -f deploy/lab/so-um-namespace.yaml -f deploy/lab/sem-eventos.yaml \
  -f deploy/rbac/clusterrole-somente-leitura.yaml
rm -rf .kubeconfigs-lab
```
