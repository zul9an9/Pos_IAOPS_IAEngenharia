import pathlib
import unittest

from tests.helpers import baseline_texto
from vminv.baseline import carregar_baseline, parse_yaml
from vminv.errors import BaselineInvalido

RAIZ = pathlib.Path(__file__).resolve().parent.parent
BASELINE_OFICIAL = (RAIZ / "baseline.exemplo.yaml").read_text(encoding="utf-8")

REGRA_SWAP = ("swap.habilitado", "true", "medio")


def swap(**kw):
    return baseline_texto(REGRA_SWAP, **kw)


class ParserValidoTest(unittest.TestCase):  # 5.1
    def test_baseline_oficial_do_enunciado(self):
        b = carregar_baseline(BASELINE_OFICIAL)
        self.assertEqual((b.versao, b.aplica_a), (1, "vms-do-parque"))
        self.assertEqual([r.id for r in b.regras], [
            "so.distribuicao", "so.versao_minima", "kernel.versao_minima",
            "servicos.ativos", "servicos.proibidos", "swap.habilitado",
            "portas_em_escuta.publicas_permitidas", "portas_em_escuta.somente_rede_interna",
            "chaves_ssh.emitidas_por", "ssh.login_de_root", "ntp.sincronizado"])
        por_id = {r.id: r for r in b.regras}
        self.assertEqual(por_id["so.distribuicao"].esperado, "ubuntu")
        self.assertEqual(por_id["so.versao_minima"].esperado, "22.04")
        self.assertEqual(por_id["kernel.versao_minima"].esperado, "6.5")
        self.assertEqual(por_id["servicos.ativos"].esperado, ["ssh", "containerd", "node_exporter", "chrony"])
        self.assertEqual(por_id["servicos.proibidos"].esperado, ["telnet.socket", "rpcbind.socket"])
        self.assertIs(por_id["swap.habilitado"].esperado, False)
        self.assertEqual(por_id["portas_em_escuta.publicas_permitidas"].esperado, [22])
        self.assertEqual(por_id["portas_em_escuta.somente_rede_interna"].esperado, [9100])
        self.assertEqual(por_id["chaves_ssh.emitidas_por"].esperado, "metacortex-platform")
        self.assertIs(por_id["ssh.login_de_root"].esperado, False)
        self.assertIs(por_id["ntp.sincronizado"].esperado, True)

    def test_mapeamento_em_linha_com_listas(self):
        self.assertEqual(
            parse_yaml("servicos: {ativos: [ssh, chrony], proibidos: [telnet.socket]}\n"),
            {"servicos": {"ativos": ["ssh", "chrony"], "proibidos": ["telnet.socket"]}})

    def test_flow_style_variacoes(self):
        self.assertEqual(parse_yaml("a: {x: 1, y: true, z: \"q, r\"}\n"), {"a": {"x": 1, "y": True, "z": "q, r"}})
        self.assertEqual(parse_yaml("a: []\nb: {}\n" if False else "a: []\n"), {"a": []})
        self.assertEqual(parse_yaml("a: { x: [ 1 , 2 ] }   # comentário\n"), {"a": {"x": [1, 2]}})

    def test_documento_com_marcador_inicial_unico(self):
        self.assertEqual(parse_yaml("---\na: 1\n"), {"a": 1})

    def test_lista_em_bloco_e_no_mesmo_nivel_da_chave(self):
        self.assertEqual(parse_yaml("a:\n- x\n- z\nb: 2\n"), {"a": ["x", "z"], "b": 2})
        self.assertEqual(parse_yaml("a:\n  - x\n  - z\n"), {"a": ["x", "z"]})

    def test_aspas_e_cerquilha_em_string(self):
        self.assertEqual(parse_yaml("a: 'x # y'\nb: \"c\\\"d\"\n"), {"a": "x # y", "b": 'c"d'})

    def test_booleano_entre_aspas_e_texto(self):
        self.assertEqual(parse_yaml('a: "no"\n'), {"a": "no"})


