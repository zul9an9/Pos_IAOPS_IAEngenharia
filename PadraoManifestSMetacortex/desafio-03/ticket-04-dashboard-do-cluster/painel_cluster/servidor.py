"""Servidor HTTP local: só 127.0.0.1, só GET (spec; design.md, D1 e D5).

Cada GET em "/" é uma ação explícita de quem opera (abrir, Atualizar ou
trocar namespace) e produz exatamente uma coleta (D3).
"""

import logging
import socketserver
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit

from . import acesso, coleta, render, traducao
from .erros import ErroPainel

log = logging.getLogger(__name__)

# Fixo por requisito: o endereço de escuta não é configurável.
ENDERECO = "127.0.0.1"
PORTA_PADRAO = 8765


class Painel:
    """Liga kubeconfig, coleta e renderização. Dependências injetáveis para teste."""

    def __init__(self, carregar_contexto=acesso.carregar_contexto,
                 fabrica_acesso=acesso.AcessoLeitura, relogio=datetime.now):
        self.carregar_contexto = carregar_contexto
        self.fabrica_acesso = fabrica_acesso
        self.relogio = relogio

    def pagina(self, consulta):
        agora = self.relogio().astimezone()
        try:
            contexto = self.carregar_contexto()
        except ErroPainel as erro:
            log.warning("kubeconfig: %s (%s)", erro.categoria, erro.detalhe)
            return render.pagina_kubeconfig(erro, agora)
        namespace = (consulta.get("ns") or [""])[0].strip() or None
        if namespace is not None and not traducao.namespace_valido(namespace):
            return render.pagina_namespace_invalido(contexto, namespace, agora)
        resultado = coleta.coletar(self.fabrica_acesso(contexto.api_client), contexto,
                                   namespace, self.relogio)
        return render.pagina(resultado)


class Manipulador(BaseHTTPRequestHandler):
    painel = None  # definido por criar_servidor
    server_version = "painel-cluster"
    sys_version = ""

    def do_GET(self):
        partes = urlsplit(self.path)
        agora = datetime.now().astimezone()
        if partes.path != "/":
            self._responder(404, render.pagina_simples(agora, "Página não encontrada", "O painel só tem a página inicial: /"))
            return
        try:
            corpo = self.painel.pagina(parse_qs(partes.query))
        except Exception:
            log.exception("erro inesperado ao montar a página")
            corpo = render.pagina_inesperada(agora)
        self._responder(200, corpo)

    def _metodo_nao_permitido(self):
        corpo = render.pagina_simples(datetime.now().astimezone(), "Método não permitido",
                                      "Este painel é somente leitura e aceita apenas GET.")
        self._responder(405, corpo, {"Allow": "GET"}, com_corpo=self.command != "HEAD")

    def __getattr__(self, nome):
        # Qualquer método HTTP que não seja GET (POST, PUT, PATCH, DELETE, HEAD,
        # OPTIONS, métodos inventados...) recebe 405, sem chegar à coleta.
        if nome.startswith("do_"):
            return self._metodo_nao_permitido
        raise AttributeError(nome)

    def _responder(self, status, corpo, cabecalhos=None, com_corpo=True):
        dados = corpo.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", render.CSP)
        for nome, valor in (cabecalhos or {}).items():
            self.send_header(nome, valor)
        self.end_headers()
        if com_corpo:
            self.wfile.write(dados)

    def log_message(self, formato, *args):
        log.info("%s - %s", self.address_string(), formato % args)


class ServidorLocal(HTTPServer):
    def server_bind(self):
        # Evita o getfqdn() do HTTPServer, lento em algumas redes Windows.
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


def criar_servidor(porta=PORTA_PADRAO, painel=None):
    """Cria o servidor ligado a 127.0.0.1. Não há parâmetro de endereço."""
    manipulador = type("ManipuladorDoPainel", (Manipulador,), {"painel": painel or Painel()})
    return ServidorLocal((ENDERECO, porta), manipulador)
