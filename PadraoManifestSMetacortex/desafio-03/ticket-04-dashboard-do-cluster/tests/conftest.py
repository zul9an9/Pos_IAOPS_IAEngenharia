import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def carregar(namespace, tipo):
    """Itens de uma fixture capturada do laboratório (tests/fixtures/capturar.sh)."""
    with open(FIXTURES / namespace / f"{tipo}.json", encoding="utf-8") as arquivo:
        return json.load(arquivo)["items"]


def por_nome(itens, prefixo):
    return [i for i in itens if i["metadata"]["name"].startswith(prefixo)]


@pytest.fixture
def fixture():
    return carregar


class AcessoFalso:
    """Substituto da camada de acesso servido pelas fixtures.

    Registra cada chamada em `chamadas`. `falhas` mapeia nome da operação para
    o ErroPainel a levantar.
    """

    TIPO = {"pod": "pods", "deployment": "deployments", "service": "services",
            "endpoint_slice": "endpointslices", "event": "events"}

    def __init__(self, falhas=None, namespaces=("nyx-prod", "nyx-stg", "orion-prod",
                                                "orion-stg", "kube-public")):
        self.falhas = falhas or {}
        self.chamadas = []
        self._namespaces = namespaces

    def __getattr__(self, nome):
        if not nome.startswith("list_"):
            raise AttributeError(nome)

        def operacao(*args):
            self.chamadas.append((nome, *args))
            if nome in self.falhas:
                raise self.falhas[nome]
            if nome == "list_namespace":
                return [{"metadata": {"name": ns}} for ns in self._namespaces]
            recurso = nome.removeprefix("list_namespaced_").removeprefix("list_") \
                .removesuffix("_for_all_namespaces")
            tipo = self.TIPO[recurso]
            alvos = args if args else self._namespaces
            return [item for ns in alvos for item in _itens_ou_vazio(ns, tipo)]
        return operacao


def _itens_ou_vazio(namespace, tipo):
    try:
        return carregar(namespace, tipo)
    except FileNotFoundError:
        return []


class ContextoFalso:
    def __init__(self, nome="kind-metacortex-lab", servidor="https://127.0.0.1:6443",
                 namespace=None, caminho="C:/kube/config"):
        self.nome, self.servidor, self.namespace, self.caminho = nome, servidor, namespace, caminho
        self.api_client = None
