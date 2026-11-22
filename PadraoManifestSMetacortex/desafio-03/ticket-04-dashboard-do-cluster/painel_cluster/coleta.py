"""Coleta sob demanda (design.md, D3) com erros classificados por bloco (D6).

Cada listagem é independente: a falha de uma não derruba as outras. Só
`nao-respondeu` e `credencial` valem para a tela inteira.
"""

from dataclasses import dataclass, field
from datetime import datetime

from . import erros, traducao
from .erros import ErroPainel

AVISO_SELECIONE_NAMESPACE = "Selecione um namespace para ver os eventos."


@dataclass
class Bloco:
    itens: list = field(default_factory=list)
    erro: ErroPainel | None = None
    aviso: str | None = None

    @property
    def estado(self):
        if self.erro is not None:
            return "erro"
        if self.aviso is not None:
            return "aviso"
        return "dados" if self.itens else "vazio"


@dataclass
class Coleta:
    contexto: object
    carimbo: datetime
    namespace: str | None = None
    namespaces_negados: bool = False
    namespaces: Bloco = field(default_factory=Bloco)
    pods: Bloco = field(default_factory=Bloco)
    deployments: Bloco = field(default_factory=Bloco)
    services: Bloco = field(default_factory=Bloco)
    eventos: Bloco = field(default_factory=Bloco)
    erro_global: ErroPainel | None = None


def _tentar(operacao, *args):
    try:
        return operacao(*args), None
    except ErroPainel as erro:
        return None, erro


def coletar(acesso, contexto, namespace=None, relogio=datetime.now):
    """Faz UMA coleta. `namespace` já deve ter sido validado (DNS-1123)."""
    if namespace is not None and not traducao.namespace_valido(namespace):
        raise ValueError("namespace inválido")  # o servidor valida antes; defesa extra
    coleta = Coleta(contexto=contexto, carimbo=relogio().astimezone())

    itens, erro = _tentar(acesso.list_namespace)
    if erro is not None and erro.categoria in (erros.NAO_RESPONDEU, erros.CREDENCIAL):
        coleta.erro_global = erro  # problema do cluster inteiro: não insiste
        return coleta
    if erro is not None:
        coleta.namespaces = Bloco(erro=erro)
        if erro.categoria == erros.SEM_PERMISSAO:
            coleta.namespaces_negados = True
            if namespace is None:
                namespace = contexto.namespace
    else:
        coleta.namespaces = Bloco(itens=traducao.namespaces(itens))
    coleta.namespace = namespace

    if namespace:
        chamadas = {
            "pods": (acesso.list_namespaced_pod, namespace),
            "deployments": (acesso.list_namespaced_deployment, namespace),
            "services": (acesso.list_namespaced_service, namespace),
            "endpointslices": (acesso.list_namespaced_endpoint_slice, namespace),
            "eventos": (acesso.list_namespaced_event, namespace),
        }
    else:
        chamadas = {
            "pods": (acesso.list_pod_for_all_namespaces,),
            "deployments": (acesso.list_deployment_for_all_namespaces,),
            "services": (acesso.list_service_for_all_namespaces,),
            "endpointslices": (acesso.list_endpoint_slice_for_all_namespaces,),
        }
    resultados = {nome: _tentar(*chamada) for nome, chamada in chamadas.items()}

    def bloco(nome, traduzir):
        itens, erro = resultados[nome]
        return Bloco(erro=erro) if erro is not None else Bloco(itens=traduzir(itens))

    coleta.pods = bloco("pods", lambda itens: [traducao.pod(i) for i in itens])
    coleta.deployments = bloco("deployments",
                               lambda itens: [traducao.deployment(i) for i in itens])

    slices, erro_slices = resultados["endpointslices"]
    aviso_endpoint = None
    if erro_slices is not None:
        aviso_endpoint = ("sem permissão para ler endpointslices"
                          if erro_slices.categoria == erros.SEM_PERMISSAO
                          else "não foi possível ler endpointslices")
    coleta.services = bloco("services", lambda itens: traducao.services(
        itens, slices or [], aviso_endpoint))

    if "eventos" in resultados:
        coleta.eventos = bloco("eventos", traducao.eventos)
    else:
        coleta.eventos = Bloco(aviso=AVISO_SELECIONE_NAMESPACE)

    # Se tudo falhou por motivo de cluster, a tela inteira diz isso.
    falhas = [erro for _, erro in resultados.values()]
    if all(f is not None for f in falhas):
        globais = [f for f in falhas if f.categoria in (erros.NAO_RESPONDEU, erros.CREDENCIAL)]
        if len(globais) == len(falhas):
            coleta.erro_global = globais[0]
    return coleta
