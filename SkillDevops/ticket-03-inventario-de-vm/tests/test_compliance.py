import unittest
from unittest import mock

from tests.helpers import baseline_texto, inventario, nao_lido, ok, resposta_bruta
from vminv import compliance, ssh_transport
from vminv.baseline import Baseline, Regra, carregar_baseline
from vminv.compliance import CONFORME, DESVIO, NAO_VERIFICADO, avaliar, avaliar_regra


def regra(id_, esperado, severidade="alta"):
    return Regra(id=id_, esperado=esperado, severidade=severidade)


def avalia(id_, esperado, **fatos):
    return avaliar_regra(regra(id_, esperado), inventario(**fatos))


def portas(*itens):
    return ok([{"endereco": e, "porta": p, "processo": nao_lido("x")} for e, p in itens])


class UmaEntradaPorRegraTest(unittest.TestCase):  # 6.1
    def test_contagem_igual_a_de_regras(self):
        regras = tuple([
            regra("servicos.ativos", ["ssh"]), regra("swap.habilitado", True),
            regra("ntp.sincronizado", True), regra("disco.inexistente", 1),
        ])
        entradas = avaliar(Baseline(1, "vms-do-parque", regras), inventario())
        self.assertEqual(len(entradas), len(regras))
        self.assertEqual([e.regra for e in entradas], [r.id for r in regras])
        for e in entradas:
            self.assertIsNotNone(e.veredito)


class TresVereditosTest(unittest.TestCase):  # 6.2
    def test_conforme(self):
        e = avalia("swap.habilitado", True)
        self.assertEqual((e.veredito, e.severidade, e.motivo), (CONFORME, None, None))

    def test_desvio_carrega_a_severidade_da_regra(self):
        e = avaliar_regra(regra("swap.habilitado", False, severidade="critica"), inventario())
        self.assertEqual((e.veredito, e.severidade), (DESVIO, "critica"))

    def test_nao_verificado_com_motivo_quando_fato_nao_lido(self):
        for id_, esperado, fato in (
            ("swap.habilitado", True, "swap"), ("servicos.ativos", ["ssh"], "servicos"),
            ("so.versao_minima", "22.04", "so"), ("kernel.versao_minima", "5.15", "kernel"),
            ("portas_em_escuta.publicas_permitidas", [22], "portas"),
            ("portas_em_escuta.somente_rede_interna", [9100], "portas"),
            ("chaves_ssh.emitidas_por", "x", "chaves_ssh"), ("ntp.sincronizado", True, "ntp"),
            ("ssh.login_de_root", False, "ssh_login_root"),
        ):
            with self.subTest(regra=id_):
                e = avalia(id_, esperado, **{fato: nao_lido("sem privilégio")})
                self.assertEqual(e.veredito, NAO_VERIFICADO)
                self.assertIn("sem privilégio", e.motivo)
                self.assertNotEqual(e.veredito, CONFORME)

    def test_login_de_root_no_laboratorio_e_nao_verificado(self):
        self.assertEqual(avalia("ssh.login_de_root", False).veredito, NAO_VERIFICADO)


class FormatoDaEntradaTest(unittest.TestCase):  # 6.2 — severidade só em desvio, motivo só em nao_verificado
    def test_conforme_nao_tem_severidade_nem_motivo(self):
        d = avalia("swap.habilitado", True).como_dict()
        self.assertEqual(set(d), {"regra", "esperado", "encontrado", "veredito"})

    def test_desvio_tem_severidade_e_nao_tem_motivo(self):
        d = avalia("swap.habilitado", False).como_dict()
        self.assertEqual(set(d), {"regra", "esperado", "encontrado", "veredito", "severidade"})
        self.assertEqual(d["severidade"], "alta")

    def test_nao_verificado_tem_motivo_encontrado_nulo_e_nao_tem_severidade(self):
        for e in (avalia("ssh.login_de_root", False), avalia("disco.livre_minimo", 10),
                  avalia("so.versao_minima", "22.04", so=ok({"distribuicao": "debian", "versao": "sid"}))):
            d = e.como_dict()
            self.assertEqual(set(d), {"regra", "esperado", "encontrado", "veredito", "motivo"})
            self.assertIsNone(d["encontrado"])
            self.assertTrue(d["motivo"])


