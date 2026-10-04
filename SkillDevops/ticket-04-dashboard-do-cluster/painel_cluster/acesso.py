"""Camada única de acesso ao cluster (design.md, D5).

Este é o ÚNICO módulo do projeto que importa o cliente `kubernetes`, e ele
só expõe operações de listagem (OPERACOES_PERMITIDAS). O teste
tests/test_somente_leitura.py garante as duas coisas.

Aqui também ficam o carregamento do kubeconfig (que precisa do cliente) e a
tradução das exceções do cliente em ErroPainel (D6), para que nenhum outro
módulo precise conhecer os tipos de exceção do `kubernetes`.
"""

import json
import logging
import os
from dataclasses import dataclass

import urllib3
import yaml
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
from kubernetes.config.config_exception import ConfigException

from . import erros
from .erros import ErroPainel

log = logging.getLogger(__name__)

# (conexão, leitura) em segundos; sem retentativas (design.md, D6).
TIMEOUT = (3, 10)
TAMANHO_PAGINA = 500

OPERACOES_PERMITIDAS = frozenset({
    "list_namespace",
    "list_pod_for_all_namespaces",
    "list_namespaced_pod",
    "list_deployment_for_all_namespaces",
    "list_namespaced_deployment",
    "list_service_for_all_namespaces",
    "list_namespaced_service",
    "list_endpoint_slice_for_all_namespaces",
    "list_namespaced_endpoint_slice",
    "list_namespaced_event",
})


@dataclass
class Contexto:
    nome: str
    servidor: str
    namespace: str | None
    caminho: str
    api_client: object


# --------------------------------------------------------------------------
# kubeconfig
# --------------------------------------------------------------------------

def caminhos_kubeconfig():
    """Caminhos na ordem do kubectl: KUBECONFIG (lista) ou ~/.kube/config."""
    valor = os.environ.get("KUBECONFIG")
    if valor:
        caminhos = [p for p in valor.split(os.pathsep) if p]
        if caminhos:
            return caminhos
    return [os.path.expanduser(os.path.join("~", ".kube", "config"))]


def _invalido(caminho, tipo, motivo, detalhe=""):
    return ErroPainel(erros.KUBECONFIG_INVALIDO, caminho=caminho, tipo=tipo,
                      motivo=motivo, detalhe=detalhe)


def _ler_documento(caminho):
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            texto = arquivo.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise _invalido(caminho, erros.ILEGIVEL, "o arquivo não pôde ser lido",
                        repr(exc)) from None
    try:
        documento = yaml.safe_load(texto)
    except yaml.YAMLError as exc:
        raise _invalido(caminho, erros.MALFORMADO, "o arquivo não é YAML válido",
                        repr(exc)) from None
    if documento is None:
        return {}
    if not isinstance(documento, dict):
        raise _invalido(caminho, erros.MALFORMADO,
                        "o arquivo não tem a estrutura de um kubeconfig")
    return documento


def _mesclar(documentos, caminho):
    """Mescla como o kubectl: o primeiro arquivo que define um valor vence."""
    atual = None
    entradas = {"contexts": {}, "clusters": {}, "users": {}}
    for doc in documentos:
        if not atual and doc.get("current-context"):
            atual = doc["current-context"]
        for chave, destino in entradas.items():
            lista = doc.get(chave) or []
            if not isinstance(lista, list):
                raise _invalido(caminho, erros.MALFORMADO,
                                f"a seção '{chave}' não é uma lista")
            for item in lista:
                if not isinstance(item, dict) or "name" not in item:
                    raise _invalido(caminho, erros.MALFORMADO,
                                    f"há uma entrada sem nome em '{chave}'")
                destino.setdefault(item["name"], item)
    return atual, entradas


def carregar_contexto():
    """Carrega o contexto corrente sem nenhuma chamada à API.

    Levanta ErroPainel(kubeconfig-invalido) ou ErroPainel(sem-contexto).
    """
    caminhos = caminhos_kubeconfig()
    exibicao = os.pathsep.join(caminhos)
    existentes = [p for p in caminhos if os.path.exists(p)]
    if not existentes:
        raise _invalido(exibicao, erros.INEXISTENTE, "o arquivo não existe")

    documentos = [_ler_documento(p) for p in existentes]
    atual, entradas = _mesclar(documentos, exibicao)
    if not atual:
        raise ErroPainel(erros.SEM_CONTEXTO, caminho=exibicao)

    entrada_ctx = entradas["contexts"].get(atual)
    if entrada_ctx is None:
        raise _invalido(exibicao, erros.MALFORMADO,
                        "o contexto corrente não existe no arquivo")
    ctx = entrada_ctx.get("context") or {}
    cluster = entradas["clusters"].get(ctx.get("cluster"))
    if cluster is None:
        raise _invalido(exibicao, erros.MALFORMADO,
                        "o contexto corrente aponta para um cluster que não existe no arquivo")
    if ctx.get("user") and ctx["user"] not in entradas["users"]:
        raise _invalido(exibicao, erros.MALFORMADO,
                        "o contexto corrente aponta para um usuário que não existe no arquivo")
    servidor = (cluster.get("cluster") or {}).get("server")
    if not servidor:
        raise _invalido(exibicao, erros.MALFORMADO,
                        "o cluster do contexto corrente não tem endereço de servidor")

    configuracao = client.Configuration()
    try:
        # persist_config=False: o painel nunca grava no kubeconfig de quem opera.
        config.load_kube_config(config_file=os.pathsep.join(existentes),
                                context=atual,
                                client_configuration=configuracao,
                                persist_config=False)
    except Exception as exc:  # ConfigException, certificado inválido etc.
        raise _invalido(exibicao, erros.MALFORMADO,
                        "o cliente do Kubernetes recusou o conteúdo do arquivo",
                        repr(exc)) from None
    configuracao.retries = False

    return Contexto(nome=atual, servidor=servidor, namespace=ctx.get("namespace"),
                    caminho=exibicao, api_client=client.ApiClient(configuracao))


