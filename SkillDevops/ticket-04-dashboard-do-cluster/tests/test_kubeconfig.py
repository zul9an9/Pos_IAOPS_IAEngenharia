"""Carregamento do kubeconfig e contexto corrente (tarefas 2.1 a 2.3)."""

import socket

import pytest

from painel_cluster import acesso, erros
from painel_cluster.erros import ErroPainel

DOIS_CONTEXTOS = """
apiVersion: v1
kind: Config
current-context: laboratorio
contexts:
- name: laboratorio
  context: {cluster: kind-lab, user: operador, namespace: nyx-prod}
- name: producao
  context: {cluster: prod, user: operador}
clusters:
- name: kind-lab
  cluster: {server: "https://127.0.0.1:6443", insecure-skip-tls-verify: true}
- name: prod
  cluster: {server: "https://prod.example.invalid:6443"}
users:
- name: operador
  user: {token: token-de-teste}
"""


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    """Qualquer tentativa de conexão durante o carregamento é falha de teste."""
    def proibido(*args, **kwargs):
        raise AssertionError("o carregamento do kubeconfig tentou acessar a rede")
    monkeypatch.setattr(socket.socket, "connect", proibido)
    monkeypatch.setattr(socket.socket, "connect_ex", proibido)


def usar_kubeconfig(monkeypatch, tmp_path, conteudo):
    arquivo = tmp_path / "config"
    arquivo.write_text(conteudo, encoding="utf-8")
    monkeypatch.setenv("KUBECONFIG", str(arquivo))
    return arquivo


def falha_de(monkeypatch):
    with pytest.raises(ErroPainel) as info:
        acesso.carregar_contexto()
    return info.value


def test_usa_somente_o_contexto_corrente(monkeypatch, tmp_path):
    usar_kubeconfig(monkeypatch, tmp_path, DOIS_CONTEXTOS)
    contexto = acesso.carregar_contexto()
    assert contexto.nome == "laboratorio"
    assert contexto.servidor == "https://127.0.0.1:6443"
    assert contexto.namespace == "nyx-prod"
    assert contexto.api_client.configuration.host == "https://127.0.0.1:6443"


def test_nao_grava_no_kubeconfig(monkeypatch, tmp_path):
    arquivo = usar_kubeconfig(monkeypatch, tmp_path, DOIS_CONTEXTOS)
    antes = arquivo.read_bytes(), arquivo.stat().st_mtime_ns
    acesso.carregar_contexto()
    assert (arquivo.read_bytes(), arquivo.stat().st_mtime_ns) == antes


def test_sem_contexto_corrente(monkeypatch, tmp_path):
    usar_kubeconfig(monkeypatch, tmp_path,
                    DOIS_CONTEXTOS.replace("current-context: laboratorio\n", ""))
    erro = falha_de(monkeypatch)
    assert erro.categoria == erros.SEM_CONTEXTO


def test_sem_contexto_corrente_com_campo_vazio(monkeypatch, tmp_path):
    usar_kubeconfig(monkeypatch, tmp_path,
                    DOIS_CONTEXTOS.replace("current-context: laboratorio", 'current-context: ""'))
    assert falha_de(monkeypatch).categoria == erros.SEM_CONTEXTO


def test_kubeconfig_inexistente(monkeypatch, tmp_path):
    monkeypatch.setenv("KUBECONFIG", str(tmp_path / "nao-existe"))
    erro = falha_de(monkeypatch)
    assert (erro.categoria, erro.tipo) == (erros.KUBECONFIG_INVALIDO, erros.INEXISTENTE)
    assert erro.caminho == str(tmp_path / "nao-existe")


def test_kubeconfig_ilegivel_diretorio(monkeypatch, tmp_path):
    diretorio = tmp_path / "um-diretorio"
    diretorio.mkdir()
    monkeypatch.setenv("KUBECONFIG", str(diretorio))
    erro = falha_de(monkeypatch)
    assert (erro.categoria, erro.tipo) == (erros.KUBECONFIG_INVALIDO, erros.ILEGIVEL)


def test_kubeconfig_ilegivel_binario(monkeypatch, tmp_path):
    arquivo = tmp_path / "config"
    arquivo.write_bytes(b"\xff\xfe\x00\x81binario")
    monkeypatch.setenv("KUBECONFIG", str(arquivo))
    erro = falha_de(monkeypatch)
    assert (erro.categoria, erro.tipo) == (erros.KUBECONFIG_INVALIDO, erros.ILEGIVEL)


def test_kubeconfig_yaml_invalido(monkeypatch, tmp_path):
    usar_kubeconfig(monkeypatch, tmp_path, "current-context: [sem fechar\n  : :")
    erro = falha_de(monkeypatch)
    assert (erro.categoria, erro.tipo) == (erros.KUBECONFIG_INVALIDO, erros.MALFORMADO)


def test_contexto_aponta_para_usuario_inexistente(monkeypatch, tmp_path):
    usar_kubeconfig(monkeypatch, tmp_path,
                    DOIS_CONTEXTOS.replace("user: operador, namespace", "user: fantasma, namespace"))
    erro = falha_de(monkeypatch)
    assert (erro.categoria, erro.tipo) == (erros.KUBECONFIG_INVALIDO, erros.MALFORMADO)
    assert "usuário" in erro.motivo


def test_contexto_aponta_para_cluster_inexistente(monkeypatch, tmp_path):
    usar_kubeconfig(monkeypatch, tmp_path,
                    DOIS_CONTEXTOS.replace("cluster: kind-lab, user", "cluster: sumiu, user"))
    erro = falha_de(monkeypatch)
    assert (erro.categoria, erro.tipo) == (erros.KUBECONFIG_INVALIDO, erros.MALFORMADO)


def test_motivo_nao_expoe_conteudo(monkeypatch, tmp_path):
    usar_kubeconfig(monkeypatch, tmp_path,
                    DOIS_CONTEXTOS.replace("user: operador, namespace", "user: fantasma, namespace"))
    erro = falha_de(monkeypatch)
    assert "fantasma" not in erro.motivo and "token-de-teste" not in erro.motivo
