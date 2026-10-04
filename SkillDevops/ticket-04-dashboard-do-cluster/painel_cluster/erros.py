"""Categorias de erro do painel (design.md, D6).

Nenhuma exceção chega ao HTML: o renderizador recebe só a categoria e
campos de texto já pensados para exibição.
"""

KUBECONFIG_INVALIDO = "kubeconfig-invalido"
SEM_CONTEXTO = "sem-contexto"
NAO_RESPONDEU = "nao-respondeu"
CREDENCIAL = "credencial"
SEM_PERMISSAO = "sem-permissao"
INESPERADO = "inesperado"

# Categorias que valem para o cluster inteiro, não para um bloco.
GLOBAIS = frozenset({KUBECONFIG_INVALIDO, SEM_CONTEXTO, NAO_RESPONDEU, CREDENCIAL})

# Tipos de problema de kubeconfig-invalido.
INEXISTENTE = "inexistente"
ILEGIVEL = "ilegível"
MALFORMADO = "malformado"


class ErroPainel(Exception):
    """Erro já classificado.

    `caminho` e `tipo` só se aplicam a kubeconfig-invalido e sem-contexto;
    `recurso` só a erros de listagem. `detalhe` vai para o log local, nunca
    para a tela.
    """

    def __init__(self, categoria, *, recurso=None, caminho=None, tipo=None,
                 motivo=None, detalhe=""):
        super().__init__(categoria)
        self.categoria = categoria
        self.recurso = recurso
        self.caminho = caminho
        self.tipo = tipo
        self.motivo = motivo
        self.detalhe = detalhe

    def __repr__(self):
        return f"ErroPainel({self.categoria!r}, recurso={self.recurso!r})"
