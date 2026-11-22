"""CLI: coleta um host por SSH, compara com o baseline e reporta.

Códigos de saída: 0 sem desvio, 1 com pelo menos um desvio, 2 falha de execução.
Stdout carrega só o relatório; mensagens de erro vão para o stderr.
"""

import argparse
import sys

from . import baseline as baseline_mod
from . import compliance, inventory, report, ssh_transport
from .errors import BaselineInvalido, FalhaDeExecucao, SaidaNaoGravavel, UsoIncorreto

EXIT_CONFORME = 0
EXIT_DESVIO = 1
EXIT_FALHA = 2

OBRIGATORIOS = (("host", "--host"), ("usuario", "--usuario"), ("chave", "--chave"),
                ("baseline", "--baseline"))


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise UsoIncorreto(f"argumentos inválidos: {message}. Use --help para ver o uso.")


def criar_parser():
    p = _Parser(
        prog="python -m vminv",
        allow_abbrev=False,
        description="Levanta o inventário de UMA VM por SSH (somente leitura) e o compara "
                    "com o baseline do parque. Saída: 0 sem desvio, 1 com desvio, 2 falha de execução.",
    )
    p.add_argument("--host", help="endereço da VM alvo (um único host por execução)")
    p.add_argument("--usuario", help="usuário SSH (comum, sem privilégio)")
    p.add_argument("--chave", help="caminho da chave privada (só o caminho é usado; a chave nunca é lida)")
    p.add_argument("--baseline", help="caminho do baseline.yaml")
    p.add_argument("--timeout", type=int, default=ssh_transport.CONNECT_TIMEOUT_PADRAO,
                   help="ConnectTimeout do ssh, em segundos (padrão: %(default)s)")
    p.add_argument("--aceitar-host-novo", action="store_true",
                   help="aceita a chave de um host ainda desconhecido (StrictHostKeyChecking=accept-new); "
                        "chave de host alterada continua sendo recusada")
    p.add_argument("--formato", choices=("markdown", "json"), default="markdown",
                   help="relatório enviado ao stdout (padrão: %(default)s)")
    p.add_argument("--saida-json", metavar="ARQUIVO", help="grava também o relatório JSON neste arquivo")
    p.add_argument("--saida-markdown", metavar="ARQUIVO", help="grava também o relatório Markdown neste arquivo")
    return p


def _validar_obrigatorios(args):
    faltando = [flag for atributo, flag in OBRIGATORIOS if not getattr(args, atributo)]
    if faltando:
        raise UsoIncorreto(
            f"faltam argumentos obrigatórios: {', '.join(faltando)}. Use --help para ver o uso."
        )
    if args.timeout < 1:
        raise UsoIncorreto("--timeout deve ser um número de segundos maior que zero")


def _ler_baseline(caminho):
    try:
        with open(caminho, "r", encoding="utf-8") as arq:
            texto = arq.read()
    except (OSError, UnicodeDecodeError):
        raise BaselineInvalido(
            f"baseline inválido: não foi possível ler o arquivo '{caminho}'"
        ) from None
    return baseline_mod.carregar_baseline(texto)


def _gravar(caminho, conteudo):
    try:
        with open(caminho, "w", encoding="utf-8", newline="\n") as arq:
            arq.write(conteudo)
    except OSError:
        raise SaidaNaoGravavel(
            f"não foi possível gravar o arquivo de saída '{caminho}'"
        ) from None


def _configurar_stdout():
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def executar(args, executor=None):
    """Roda o fluxo completo e devolve o código de saída. Levanta `FalhaDeExecucao`."""
    _validar_obrigatorios(args)
    baseline = _ler_baseline(args.baseline)  # baseline ruim falha antes de tocar no host
    kwargs = {"executor": executor} if executor else {}
    resposta = ssh_transport.coletar(
        args.host, args.usuario, args.chave, timeout=args.timeout,
        aceitar_host_novo=args.aceitar_host_novo, **kwargs)
    inv = inventory.interpretar_resposta(resposta, args.host)
    entradas = compliance.avaliar(baseline, inv)
    relatorio = report.montar_relatorio(inv, entradas)
    em_json = report.relatorio_json(relatorio)
    em_markdown = report.relatorio_markdown(relatorio, baseline.versao)
    if args.saida_json:
        _gravar(args.saida_json, em_json)
    if args.saida_markdown:
        _gravar(args.saida_markdown, em_markdown)
    sys.stdout.write(em_json if args.formato == "json" else em_markdown)
    sys.stdout.flush()
    tem_desvio = any(e.veredito == compliance.DESVIO for e in entradas)
    return EXIT_DESVIO if tem_desvio else EXIT_CONFORME


def main(argv=None, executor=None):
    _configurar_stdout()
    try:
        args = criar_parser().parse_args(argv)
        return executar(args, executor=executor)
    except FalhaDeExecucao as falha:
        print(f"erro: {falha.mensagem}", file=sys.stderr)
        return EXIT_FALHA
    except KeyboardInterrupt:
        print("erro: execução interrompida pelo operador", file=sys.stderr)
        return EXIT_FALHA
    except Exception:  # noqa: BLE001 — nunca vaza stack trace nem texto interno de exceção
        print("erro: falha inesperada da ferramenta (sem detalhes exibidos por segurança)",
              file=sys.stderr)
        return EXIT_FALHA
