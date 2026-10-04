"""Servidor local: só 127.0.0.1, só GET, uma coleta por GET (tarefas 5.1 e 5.3)."""

import inspect
import socket
import threading
import urllib.request

import pytest
from conftest import AcessoFalso, ContextoFalso

from painel_cluster import servidor


@pytest.fixture
def no_ar():
    """Sobe o servidor em porta efêmera com a camada de acesso falsa."""
    falso = AcessoFalso()
    painel = servidor.Painel(carregar_contexto=ContextoFalso,
                             fabrica_acesso=lambda _api: falso)
    srv = servidor.criar_servidor(0, painel)
    fio = threading.Thread(target=srv.serve_forever, daemon=True)
    fio.start()
    yield srv, falso
    srv.shutdown()
    srv.server_close()


def obter(srv, caminho="/"):
    with urllib.request.urlopen(f"http://127.0.0.1:{srv.server_port}{caminho}", timeout=5) as r:
        return r.status, dict(r.headers), r.read().decode("utf-8")


def enviar_cru(porta, metodo):
    """Envia uma requisição HTTP mínima e devolve o status."""
    with socket.socket() as s:
        s.settimeout(5)
        s.connect(("127.0.0.1", porta))
        s.sendall(f"{metodo} / HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Length: 0\r\n"
                  "Connection: close\r\n\r\n".encode("ascii"))
        resposta = b""
        while True:
            parte = s.recv(4096)
            if not parte:
                break
            resposta += parte
    return int(resposta.split()[1])


def ip_da_rede_local():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("192.0.2.1", 9))  # UDP: nenhum pacote é enviado
            ip = s.getsockname()[0]
        except OSError:
            return None
    return None if ip.startswith("127.") or ip == "0.0.0.0" else ip


def test_escuta_somente_em_127_0_0_1(no_ar):
    srv, _ = no_ar
    assert srv.socket.getsockname()[0] == "127.0.0.1"
    assert srv.server_address[0] == "127.0.0.1"


def test_endereco_nao_e_configuravel():
    parametros = inspect.signature(servidor.criar_servidor).parameters
    assert set(parametros) == {"porta", "painel"}


def test_conexao_por_outra_interface_e_recusada(no_ar):
    srv, _ = no_ar
    ip = ip_da_rede_local()
    if ip is None:
        pytest.skip("máquina sem endereço de rede local além do loopback")
    with socket.socket() as s:
        s.settimeout(3)
        with pytest.raises(OSError):
            s.connect((ip, srv.server_port))


@pytest.mark.parametrize("metodo", ["POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "FOO"])
def test_metodos_que_nao_sao_get_recebem_405_sem_coleta(no_ar, metodo):
    srv, falso = no_ar
    assert enviar_cru(srv.server_port, metodo) == 405
    assert falso.chamadas == []


def test_get_faz_uma_coleta_e_envia_csp(no_ar):
    srv, falso = no_ar
    status, cabecalhos, corpo = obter(srv, "/?ns=nyx-prod")
    assert status == 200
    assert "script-src 'sha256-" in cabecalhos["Content-Security-Policy"]
    assert [c[0] for c in falso.chamadas].count("list_namespace") == 1
    assert "nyx-api-" in corpo


def test_namespace_invalido_recusado_sem_chamar_api(no_ar):
    srv, falso = no_ar
    for nome in ("Nyx_Prod", "%3Cscript%3E"):
        status, _, corpo = obter(srv, f"/?ns={nome}")
        assert status == 200 and "Nome de namespace inválido" in corpo
    assert falso.chamadas == []
    assert "&lt;script&gt;" in corpo


def test_caminho_desconhecido_404_sem_coleta(no_ar):
    srv, falso = no_ar
    with pytest.raises(urllib.error.HTTPError) as info:
        obter(srv, "/api/v1/pods")
    assert info.value.code == 404
    assert falso.chamadas == []


def test_erro_inesperado_nao_vaza_traceback(no_ar):
    srv, _ = no_ar

    def explode(_api):
        raise RuntimeError("detalhe interno secreto")
    srv.RequestHandlerClass.painel.fabrica_acesso = explode
    status, _, corpo = obter(srv)
    assert status == 200
    assert "Erro inesperado" in corpo
    assert "Traceback" not in corpo and "RuntimeError" not in corpo \
        and "detalhe interno secreto" not in corpo