class ParserRejeicoesTest(unittest.TestCase):  # 5.2
    def rejeita(self, texto, trecho):
        with self.assertRaises(BaselineInvalido) as cm:
            parse_yaml(texto)
        self.assertIn(trecho, cm.exception.mensagem)
        self.assertRegex(cm.exception.mensagem, r"linha \d+")

    def test_ancora(self):
        self.rejeita("a: &x 1\n", "âncora")

    def test_alias(self):
        self.rejeita("a: 1\nb: *x\n", "alias")

    def test_multi_documento(self):
        self.rejeita("a: 1\n---\nb: 2\n", "múltiplos documentos")

    def test_marcador_fim_de_documento(self):
        self.rejeita("a: 1\n...\n", "fim de documento")

    def test_tag(self):
        self.rejeita("a: !!str 1\n", "tag")

    def test_bloco_literal(self):
        self.rejeita("a: |\n  texto\n", "bloco literal")

    def test_mapeamento_em_linha_aninhado(self):
        self.rejeita("a: {x: {y: 1}}\n", "mapeamento em linha aninhado")

    def test_lista_aninhada_em_linha(self):
        self.rejeita("a: [[1], 2]\n", "aninhada")
        self.rejeita("a: {x: [[1]]}\n", "aninhada")

    def test_mapeamento_dentro_de_lista_em_linha(self):
        self.rejeita("a: [{x: 1}]\n", "mapeamento dentro de lista")

    def test_flow_multilinha(self):
        self.rejeita("a: [x,\n  y]\n", "não fechado")
        self.rejeita("a: {x: 1,\n  y: 2}\n", "não fechado")

    def test_flow_malformado(self):
        self.rejeita("a: {x 1}\n", "chave: valor")
        self.rejeita("a: {x: }\n", "vazio")
        self.rejeita("a: [x, ]\n", "vazio")
        self.rejeita("a: {x: 1, x: 2}\n", "duplicada")
        self.rejeita("a: [x] y\n", "após o fechamento")

    def test_mapeamento_dentro_de_lista_em_bloco(self):
        self.rejeita("a:\n  - x: 1\n", "mapeamento dentro de uma lista")

    def test_tabulacao(self):
        self.rejeita("a:\n\tb: 1\n", "tabulação")

    def test_chave_duplicada(self):
        self.rejeita("a: 1\na: 2\n", "duplicada")

    def test_booleanos_ambiguos(self):
        for valor in ("yes", "no", "on", "off", "Yes", "NO", "y", "n", "null", "~", "True", "FALSE"):
            with self.subTest(valor=valor):
                self.rejeita(f"a: {valor}\n", "ambíguo")

    def test_booleano_ambiguo_em_flow_style(self):
        self.rejeita("a: [ssh, no]\n", "ambíguo")
        self.rejeita("a: {habilitado: yes}\n", "ambíguo")

    def test_inteiro_com_zero_a_esquerda(self):
        self.rejeita("a: 0755\n", "zero à esquerda")

    def test_valor_ausente(self):
        self.rejeita("a:\nb: 1\n", "não tem valor")

    def test_escape_nao_suportado(self):
        self.rejeita('a: "x\\ty"\n', "escape")


