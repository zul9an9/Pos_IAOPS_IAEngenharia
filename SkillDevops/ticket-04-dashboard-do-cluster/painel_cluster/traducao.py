"""Tradução API → tela (design.md, D7). Sem I/O.

As três armadilhas de dados vivem só aqui:
(a) campo ausente vira o valor semântico da API, nunca vazio, None ou erro;
(b) um objeto Event é uma linha, com count e carimbos;
(c) só o que a API reporta: nenhum juízo de saúde é sintetizado.

Todas as funções recebem o JSON cru da API (dicts) e devolvem texto cru; o
escape para HTML é responsabilidade exclusiva do renderizador.
"""

import re

AUSENTE = "—"
ROTULO_SERVICE = "kubernetes.io/service-name"
NOME_DE_NAMESPACE = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")


def namespace_valido(nome):
    """Rótulo DNS-1123: minúsculas, dígitos e hífen, até 63 caracteres."""
    return isinstance(nome, str) and len(nome) <= 63 and bool(NOME_DE_NAMESPACE.match(nome))


def _plural(n, singular, plural):
    return f"{n} {singular if n == 1 else plural}"


def _meta(item):
    meta = item.get("metadata") or {}
    return meta.get("namespace") or "", meta.get("name") or ""


# --------------------------------------------------------------------------
# namespaces
# --------------------------------------------------------------------------

def namespaces(itens):
    return sorted(_meta(i)[1] for i in itens)


# --------------------------------------------------------------------------
# pods
# --------------------------------------------------------------------------

def _falhas_do_conteiner(status):
    """Motivos reportados pela API para um contêiner, ou [] se não está em falha."""
    estado = status.get("state") or {}
    esperando = estado.get("waiting") or {}
    terminado = estado.get("terminated")
    ultimo = (status.get("lastState") or {}).get("terminated")
    partes = []
    if esperando.get("reason"):
        partes.append(esperando["reason"])
    elif terminado and (terminado.get("exitCode") or 0) != 0:
        partes.append(f"{terminado.get('reason') or 'Terminated'} "
                      f"(exit {terminado.get('exitCode')})")
    if ultimo and (status.get("restartCount") or 0) > 0:
        partes.append(f"última terminação: {ultimo.get('reason') or AUSENTE} "
                      f"(exit {ultimo.get('exitCode', AUSENTE)})")
    return partes


def pod(item):
    namespace, nome = _meta(item)
    spec = item.get("spec") or {}
    status = item.get("status") or {}
    conteineres = status.get("containerStatuses") or []
    iniciais = status.get("initContainerStatuses") or []

    total = len(spec.get("containers") or []) or len(conteineres)
    prontos = sum(1 for c in conteineres if c.get("ready") is True)
    reinicios = sum(c.get("restartCount") or 0 for c in conteineres + iniciais)

    motivos = []
    if status.get("reason"):
        motivos.append(status["reason"])
    for c in iniciais:
        falhas = _falhas_do_conteiner(c)
        if falhas:
            motivos.append(f"init container {c.get('name')}: " + "; ".join(falhas))
    for c in conteineres:
        falhas = _falhas_do_conteiner(c)
        if falhas:
            prefixo = f"{c.get('name')}: " if len(conteineres) > 1 else ""
            motivos.append(prefixo + "; ".join(falhas))

    return {
        "namespace": namespace,
        "nome": nome,
        "fase": status.get("phase") or AUSENTE,
        "prontos": f"{prontos}/{total}",
        "reinicios": reinicios,
        "motivo": " | ".join(motivos),
    }


# --------------------------------------------------------------------------
# deployments
# --------------------------------------------------------------------------

def deployment(item):
    namespace, nome = _meta(item)
    prontas = (item.get("status") or {}).get("readyReplicas")
    desejadas = (item.get("spec") or {}).get("replicas")
    prontas = 0 if prontas is None else prontas        # ausente: nenhuma pronta
    desejadas = 1 if desejadas is None else desejadas  # ausente: default da API
    return {"namespace": namespace, "nome": nome, "prontas": f"{prontas}/{desejadas}"}


# --------------------------------------------------------------------------
# services e endpoints (EndpointSlice)
# --------------------------------------------------------------------------

def agrupar_slices(slices):
    """{(namespace, service): [slices]} pelo rótulo kubernetes.io/service-name."""
    grupos = {}
    for s in slices:
        meta = s.get("metadata") or {}
        servico = (meta.get("labels") or {}).get(ROTULO_SERVICE)
        if servico:
            grupos.setdefault((meta.get("namespace") or "", servico), []).append(s)
    return grupos


def resumo_endpoints(service, slices_do_service):
    spec = service.get("spec") or {}
    if spec.get("type") == "ExternalName":
        return f"ExternalName ({spec.get('externalName') or AUSENTE})"
    enderecos, prontos = set(), set()
    for s in slices_do_service:
        for endpoint in s.get("endpoints") or []:  # ausente ou nulo: nenhum endereço
            # A API define que `ready` ausente deve ser interpretado como true.
            pronto = (endpoint.get("conditions") or {}).get("ready") is not False
            for endereco in endpoint.get("addresses") or []:
                enderecos.add(endereco)
                if pronto:
                    prontos.add(endereco)
    if not enderecos:
        return "sem endpoint"
    return (f"{_plural(len(enderecos), 'endereço', 'endereços')}, "
            f"{_plural(len(prontos), 'pronto', 'prontos')}")


def _portas(spec):
    portas = spec.get("ports") or []
    return ", ".join(f"{p.get('port')}/{p.get('protocol') or 'TCP'}" for p in portas) or AUSENTE


def services(itens, slices, aviso_endpoint=None):
    """`aviso_endpoint` substitui o resumo quando os EndpointSlices não puderam ser lidos."""
    grupos = agrupar_slices(slices)
    linhas = []
    for item in itens:
        namespace, nome = _meta(item)
        spec = item.get("spec") or {}
        if aviso_endpoint and spec.get("type") != "ExternalName":
            endpoint = aviso_endpoint
        else:
            endpoint = resumo_endpoints(item, grupos.get((namespace, nome), []))
        linhas.append({
            "namespace": namespace,
            "nome": nome,
            "tipo": spec.get("type") or AUSENTE,
            "cluster_ip": spec.get("clusterIP") or AUSENTE,
            "portas": _portas(spec),
            "endpoint": endpoint,
        })
    return linhas


# --------------------------------------------------------------------------
# eventos
# --------------------------------------------------------------------------

def evento(item):
    _, nome = _meta(item)
    objeto = item.get("involvedObject") or {}
    serie = item.get("series") or {}
    contagem = item.get("count")
    if contagem is None:
        contagem = serie.get("count")
    return {
        "nome": nome,
        "tipo": item.get("type") or AUSENTE,
        "razao": item.get("reason") or AUSENTE,
        "mensagem": item.get("message") or "",
        "objeto_tipo": objeto.get("kind") or AUSENTE,
        "objeto_nome": objeto.get("name") or "",
        "contagem": 1 if contagem is None else contagem,
        "primeira": item.get("firstTimestamp") or item.get("eventTime") or AUSENTE,
        "ultima": (item.get("lastTimestamp") or serie.get("lastObservedTime")
                   or item.get("eventTime") or AUSENTE),
    }


def eventos(itens):
    """Uma linha por objeto Event, do mais recente para o mais antigo."""
    linhas = [evento(i) for i in itens]
    linhas.sort(key=lambda e: (e["ultima"] != AUSENTE, e["ultima"]), reverse=True)
    return linhas
