#!/usr/bin/env python3
"""k.py — kubectl SOMENTE LEITURA que registra a triagem manual (Ticket 02, fluxo de origem).

Por que existe: a skill de triagem tem que nascer de um fluxo rodado de verdade. Este wrapper
grava, na ordem, cada comando, a saída e as notas de raciocínio ("por que olhei isso agora"),
num log por chamado. É esse log que vira o método.

Uso:
  python k.py --chamado <N> inicio "<sintoma que o cliente declarou>"
  python k.py --chamado <N> nota "<por que vou olhar isto agora>"
  python k.py --chamado <N> <comando kubectl de leitura>     (ex.: get pods -n <namespace>)
  python k.py --chamado <N> causa "<camada> — <causa> — <evidência>"
  python k.py --chamado <N> fim

Os logs ficam em fluxo-de-origem/logs/chamado-<N>.md (a pasta é criada no primeiro registro).
Sem argumentos, o k.py só mostra esta ajuda e não grava nada.

Somente verbos de leitura passam (get, describe, logs, events, top, explain, api-resources,
auth can-i, version, cluster-info, config view/current-context/get-contexts). Qualquer outro é
recusado e a recusa também fica no log.
"""
import datetime as dt
import shutil
import subprocess
import sys
from pathlib import Path

LEITURA = {"get", "describe", "logs", "events", "top", "explain", "api-resources",
           "api-versions", "version", "cluster-info"}
LEITURA_COMPOSTA = {("auth", "can-i"), ("config", "view"), ("config", "current-context"),
                    ("config", "get-contexts")}
PROIBIDO_EM_LOGS = {"-f", "--follow"}  # não travar o log

AQUI = Path(__file__).resolve().parent
LOGS = AQUI / "logs"


def agora():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def escrever(chamado, texto):
    LOGS.mkdir(exist_ok=True)
    with open(LOGS / f"chamado-{chamado}.md", "a", encoding="utf-8") as f:
        f.write(texto + "\n")


def main():
    args = sys.argv[1:]
    if len(args) < 3 or args[0] != "--chamado":
        print(__doc__)
        return 2
    chamado, args = args[1], args[2:]
    verbo = args[0]

    if verbo == "inicio":
        escrever(chamado, f"# Triagem manual — chamado {chamado}\n\n**Início:** {agora()}  \n"
                          f"**Sintoma declarado:** {' '.join(args[1:])}\n")
        print("registrado.")
        return 0
    if verbo in ("nota", "causa", "fim"):
        marca = {"nota": "> **Raciocínio**", "causa": "## Causa identificada",
                 "fim": "---\n**Fim:**"}[verbo]
        texto = " ".join(args[1:])
        escrever(chamado, f"\n{marca} ({agora()}): {texto}\n" if verbo != "fim" else f"\n{marca} {agora()}\n")
        print("registrado.")
        return 0

    le = verbo in LEITURA or tuple(args[:2]) in LEITURA_COMPOSTA
    if not le:
        escrever(chamado, f"\n### {agora()} — RECUSADO (escrita): `kubectl {' '.join(args)}`\n")
        print(f"RECUSADO: '{verbo}' não é leitura. A triagem lê, nunca escreve.", file=sys.stderr)
        return 3
    if verbo == "logs" and PROIBIDO_EM_LOGS & set(args):
        print("Use logs sem -f (o log precisa terminar para ser registrado).", file=sys.stderr)
        return 2

    kubectl = shutil.which("kubectl")
    if not kubectl:
        print("kubectl não encontrado no PATH", file=sys.stderr)
        return 2
    t0 = dt.datetime.now()
    r = subprocess.run([kubectl, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    ms = int((dt.datetime.now() - t0).total_seconds() * 1000)
    saida = (r.stdout + (("\n[stderr]\n" + r.stderr) if r.stderr.strip() else "")).rstrip()
    print(saida)
    escrever(chamado, f"\n### {agora()} — `kubectl {' '.join(args)}` (rc={r.returncode}, {ms} ms)\n"
                      f"```\n{saida}\n```")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