class LayoutDoBaselineTest(unittest.TestCase):  # 5.3 e 5.5
    def rejeita(self, texto, trecho):
        with self.assertRaises(BaselineInvalido) as cm:
            carregar_baseline(texto)
        self.assertIn(trecho, cm.exception.mensagem)

    def test_arquivo_vazio(self):
        self.rejeita("", "vazio")

    def test_raiz_nao_mapeamento(self):
        self.rejeita("- a\n- b\n", "mapeamento")

    def test_ids_e_severidades_do_baseline_oficial(self):
        esperadas = {
            "swap.habilitado": "critico", "chaves_ssh.emitidas_por": "critico",
            "portas_em_escuta.publicas_permitidas": "critico",
            "portas_em_escuta.somente_rede_interna": "critico",
            "servicos.ativos": "alto", "servicos.proibidos": "alto", "ssh.login_de_root": "alto",
            "so.distribuicao": "alto", "so.versao_minima": "alto",
            "kernel.versao_minima": "medio", "ntp.sincronizado": "medio"}
        b = carregar_baseline(BASELINE_OFICIAL)
        self.assertEqual({r.id: r.severidade for r in b.regras}, esperadas)

    def test_chave_de_raiz_desconhecida_inclusive_o_layout_antigo(self):
        self.rejeita(swap() + "extra: 1\n", "desconhecida")
        self.rejeita("versao: 1\nregras:\n  swap.habilitado:\n    esperado: true\n    severidade: medio\n",
                     "'regras'")

    def test_chaves_de_raiz_ausentes(self):
        esperado = "esperado:\n  swap: {habilitado: true}\n"
        severidade = "severidade:\n  medio: [swap.habilitado]\n"
        casos = {"aplica_a": f"versao: 1\n{esperado}{severidade}",
                 "esperado": f"versao: 1\naplica_a: x\n{severidade}",
                 "severidade": f"versao: 1\naplica_a: x\n{esperado}"}
        for chave, texto in casos.items():
            with self.subTest(chave=chave):
                self.rejeita(texto, f"'{chave}' está ausente")

    def test_aplica_a_vazio_ou_de_tipo_errado(self):
        self.rejeita(swap().replace("aplica_a: vms-do-parque", "aplica_a: 5"), "aplica_a")
        self.rejeita(swap().replace("aplica_a: vms-do-parque", 'aplica_a: ""'), "aplica_a")

    def test_grupo_de_esperado_que_nao_e_mapeamento(self):
        self.rejeita("versao: 1\naplica_a: x\nesperado:\n  swap: 3\nseveridade:\n  medio: []\n", "grupo 'swap'")

    def test_valores_esperados_de_tipo_errado(self):
        casos = [
            (("swap.habilitado", "sim", "medio"), "true ou false"),
            (("ssh.login_de_root", "1", "alto"), "true ou false"),
            (("so.versao_minima", "jammy", "alto"), "versão numérica"),
            (("kernel.versao_minima", "[6, 5]", "medio"), "versão numérica"),
            (("so.distribuicao", "[ubuntu]", "alto"), "texto não vazio"),
            (("servicos.ativos", "ssh", "alto"), "lista de nomes"),
            (("portas_em_escuta.publicas_permitidas", "[22, 70000]", "critico"), "portas"),
            (("portas_em_escuta.somente_rede_interna", "[ssh]", "critico"), "portas"),
            (("chaves_ssh.emitidas_por", "[a]", "critico"), "texto não vazio"),
        ]
        for regra, trecho in casos:
            with self.subTest(regra=regra[0]):
                self.rejeita(baseline_texto(regra), trecho)

    def test_regra_desconhecida_com_severidade_e_aceita(self):
        b = carregar_baseline(baseline_texto(("disco.livre_minimo", "10", "medio")))
        self.assertEqual((b.regras[0].id, b.regras[0].esperado), ("disco.livre_minimo", 10))

    def test_ordem_das_regras_e_a_de_esperado(self):
        b = carregar_baseline(baseline_texto(("ntp.sincronizado", "true", "medio"),
                                             ("swap.habilitado", "false", "critico"),
                                             ("kernel.versao_minima", '"6.5"', "medio")))
        self.assertEqual([r.id for r in b.regras], ["ntp.sincronizado", "swap.habilitado", "kernel.versao_minima"])


