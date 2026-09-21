"""Transporte SSH: subprocesso do cliente `ssh` do sistema.

A chave privada é tratada como credencial: este módulo só conhece o *caminho*
dela e o entrega ao `ssh` por `-i`; o arquivo nunca é aberto ou lido aqui. O
stderr do `ssh` é classificado em categorias fixas e nunca é repassado cru.
"""

import enum
import os
import shutil
import subprocess
from pathlib import Path

from .errors import FalhaDeConexao, FalhaDeExecucao

CONNECT_TIMEOUT_PADRAO = 10
# Teto para a sessão inteira (o ConnectTimeout só cobre o estabelecimento da conexão).
TEMPO_MAXIMO_SESSAO = 120

COLETOR_PATH = Path(__file__).with_name("collector.sh")


class Resultado(enum.Enum):
    SUCESSO = "sucesso"
    INALCANCAVEL = "inalcancavel"
    HOST_DESCONHECIDO = "host_desconhecido"
    HOST_ALTERADO = "host_alterado"
    AUTENTICACAO = "autenticacao"
    OUTRA = "outra"


MENSAGENS = {
    Resultado.INALCANCAVEL: (
        "não foi possível conectar ao host {host}: inalcançável, sem resposta dentro do "
        "tempo limite ou conexão recusada/encerrada"
    ),
    Resultado.HOST_DESCONHECIDO: (
        "a chave do host {host} é desconhecida (não consta no known_hosts) e a política "
        "padrão recusa hosts desconhecidos; confirme a identidade do host e adicione-o ao "
        "known_hosts, ou use --aceitar-host-novo se aceitar esse risco"
    ),
    Resultado.HOST_ALTERADO: (
        "a chave do host {host} foi alterada em relação à registrada no known_hosts; "
        "a conexão foi recusada por segurança (possível troca do host ou interceptação)"
    ),
    Resultado.AUTENTICACAO: (
        "o host {host} rejeitou a autenticação SSH para o usuário {usuario}: chave recusada, "
        "protegida por senha ou sem permissão de uso"
    ),
    Resultado.OUTRA: (
        "a coleta em {host} falhou por um motivo não classificado (código de saída {codigo} "
        "do cliente ssh)"
    ),
}


def montar_argv(host, usuario, caminho_chave, timeout=CONNECT_TIMEOUT_PADRAO,
                aceitar_host_novo=False, ssh_bin="ssh"):
    """Monta o argv do cliente `ssh`. A chave só aparece como caminho, em `-i`."""
    politica = "accept-new" if aceitar_host_novo else "yes"
    return [
        ssh_bin,
        "-i", str(caminho_chave),
        "-o", "IdentitiesOnly=yes",
        "-o", "BatchMode=yes",
        "-o", f"ConnectTimeout={int(timeout)}",
        "-o", f"StrictHostKeyChecking={politica}",
        f"{usuario}@{host}",
        "sh", "-s",
    ]


def classificar(codigo_saida, stderr_texto):
    """Classifica o desfecho do subprocesso.

    O status de saída vem primeiro (255 = falha de conexão/autenticação do
    próprio ssh); o texto do stderr é só apoio para distinguir subcategorias,
    porque varia entre versões e locales do OpenSSH.
    """
    if codigo_saida == 0:
        return Resultado.SUCESSO
    if codigo_saida != 255:
        return Resultado.OUTRA
    texto = (stderr_texto or "").lower()
    if "host key verification failed" in texto or "host identification has changed" in texto:
        if "identification has changed" in texto or "offending" in texto:
            return Resultado.HOST_ALTERADO
        return Resultado.HOST_DESCONHECIDO
    if "permission denied" in texto or "no supported authentication" in texto:
        return Resultado.AUTENTICACAO
    return Resultado.INALCANCAVEL


def _mensagem(resultado, host, usuario, codigo):
    return MENSAGENS[resultado].format(host=host, usuario=usuario, codigo=codigo)


def ler_coletor():
    """Devolve o script de coleta como bytes, com finais de linha LF."""
    return COLETOR_PATH.read_bytes().replace(b"\r\n", b"\n")


def coletar(host, usuario, caminho_chave, timeout=CONNECT_TIMEOUT_PADRAO,
            aceitar_host_novo=False, ssh_bin=None, executor=subprocess.run):
    """Executa a coleta em uma única sessão SSH e devolve o stdout do script.

    `executor` existe para os testes injetarem um test double do subprocesso.
    """
    # Só verifica a existência do caminho; o conteúdo da chave nunca é aberto.
    if not os.path.isfile(caminho_chave):
        raise FalhaDeExecucao(
            f"chave privada não encontrada em '{caminho_chave}' "
            "(verifique o caminho informado em --chave)"
        )
    binario = ssh_bin or shutil.which("ssh")
    if not binario:
        raise FalhaDeExecucao("o cliente ssh do sistema não foi encontrado no PATH")

    argv = montar_argv(host, usuario, caminho_chave, timeout, aceitar_host_novo, binario)
    try:
        proc = executor(
            argv,
            input=ler_coletor(),
            capture_output=True,
            timeout=TEMPO_MAXIMO_SESSAO,
        )
    except subprocess.TimeoutExpired:
        raise FalhaDeConexao(
            f"a sessão SSH com {host} excedeu o tempo máximo de {TEMPO_MAXIMO_SESSAO}s "
            "e foi interrompida"
        ) from None
    except OSError:
        raise FalhaDeExecucao("não foi possível executar o cliente ssh do sistema") from None

    stderr_texto = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""
    resultado = classificar(proc.returncode, stderr_texto)
    if resultado is Resultado.SUCESSO:
        return proc.stdout.decode("utf-8", errors="replace")
    mensagem = _mensagem(resultado, host, usuario, proc.returncode)
    if resultado is Resultado.OUTRA:
        raise FalhaDeExecucao(mensagem)
    raise FalhaDeConexao(mensagem)