class ResumoTest(unittest.TestCase):
    def test_por_severidade_conta_apenas_desvios(self):
        baseline = carregar_baseline(baseline_texto(
            ("swap.habilitado", "false", "critico"),                       # desvio critico
            ("portas_em_escuta.somente_rede_interna", "[9101]", "critico"),  # desvio critico (9101 ausente)
            ("servicos.ativos", "[ssh, nginx]", "alto"),                   # desvio alto
            ("ssh.login_de_root", "false", "alto"),                        # nao_verificado (não conta)
            ("kernel.versao_minima", '"5.15"', "medio"),                   # conforme (não conta)
            ("ntp.sincronizado", "true", "medio")))                        # conforme
        r = compliance.resumo(avaliar(baseline, inventario()))
        self.assertEqual(r, {"conforme": 2, "desvio": 3, "nao_verificado": 1,
                             "por_severidade": {"critico": 2, "alto": 1, "medio": 0}})
        self.assertNotIn("total", r)


class DeterminismoTest(unittest.TestCase):  # 6.3
    def test_mesmos_insumos_mesmos_vereditos(self):
        baseline = carregar_baseline(baseline_texto(
            ("servicos.ativos", "[ssh, nginx]", "alto"), ("swap.habilitado", "false", "medio"),
            ("ssh.login_de_root", "false", "critico")))
        inv = inventario()
        a = [e.como_dict() for e in avaliar(baseline, inv)]
        b = [e.como_dict() for e in avaliar(baseline, inv)]
        self.assertEqual(a, b)


class ComparacaoLocalTest(unittest.TestCase):  # 6.4
    def test_motor_nao_invoca_transporte_nem_subprocesso(self):
        baseline = carregar_baseline(baseline_texto(("swap.habilitado", "true", "medio")))
        with mock.patch.object(ssh_transport, "coletar", side_effect=AssertionError("transporte")), \
                mock.patch("subprocess.run", side_effect=AssertionError("subprocess")), \
                mock.patch("subprocess.Popen", side_effect=AssertionError("subprocess")):
            entradas = avaliar(baseline, inventario())
        self.assertEqual(entradas[0].veredito, CONFORME)

    def test_modulo_de_conformidade_nao_importa_o_transporte(self):
        self.assertNotIn("ssh_transport", vars(compliance))
        self.assertNotIn("subprocess", vars(compliance))


class DistribuicaoTest(unittest.TestCase):  # 6.11
    def test_igual_e_conforme_sem_diferenciar_caixa(self):
        for esperado in ("ubuntu", "Ubuntu", "UBUNTU"):
            with self.subTest(esperado=esperado):
                self.assertEqual(avalia("so.distribuicao", esperado).veredito, CONFORME)

    def test_diferente_e_desvio_com_severidade_e_a_distribuicao_encontrada(self):
        e = avalia("so.distribuicao", "ubuntu", so=ok({"distribuicao": "debian", "versao": "12"}))
        self.assertEqual((e.veredito, e.severidade, e.encontrado), (DESVIO, "alta", "debian"))

    def test_so_nao_lido_e_nao_verificado(self):
        e = avalia("so.distribuicao", "ubuntu", so=nao_lido("os-release ilegível"))
        self.assertEqual(e.veredito, NAO_VERIFICADO)
        self.assertIn("os-release ilegível", e.motivo)


