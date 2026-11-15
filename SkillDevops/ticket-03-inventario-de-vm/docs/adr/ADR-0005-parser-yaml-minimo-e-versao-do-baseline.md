# ADR-0005 — Parser YAML mínimo e específico, e validação da versão do baseline

| | |
|---|---|
| **Status** | Aceito |
| **Data da decisão** | 2026-09-20 (change `vm-inventory-drift`) |
| **Origem** | `design.md` D5; brainstorm D6 |
| **Relacionados** | [ADR-0001](ADR-0001-python-somente-biblioteca-padrao.md), [ADR-0006](ADR-0006-nao-verificado-veredito-de-primeira-classe.md), [ADR-0007](ADR-0007-contrato-de-dados-baseline-comparacao-e-saidas.md) |

## Contexto

A ferramenta lê o `baseline.yaml` do parque. É a **única peça de parsing com risco real de
correção**: um baseline malformado produziria vereditos errados no parque inteiro. O pior defeito
possível numa ferramenta de auditoria é o **falso conforme**. O YAML tem tipagem implícita que
produz exatamente esse tipo de surpresa (`no` vira `False`, e um desvio real viraria `conforme`).

## Decisão

1. Escrever um **parser YAML mínimo, específico para o layout oficial do baseline**. Ele suporta só
   o subconjunto de que o layout realmente precisa: mapeamentos em bloco, listas em bloco,
   escalares, comentários e *flow style de uma linha* (`[a, b]` e `{chave: valor, outra: [x, y]}`,
   com o mapeamento em linha só de escalares ou de listas de escalares).
2. **Recusar, com erro claro de "construção não suportada"**, tudo o mais: âncoras e aliases,
   streams multi-documento, tags complexas, mapeamento em linha aninhado, mapeamento dentro de
   lista, flow multilinha etc. O erro nomeia a construção e a linha. Nunca coagir nem interpretar
   mal em silêncio.
3. **Booleanos somente como os literais `true` e `false`.** As formas `yes`, `no`, `on`, `off`, `y`
   e `n` são rejeitadas como construção não suportada.
4. **Versão do baseline.** O campo `versao` é lido e **validado antes de interpretar qualquer
   regra**. O conjunto suportado hoje é `{1}` (inteiro). Versão **ausente**, não inteira ou fora do
   conjunto é falha de execução (exit 2), com mensagem que distingue **ausente**, **desconhecida**
   e **futura** (maior que a suportada: baseline escrito para uma ferramenta mais nova). Nunca há
   interpretação otimista de uma versão que a ferramenta não conhece.
5. "Recusar construções desconhecidas" é tratado como **requisito duro**, não como desejável.

## Alternativas consideradas

| Alternativa | Por que foi rejeitada |
|---|---|
| **PyYAML ou ruamel** | (1) Mantém absoluta a fronteira "só stdlib" do ADR-0001. (2) Um parser geral **consegue** parsear construções cuja interpretação esta ferramenta nunca validou (como a tipagem implícita acima), que é exatamente a leitura errada silenciosa que poderia virar um falso `conforme`. Um parser estreito que recusa o que não entende é mais seguro aqui do que um permissivo que entende tudo |
| **Usar PyYAML "se já estiver presente"** (variante do brainstorm, D6) | Superada pelo `design.md`, que adotou só o parser próprio. Exigir PyYAML contraria o ADR-0001, e usá-lo quando disponível reintroduziria o parser permissivo e o risco acima |

## Consequências

**Positivas**

- Nenhum baseline é interpretado de forma parcial e silenciosa. O autor do baseline recebe o nome da
  construção recusada e a linha.
- Uma versão desconhecida nunca é interpretada "na esperança".

**Negativas e riscos aceitos**

- **Um `baseline.yaml` legítimo, mas incomum, pode ser rejeitado**, porque a gramática suportada é
  menor que a de uma implementação real de YAML. Mitigação: falhar de forma ruidosa e específica
  (a construção e a linha). A orientação de autoria do baseline, que documentaria o subconjunto
  suportado, ficou fora do escopo desta mudança (PRD, questão Q3).
- É código próprio para manter: `baseline.py` é o maior módulo da ferramenta.

## Verificação

- `tests/test_baseline.py`: construções recusadas (por exemplo `test_ancora`) e validação da versão
  (ausente, `test_futura`). `tests/test_cli.py` confere que a mensagem "futura" chega ao operador.
- O baseline é validado **antes** de qualquer conexão (`cli.executar`), então um baseline inválido
  sai com exit 2 sem tocar no host.
