"""Uso: python -m painel_cluster [--porta 8765]"""

import argparse
import logging

from .servidor import ENDERECO, PORTA_PADRAO, criar_servidor


def main():
    parser = argparse.ArgumentParser(
        prog="python -m painel_cluster",
        description="Painel local, somente leitura, do cluster do contexto corrente do "
                    "kubeconfig. Escuta apenas em 127.0.0.1.")
    parser.add_argument("--porta", type=int, default=PORTA_PADRAO,
                        help=f"porta local (padrão: {PORTA_PADRAO})")
    argumentos = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    servidor = criar_servidor(argumentos.porta)
    print(f"Painel (somente leitura) em http://{ENDERECO}:{servidor.server_port}/ "
          "- Ctrl+C para encerrar", flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