class ServicosTest(unittest.TestCase):  # 6.5
    def test_ativos_todos_presentes(self):
        self.assertEqual(avalia("servicos.ativos", ["ssh", "cron"]).veredito, CONFORME)

    def test_ativos_nome_sem_sufixo_e_service_e_socket_exige_sufixo(self):
        self.assertEqual(avalia("servicos.ativos", ["ssh.socket"]).veredito, CONFORME)
        e = avalia("servicos.ativos", ["cron.socket"])
        self.assertEqual(e.veredito, DESVIO)
        self.assertEqual(e.encontrado["ausentes_ou_inativos"], ["cron.socket"])

    def test_ativos_ausente_lista_os_ausentes(self):
        e = avalia("servicos.ativos", ["ssh", "nginx"])
        self.assertEqual(e.veredito, DESVIO)
        self.assertEqual(e.encontrado["ausentes_ou_inativos"], ["nginx.service"])
        self.assertEqual(e.severidade, "alta")

    def test_proibidos_nenhum_presente(self):
        self.assertEqual(avalia("servicos.proibidos", ["telnet", "rsh"]).veredito, CONFORME)

    def test_proibidos_presente_lista_os_proibidos(self):
        e = avalia("servicos.proibidos", ["telnet", "cron"])
        self.assertEqual(e.veredito, DESVIO)
        self.assertEqual(e.encontrado["proibidos_presentes"], ["cron.service"])


class VersoesTest(unittest.TestCase):  # 6.6
    def test_comparacao_numerica_e_nao_textual(self):
        self.assertEqual(compliance.comparar_versoes((6, 10), (6, 9)), 1)   # texto diria 6.10 < 6.9
        self.assertEqual(compliance.comparar_versoes((24, 4), (22, 4)), 1)
        self.assertEqual(compliance.comparar_versoes((5, 15), (5, 15, 0)), 0)
        self.assertEqual(compliance.comparar_versoes((5, 4), (5, 15)), -1)

    def test_kernel_seis_dez_atende_minimo_seis_nove(self):
        e = avalia("kernel.versao_minima", "6.9", kernel=ok("6.10.2-generic"))
        self.assertEqual(e.veredito, CONFORME)

    def test_kernel_com_sufixo_de_build(self):
        self.assertEqual(avalia("kernel.versao_minima", "5.15.0").veredito, CONFORME)  # 5.15.0-101-generic
        self.assertEqual(avalia("kernel.versao_minima", "5.15.1").veredito, DESVIO)

    def test_so_vinte_e_quatro_zero_quatro_vs_vinte_e_dois(self):
        self.assertEqual(avalia("so.versao_minima", "22.04").veredito, CONFORME)
        e = avalia("so.versao_minima", "24.10")
        self.assertEqual((e.veredito, e.encontrado), (DESVIO, "24.04"))

    def test_versao_abaixo_da_minima_e_desvio(self):
        e = avalia("kernel.versao_minima", "6.1", kernel=ok("5.15.0-101-generic"))
        self.assertEqual(e.veredito, DESVIO)

    def test_versao_encontrada_ilegivel_e_nao_verificado(self):
        e = avalia("so.versao_minima", "22.04", so=ok({"distribuicao": "debian", "versao": "sid"}))
        self.assertEqual(e.veredito, NAO_VERIFICADO)
        e = avalia("kernel.versao_minima", "5.15", kernel=ok("desconhecido"))
        self.assertEqual(e.veredito, NAO_VERIFICADO)

    def test_versao_minima_ilegivel_no_baseline_e_baseline_invalido(self):
        from vminv.errors import BaselineInvalido
        for id_ in ("so.versao_minima", "kernel.versao_minima"):
            with self.subTest(regra=id_), self.assertRaises(BaselineInvalido):
                carregar_baseline(baseline_texto((id_, "jammy", "medio")))