# --------------------------------------------------------------------------
# classificação de exceções (D6)
# --------------------------------------------------------------------------

def classificar(exc, recurso=None):
    """Traduz uma exceção do cliente em ErroPainel. Nunca levanta."""
    detalhe = repr(exc)
    if isinstance(exc, ApiException):
        status = exc.status
        if status == 401:
            return ErroPainel(erros.CREDENCIAL, recurso=recurso, detalhe=detalhe)
        if status == 403:
            corpo = exc.body or b""
            if isinstance(corpo, bytes):
                corpo = corpo.decode("utf-8", errors="replace")
            if "system:anonymous" in corpo:
                # A credencial não autenticou; com anonymous-auth ligado o
                # apiserver responde 403 em vez de 401.
                return ErroPainel(erros.CREDENCIAL, recurso=recurso, detalhe=detalhe)
            return ErroPainel(erros.SEM_PERMISSAO, recurso=recurso, detalhe=detalhe)
        if not status:
            # status 0: o cliente não obteve resposta HTTP (ex.: erro de TLS).
            return ErroPainel(erros.NAO_RESPONDEU, recurso=recurso, detalhe=detalhe)
        return ErroPainel(erros.INESPERADO, recurso=recurso, motivo=f"HTTP {status}",
                          detalhe=detalhe)
    if isinstance(exc, (urllib3.exceptions.HTTPError, ConnectionError, TimeoutError)):
        return ErroPainel(erros.NAO_RESPONDEU, recurso=recurso, detalhe=detalhe)
    if isinstance(exc, ConfigException):
        # Falha ao obter ou renovar credencial durante a requisição.
        return ErroPainel(erros.CREDENCIAL, recurso=recurso, detalhe=detalhe)
    return ErroPainel(erros.INESPERADO, recurso=recurso, detalhe=detalhe)


# --------------------------------------------------------------------------
# operações de leitura
# --------------------------------------------------------------------------

class AcessoLeitura:
    """Única porta de entrada ao cluster. Só listagens.

    Devolve os itens como o JSON cru da API (dicts), de modo que campo ausente
    continua ausente e a tradução para a tela trata isso num só lugar.
    """

    def __init__(self, api_client):
        self._core = client.CoreV1Api(api_client)
        self._apps = client.AppsV1Api(api_client)
        self._discovery = client.DiscoveryV1Api(api_client)

    def list_namespace(self):
        return self._listar("namespaces", self._core.list_namespace)

    def list_pod_for_all_namespaces(self):
        return self._listar("pods", self._core.list_pod_for_all_namespaces)

    def list_namespaced_pod(self, namespace):
        return self._listar("pods", self._core.list_namespaced_pod, namespace)

    def list_deployment_for_all_namespaces(self):
        return self._listar("deployments", self._apps.list_deployment_for_all_namespaces)

    def list_namespaced_deployment(self, namespace):
        return self._listar("deployments", self._apps.list_namespaced_deployment, namespace)

    def list_service_for_all_namespaces(self):
        return self._listar("services", self._core.list_service_for_all_namespaces)

    def list_namespaced_service(self, namespace):
        return self._listar("services", self._core.list_namespaced_service, namespace)

    def list_endpoint_slice_for_all_namespaces(self):
        return self._listar("endpointslices",
                            self._discovery.list_endpoint_slice_for_all_namespaces)

    def list_namespaced_endpoint_slice(self, namespace):
        return self._listar("endpointslices",
                            self._discovery.list_namespaced_endpoint_slice, namespace)

    def list_namespaced_event(self, namespace):
        return self._listar("events", self._core.list_namespaced_event, namespace)

    def _listar(self, recurso, operacao, *args):
        itens = []
        continuacao = None
        try:
            while True:
                opcoes = {"limit": TAMANHO_PAGINA, "_preload_content": False,
                          "_request_timeout": TIMEOUT}
                if continuacao:
                    opcoes["_continue"] = continuacao
                resposta = operacao(*args, **opcoes)
                try:
                    corpo = json.loads(resposta.data)
                finally:
                    resposta.release_conn()
                itens.extend(corpo.get("items") or [])
                continuacao = (corpo.get("metadata") or {}).get("continue")
                if not continuacao:
                    return itens
        except Exception as exc:
            erro = classificar(exc, recurso)
            log.warning("falha ao listar %s: %s (%s)", recurso, erro.categoria, erro.detalhe)
            raise erro from None
