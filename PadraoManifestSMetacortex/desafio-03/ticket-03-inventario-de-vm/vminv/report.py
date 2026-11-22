"""Relatórios JSON (formato do Roster) e Markdown (para o plantão).

Os relatórios circulam fora da máquina do operador: não carregam o caminho nem
o conteúdo da chave privada (que este módulo sequer conhece).

No JSON, um campo que a coleta não leu é `null` — nunca `[]`, `0`, `false` ou
`""`, que são valores reais. O motivo viaja na entrada de `conformidade`.
"""

import json

from . import compliance

ORDEM_SEVERIDADE = {"critico": 0, "alto": 1, "medio": 2}
SUFIXOS_DE_UNIDADE = (".service", ".socket")


# ------------------------------------------------------------------- JSON

def _valor(inventario, nome):
    fato = inventario.fatos[nome]
    return fato.valor if fato.lido else None


def _sem_sufixo(nome):
    for sufixo in SUFIXOS_DE_UNIDADE:
        if nome.endswith(sufixo):
            return nome[:-len(sufixo)]
    return nome


def _identificacao(chave):
    comentario = chave.get("comentario") or ""
    if comentario:
        return comentario
    fingerprint = chave.get("fingerprint") or {}
    return fingerprint["value"] if fingerprint.get("read") else None


def _projetar_inventario(inv):
    so = _valor(inv, "so")
    swap = _valor(inv, "swap")
    ntp = _valor(inv, "ntp")
    servicos = _valor(inv, "servicos")
    portas = _valor(inv, "portas")
    chaves = _valor(inv, "chaves_ssh")
    login_root = _valor(inv, "ssh_login_root")
    return {
        "so": {"distribuicao": so["distribuicao"] if so else None,
               "versao": so["versao"] if so else None},
        "kernel": {"versao": _valor(inv, "kernel")},
        "servicos": None if servicos is None else [
            {"nome": _sem_sufixo(u["nome"]), "tipo": u["tipo"], "estado": u["estado"]}
            for u in servicos],
        "swap": {"habilitado": swap["habilitado"] if swap else None,
                 "tamanho": swap["tamanho_kib"] * 1024 if swap else None},
        "portas_em_escuta": None if portas is None else [
            {"porta": p["porta"], "bind": p["endereco"],
             "processo": p["processo"]["value"] if p["processo"]["read"] else None}
            for p in portas],
        "chaves_ssh": None if chaves is None else [
            {"identificacao": _identificacao(c)} for c in chaves["chaves"]],
        "ssh": {"login_de_root": None if login_root is None else login_root != "no"},
        "ntp": {"sincronizado": ntp["ativo"] if ntp else None,
                "mecanismo": ntp["mecanismo"] if ntp else None},
    }


def montar_relatorio(inventario, entradas):
    return {
        "host": {"endereco": inventario.endereco,
                 "hostname": _valor(inventario, "hostname"),
                 "coletado_em": _valor(inventario, "coletado_em")},
        "inventario": _projetar_inventario(inventario),
        "conformidade": [e.como_dict() for e in entradas],
        "resumo": compliance.resumo(entradas),
    }


def relatorio_json(relatorio):
    return json.dumps(relatorio, ensure_ascii=False, indent=2) + "\n"


# --------------------------------------------------------------- Markdown

def _celula(valor):
    if valor is None:
        return "—"
    if isinstance(valor, (dict, list)):
        texto = json.dumps(valor, ensure_ascii=False, sort_keys=True)
    elif isinstance(valor, bool):
        texto = "true" if valor else "false"
    else:
        texto = str(valor)
    return texto.replace("|", "\\|").replace("\n", " ")


def relatorio_markdown(relatorio, versao_baseline):
    """Estrutura para o plantão: primeiro o que exige ação (desvios), depois o resto."""
    host = relatorio["host"]
    entradas = relatorio["conformidade"]
    desvios = sorted((e for e in entradas if e["veredito"] == compliance.DESVIO),
                     key=lambda e: ORDEM_SEVERIDADE[e["severidade"]])  # estável: mantém a ordem do baseline
    nao_verificados = [e for e in entradas if e["veredito"] == compliance.NAO_VERIFICADO]
    conformes = [e["regra"] for e in entradas if e["veredito"] == compliance.CONFORME]

    linhas = [
        f"# Inventário — {host['hostname'] or 'hostname não lido'} ({host['endereco']})",
        "",
        f"Coletado em {host['coletado_em'] or 'data não lida'} · baseline v{versao_baseline}",
        "",
        "## Desvios",
        "",
    ]
    if desvios:
        linhas += ["| Severidade | Regra | Esperado | Encontrado |", "|---|---|---|---|"]
        for e in desvios:
            linhas.append(f"| {e['severidade']} | `{e['regra']}` | {_celula(e['esperado'])} | "
                          f"{_celula(e['encontrado'])} |")
    else:
        linhas.append("Nenhum desvio.")
    linhas += ["", "## Não verificado", ""]
    if nao_verificados:
        linhas += ["| Regra | Motivo |", "|---|---|"]
        for e in nao_verificados:
            linhas.append(f"| `{e['regra']}` | {_celula(e['motivo'])} |")
    else:
        linhas.append("Nenhuma regra não verificada.")
    linhas += ["", "## Conforme", ""]
    linhas.append(" · ".join(conformes) if conformes else "Nenhuma regra conforme.")
    return "\n".join(linhas) + "\n"
