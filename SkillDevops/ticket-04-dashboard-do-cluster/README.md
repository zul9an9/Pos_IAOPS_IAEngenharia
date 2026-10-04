# Painel do cluster

Painel local e **somente leitura** do cluster Kubernetes do contexto corrente do
seu kubeconfig. Serve para encurtar os primeiros dez minutos de um chamado. Numa
única página, mostra:

- namespaces;
- pods, com fase, contêineres prontos, reinícios e motivo quando em falha;
- deployments, com prontas/desejadas;
- services, com o resumo de endpoints lido dos EndpointSlices;
- eventos recentes do namespace selecionado.

Fora de escopo nesta versão: logs, métricas de consumo, histórico, troca de
contexto/multicluster e qualquer escrita no cluster.

## Como executar

Requer Python 3.12 ou superior. Foi validado com 3.14.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Linux/macOS: .venv/bin/python
.venv/Scripts/python -m painel_cluster                     # http://127.0.0.1:8765/
.venv/Scripts/python -m painel_cluster --porta 9000        # outra porta
```

O painel usa **somente o contexto corrente** (`current-context`) do kubeconfig
indicado por `KUBECONFIG` ou, na falta dele, de `~/.kube/config`. O nome do
contexto e o endereço do servidor aparecem no topo da página. Para olhar outro
cluster, troque o contexto fora do painel (`kubectl config use-context`) e
clique em **Atualizar**.

## Como a tela se comporta

- **Coleta sob demanda.** O painel só consulta o cluster quando você abre a
  página, clica em **Atualizar** ou troca o namespace. Não há atualização
  automática. O horário da coleta aparece no topo.
- **A busca por nome** filtra a coleta já exibida, no navegador, sem nova
  consulta e sem mudar o horário.
- **Campo ausente não é erro.** Deployment sem `readyReplicas` aparece como
  `0/N`. Service cujos EndpointSlices não trazem endereços aparece como
  `sem endpoint`. Service com endereços mostra quantos existem e quantos estão
  prontos, por exemplo `2 endereços, 0 prontos`.
- **Eventos:** cada evento é uma linha, com contagem, primeira e última
  ocorrência. A API retém eventos por tempo limitado (padrão: 1 hora).
- **Sem juízo de saúde.** O painel mostra o que a API afirma (fase, razões,
  condições) e não rotula nada como "saudável".
- **Falhas têm mensagem própria, sem stack trace:** kubeconfig inexistente,
  ilegível ou malformado; kubeconfig sem contexto corrente; cluster que não
  responde; credencial recusada ou expirada; permissão negada para um tipo de
  recurso (só aquele bloco mostra `sem permissão`); namespace vazio. O detalhe
  técnico vai apenas para o log do processo, no terminal.
- **Credencial restrita a um namespace.** Se a credencial não puder listar
  namespaces, o seletor avisa e aceita o nome digitado, já preenchido com o
  `namespace` do contexto quando houver.

## Garantia de somente leitura

A garantia não depende de promessa. Ela está em três camadas verificáveis:

1. **Camada única de acesso.** Só `painel_cluster/acesso.py` importa o cliente
   `kubernetes`, e ele expõe apenas funções `list_*`.
2. **Teste que falha com escrita.** `tests/test_somente_leitura.py` varre todo o
   código e falha, com arquivo e linha, ao encontrar qualquer um destes itens:
   - chamadas `create_*`, `patch_*`, `replace_*`, `delete_*` ou `connect_*`;
   - `watch.Watch` ou o argumento `watch=True`;
   - `kubectl` executado como subprocesso;
   - chamada direta de API com POST/PUT/PATCH/DELETE;
   - import do cliente `kubernetes` fora da camada de acesso.
3. **RBAC de exemplo.** `deploy/rbac/clusterrole-somente-leitura.yaml` concede
   só `get`/`list`/`watch`, sem curingas. `watch` está ali por ser do conjunto
   canônico de leitura; o código não o usa. Rodando o painel com uma credencial
   ligada a esse papel, o próprio apiserver nega qualquer escrita. Para gerar
   essa credencial, veja [`deploy/lab/README.md`](deploy/lab/README.md).

   As camadas 1 e 2 valem para qualquer credencial. A camada 3 só vale se o
   painel rodar com a credencial ligada ao papel de exemplo, e não com o seu
   kubeconfig pessoal, geralmente administrativo.

Além disso:

- o servidor escuta **somente em `127.0.0.1`**, sem opção para mudar o
  endereço;
- aceita **somente GET** e responde 405 a qualquer outro método;
- escapa todo texto vindo da API antes de montar o HTML;
- envia `Content-Security-Policy` que só permite o próprio script de busca;
- lê o kubeconfig sem nunca gravar nele;
- mostra o aviso de somente leitura em todas as telas.

## Testes

```bash
.venv/Scripts/python -m pytest
```

Os testes usam fixtures capturadas do cluster de laboratório em
`tests/fixtures/`. Para recapturar (usa só `kubectl get` e remove valores de
`env` e anotações `last-applied-configuration`):

```bash
bash tests/fixtures/capturar.sh
```

## Mapa da entrega (Desafio 03, Ticket 04)

| O enunciado pede | Onde está |
|---|---|
| Documentos de spec e artefatos do OpenSpec | `openspec/` (change `add-cluster-dashboard`: `proposal.md`, `design.md`, `specs/`, `tasks.md`; depois do archive, `openspec/changes/archive/` e `openspec/specs/cluster-dashboard/`) |
| Código | `painel_cluster/` e `tests/` |
| Evidência de execução, incluindo cenários adversos | `validacao/registro-laboratorio.md` e `validacao/pytest-2026-09-27.txt` |
| Manifests dos workloads gerados pela skill do Ticket 01 | `manifests-lab/` |
| Registro do comportamento das duas skills | [`REGISTRO-SKILLS.md`](REGISTRO-SKILLS.md) |
| Curadoria e justificativa das decisões abertas | [`CURADORIA.md`](CURADORIA.md) |
