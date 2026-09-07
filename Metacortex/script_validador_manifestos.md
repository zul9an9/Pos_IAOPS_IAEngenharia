# Validador de Manifestos — Metacórtex

> **Papel:** engenheiro de plataforma / tooling de conformidade
> **Framework do prompt:** RISE (Role · Input · Steps · Expectation)
> **Entregável de biblioteca:** o prompt da seção 1. A seção 2 é a instância deste caso.

---

## 1. Prompt parametrizável

Este é o artefato que entra no playbook. Ele não resolve o Metacórtex especificamente:
recebe qualquer página de padrão por parâmetro e devolve o validador correspondente.

```text
### ROLE
Você é engenheiro de plataforma especializado em tooling de conformidade para Kubernetes.
Você escreve validadores que times usam em pipeline, e por isso é conservador em uma
direção específica: um validador que aprova o que não conseguiu checar é pior que um
validador que declara o limite. Você nunca implementa uma checagem que dependa de
informação ausente do artefato analisado.

### INPUT (parâmetros)
- PADRAO:          {{PADRAO}}           # a página de padrão, na íntegra, como está
- ESCOPO:          {{ESCOPO}}           # arquivo único | diretório
- RUNTIME:         {{RUNTIME}}          # linguagem, versão e dependências permitidas
- FORMATO_SAIDA:   {{FORMATO_SAIDA}}    # como o resultado é apresentado e o contrato de exit code
- EXCECOES:        {{EXCECOES}}         # mecanismo de exceção previsto no padrão, se houver
- PROVEDOR:        {{PROVEDOR}}         # provedor/modelo de destino (formatação da saída)

### STEPS

1. NORMALIZAÇÃO DO PADRÃO.
   PADRAO pode chegar com defeito de extração: palavras coladas, negação invertida,
   trechos truncados. Antes de qualquer código, releia PADRAO e produza uma lista de
   passagens ambíguas com a leitura que você adotou e por quê.
   Restrição rígida: quando o texto não permitir decidir a intenção da regra, registre a
   ambiguidade e NÃO implemente a checagem. Não invente regra para preencher lacuna.

2. EXTRAÇÃO. Monte uma tabela com uma linha por regra, contendo:
   - id e título, como aparecem em PADRAO;
   - severidade, usando a taxonomia declarada no próprio PADRAO;
   - decidibilidade: TOTAL, PARCIAL ou NULA — a partir apenas do artefato em ESCOPO;
   - quando PARCIAL: qual fração é checável e qual não é, separadamente;
   - quando NULA: qual informação externa seria necessária.

3. RECORTE. Declare explicitamente quais regras entram no validador e quais ficam de fora.
   Regra de decidibilidade NULA não vira função. Regra PARCIAL vira função que checa só
   a fração decidível, e o relatório precisa deixar visível que a checagem é parcial.
   Seções puramente conceituais ou de glossário não geram regra.

4. GERAÇÃO. Escreva o validador em RUNTIME, respeitando:
   - severidade governa o resultado: severidade que reprova produz falha, severidade que
     apenas orienta produz aviso e não altera o exit code;
   - três resultados por regra, nunca dois: aprovado, reprovado e não-avaliado. Regra que
     não pôde ser avaliada por ausência de informação no artefato é não-avaliado, jamais
     aprovado por omissão;
   - uma função por regra, nomeada pelo id da regra, com docstring citando o texto da regra;
   - o artefato pode conter múltiplos documentos; processe todos e reporte por documento,
     identificando kind, nome e namespace;
   - checagem que dependa de heurística deve ser marcada como heurística no relatório,
     com a natureza do erro esperado (falso positivo ou falso negativo) explicitada;
   - falha de parse é resultado do validador, não exceção não tratada.

5. EXCEÇÕES. Implemente EXCECOES como mecanismo de primeira classe. Se o padrão prevê
   exceção com validade, o validador verifica a validade e trata exceção vencida como
   violação. Se o padrão declara categoria sem exceção possível, o mecanismo não pode
   suprimir essa categoria.

6. TESTES. Entregue um conjunto mínimo de manifestos de fixture: um conforme, um violando
   cada categoria de severidade, e um exercitando o caminho de não-avaliado.

### EXPECTATION
Entregue, nesta ordem:
1. a lista de ambiguidades do passo 1;
2. a tabela de regras do passo 2;
3. o recorte do passo 3, como duas listas nomeadas: implementadas e não implementadas;
4. o código do validador, executável, sem dependência fora do declarado em RUNTIME;
5. as fixtures do passo 6;
6. as limitações conhecidas, em prosa curta: o que este validador não vê.

Não produza texto introdutório nem resumo final. Formate segundo PROVEDOR.
```

---

## 2. Prompt instanciado — Metacórtex

