# ADR-0005 — Garantia de somente leitura em três camadas

| | |
|---|---|
| **Status** | Aceito |
| **Data da decisão** | 2026-09-27 (change `add-cluster-dashboard`) |
| **Origem** | `design.md` D5; `CURADORIA.md` §3.6. Proposta pelo agente durante o `/opsx:propose` e aceita na revisão da spec |
| **Relacionados** | [ADR-0002](ADR-0002-cliente-oficial-do-kubernetes.md), [ADR-0003](ADR-0003-atualizacao-sob-demanda.md) |

## Contexto

O invariante do projeto é **só leitura**, e ele precisa ser **verificável por máquina e visível no
projeto**, não só prometido. O painel pode rodar com o kubeconfig pessoal de quem está de plantão,
geralmente com privilégio amplo, que é o caso comum.

## Decisão

Três camadas **independentes**, mais proteções no servidor:

1. **Camada única de acesso.** Um módulo, e só ele, importa o cliente `kubernetes`, e expõe apenas as
   funções `list_*` (`list_namespace`, `list_pod_*`, `list_deployment_*`, `list_service_*`,
   `list_endpoint_slice_*` e `list_namespaced_event`).
2. **Teste estático.** O teste percorre com `ast` todos os `.py` do projeto, inclusive a camada de
   acesso, e falha com arquivo e linha ao encontrar:
   - atributo com prefixo `create_`, `patch_`, `replace_`, `delete_` ou `connect_` (`connect_*` cobre
     exec, attach, port-forward e proxy);
   - `kubernetes.stream`, `watch.Watch`, o argumento nomeado `watch=True` em qualquer chamada, ou
     `call_api`/`request` com método de escrita. O `watch=True` num `list_*` abre watch **sem** passar
     por `watch.Watch`, por isso é barrado à parte;
   - `subprocess` invocando `kubectl`;
   - import de `kubernetes` fora da camada de acesso.

   Um segundo teste confirma que a camada exporta **exatamente** a lista permitida. Um terceiro
   **planta** arquivos proibidos num diretório temporário e exige que o scanner os detecte, para
   provar que o teste não passa por vacuidade.
3. **RBAC de exemplo.** ClusterRole só com `get`/`list`/`watch` nos recursos lidos, sem curingas.
   Sob esse papel, um erro que escape das camadas 1 e 2 é negado pelo próprio apiserver. **O verbo
   `watch` entra no papel** por fazer parte do conjunto canônico de leitura (o mesmo do papel
   embutido `view`). Isso **não contradiz** o ADR-0003: o papel diz o que a credencial *poderia* ler,
   e o teste da camada 2 garante que o código *não* abre watch. A spec e o YAML trazem a mesma
   explicação.

Somam-se o servidor local, que aceita só GET e escuta só em `127.0.0.1`, e o aviso permanente na
tela, que tornam o invariante visível também para quem usa.

## Alternativas consideradas

| Alternativa | Por que foi rejeitada |
|---|---|
| **Só RBAC** | É defesa real, mas **não quebra o build**. A regressão chega silenciosa a quem roda com o próprio kubeconfig de plantão, geralmente com privilégio amplo |
| **Só revisão de código** | É processo humano, não é automatizável nem "visível no projeto". Um revisor cansado não pega um `patch_` perdido numa função auxiliar |

## Consequências

**Positivas**

- Uma regressão **quebra o build**, e as camadas 1 e 2 valem para qualquer credencial.
- O invariante é visível no projeto (testes), no YAML e na tela.

**Negativas e riscos aceitos**

- **Simplicidade:** são três artefatos para manter.
- **A camada 3 só protege se o painel rodar com a credencial ligada ao papel de exemplo**, e não com o
  kubeconfig pessoal. Mitigação: a documentação explica como gerar um contexto dedicado
  (`deploy/lab/README.md`).

## Verificação

- `tests/test_somente_leitura.py`: `test_projeto_nao_tem_escrita_nem_watch`,
  `test_varredura_detecta_arquivo_plantado` (seis arquivos plantados: escrita, `watch.Watch`,
  `watch=True`, `kubectl`, `call_api` POST e import) e `test_camada_de_acesso_exporta_so_listagens`.
- `tests/test_rbac.py`: `test_somente_get_list_watch_sem_curinga`,
  `test_exemplo_cobre_exatamente_os_recursos_do_painel`, `test_exemplo_explica_o_verbo_watch`.
- Laboratório: nenhuma escrita no cluster (as fixtures foram capturadas só com `kubectl get`).
