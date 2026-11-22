"""Falhas de execução: sempre terminam o processo com código 2 e uma mensagem simples."""


class FalhaDeExecucao(Exception):
    """Falha que impede a ferramenta de entregar um resultado confiável.

    A mensagem é escrita em linguagem simples para o operador; nunca carrega
    stack trace, texto cru do `ssh` nem conteúdo da chave privada.
    """

    def __init__(self, mensagem):
        super().__init__(mensagem)
        self.mensagem = mensagem


class UsoIncorreto(FalhaDeExecucao):
    """Argumentos de linha de comando ausentes ou inválidos."""


class BaselineInvalido(FalhaDeExecucao):
    """`baseline.yaml` que não pode ser interpretado com segurança."""


class FalhaDeConexao(FalhaDeExecucao):
    """Host inalcançável, chave do host não confiável ou autenticação recusada."""


class RespostaInvalida(FalhaDeExecucao):
    """Resposta do script de coleta malformada ou truncada."""


class SaidaNaoGravavel(FalhaDeExecucao):
    """Arquivo de saída que não pôde ser gravado."""
