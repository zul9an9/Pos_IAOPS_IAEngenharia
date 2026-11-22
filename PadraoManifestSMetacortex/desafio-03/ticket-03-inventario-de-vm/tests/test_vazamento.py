"""Confidencialidade da chave privada (tarefas 2.3 e 7.4).

Uma chave com conteúdo sentinela é usada em toda execução; nenhum texto capturado
(stdout, stderr, arquivos de saída, mensagens de erro) pode conter esse conteúdo.
O caminho da chave só pode aparecer em mensagens de erro do stderr.
"""

import builtins
import json
import os
import pathlib
import unittest
from unittest import mock

from tests.helpers import CONTEUDO_CHAVE, ExecutorFalso, resposta_bruta
from tests.test_cli import STDERR_AUTH, STDERR_HOST_DESCONHECIDO, STDERR_TIMEOUT, Ambiente
from vminv import ssh_transport

HOST_ALTERADO = (b"@@@ WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED! @@@\n"
                 b"Host key verification failed.\n")


def com_vazamento_no_stderr(base):
    """Simula um `ssh` que ecoaria conteúdo da chave no stderr (o que nunca pode ser repassado)."""
    return base + f"\nLoad key: {CONTEUDO_CHAVE}\n".encode()


def resposta():
    return json.dumps(resposta_bruta()).encode("utf-8")


class SemVazamentoTest(unittest.TestCase):
    CENARIOS = {
        "sucesso conforme": lambda: ExecutorFalso(stdout=resposta()),
        "chave rejeitada": lambda: ExecutorFalso(255, stderr=com_vazamento_no_stderr(STDERR_AUTH)),
        "host inalcançável": lambda: ExecutorFalso(255, stderr=com_vazamento_no_stderr(STDERR_TIMEOUT)),
        "host desconhecido": lambda: ExecutorFalso(255, stderr=com_vazamento_no_stderr(STDERR_HOST_DESCONHECIDO)),
        "host alterado": lambda: ExecutorFalso(255, stderr=com_vazamento_no_stderr(HOST_ALTERADO)),
        "outra falha": lambda: ExecutorFalso(9, stderr=com_vazamento_no_stderr(b"boom")),
        "resposta truncada": lambda: ExecutorFalso(stdout=b'{"formato": 1,', stderr=CONTEUDO_CHAVE.encode()),
        "exceção com conteúdo": lambda: ExecutorFalso(levanta=RuntimeError(CONTEUDO_CHAVE)),
    }

    def executar_e_coletar_textos(self, amb, executor, *extras):
        j, m = amb.dir / "saida.json", amb.dir / "saida.md"
        codigo, out, err = amb.rodar(
            amb.args("--saida-json", str(j), "--saida-markdown", str(m), *extras), executor)
        arquivos = {p.name: p.read_text(encoding="utf-8") for p in (j, m) if p.exists()}
        return codigo, out, err, arquivos

    def test_conteudo_da_chave_nunca_aparece_em_lugar_nenhum(self):  # 2.3 + 7.4
        for nome, fabrica in self.CENARIOS.items():
            with self.subTest(nome), Ambiente() as amb:
                codigo, out, err, arquivos = self.executar_e_coletar_textos(amb, fabrica())
                for onde, texto in (("stdout", out), ("stderr", err), *arquivos.items()):
                    self.assertNotIn(CONTEUDO_CHAVE, texto, f"{nome}: vazou em {onde}")
                    self.assertNotIn("PRIVATE KEY", texto, f"{nome}: vazou em {onde}")

    def test_sucesso_gera_os_arquivos_e_eles_entram_no_teste(self):  # 7.4
        with Ambiente() as amb:
            codigo, out, err, arquivos = self.executar_e_coletar_textos(amb, self.CENARIOS["sucesso conforme"]())
        self.assertEqual(codigo, 0)
        self.assertEqual(set(arquivos), {"saida.json", "saida.md"})
        self.assertTrue(all(arquivos.values()))

    def test_falhas_nao_geram_relatorio(self):
        with Ambiente() as amb:
            _, out, _, arquivos = self.executar_e_coletar_textos(amb, self.CENARIOS["chave rejeitada"]())
        self.assertEqual((out, arquivos), ("", {}))

    def test_caminho_da_chave_nunca_aparece_em_relatorios(self):  # 7.4 — o caminho só vale no stderr
        with Ambiente() as amb:
            for formato in ("markdown", "json"):
                codigo, out, err, arquivos = self.executar_e_coletar_textos(
                    amb, ExecutorFalso(stdout=resposta()), "--formato", formato)
                self.assertEqual(codigo, 0)
                for texto in (out, err, *arquivos.values()):
                    self.assertNotIn(amb.chave.caminho, texto)
                    self.assertNotIn(os.path.basename(amb.chave.caminho), texto)

    def test_caminho_pode_aparecer_no_stderr_quando_a_chave_nao_existe(self):
        with Ambiente() as amb:
            ausente = str(amb.dir / "sem_chave")
            codigo, out, err = amb.rodar(amb.args(chave=ausente), ExecutorFalso(stdout=resposta()))
        self.assertEqual(codigo, 2)
        self.assertEqual(out, "")
        self.assertIn(ausente, err)

    def test_mensagens_de_conexao_nao_citam_o_caminho_da_chave(self):
        for nome in ("chave rejeitada", "host inalcançável", "host desconhecido", "outra falha"):
            with self.subTest(nome), Ambiente() as amb:
                _, _, err, _ = self.executar_e_coletar_textos(amb, self.CENARIOS[nome]())
                self.assertNotIn(amb.chave.caminho, err)

    def test_a_ferramenta_nunca_abre_o_arquivo_da_chave(self):
        abrir_real = builtins.open
        with Ambiente() as amb:
            chave = os.path.normcase(os.path.abspath(amb.chave.caminho))

            def open_vigiado(arquivo, *a, **kw):
                if isinstance(arquivo, (str, os.PathLike)) and os.path.normcase(os.path.abspath(arquivo)) == chave:
                    raise AssertionError("a ferramenta tentou abrir o arquivo da chave privada")
                return abrir_real(arquivo, *a, **kw)

            leituras = []
            ler_bytes_real = pathlib.Path.read_bytes

            def read_bytes_vigiado(self):
                leituras.append(self)
                return ler_bytes_real(self)

            with mock.patch("builtins.open", open_vigiado), \
                    mock.patch.object(pathlib.Path, "read_text", side_effect=AssertionError("read_text")), \
                    mock.patch.object(pathlib.Path, "read_bytes", read_bytes_vigiado):
                amb.rodar(amb.args(), ExecutorFalso(stdout=resposta()))
            self.assertEqual(leituras, [ssh_transport.COLETOR_PATH])  # só o script coletor é lido

    def test_o_argv_carrega_o_caminho_e_nunca_o_conteudo(self):
        with Ambiente() as amb:
            ex = ExecutorFalso(stdout=resposta())
            amb.rodar(amb.args(), ex)
            argv, kwargs = ex.chamadas[0]
            self.assertIn(amb.chave.caminho, argv)
            self.assertNotIn(CONTEUDO_CHAVE, " ".join(argv))
            self.assertNotIn(CONTEUDO_CHAVE.encode(), kwargs["input"])


if __name__ == "__main__":
    unittest.main()