class PortasTest(unittest.TestCase):  # 6.7
    def test_classificacao_de_enderecos(self):
        c = compliance.classificar_endereco
        for interno in ("127.0.0.1", "127.0.0.53%lo", "::1", "[::1]", "10.1.2.3", "172.16.0.1",
                        "172.31.255.255", "172.29.2.241", "192.168.1.1", "169.254.1.1", "fe80::1", "fd00::1",
                        "::ffff:10.0.0.1"):
            self.assertEqual(c(interno), "interno", interno)
        for publico in ("0.0.0.0", "::", "[::]", "*", "8.8.8.8", "172.32.0.1", "192.169.0.1",
                        "2001:db8::1", "::ffff:8.8.8.8", "isto-nao-e-ip"):
            self.assertEqual(c(publico), "publico", publico)

    def test_9100_em_0000_e_desvio_em_interno_e_conforme(self):
        e = avalia("portas_em_escuta.somente_rede_interna", [9100], portas=portas(("0.0.0.0", 9100)))
        self.assertEqual(e.veredito, DESVIO)
        self.assertEqual(e.encontrado, [{"porta": 9100, "enderecos": ["0.0.0.0"]}])
        for interno in ("172.29.2.241", "127.0.0.1", "10.0.0.5"):
            e = avalia("portas_em_escuta.somente_rede_interna", [9100], portas=portas((interno, 9100)))
            self.assertEqual(e.veredito, CONFORME, interno)

    def test_9100_em_0000_e_tambem_em_loopback_e_desvio(self):
        e = avalia("portas_em_escuta.somente_rede_interna", [9100],
                   portas=portas(("0.0.0.0", 9100), ("127.0.0.1", 9100)))
        self.assertEqual(e.veredito, DESVIO)

    def test_porta_inexistente_em_somente_rede_interna_e_desvio(self):
        e = avalia("portas_em_escuta.somente_rede_interna", [9100], portas=portas(("0.0.0.0", 22)))
        self.assertEqual(e.veredito, DESVIO)
        self.assertEqual(e.encontrado, [{"porta": 9100, "enderecos": []}])

    def test_publicas_permitidas_conforme_quando_so_listadas_ou_internas(self):
        e = avalia("portas_em_escuta.publicas_permitidas", [22],
                   portas=portas(("0.0.0.0", 22), ("::", 22), ("127.0.0.1", 9100), ("10.0.0.5", 9100)))
        self.assertEqual(e.veredito, CONFORME)

    def test_publicas_permitidas_desvio_lista_as_ofensoras(self):
        e = avalia("portas_em_escuta.publicas_permitidas", [22],
                   portas=portas(("0.0.0.0", 22), ("0.0.0.0", 9100), ("*", 8080)))
        self.assertEqual(e.veredito, DESVIO)
        self.assertEqual(e.encontrado["publicas_nao_permitidas"],
                         [{"endereco": "*", "porta": 8080}, {"endereco": "0.0.0.0", "porta": 9100}])


def chaves(*comentarios, fingerprint_lido=True):
    return ok({"escopo": "usuario_conectado", "usuario": "orpheu", "arquivo": ".ssh/authorized_keys",
               "chaves": [{"tipo": "ssh-ed25519", "comentario": c,
                           "fingerprint": ok(f"SHA256:fp{i}") if fingerprint_lido else nao_lido("x")}
                          for i, c in enumerate(comentarios)]})


class ChavesTest(unittest.TestCase):  # 6.8
    def test_comentario_com_emissor_compativel_e_conforme(self):
        e = avalia("chaves_ssh.emitidas_por", "metacortex-platform")
        self.assertEqual(e.veredito, CONFORME)
        self.assertIn("usuário que conectou", e.encontrado["escopo"])

    def test_emissor_diferente_e_desvio_com_identificacao(self):
        e = avalia("chaves_ssh.emitidas_por", "metacortex-platform",
                   chaves_ssh=chaves("platform@metacortex-platform", "joao@laptop"))
        self.assertEqual(e.veredito, DESVIO)
        self.assertEqual(e.encontrado["incompativeis"], ["joao@laptop"])

    def test_sem_comentario_e_desvio_e_usa_fingerprint(self):
        e = avalia("chaves_ssh.emitidas_por", "metacortex-platform", chaves_ssh=chaves(""))
        self.assertEqual(e.veredito, DESVIO)
        self.assertEqual(e.encontrado["incompativeis"], ["SHA256:fp0"])

    def test_sem_comentario_e_sem_fingerprint_nao_expoe_material(self):
        e = avalia("chaves_ssh.emitidas_por", "x", chaves_ssh=chaves("", fingerprint_lido=False))
        self.assertEqual(e.veredito, DESVIO)
        self.assertIn("sem identificação", e.encontrado["incompativeis"][0])

    def test_emissor_precisa_ser_igual_e_nao_sufixo(self):
        e = avalia("chaves_ssh.emitidas_por", "platform", chaves_ssh=chaves("a@metacortex-platform"))
        self.assertEqual(e.veredito, DESVIO)

    def test_conjunto_vazio_e_conforme(self):
        self.assertEqual(avalia("chaves_ssh.emitidas_por", "x", chaves_ssh=chaves()).veredito, CONFORME)

    def test_arquivo_nao_lido_e_nao_verificado(self):
        e = avalia("chaves_ssh.emitidas_por", "x", chaves_ssh=nao_lido("authorized_keys ilegível"))
        self.assertEqual(e.veredito, NAO_VERIFICADO)


