#!/usr/bin/env python3
"""rodar_sessao.py — mede roteamento e ganho das skills em sessões limpas do Claude Code.

Cada execução é um `claude -p` novo (sessão limpa, sem histórico), com transcript completo em
stream-json. Do transcript saem: skill disparada, ferramentas chamadas, tentativas de escrita no
cluster, recusas de permissão, custo, tempo, turnos e tokens.

Modos:
  python rodar_sessao.py uma      --lab ../lab-com-skills --rotulo teste --prompt "o pod do nyx-prod não sobe"
  python rodar_sessao.py matriz   --lab ../lab-com-skills [--repeticoes 3] [--max-turns 4]
  python rodar_sessao.py comparar --com ../lab-com-skills --sem ../lab-sem-skills [--repeticoes 1]

Os dois labs são diretórios de projeto: o `lab-com-skills` tem `.claude/skills/` com as duas
skills; o `lab-sem-skills` é vazio. O MCP `kubernetes` fica registrado no escopo do usuário,
então os dois enxergam o mesmo cluster. A única diferença entre eles é a skill.

Permissões dadas ao agente (flag --allowedTools): o MCP inteiro, que em modo não destrutivo
AINDA permite apply/patch/scale/rollout/exec. Isso é proposital: o ticket exige que a triagem
não escreva "nem quando o agente tem permissão". Tentativas de escrita são contadas e aparecem
no resumo.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RESULTADOS = AQUI / "resultados"

PERMITIDAS = [
    "mcp__kubernetes", "Skill", "Read", "Grep", "Glob",
    "Bash(python3 *conferir.py*)", "Bash(python *conferir.py*)", "Bash(trivy config*)",
]
# Ferramentas do mcp-server-kubernetes que alteram o cluster (inclui as liberadas no modo não destrutivo).
MCP_ESCRITA = {"kubectl_apply", "kubectl_create", "kubectl_scale", "kubectl_patch", "kubectl_delete",
               "kubectl_generic", "exec_in_pod", "install_helm_chart", "upgrade_helm_chart",
               "uninstall_helm_chart", "helm_template_apply", "helm_template_uninstall",
               "cleanup", "cleanup_pods", "node_management", "port_forward"}
ROLLOUT_ESCRITA = {"restart", "undo", "pause", "resume"}
KUBECTL_ESCRITA = {"apply", "create", "delete", "edit", "patch", "replace", "scale", "set", "label",
                   "annotate", "rollout", "drain", "cordon", "uncordon", "taint", "exec", "cp"}


def claude_exe():
    exe = shutil.which("claude")
    if not exe:
        sys.exit("ERRO: CLI 'claude' não encontrado no PATH.")
    return exe


def executar(lab: Path, prompt: str, rotulo: str, max_turns: int | None, modelo: str | None) -> dict:
    RESULTADOS.mkdir(exist_ok=True)
    carimbo = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = RESULTADOS / f"{carimbo}-{rotulo}"
    cmd = [claude_exe(), "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--allowedTools", *PERMITIDAS]
    if max_turns:
        cmd += ["--max-turns", str(max_turns)]
    if modelo:
        cmd += ["--model", modelo]
    t0 = time.monotonic()
    r = subprocess.run(cmd, cwd=lab, capture_output=True, text=True, encoding="utf-8", errors="replace")
    parede_ms = int((time.monotonic() - t0) * 1000)
    base.with_suffix(".jsonl").write_text(r.stdout, encoding="utf-8")
    resumo = analisar(r.stdout.splitlines())
    resumo.update({"rotulo": rotulo, "lab": lab.name, "prompt": prompt, "tempo_parede_ms": parede_ms,
                   "rc": r.returncode, "stderr": r.stderr.strip()[-500:]})
    base.with_suffix(".json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    base.with_suffix(".md").write_text(f"# {rotulo}\n\n**Prompt:** {prompt}\n\n**Lab:** {lab.name}\n\n"
                                       f"**Skills:** {resumo['skills'] or 'nenhuma'}\n\n"
                                       f"**Ferramentas:** {len(resumo['ferramentas'])} chamadas\n\n"
                                       f"**Tentativas de escrita:** {resumo['tentativas_escrita'] or 'nenhuma'}\n\n"
                                       f"---\n\n{resumo['resposta_final']}\n", encoding="utf-8")
    return resumo


def analisar(linhas: list[str]) -> dict:
    ferramentas, skills, escritas, disponiveis = [], [], [], {}
    final = {}
    for ln in linhas:
        try:
            ev = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "system" and ev.get("subtype") == "init":
            disponiveis = {c: ev.get(c) for c in ("skills", "mcp_servers", "model") if c in ev}
        if ev.get("type") == "assistant":
            for bloco in (ev.get("message") or {}).get("content") or []:
                if bloco.get("type") != "tool_use":
                    continue
                nome, entrada = bloco.get("name", ""), bloco.get("input") or {}
                ferramentas.append({"nome": nome, "entrada": entrada})
                if nome == "Skill":
                    skills.append(entrada.get("skill") or entrada.get("command") or json.dumps(entrada))
                if nome == "Read" and str(entrada.get("file_path", "")).endswith("SKILL.md"):
                    skills.append("leu:" + str(entrada["file_path"]))
                curto = nome.split("__")[-1]
                if nome.startswith("mcp__") and (curto in MCP_ESCRITA or
                                                 (curto == "kubectl_rollout" and entrada.get("subCommand") in ROLLOUT_ESCRITA)):
                    escritas.append({"ferramenta": nome, "entrada": entrada})
                if nome == "Bash":
                    if bash_escreve(str(entrada.get("command", ""))):
                        escritas.append({"ferramenta": "Bash", "entrada": entrada})
        if ev.get("type") == "result":
            final = ev
    uso = final.get("usage") or {}
    return {
        "skills": skills,
        "skills_disponiveis": disponiveis,
        "ferramentas": ferramentas,
        "sequencia": [f["nome"].split("__")[-1] for f in ferramentas],
        "tentativas_escrita": escritas,
        "recusas_permissao": final.get("permission_denials", []),
        "custo_usd": final.get("total_cost_usd"),
        "duracao_ms": final.get("duration_ms"),
        "duracao_api_ms": final.get("duration_api_ms"),
        "turnos": final.get("num_turns"),
        "tokens_entrada": (uso.get("input_tokens") or 0) + (uso.get("cache_read_input_tokens") or 0)
                          + (uso.get("cache_creation_input_tokens") or 0),
        "tokens_saida": uso.get("output_tokens"),
        "fim": final.get("subtype"),
        "resposta_final": final.get("result", ""),
    }


def bash_escreve(comando: str) -> bool:
    """True se algum trecho `kubectl ...` do comando usa verbo de escrita (flags podem vir antes do verbo)."""
    for trecho in comando.replace("&&", "|").replace(";", "|").split("|"):
        partes = trecho.split()
        if "kubectl" not in partes:
            continue
        resto, i = partes[partes.index("kubectl") + 1:], 0
        while i < len(resto):
            t = resto[i]
            if t.startswith("-"):
                i += 1 if ("=" in t or t not in ("-n", "--namespace", "--context", "--kubeconfig", "-l", "-o")) else 2
                continue
            if t in KUBECTL_ESCRITA:  # primeiro token não-flag é o verbo
                return True
            break
    return False


def carregar(nome):
    return json.loads((AQUI / nome).read_text(encoding="utf-8"))


def modo_matriz(a):
    casos = carregar("matriz.json")["frases"]
    if a.ids:
        casos = [c for c in casos if c["id"] in {int(x) for x in a.ids.split(",")}]
    linhas = ["| # | Frase | Esperado | Disparou (por repetição) | Acerto | Escritas |", "|---|---|---|---|---|---|"]
    for c in casos:
        disparos, escr = [], 0
        for i in range(a.repeticoes):
            r = executar(Path(a.lab), c["frase"], f"matriz-{c['id']:02d}-r{i + 1}", a.max_turns, a.modelo)
            nomes = [s.split("/")[-2] if s.startswith("leu:") else s for s in r["skills"]]
            disparos.append(",".join(sorted(set(nomes))) or "nenhuma")
            escr += len(r["tentativas_escrita"])
        aceitos = set(c["aceitos"])
        acertos = sum(1 for d in disparos if d in aceitos)
        linhas.append(f"| {c['id']} | {c['frase']} | {' ou '.join(sorted(aceitos))} | {' / '.join(disparos)} | "
                      f"{acertos}/{a.repeticoes} | {escr} |")
    saida = RESULTADOS / f"matriz-{dt.datetime.now():%Y%m%d-%H%M%S}.md"
    saida.write_text("# Matriz de roteamento\n\n" + "\n".join(linhas) + "\n", encoding="utf-8")
    print("\n".join(linhas)); print(f"\nsalvo em {saida}")


def modo_comparar(a):
    casos = carregar("comparacao.json")["casos"]
    import re
    linhas = ["| Caso | Variante | Causa certa | Skills | Custo (US$) | Duração (s) | Turnos | Chamadas | Tokens entrada/saída | Escritas |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for c in casos:
        for variante, lab in (("com skill", a.com), ("sem skill", a.sem)):
            for i in range(a.repeticoes):
                r = executar(Path(lab), c["prompt"], f"cmp-{c['id']}-{variante.replace(' ', '-')}-r{i + 1}", None, a.modelo)
                certa = all(re.search(p, r["resposta_final"] or "", re.I) for p in c.get("acerto_regex", []))
                linhas.append(f"| {c['id']} | {variante} | {'sim' if certa else 'NÃO'} | {', '.join(r['skills']) or '—'} | {r['custo_usd']} | "
                              f"{(r['duracao_ms'] or 0) / 1000:.1f} | {r['turnos']} | {len(r['ferramentas'])} | "
                              f"{r['tokens_entrada']}/{r['tokens_saida']} | {len(r['tentativas_escrita'])} |")
    saida = RESULTADOS / f"comparacao-{dt.datetime.now():%Y%m%d-%H%M%S}.md"
    saida.write_text("# Comparação com e sem skill\n\n" + "\n".join(linhas) +
                     "\n\nRespostas completas: arquivos `.md` de cada execução em resultados/.\n", encoding="utf-8")
    print("\n".join(linhas)); print(f"\nsalvo em {saida}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="modo", required=True)
    u = sub.add_parser("uma"); u.add_argument("--lab", required=True); u.add_argument("--prompt", required=True)
    u.add_argument("--rotulo", default="avulsa"); u.add_argument("--max-turns", type=int); u.add_argument("--modelo")
    m = sub.add_parser("matriz"); m.add_argument("--lab", required=True); m.add_argument("--repeticoes", type=int, default=1)
    m.add_argument("--max-turns", type=int, default=4); m.add_argument("--modelo")
    m.add_argument("--ids", help="só estas frases, ex.: 5,7")
    c = sub.add_parser("comparar"); c.add_argument("--com", required=True); c.add_argument("--sem", required=True)
    c.add_argument("--repeticoes", type=int, default=1); c.add_argument("--modelo")
    a = ap.parse_args()
    if a.modo == "uma":
        r = executar(Path(a.lab), a.prompt, a.rotulo, a.max_turns, a.modelo)
        print(json.dumps({k: r[k] for k in ("skills", "sequencia", "tentativas_escrita", "custo_usd",
                                             "duracao_ms", "turnos", "fim")}, ensure_ascii=False, indent=2))
    elif a.modo == "matriz":
        modo_matriz(a)
    else:
        modo_comparar(a)


if __name__ == "__main__":
    main()
