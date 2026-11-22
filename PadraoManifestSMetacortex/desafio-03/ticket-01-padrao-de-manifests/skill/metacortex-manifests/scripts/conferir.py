#!/usr/bin/env python3
"""Conferência mecânica de manifests contra o Padrão de Manifests da Metacortex
(wiki de Plataforma, revisão 2026-07-29). Regras numeradas como no padrão: 1.1 ... 3.7.

Duas fontes, sem sobreposição:
  * Trivy (`trivy config`) cobre o que é do Kubernetes: securityContext, requests/limits,
    :latest, hostNetwork/hostPID/privileged. O script NÃO reimplementa essas regras; só traduz
    os IDs KSV para a numeração do padrão. É a mesma varredura que Segurança & Compliance roda
    no pipeline.
  * Este script cobre o que o Trivy não conhece: nomes, namespace, rótulos, seletores,
    anotação de dono, nome de container, réplicas e estratégia em prod, PDB, segredo em texto
    (env, ConfigMap, comentário), token de service account, service account dedicada, registry
    interno.

O que só se decide lendo o projeto sai como REVISAR, para o agente resolver pelo SKILL.md.

Severidades (seção "Exceções" do padrão):
  obrigatório -> FALHA   (barra; exceção só com aprovação escrita de S&C no PR, com prazo)
  proibido    -> FALHA   (barra; sem exceção para workload de cliente)
  recomendado -> AVISO   (não barra; exceção precisa de justificativa no PR)

Uso:   python3 conferir.py <arquivo-ou-diretório> [...] [--json saida.json] [--sem-trivy]
Saída: relatório Markdown no stdout.
Código de saída: 0 = nenhuma FALHA; 1 = há FALHA; 2 = erro de uso/leitura.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("ERRO: PyYAML não instalado (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

AQUI = Path(__file__).resolve().parent
IGNOREFILE = AQUI / "trivyignore"

OBR, PROIB, REC = "obrigatório", "proibido", "recomendado"
REGRAS = {  # id: (severidade, resumo)
    "1.1": (OBR, "Nome de recurso em kebab-case"),
    "1.2": (OBR, "Namespace <cliente>-<dev|stg|prod>"),
    "1.3": (OBR, "Quatro rótulos app.kubernetes.io/* em todo objeto"),
    "1.4": (OBR, "Seletor idêntico aos rótulos do pod"),
    "1.5": (REC, "Anotação metacortex.io/owner"),
    "1.6": (REC, "Nome de container igual ao componente"),
    "2.1": (OBR, "requests e limits de CPU e memória"),
    "2.2": (OBR, "readinessProbe e livenessProbe em endpoints reais"),
    "2.3": (OBR, "replicas >= 2 em prod"),
    "2.4": (OBR, "RollingUpdate maxUnavailable 0 / maxSurge 1 em prod"),
    "2.5": (REC, "PodDisruptionBudget em prod com mais de uma réplica"),
    "2.6": (REC, "terminationGracePeriodSeconds compatível com a aplicação"),
    "3.1": (PROIB, "Tag :latest"),
    "3.2": (OBR, "securityContext (non-root, UID 10001, sem escalonamento, FS read-only, drop ALL)"),
    "3.3": (PROIB, "Segredo em texto puro (env, ConfigMap, comentário)"),
    "3.4": (OBR, "automountServiceAccountToken: false"),
    "3.5": (REC, "ServiceAccount dedicada"),
    "3.6": (PROIB, "hostNetwork, hostPID, privileged"),
    "3.7": (OBR, "Imagem só de registry.metacortex.io"),
}

# Tradução do catálogo do Trivy (levantada rodando o Trivy 0.74.0; ver fluxo-de-origem/).
TRIVY_PARA_REGRA = {
    "KSV-0013": "3.1",
    "KSV-0001": "3.2", "KSV-0003": "3.2", "KSV-0004": "3.2", "KSV-0012": "3.2",
    "KSV-0014": "3.2", "KSV-0020": "3.2", "KSV-0106": "3.2", "KSV-0118": "3.2",
    "KSV-0009": "3.6", "KSV-0010": "3.6", "KSV-0017": "3.6",
    "KSV-0011": "2.1", "KSV-0015": "2.1", "KSV-0016": "2.1", "KSV-0018": "2.1",
}
SO_TRIVY = {"2.1", "3.2", "3.6"}  # regras conferidas exclusivamente pelo Trivy

WORKLOADS = {"Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob"}
ROTULOS = ["app.kubernetes.io/name", "app.kubernetes.io/instance",
           "app.kubernetes.io/part-of", "app.kubernetes.io/managed-by"]
MANAGED_BY = {"platform", "argocd", "helm"}
NOMES_GENERICOS = {"app", "main", "container"}
RE_KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
RE_NS = re.compile(r"^([a-z0-9]+)-(dev|stg|prod)$")
RE_VERSAO = re.compile(r"^v?\d+(\.\d+)+([-+][0-9A-Za-z.-]+)?$")
RE_SEGREDO_NOME = re.compile(r"(PASS|PWD|SECRET|TOKEN|APIKEY|API_KEY|PRIVATE_KEY|CREDENTIAL)", re.I)
RE_URL_CRED = re.compile(r"[a-z][a-z0-9+.-]*://[^/\s:@]+:[^/\s@]+@", re.I)


def achado(regra, veredito, recurso, detalhe, origem="script", arquivo=""):
    return {"regra": regra, "severidade": REGRAS.get(regra, ("—",))[0], "veredito": veredito,
            "recurso": recurso, "detalhe": detalhe, "origem": origem, "arquivo": arquivo}


def barra(regra):
    return "falha" if REGRAS[regra][0] in (OBR, PROIB) else "aviso"


# ----------------------------------------------------------------- leitura
def arquivos_de(caminhos):
    out = []
    for c in caminhos:
        p = Path(c)
        if p.is_dir():
            out += sorted(list(p.rglob("*.yaml")) + list(p.rglob("*.yml")))
        elif p.is_file():
            out.append(p)
        else:
            raise FileNotFoundError(c)
    return out


def carregar(arquivos):
    docs = []
    for a in arquivos:
        for d in yaml.safe_load_all(a.read_text(encoding="utf-8")):
            if isinstance(d, dict) and d.get("kind"):
                d["__arquivo"] = str(a)
                docs.append(d)
    return docs


def nome(d):
    return f'{d["kind"]}/{(d.get("metadata") or {}).get("name", "?")}'


def pod_template(d):
    spec = d.get("spec") or {}
    if d["kind"] == "CronJob":
        return ((spec.get("jobTemplate") or {}).get("spec") or {}).get("template") or {}
    return spec.get("template") or {}


def containers(pspec, init=True):
    return list(pspec.get("containers") or []) + (list(pspec.get("initContainers") or []) if init else [])


def ambiente(ns):
    m = RE_NS.match(ns or "")
    return m.group(2) if m else None


# ----------------------------------------------------------------- Trivy
def rodar_trivy(caminhos):
    exe = shutil.which("trivy")
    if not exe:
        return None, "trivy não encontrado no PATH"
    out = []
    for c in caminhos:
        cmd = [exe, "config", "-q", "-f", "json"]
        if IGNOREFILE.exists():
            cmd += ["--ignorefile", str(IGNOREFILE)]
        r = subprocess.run(cmd + [str(c)], capture_output=True, text=True)
        if r.returncode not in (0, 1) or not r.stdout.strip():
            return None, f"trivy falhou: {r.stderr.strip()[:300]}"
        for res in json.loads(r.stdout).get("Results", []) or []:
            for m in res.get("Misconfigurations", []) or []:
                out.append({"id": m["ID"], "sev": m["Severity"], "titulo": m["Title"],
                            "msg": m["Message"], "arquivo": res["Target"]})
    return out, None


# ----------------------------------------------------------------- regras do script
def conferir(docs, arquivos, trivy_rodou):
    A = []
    workloads = [d for d in docs if d["kind"] in WORKLOADS]
    sas = {((d.get("metadata") or {}).get("namespace"), (d.get("metadata") or {}).get("name")): d
           for d in docs if d["kind"] == "ServiceAccount"}
    pdbs = [d for d in docs if d["kind"] == "PodDisruptionBudget"]

    # 3.3 — varredura do texto cru: pega env, ConfigMap e comentário
    for a in arquivos:
        for i, linha in enumerate(a.read_text(encoding="utf-8").splitlines(), 1):
            if RE_URL_CRED.search(linha):
                onde = "comentário" if linha.lstrip().startswith("#") else "valor"
                A.append(achado("3.3", "falha", f"{a.name}:{i}", f"URL com usuário:senha em texto ({onde})", arquivo=str(a)))

    for d in docs:
        md = d.get("metadata") or {}
        n, arq, k = nome(d), d["__arquivo"], d["kind"]
        ns = md.get("namespace")

        if k == "Namespace":
            A.append(achado("1.2", "revisar", n, "o namespace é criado pelo Construct; normalmente não vai no manifesto do workload", arquivo=arq))
            continue

        nm = md.get("name", "")
        if not RE_KEBAB.match(nm):
            A.append(achado("1.1", "falha", n, f"'{nm}' não é kebab-case minúsculo (sem camelCase, underscore ou ponto)", arquivo=arq))

        if not ns:
            A.append(achado("1.2", "falha", n, "sem metadata.namespace explícito", arquivo=arq))
        elif not RE_NS.match(ns):
            A.append(achado("1.2", "falha", n, f"namespace '{ns}' fora de <cliente>-<dev|stg|prod>", arquivo=arq))

        lb = md.get("labels") or {}
        A += _rotulos(lb, n, ns, arq, "")

        if k == "Secret" and (d.get("data") or d.get("stringData")):
            A.append(achado("3.3", "falha", n, "Secret com valores no manifesto — segredo não se versiona no Git", arquivo=arq))
        if k == "ConfigMap":
            for chave in (d.get("data") or {}):
                if RE_SEGREDO_NOME.search(chave):
                    A.append(achado("3.3", "falha", n, f"chave '{chave}' com cara de segredo em ConfigMap — usar Secret", arquivo=arq))

    for d in workloads:
        md, spec = d.get("metadata") or {}, d.get("spec") or {}
        n, arq, k = nome(d), d["__arquivo"], d["kind"]
        ns = md.get("namespace")
        amb = ambiente(ns)
        tpl = pod_template(d)
        tl = ((tpl.get("metadata") or {}).get("labels")) or {}
        ps = tpl.get("spec") or {}

        A += _rotulos(tl, n, ns, arq, " (template do pod)")

        # 1.4 — matchLabels idêntico aos rótulos do template
        if k in ("Deployment", "StatefulSet", "DaemonSet"):
            sel = (spec.get("selector") or {}).get("matchLabels") or {}
            if not sel:
                A.append(achado("1.4", "falha", n, "sem selector.matchLabels", arquivo=arq))
            dif = {c: v for c, v in sel.items() if tl.get(c) != v}
            if dif:
                A.append(achado("1.4", "falha", n, f"matchLabels diverge do template: {dif} vs {({c: tl.get(c) for c in dif})}", arquivo=arq))

        # 1.5
        if not (md.get("annotations") or {}).get("metacortex.io/owner"):
            A.append(achado("1.5", "aviso", n, "sem metacortex.io/owner (justificar no PR)", arquivo=arq))

        # 1.6 e 3.7 e 3.1 (complemento)
        for c in containers(ps):
            cn = f"{n}:{c.get('name')}"
            if c.get("name") in NOMES_GENERICOS:
                A.append(achado("1.6", "aviso", cn, f"container chamado '{c.get('name')}' — use o nome do componente", arquivo=arq))
            img = c.get("image", "")
            if not img.startswith("registry.metacortex.io/"):
                A.append(achado("3.7", "falha", cn, f"imagem '{img}' fora de registry.metacortex.io — entra pelo Loom", arquivo=arq))
            if "@sha256:" not in img:
                ultimo = img.rsplit("/", 1)[-1]
                tag = ultimo.split(":", 1)[1] if ":" in ultimo else ""
                if (not tag or tag == "latest") and not trivy_rodou:
                    A.append(achado("3.1", "falha", cn, f"tag '{tag or '(nenhuma)'}' — :latest/sem tag é proibido", arquivo=arq))
                elif tag and tag != "latest" and not RE_VERSAO.match(tag):
                    A.append(achado("3.1", "revisar", cn, f"tag '{tag}' não parece versão; confirmar que é imutável", arquivo=arq))

        # 2.2 — presença (destino é contextual)
        if k in ("Deployment", "StatefulSet", "DaemonSet"):
            for c in containers(ps, init=False):
                cn = f"{n}:{c.get('name')}"
                for p in ("readinessProbe", "livenessProbe"):
                    if p not in c:
                        A.append(achado("2.2", "falha", cn, f"sem {p}", arquivo=arq))
                alvos = {p: _alvo(c[p]) for p in ("startupProbe", "readinessProbe", "livenessProbe") if c.get(p)}
                msg = ("confirmar no código que os destinos existem; readiness e liveness NÃO podem ser o mesmo endpoint que checa banco. "
                       + (json.dumps(alvos, ensure_ascii=False) if alvos else "Nenhuma probe declarada — descobrir endpoints no projeto."))
                if alvos.get("readinessProbe") and alvos.get("readinessProbe") == alvos.get("livenessProbe"):
                    msg = "readiness e liveness no MESMO destino — verificar se ele toca o banco. " + msg
                A.append(achado("2.2", "revisar", cn, msg, arquivo=arq))

        # 2.3 / 2.4 / 2.5 — só prod
        replicas = spec.get("replicas", 1) if k in ("Deployment", "StatefulSet") else None
        if amb == "prod" and replicas is not None:
            if replicas < 2:
                A.append(achado("2.3", "falha", n, f"replicas={replicas} em prod (exceção só com aprovação escrita de S&C no PR, com prazo)", arquivo=arq))
            elif not any(_pdb_casa(p, tl, ns) for p in pdbs):
                A.append(achado("2.5", "aviso", n, f"replicas={replicas} em prod sem PodDisruptionBudget (minAvailable >= 1)", arquivo=arq))
        if amb == "prod" and k == "Deployment":
            st = spec.get("strategy") or {}
            ru = st.get("rollingUpdate") or {}
            if st.get("type", "RollingUpdate") != "RollingUpdate" or ru.get("maxUnavailable") != 0 or ru.get("maxSurge") != 1:
                A.append(achado("2.4", "falha", n, f"strategy {st or '(padrão do Kubernetes: 25%/25%)'} — prod exige RollingUpdate maxUnavailable: 0, maxSurge: 1", arquivo=arq))

        # 3.3 — nome sensível com valor literal (URL já é pega na varredura do texto)
        for c in containers(ps):
            for e in c.get("env") or []:
                if "value" in e and RE_SEGREDO_NOME.search(e["name"]) and not RE_URL_CRED.search(str(e["value"])):
                    A.append(achado("3.3", "falha", f"{n}:{c.get('name')}", f"{e['name']} com valor literal — usar secretKeyRef", arquivo=arq))

        # 3.4 / 3.5
        sa_nome = ps.get("serviceAccountName") or ps.get("serviceAccount") or "default"
        auto = ps.get("automountServiceAccountToken")
        if auto is None:
            auto = (sas.get((ns, sa_nome)) or {}).get("automountServiceAccountToken")
        if auto is not False:
            A.append(achado("3.4", "falha", n, "automountServiceAccountToken não é false (no pod nem na ServiceAccount do conjunto)", arquivo=arq))
        if sa_nome == "default":
            A.append(achado("3.5", "aviso", n, "usa a ServiceAccount default do namespace", arquivo=arq))

        # Pendências contextuais
        envs = sorted({e["name"] for c in containers(ps) for e in (c.get("env") or [])})
        A.append(achado("3.3", "revisar", n, f"confrontar as variáveis entregues {envs} com as que o código lê, e decidir quais são sensíveis", arquivo=arq))
        A.append(achado("3.2", "revisar", n, "com readOnlyRootFilesystem, confirmar no projeto onde a aplicação escreve e montar emptyDir", arquivo=arq))
        A.append(achado("2.1", "revisar", n, "limits de memória devem ficar entre 1,5x e 2x o consumo observado em regime — conferir contra métrica real", arquivo=arq))
        A.append(achado("2.6", "revisar", n, f"terminationGracePeriodSeconds={ps.get('terminationGracePeriodSeconds', '30 (padrão)')}: a aplicação trata SIGTERM e drena nesse tempo?", arquivo=arq))
        A.append(achado("3.4", "revisar", n, "confirmar no código que a aplicação não fala com o apiserver", arquivo=arq))

    # 1.4 — Service
    for s in (d for d in docs if d["kind"] == "Service"):
        sel = (s.get("spec") or {}).get("selector") or {}
        ns = (s.get("metadata") or {}).get("namespace")
        alvos = [w for w in workloads if (w.get("metadata") or {}).get("namespace") == ns and
                 all(((pod_template(w).get("metadata") or {}).get("labels") or {}).get(c) == v for c, v in sel.items())]
        if sel and not alvos:
            A.append(achado("1.4", "falha", nome(s), f"selector {sel} não casa com nenhum pod do conjunto — o Service fica sem endpoint", arquivo=s["__arquivo"]))
        portas = [(p.get("containerPort"), p.get("name")) for w in alvos
                  for c in containers(pod_template(w).get("spec") or {}, init=False) for p in (c.get("ports") or [])]
        for p in (s.get("spec") or {}).get("ports") or []:
            tp = p.get("targetPort", p.get("port"))
            if alvos and not any(tp in pr for pr in portas):
                A.append(achado("1.4", "falha", nome(s), f"targetPort {tp} não existe nos pods selecionados", arquivo=s["__arquivo"]))
    return A


def _rotulos(lb, n, ns, arq, onde):
    out = []
    faltam = [r for r in ROTULOS if r not in lb]
    if faltam:
        extra = " (o rótulo curto 'app' não substitui os quatro)" if "app" in lb else ""
        out.append(achado("1.3", "falha", n, f"rótulos ausentes{onde}: {', '.join(faltam)}{extra}", arquivo=arq))
    mb = lb.get("app.kubernetes.io/managed-by")
    if mb is not None and mb not in MANAGED_BY:
        out.append(achado("1.3", "falha", n, f"managed-by='{mb}'{onde} — valores válidos: platform | argocd | helm", arquivo=arq))
    inst = lb.get("app.kubernetes.io/instance")
    if inst is not None and ns and inst != ns:
        out.append(achado("1.3", "revisar", n, f"instance='{inst}'{onde} difere do namespace '{ns}' (o padrão usa a instalação, ex.: nyx-prod)", arquivo=arq))
    for r in ROTULOS:
        v = lb.get(r)
        if v is not None and not RE_KEBAB.match(str(v)):
            out.append(achado("1.3", "falha", n, f"{r}='{v}'{onde} fora de kebab-case", arquivo=arq))
    return out


def _alvo(p):
    if "httpGet" in p:
        return f"http {p['httpGet'].get('path', '/')}:{p['httpGet'].get('port')}"
    if "tcpSocket" in p:
        return f"tcp :{p['tcpSocket'].get('port')}"
    if "exec" in p:
        return "exec " + " ".join(p["exec"].get("command", []))
    if "grpc" in p:
        return f"grpc :{p['grpc'].get('port')}"
    return "?"


def _pdb_casa(pdb, labels, ns):
    if (pdb.get("metadata") or {}).get("namespace") != ns:
        return False
    sel = ((pdb.get("spec") or {}).get("selector") or {}).get("matchLabels") or {}
    ma = (pdb.get("spec") or {}).get("minAvailable")
    return bool(sel) and all(labels.get(c) == v for c, v in sel.items()) and (ma is None or str(ma) not in ("0", "0%"))


# ----------------------------------------------------------------- relatório
def relatorio(caminhos, A, trivy, erro):
    fal = [a for a in A if a["veredito"] == "falha"]
    avi = [a for a in A if a["veredito"] == "aviso"]
    rev = [a for a in A if a["veredito"] == "revisar"]
    L = ["# Conferência — Padrão de Manifests da Metacortex (rev. 2026-07-29)", "",
         f"Entrada: {', '.join(map(str, caminhos))}  ",
         f"Trivy: {'executado' if trivy is not None else 'NÃO executado (' + erro + ')'}", "",
         "## Resumo por regra", "", "| Regra | Severidade | Descrição | Resultado | Fonte |", "|---|---|---|---|---|"]
    for r, (sev, desc) in REGRAS.items():
        f = [a for a in fal + avi if a["regra"] == r]
        rv = [a for a in rev if a["regra"] == r]
        fonte = "trivy" if r in SO_TRIVY else ("trivy + script" if r == "3.1" else "script")
        if r in SO_TRIVY and trivy is None:
            res = "não verificado (sem trivy)"
        elif f:
            res = f"**{f[0]['veredito']} ({len(f)})**"
        elif rv:
            res = "revisar (ler projeto)"
        else:
            res = "ok"
        L.append(f"| {r} | {sev} | {desc} | {res} | {fonte} |")

    for titulo, grupo in (("Falhas — barram a subida", fal), ("Avisos — recomendado; exceção precisa de justificativa no PR", avi)):
        L += ["", f"## {titulo}", ""]
        if not grupo:
            L.append("Nenhuma.")
            continue
        L += ["| Regra | Recurso | Detalhe | Fonte |", "|---|---|---|---|"]
        for a in sorted(grupo, key=lambda x: ([int(p) for p in x["regra"].split(".")], x["recurso"])):
            L.append(f"| {a['regra']} | `{a['recurso']}` | {a['detalhe']} | {a['origem']} |")

    L += ["", "## Revisar lendo o projeto (instrução do SKILL.md)", ""]
    L += [f"- **{a['regra']}** `{a['recurso']}` — {a['detalhe']}" for a in rev] or ["Nada."]

    extras = [t for t in (trivy or []) if t["id"] not in TRIVY_PARA_REGRA]
    if extras:
        L += ["", "## Informativo — catálogo do Trivy fora do padrão (não barra)", ""]
        L += [f"- {t['id']} ({t['sev']}) {t['titulo']} — {t['msg']}" for t in extras]
    L += ["", f"**Total:** {len(fal)} falha(s), {len(avi)} aviso(s), {len(rev)} ponto(s) a revisar lendo o projeto."]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("caminhos", nargs="+")
    ap.add_argument("--json", help="grava os achados em JSON")
    ap.add_argument("--sem-trivy", action="store_true", help="não executa o trivy")
    a = ap.parse_args()
    try:
        arqs = arquivos_de(a.caminhos)
        docs = carregar(arqs)
    except (FileNotFoundError, yaml.YAMLError) as e:
        print(f"ERRO ao ler manifests: {e}", file=sys.stderr)
        return 2
    if not docs:
        print("ERRO: nenhum documento Kubernetes encontrado", file=sys.stderr)
        return 2

    trivy, erro = (None, "desativado por --sem-trivy") if a.sem_trivy else rodar_trivy(a.caminhos)
    A = conferir(docs, arqs, trivy is not None)
    for t in trivy or []:
        if t["id"] in TRIVY_PARA_REGRA:
            A.append(achado(TRIVY_PARA_REGRA[t["id"]], "falha", Path(t["arquivo"]).name,
                            f"{t['id']} ({t['sev']}): {t['msg']}", origem="trivy", arquivo=t["arquivo"]))
    print(relatorio(a.caminhos, A, trivy, erro))
    if a.json:
        Path(a.json).write_text(json.dumps({"achados": A, "trivy_fora_do_padrao":
                                            [t for t in (trivy or []) if t["id"] not in TRIVY_PARA_REGRA]},
                                           ensure_ascii=False, indent=2), encoding="utf-8")
    return 1 if any(x["veredito"] == "falha" for x in A) else 0


if __name__ == "__main__":
    sys.exit(main())
