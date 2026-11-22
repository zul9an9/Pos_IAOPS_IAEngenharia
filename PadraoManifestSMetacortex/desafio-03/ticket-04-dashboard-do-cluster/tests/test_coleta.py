"""Coleta, classificação de erros e degradação do seletor (tarefas 4.1 a 4.4)."""

from datetime import datetime, timezone

import pytest
import urllib3
from conftest import AcessoFalso, ContextoFalso

from painel_cluster import acesso, coleta, erros
from painel_cluster.erros import ErroPainel

RELOGIO = lambda: datetime(2026, 9, 27, 22, 0, tzinfo=timezone.utc)  # noqa: E731


def negado(recurso):
    return ErroPainel(erros.SEM_PERMISSAO, recurso=recurso)


# --- 4.1 coleta ---------------------------------------------------------------

def test_coleta_todos_os_namespaces_faz_exatamente_estas_chamadas():
    falso = AcessoFalso()
    resultado = coleta.coletar(falso, ContextoFalso(), relogio=RELOGIO)
    assert [c[0] for c in falso.chamadas] == [
        "list_namespace",
        "list_pod_for_all_namespaces",
        "list_deployment_for_all_namespaces",
        "list_service_for_all_namespaces",
        "list_endpoint_slice_for_all_namespaces",
    ]
    assert resultado.eventos.aviso == coleta.AVISO_SELECIONE_NAMESPACE
    assert resultado.carimbo.tzinfo is not None


def test_coleta_de_um_namespace_faz_exatamente_estas_chamadas():
    falso = AcessoFalso()
    resultado = coleta.coletar(falso, ContextoFalso(), "nyx-prod", relogio=RELOGIO)
    assert falso.chamadas == [
        ("list_namespace",),
        ("list_namespaced_pod", "nyx-prod"),
        ("list_namespaced_deployment", "nyx-prod"),
        ("list_namespaced_service", "nyx-prod"),
        ("list_namespaced_endpoint_slice", "nyx-prod"),
        ("list_namespaced_event", "nyx-prod"),
    ]
    assert resultado.eventos.estado == "dados"
    assert all(p["namespace"] == "nyx-prod" for p in resultado.pods.itens)


def test_coleta_recusa_namespace_invalido_sem_chamar_api():
    falso = AcessoFalso()
    with pytest.raises(ValueError):
        coleta.coletar(falso, ContextoFalso(), "<script>")
    assert falso.chamadas == []


def test_namespace_vazio_e_distinto_de_erro():
    resultado = coleta.coletar(AcessoFalso(), ContextoFalso(), "kube-public")
    for bloco in (resultado.pods, resultado.deployments, resultado.services, resultado.eventos):
        assert bloco.estado == "vazio"
    assert resultado.erro_global is None


class RespostaFalsa:
    def __init__(self, paginas):
        self.paginas = paginas

    def __call__(self, *args, **kwargs):
        self.kwargs = kwargs
        pagina = self.paginas.pop(0)
        return pagina


class Pagina:
    def __init__(self, dados):
        self.data = dados
        self.liberada = False

    def release_conn(self):
        self.liberada = True


def test_listagem_paginada_com_timeout_e_json_cru():
    paginas = [Pagina(b'{"metadata": {"continue": "x"}, "items": [{"a": 1}]}'),
               Pagina(b'{"metadata": {}, "items": [{"b": 2}]}')]
    operacao = RespostaFalsa(list(paginas))
    camada = acesso.AcessoLeitura.__new__(acesso.AcessoLeitura)
    itens = camada._listar("pods", operacao)
    assert itens == [{"a": 1}, {"b": 2}]
    assert operacao.kwargs["_request_timeout"] == (3, 10)
    assert operacao.kwargs["_preload_content"] is False
    assert operacao.kwargs["limit"] == acesso.TAMANHO_PAGINA
    assert operacao.kwargs["_continue"] == "x"
    assert all(p.liberada for p in paginas)


def test_cliente_sem_retentativas(monkeypatch, tmp_path):
    arquivo = tmp_path / "config"
    arquivo.write_text("""
current-context: c
contexts: [{name: c, context: {cluster: k, user: u}}]
clusters: [{name: k, cluster: {server: "https://127.0.0.1:1"}}]
users: [{name: u, user: {token: t}}]
""", encoding="utf-8")
    monkeypatch.setenv("KUBECONFIG", str(arquivo))
    assert acesso.carregar_contexto().api_client.configuration.retries is False


# --- 4.2 classificação --------------------------------------------------------

def api_exception(status, corpo=b""):
    exc = acesso.ApiException(status=status, reason="motivo")
    exc.body = corpo
    return exc


