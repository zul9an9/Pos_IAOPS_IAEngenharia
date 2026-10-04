#!/usr/bin/env bash
# Captura as fixtures do cluster do laboratório SOMENTE com `kubectl get`.
# Remove valores de env e a anotação last-applied-configuration, que trazem
# senhas do laboratório em texto claro. Uso: bash tests/fixtures/capturar.sh
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-../../.venv/Scripts/python}"

capturar() {  # namespace tipo
  mkdir -p "$1"
  kubectl get "$2" -n "$1" -o json | "$PY" -c '
import json, sys
doc = json.load(sys.stdin)
for item in doc.get("items", []):
    item.get("metadata", {}).get("annotations", {}).pop(
        "kubectl.kubernetes.io/last-applied-configuration", None)
    specs = [item.get("spec", {})]
    specs.append(item.get("spec", {}).get("template", {}).get("spec", {}))
    for spec in specs:
        for chave in ("containers", "initContainers"):
            for c in spec.get(chave, []) or []:
                for var in c.get("env", []) or []:
                    if "value" in var:
                        var["value"] = "<removido>"
json.dump(doc, sys.stdout, indent=2, ensure_ascii=False)
' > "$1/$2.json"
}

for ns in nyx-prod nyx-stg orion-prod orion-stg kube-public; do
  for tipo in pods deployments services endpointslices events; do
    capturar "$ns" "$tipo"
  done
done
kubectl version -o json | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["serverVersion"]["gitVersion"])' > versao-do-servidor.txt
date -u +%Y-%m-%dT%H:%M:%SZ > capturado-em.txt