class BooleanosTest(unittest.TestCase):  # 6.9
    def test_swap(self):
        self.assertEqual(avalia("swap.habilitado", True).veredito, CONFORME)
        self.assertEqual(avalia("swap.habilitado", False).veredito, DESVIO)
        off = ok({"habilitado": False, "tamanho_kib": 0})
        self.assertEqual(avalia("swap.habilitado", False, swap=off).veredito, CONFORME)
        self.assertEqual(avalia("swap.habilitado", True, swap=off).veredito, DESVIO)

    def test_ntp(self):
        self.assertEqual(avalia("ntp.sincronizado", True).veredito, CONFORME)
        inativo = ok({"mecanismo": "nenhum", "ativo": False})
        self.assertEqual(avalia("ntp.sincronizado", True, ntp=inativo).veredito, DESVIO)
        self.assertEqual(avalia("ntp.sincronizado", False, ntp=inativo).veredito, CONFORME)

    def test_login_de_root_mapeamento_do_valor_efetivo(self):
        casos = {"no": False, "yes": True, "prohibit-password": True, "forced-commands-only": True}
        for valor, habilitado in casos.items():
            for esperado in (True, False):
                with self.subTest(valor=valor, esperado=esperado):
                    e = avalia("ssh.login_de_root", esperado, ssh_login_root=ok(valor))
                    self.assertEqual(e.veredito, CONFORME if habilitado == esperado else DESVIO)
                    self.assertEqual(e.encontrado["habilitado"], habilitado)

    def test_prohibit_password_com_esperado_false_e_desvio(self):
        e = avalia("ssh.login_de_root", False, ssh_login_root=ok("prohibit-password"))
        self.assertEqual(e.veredito, DESVIO)
        self.assertEqual(e.encontrado["valor_efetivo"], "prohibit-password")


class FatoNaoColetadoTest(unittest.TestCase):  # 6.10
    def test_regra_sobre_fato_que_a_coleta_nao_produz(self):
        e = avalia("disco.livre_minimo", 10)
        self.assertEqual(e.veredito, NAO_VERIFICADO)
        self.assertIsNone(e.severidade)
        self.assertIn("a coleta não produz o fato", e.motivo)
        self.assertNotIn("não lido", e.motivo)

    def test_conta_como_uma_entrada_e_nunca_conforme(self):
        baseline = carregar_baseline(baseline_texto(
            ("disco.livre_minimo", "10", "alto"), ("swap.habilitado", "true", "medio")))
        entradas = avaliar(baseline, inventario())
        self.assertEqual(len(entradas), 2)
        self.assertEqual(entradas[0].veredito, NAO_VERIFICADO)

    def test_motivo_distingue_nao_produzido_de_nao_lido(self):
        produzido = avalia("disco.livre_minimo", 10).motivo
        nao_lido_ = avalia("swap.habilitado", True, swap=nao_lido("x")).motivo
        self.assertIn("não produz", produzido)
        self.assertIn("não lido", nao_lido_)


if __name__ == "__main__":
    unittest.main()