@pytest.mark.parametrize("excecao, categoria", [
    (api_exception(401), erros.CREDENCIAL),
    (api_exception(403, b'{"message":"pods is forbidden: User \\"system:anonymous\\" cannot list"}'),
     erros.CREDENCIAL),
    (api_exception(403, b'{"message":"pods is forbidden: User \\"dev\\" cannot list"}'),
     erros.SEM_PERMISSAO),
    (api_exception(0), erros.NAO_RESPONDEU),
    (urllib3.exceptions.NewConnectionError(None, "recusada"), erros.NAO_RESPONDEU),
    (urllib3.exceptions.ConnectTimeoutError("tempo esgotado"), erros.NAO_RESPONDEU),
    (urllib3.exceptions.ReadTimeoutError(None, "/", "tempo esgotado"), erros.NAO_RESPONDEU),
    (urllib3.exceptions.MaxRetryError(None, "/"), erros.NAO_RESPONDEU),
    (ConnectionRefusedError(), erros.NAO_RESPONDEU),
    (acesso.ConfigException("exec plugin falhou"), erros.CREDENCIAL),
    (api_exception(500), erros.INESPERADO),
    (ValueError("qualquer coisa"), erros.INESPERADO),
])
def test_classificacao(excecao, categoria):
    erro = acesso.classificar(excecao, "pods")
    assert erro.categoria == categoria
    assert erro.recurso == "pods"


def test_listagem_converte_excecao_em_erro_do_painel():
    def falha(*args, **kwargs):
        raise api_exception(403, b"forbidden")
    camada = acesso.AcessoLeitura.__new__(acesso.AcessoLeitura)
    with pytest.raises(ErroPainel) as info:
        camada._listar("events", falha)
    assert (info.value.categoria, info.value.recurso) == (erros.SEM_PERMISSAO, "events")


@pytest.mark.parametrize("categoria", [erros.NAO_RESPONDEU, erros.CREDENCIAL])
def test_erro_de_cluster_na_primeira_chamada_vira_global(categoria):
    falso = AcessoFalso(falhas={"list_namespace": ErroPainel(categoria)})
    resultado = coleta.coletar(falso, ContextoFalso())
    assert resultado.erro_global.categoria == categoria
    assert len(falso.chamadas) == 1


# --- 4.3 permissão negada para um tipo --------------------------------------------

def test_eventos_negados_e_o_resto_funciona():
    falso = AcessoFalso(falhas={"list_namespaced_event": negado("events")})
    resultado = coleta.coletar(falso, ContextoFalso(), "nyx-prod")
    assert resultado.eventos.estado == "erro"
    assert resultado.eventos.erro.categoria == erros.SEM_PERMISSAO
    for bloco in (resultado.pods, resultado.deployments, resultado.services):
        assert bloco.estado == "dados"
    assert resultado.erro_global is None


def test_endpointslices_negados_viram_aviso_na_coluna():
    falso = AcessoFalso(falhas={"list_namespaced_endpoint_slice": negado("endpointslices")})
    resultado = coleta.coletar(falso, ContextoFalso(), "nyx-prod")
    assert resultado.services.estado == "dados"
    assert {s["endpoint"] for s in resultado.services.itens} == \
        {"sem permissão para ler endpointslices"}


# --- 4.4 namespaces negados -----------------------------------------------------

def test_namespaces_negados_usa_namespace_do_contexto():
    falso = AcessoFalso(falhas={"list_namespace": negado("namespaces")})
    resultado = coleta.coletar(falso, ContextoFalso(namespace="nyx-prod"))
    assert resultado.namespaces_negados and resultado.namespace == "nyx-prod"
    assert ("list_namespaced_pod", "nyx-prod") in falso.chamadas
    for bloco in (resultado.pods, resultado.deployments, resultado.services, resultado.eventos):
        assert bloco.estado == "dados"
    assert resultado.erro_global is None


def test_namespaces_negados_sem_namespace_no_contexto_nao_quebra():
    negados = {"list_namespace": negado("namespaces")}
    for nome in ("list_pod_for_all_namespaces", "list_deployment_for_all_namespaces",
                 "list_service_for_all_namespaces", "list_endpoint_slice_for_all_namespaces"):
        negados[nome] = negado(nome)
    resultado = coleta.coletar(AcessoFalso(falhas=negados), ContextoFalso())
    assert resultado.namespaces_negados and resultado.namespace is None
    assert resultado.erro_global is None
    assert resultado.eventos.aviso == coleta.AVISO_SELECIONE_NAMESPACE
    assert resultado.pods.erro.categoria == erros.SEM_PERMISSAO