Os parâmetros abaixo já vão resolvidos. O bloco `PADRAO` recebe a página do wiki colada
na íntegra; a tabela pré-resolvida logo abaixo dele economiza uma rodada de normalização,
já que o texto disponível está corrompido em vários pontos.

```text
[ROLE e STEPS idênticos à seção 1]

### INPUT

PADRAO:
<<<
[colar aqui a página "Padrão de Manifestos do Metacórtex" na íntegra]
>>>

  Leituras já resolvidas para as passagens corrompidas — adote estas e não reinterprete:
  - 1.2 "Namespace sem formato <cliente>-<ambiente>" → leia "no formato".
    Ambientes válidos: dev, stg, prod.
  - 2.1 "limits de memória entre 1,5x e 2x o consumo apresentado em regime" → o
    consumo em regime não está no manifesto. Fração não decidível.
  - 2.3 "Em deve stg, uma réplica é aceitável" → leia "em dev e stg".
  - 3.4 a condição "quando não fala com a API" não é decidível a partir do YAML.
    Leitura adotada: exigir o campo declarado explicitamente, em qualquer valor.
  - Bloco 4 é glossário de onboarding. Não gera regra.

ESCOPO: diretório de manifestos. O validador recebe um caminho, varre .yaml e .yml
  recursivamente, e agrega o resultado. Escopo de diretório é o que torna a regra 2.5
  (PodDisruptionBudget) avaliável — num arquivo isolado ela seria não-avaliável.

RUNTIME: Python 3.11. Biblioteca padrão + PyYAML. Sem acesso a rede, sem cliente
  Kubernetes, sem chamada a kubectl. Análise estática do YAML apenas.

FORMATO_SAIDA: relatório em tabela no stdout, agrupado por arquivo, com id da regra,
  severidade, resultado e mensagem apontando o caminho do campo. Flag --json para saída
  estruturada consumível por pipeline. Exit code 0 quando não há reprovação, 1 quando há.
  Resultado não-avaliado nunca altera o exit code, mas aparece em bloco próprio no fim,
  contado — é ele que impede o relatório de mentir sobre cobertura.

EXCECOES: anotação metacortex.io/exception no objeto, valor no formato
  "<id-da-regra>:<AAAA-MM-DD>", múltiplas separadas por vírgula. A data é o prazo de
  validade exigido pela seção "Exceções" do padrão. Exceção vencida vale como ausente e
  a violação reaparece. Exceção não suprime regra de severidade "proibido": para essas,
  o validador reporta a violação e ainda sinaliza a tentativa de exceção indevida.

PROVEDOR: Claude Opus — código em bloco único por arquivo, comentário inline apenas onde
  a regra do padrão não é óbvia a partir do nome da função.
```

---

## 3. Curadoria

**Por que RISE e não B-A-B.** B-A-B pede um "antes" concreto — funciona quando existe um
artefato defeituoso para transformar. Aqui não há script anterior: o insumo é uma norma em
prosa, e o trabalho pesado é a travessia norma → código. Isso é sequência de passos, que é
o que o S do RISE carrega.

**A decisão que define o exercício.** O padrão tem 20 regras, mas não são 20 checagens.
Sem o passo 2 explícito, um modelo gera 20 funções e as que ele não consegue checar retornam
verde. O validador fica pior que inútil: vira uma aprovação com carimbo. Por isso o
não-avaliado é terceiro estado obrigatório, e não um `pass` silencioso.

**Regras com fração não decidível.** 2.1 (a razão 1,5x–2x depende de consumo em regime),
2.2 (se o endpoint da sonda existe de fato depende da aplicação — mas dá para alertar quando
liveness e readiness apontam para o mesmo path, que é a armadilha descrita no próprio texto),
2.6 (depende do tempo de drenagem da aplicação), 1.6 (barrar `app`/`main`/`container` é
checável; confirmar que o nome casa com o componente, não), 3.3 (heurística de padrão de URI
e entropia, com falso negativo garantido).

**O mecanismo de exceção não é enfeite.** A seção "Exceções" do padrão é normativa. Um
validador que a ignora quebra no primeiro PR com aprovação escrita da Segurança, e o
desfecho conhecido é alguém desligar o validador no pipeline. Implementá-lo é o que mantém
a ferramenta viva.

**Armadilha da 3.2.** `securityContext` existe em dois níveis, pod e contêiner, com campos
que só valem em um deles e herança parcial entre eles. Uma checagem ingênua olha só o
contêiner e reprova manifesto correto. O prompt não resolve isso sozinho — vale conferir
na primeira geração.

**O que este prompt não faz.** Não valida schema do Kubernetes, não resolve Helm ou
Kustomize antes de analisar, e não vê nada que dependa do estado do cluster. Manifesto que
passa no validador ainda pode não subir.