class SeveridadesFechadasTest(unittest.TestCase):  # 5.6
    def rejeita(self, texto, trecho):
        with self.assertRaises(BaselineInvalido) as cm:
            carregar_baseline(texto)
        self.assertIn(trecho, cm.exception.mensagem)

    def base(self, severidade):
        return ("versao: 1\naplica_a: x\nesperado:\n  swap: {habilitado: true}\n  ntp: {sincronizado: true}\n"
                f"severidade:\n{severidade}")

    def test_severidade_fora_do_conjunto(self):
        for nivel in ("baixo", "critica", "urgente", "alta", "médio", "crítico"):
            with self.subTest(nivel=nivel):
                self.rejeita(self.base(f"  {nivel}: [swap.habilitado, ntp.sincronizado]\n"),
                             f"severidade desconhecida '{nivel}'")

    def test_regra_sem_severidade(self):
        self.rejeita(self.base("  critico: [swap.habilitado]\n"), "'ntp.sincronizado' não tem severidade")

    def test_severidade_vazia_deixa_todas_as_regras_sem_severidade(self):
        self.rejeita(self.base("  critico: []\n"), "não tem severidade")

    def test_regra_em_dois_niveis(self):
        self.rejeita(self.base("  critico: [swap.habilitado, ntp.sincronizado]\n  medio: [swap.habilitado]\n"),
                     "mais de um nível")

    def test_id_de_severidade_inexistente_em_esperado(self):
        self.rejeita(self.base("  critico: [swap.habilitado, ntp.sincronizado, swap.habilitad0]\n"),
                     "'swap.habilitad0', que não existe")

    def test_severidade_que_nao_e_mapeamento_ou_lista(self):
        self.rejeita(self.base("  critico: swap.habilitado\n"), "lista de ids")
        self.rejeita("versao: 1\naplica_a: x\nesperado:\n  swap: {habilitado: true}\nseveridade: [critico]\n",
                     "mapeamento de nível")

    def test_severidade_valida_vem_do_nivel_em_que_a_regra_aparece(self):
        b = carregar_baseline(self.base("  alto: [ntp.sincronizado]\n  medio: [swap.habilitado]\n"))
        self.assertEqual({r.id: r.severidade for r in b.regras},
                         {"swap.habilitado": "medio", "ntp.sincronizado": "alto"})

    def test_niveis_sem_regras_sao_opcionais(self):
        b = carregar_baseline(self.base("  critico: [swap.habilitado, ntp.sincronizado]\n"))
        self.assertEqual({r.severidade for r in b.regras}, {"critico"})


class VersaoDoBaselineTest(unittest.TestCase):  # 5.4
    def rejeita(self, texto, trecho):
        with self.assertRaises(BaselineInvalido) as cm:
            carregar_baseline(texto)
        self.assertIn(trecho, cm.exception.mensagem)
        return cm.exception.mensagem

    def com_versao(self, linha):
        return swap().replace("versao: 1", linha)

    def sem_versao(self):
        return "\n".join(l for l in swap().splitlines() if not l.startswith("versao")) + "\n"

    def test_ausente(self):
        msg = self.rejeita(self.sem_versao(), "ausente")
        self.assertIn("'versao'", msg)

    def test_desconhecida_texto(self):
        self.rejeita(self.com_versao("versao: abc"), "desconhecida")

    def test_desconhecida_texto_entre_aspas(self):
        self.rejeita(self.com_versao('versao: "1"'), "desconhecida")

    def test_desconhecida_zero(self):
        self.rejeita(self.com_versao("versao: 0"), "desconhecida")

    def test_desconhecida_booleano(self):
        self.rejeita(self.com_versao("versao: true"), "desconhecida")

    def test_desconhecida_lista(self):
        self.rejeita(self.com_versao("versao: [1]"), "desconhecida")

    def test_futura(self):
        self.rejeita(self.com_versao("versao: 2"), "futura")

    def test_mensagens_distintas(self):
        msgs = set()
        for texto in (self.sem_versao(), self.com_versao("versao: abc"), self.com_versao("versao: 2")):
            with self.assertRaises(BaselineInvalido) as cm:
                carregar_baseline(texto)
            msgs.add(cm.exception.mensagem)
        self.assertEqual(len(msgs), 3)

    def test_versao_1_prossegue(self):
        self.assertEqual(carregar_baseline(swap()).versao, 1)

    def test_versao_invalida_nao_avalia_regras(self):
        # o resto do baseline também está inválido: se a versão fosse ignorada, o erro seria outro
        texto = "versao: 9\naplica_a: x\nesperado:\n  swap: {habilitado: sim}\nseveridade:\n  urgente: []\n"
        self.rejeita(texto, "futura")


if __name__ == "__main__":
    unittest.main()
