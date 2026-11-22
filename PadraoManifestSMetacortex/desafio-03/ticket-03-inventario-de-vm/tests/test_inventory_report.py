import json
import unittest

from tests.helpers import baseline_texto, inventario, nao_lido, ok, resposta_bruta
from vminv import compliance, inventory, report
from vminv.baseline import carregar_baseline
from vminv.errors import RespostaInvalida


class InterpretarRespostaTest(unittest.TestCase):  # 4.1, 4.2
    def test_inventario_totalmente_lido(self):
        inv = inventory.interpretar_resposta(json.dumps(resposta_bruta()), "10.0.0.5")
        self.assertEqual(inv.endereco, "10.0.0.5")
        for nome in inventory.FATOS_ESPERADOS:
            self.assertIn(nome, inv.fatos)
        self.assertTrue(inv.fato("so").lido)
        self.assertEqual(inv.fato("so").valor["versao"], "24.04")

    def test_inventario_com_varios_campos_nao_lidos(self):
        inv = inventario(so=nao_lido("a"), servicos=nao_lido("b"), kernel=nao_lido("c"))
        for nome, motivo in (("so", "a"), ("servicos", "b"), ("kernel", "c")):
            self.assertFalse(inv.fato(nome).lido)
            self.assertEqual(inv.fato(nome).motivo, motivo)
        self.assertTrue(inv.fato("swap").lido)

    def test_vazio_lido_difere_de_nao_lido(self):
        inv = inventario(servicos=ok([]), swap=ok({"habilitado": False, "tamanho_kib": 0}))
        self.assertTrue(inv.fato("servicos").lido)
        self.assertEqual(inv.fato("servicos").valor, [])

    def test_resposta_malformada_ou_truncada_e_falha(self):
        completo = json.dumps(resposta_bruta())
        for texto in ("", "não é json", completo[:len(completo) // 2], "[]", "null", "{}",
                      json.dumps({**resposta_bruta(), "formato": 99})):
            with self.subTest(texto=texto[:20]), self.assertRaises(RespostaInvalida):
                inventory.interpretar_resposta(texto, "h")

    def test_fato_ausente_ou_envelope_invalido_e_falha(self):
        sem_kernel = resposta_bruta()
        del sem_kernel["kernel"]
        for bruto in (sem_kernel, resposta_bruta(kernel="5.15"), resposta_bruta(kernel={"read": True}),
                      resposta_bruta(kernel={"read": False}), resposta_bruta(kernel={"read": "sim"})):
            with self.subTest(bruto=str(bruto.get("kernel"))), self.assertRaises(RespostaInvalida):
                inventory.interpretar_resposta(json.dumps(bruto), "h")

    def test_mensagem_de_falha_sem_stack_trace(self):
        with self.assertRaises(RespostaInvalida) as cm:
            inventory.interpretar_resposta("{truncado", "h")
        self.assertNotIn("Traceback", cm.exception.mensagem)
        self.assertNotIn("Expecting", cm.exception.mensagem)


# 2 desvios critico? não: swap (critico), servicos (alto); ssh.login_de_root nao_verificado; kernel conforme
BASELINE = carregar_baseline(baseline_texto(
    ("swap.habilitado", "false", "critico"),
    ("servicos.ativos", "[ssh, nginx]", "alto"),
    ("ssh.login_de_root", "false", "alto"),
    ("kernel.versao_minima", '"5.15"', "medio"),
    ("ntp.sincronizado", "false", "medio")))

CHAVES_DE_TOPO = ["host", "inventario", "conformidade", "resumo"]
CHAVES_DO_INVENTARIO = ["so", "kernel", "servicos", "swap", "portas_em_escuta", "chaves_ssh", "ssh", "ntp"]


def relatorio_de(inv, baseline=BASELINE):
    return report.montar_relatorio(inv, compliance.avaliar(baseline, inv))


class RelatorioJsonTest(unittest.TestCase):  # 7.1
    def setUp(self):
        self.inv = inventario()
        self.relatorio = relatorio_de(self.inv)
        self.dados = json.loads(report.relatorio_json(self.relatorio))

    def test_round_trip_e_chaves_de_topo_exatas(self):
        self.assertEqual(self.dados, self.relatorio)
        self.assertEqual(list(self.dados), CHAVES_DE_TOPO)

    def test_host(self):
        self.assertEqual(self.dados["host"],
                         {"endereco": "10.0.0.5", "hostname": "host-teste", "coletado_em": "2026-01-01T00:00:00Z"})

    def test_formato_do_inventario(self):
        inv = self.dados["inventario"]
        self.assertEqual(list(inv), CHAVES_DO_INVENTARIO)
        self.assertEqual(inv["so"], {"distribuicao": "ubuntu", "versao": "24.04"})
        self.assertEqual(inv["kernel"], {"versao": "5.15.0-101-generic"})
        self.assertEqual(inv["ssh"], {"login_de_root": None})  # não lido no cenário-base
        self.assertEqual(inv["ntp"], {"sincronizado": True, "mecanismo": "chrony"})
        self.assertEqual(inv["chaves_ssh"], [{"identificacao": "platform@metacortex-platform"}])

    def test_servicos_sem_sufixo_com_tipo_e_estado(self):
        self.assertEqual(self.dados["inventario"]["servicos"], [
            {"nome": "ssh", "tipo": "service", "estado": "active"},
            {"nome": "cron", "tipo": "service", "estado": "active"},
            {"nome": "ssh", "tipo": "socket", "estado": "active"}])

    def test_swap_em_bytes(self):
        self.assertEqual(self.dados["inventario"]["swap"], {"habilitado": True, "tamanho": 2048 * 1024})

    def test_portas_com_bind_e_processo_nulo_quando_nao_lido(self):
        self.assertEqual(self.dados["inventario"]["portas_em_escuta"], [
            {"porta": 22, "bind": "0.0.0.0", "processo": "sshd"},
            {"porta": 9100, "bind": "10.0.0.5", "processo": None}])

    def test_login_de_root_e_booleano_e_prohibit_password_conta_como_habilitado(self):
        for valor, esperado in (("no", False), ("yes", True), ("prohibit-password", True),
                                ("forced-commands-only", True)):
            with self.subTest(valor=valor):
                rel = relatorio_de(inventario(ssh_login_root=ok(valor)))
                self.assertIs(rel["inventario"]["ssh"]["login_de_root"], esperado)

    def test_identificacao_cai_no_fingerprint_sem_comentario(self):
        chaves = ok({"escopo": "usuario_conectado", "usuario": "u", "arquivo": "x", "chaves": [
            {"tipo": "ssh-ed25519", "comentario": "", "fingerprint": ok("SHA256:zzz")},
            {"tipo": "ssh-rsa", "comentario": "", "fingerprint": nao_lido("x")}]})
        rel = relatorio_de(inventario(chaves_ssh=chaves))
        self.assertEqual(rel["inventario"]["chaves_ssh"],
                         [{"identificacao": "SHA256:zzz"}, {"identificacao": None}])

    def test_swap_desabilitado_e_lido_nao_nulo(self):
        rel = relatorio_de(inventario(swap=ok({"habilitado": False, "tamanho_kib": 0})))
        self.assertEqual(rel["inventario"]["swap"], {"habilitado": False, "tamanho": 0})

    def test_ntp_sem_mecanismo_e_nenhum_e_nao_nulo(self):
        rel = relatorio_de(inventario(ntp=ok({"mecanismo": "nenhum", "ativo": False})))
        self.assertEqual(rel["inventario"]["ntp"], {"sincronizado": False, "mecanismo": "nenhum"})

    def test_campo_nao_lido_e_null_distinto_de_vazio(self):
        rel = relatorio_de(inventario(**{n: nao_lido("x") for n in inventory.FATOS_ESPERADOS}))
        inv = rel["inventario"]
        self.assertEqual(rel["host"], {"endereco": "10.0.0.5", "hostname": None, "coletado_em": None})
        self.assertEqual(inv["so"], {"distribuicao": None, "versao": None})
        self.assertEqual(inv["kernel"], {"versao": None})
        self.assertIsNone(inv["servicos"])
        self.assertEqual(inv["swap"], {"habilitado": None, "tamanho": None})
        self.assertIsNone(inv["portas_em_escuta"])
        self.assertIsNone(inv["chaves_ssh"])
        self.assertEqual(inv["ssh"], {"login_de_root": None})
        self.assertEqual(inv["ntp"], {"sincronizado": None, "mecanismo": None})

    def test_lidos_vazios_nao_viram_null(self):
        rel = relatorio_de(inventario(
            servicos=ok([]), portas=ok([]),
            chaves_ssh=ok({"escopo": "usuario_conectado", "usuario": "u", "arquivo": "x", "chaves": []})))
        inv = rel["inventario"]
        self.assertEqual((inv["servicos"], inv["portas_em_escuta"], inv["chaves_ssh"]), ([], [], []))

    def test_conformidade_e_lista_com_severidade_so_em_desvio_e_motivo_so_em_nao_verificado(self):
        entradas = self.dados["conformidade"]
        self.assertIsInstance(entradas, list)
        self.assertEqual([e["regra"] for e in entradas], [r.id for r in BASELINE.regras])
        por_regra = {e["regra"]: e for e in entradas}
        self.assertEqual(set(por_regra["swap.habilitado"]),
                         {"regra", "esperado", "encontrado", "veredito", "severidade"})
        self.assertEqual(por_regra["swap.habilitado"]["severidade"], "critico")
        self.assertEqual(por_regra["servicos.ativos"]["severidade"], "alto")
        self.assertEqual(por_regra["kernel.versao_minima"]["veredito"], "conforme")
        self.assertEqual(set(por_regra["kernel.versao_minima"]), {"regra", "esperado", "encontrado", "veredito"})

    def test_nao_verificado_tem_encontrado_null_e_motivo(self):
        e = {x["regra"]: x for x in self.dados["conformidade"]}["ssh.login_de_root"]
        self.assertEqual(e["veredito"], "nao_verificado")
        self.assertIsNone(e["encontrado"])
        self.assertTrue(e["motivo"])
        self.assertNotIn("severidade", e)

    def test_resumo_e_por_severidade(self):
        # swap (critico) e servicos.ativos (alto) são desvios; ntp.sincronizado=false com ntp ativo também (medio)
        self.assertEqual(self.dados["resumo"], {
            "conforme": 1, "desvio": 3, "nao_verificado": 1,
            "por_severidade": {"critico": 1, "alto": 1, "medio": 1}})
        r = self.dados["resumo"]
        self.assertEqual(r["conforme"] + r["desvio"] + r["nao_verificado"], len(BASELINE.regras))
        self.assertEqual(sum(r["por_severidade"].values()), r["desvio"])

    def test_json_nao_traz_o_layout_antigo(self):
        self.assertNotIn("total", self.dados["resumo"])
        self.assertNotIn("distribuicao", json.dumps(self.dados["conformidade"][:0]))


class RelatorioMarkdownTest(unittest.TestCase):  # 7.2
    def md(self, inv=None, baseline=BASELINE):
        inv = inv or inventario()
        return report.relatorio_markdown(report.montar_relatorio(inv, compliance.avaliar(baseline, inv)),
                                         baseline.versao)

    def secoes(self, md):
        partes = {}
        atual = None
        for linha in md.splitlines():
            if linha.startswith("## "):
                atual = linha[3:]
                partes[atual] = []
            elif atual:
                partes[atual].append(linha)
        return partes

    def test_estrutura(self):
        md = self.md()
        linhas = md.splitlines()
        self.assertEqual(linhas[0], "# Inventário — host-teste (10.0.0.5)")
        self.assertEqual(linhas[2], "Coletado em 2026-01-01T00:00:00Z · baseline v1")
        titulos = [l for l in linhas if l.startswith("## ")]
        self.assertEqual(titulos, ["## Desvios", "## Não verificado", "## Conforme"])

    def test_desvios_em_tabela_ordenada_por_severidade(self):
        baseline = carregar_baseline(baseline_texto(
            ("ntp.sincronizado", "false", "medio"),          # desvio medio (declarado primeiro)
            ("servicos.ativos", "[nginx]", "alto"),           # desvio alto
            ("swap.habilitado", "false", "critico")))         # desvio critico (declarado por último)
        desvios = self.secoes(self.md(baseline=baseline))["Desvios"]
        tabela = [l for l in desvios if l.startswith("|")]
        self.assertEqual(tabela[0], "| Severidade | Regra | Esperado | Encontrado |")
        self.assertEqual([l.split("|")[1].strip() for l in tabela[2:]], ["critico", "alto", "medio"])
        self.assertIn("`swap.habilitado`", tabela[2])

    def test_mesmo_nivel_mantem_a_ordem_do_baseline(self):
        baseline = carregar_baseline(baseline_texto(
            ("servicos.ativos", "[nginx]", "alto"), ("servicos.proibidos", "[ssh]", "alto")))
        tabela = [l for l in self.secoes(self.md(baseline=baseline))["Desvios"] if l.startswith("|")][2:]
        self.assertIn("servicos.ativos", tabela[0])
        self.assertIn("servicos.proibidos", tabela[1])

    def test_nao_verificado_em_tabela_regra_motivo(self):
        tabela = [l for l in self.secoes(self.md())["Não verificado"] if l.startswith("|")]
        self.assertEqual(tabela[0], "| Regra | Motivo |")
        self.assertIn("`ssh.login_de_root`", tabela[2])
        self.assertIn("sshd -T falhou", tabela[2])

    def test_conforme_em_lista_simples_separada_por_ponto_medio(self):
        baseline = carregar_baseline(baseline_texto(
            ("swap.habilitado", "true", "medio"), ("ntp.sincronizado", "true", "medio"),
            ("kernel.versao_minima", '"5.15"', "medio")))
        conforme = [l for l in self.secoes(self.md(baseline=baseline))["Conforme"] if l]
        self.assertEqual(conforme, ["swap.habilitado · ntp.sincronizado · kernel.versao_minima"])

    def test_secao_sem_itens_continua_presente(self):
        baseline = carregar_baseline(baseline_texto(("swap.habilitado", "true", "medio")))
        secoes = self.secoes(self.md(baseline=baseline))
        self.assertEqual([l for l in secoes["Desvios"] if l], ["Nenhum desvio."])
        self.assertEqual([l for l in secoes["Não verificado"] if l], ["Nenhuma regra não verificada."])
        baseline = carregar_baseline(baseline_texto(("swap.habilitado", "false", "medio")))
        self.assertEqual([l for l in self.secoes(self.md(baseline=baseline))["Conforme"] if l],
                         ["Nenhuma regra conforme."])

    def test_o_inventario_completo_nao_esta_no_markdown(self):
        md = self.md()
        for trecho in ("cron.service", "SHA256", "Portas em escuta", "platform@metacortex-platform", "10.0.0.5:", "chrony"):
            self.assertNotIn(trecho, md)

    def test_hostname_e_data_nao_lidos(self):
        md = self.md(inventario(hostname=nao_lido("x"), coletado_em=nao_lido("y")))
        self.assertEqual(md.splitlines()[0], "# Inventário — hostname não lido (10.0.0.5)")
        self.assertIn("Coletado em data não lida · baseline v1", md)

    def test_versao_do_baseline_aparece(self):
        inv = inventario()
        md = report.relatorio_markdown(relatorio_de(inv), 7)
        self.assertIn("· baseline v7", md)

    def test_tabela_nao_quebra_com_pipe(self):
        entrada = compliance.Entrada("r", "a|b", "c|d", compliance.DESVIO, severidade="alto")
        rel = {"host": {"endereco": "h", "hostname": "n", "coletado_em": "t"},
               "conformidade": [entrada.como_dict()]}
        self.assertIn("a\\|b", report.relatorio_markdown(rel, 1))
        self.assertIn("c\\|d", report.relatorio_markdown(rel, 1))

    def test_inventario_sem_nada_lido_ainda_gera_os_dois_relatorios(self):
        inv = inventario(**{n: nao_lido("x") for n in inventory.FATOS_ESPERADOS})
        rel = relatorio_de(inv)
        json.loads(report.relatorio_json(rel))
        self.assertIn("## Não verificado", report.relatorio_markdown(rel, 1))


if __name__ == "__main__":
    unittest.main()
