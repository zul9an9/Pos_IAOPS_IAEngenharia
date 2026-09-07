
# scripts: "script_validador_manifestos.md" para os resultados

# testes gerados: "EXPECTATIVAS.md"

Cinco fixtures mais o arquivo de expectativas, que é o oráculo — deixei fora dos YAML de propósito, senão o validador pode acertar lendo o comentário em vez de analisar o manifesto.

Os dois testes que separam um validador bom de um que só parece bom:

04 tem cinco violações e exit code 0. Recomendação avisa, não reprova. Implementação que soma tudo num contador único reprova aqui, e aí o time desliga a ferramenta no pipeline.

05 é a cascata: namespace fora do formato torna o ambiente indeterminável, e 2.3, 2.4 e 2.5 têm que cair em não-avaliado. Aprovar as três é exatamente o defeito que o passo 2 do prompt existe para evitar. No mesmo arquivo vão uma exceção válida e uma vencida na mesma anotação, e dois valores de alta entropia que não são segredo, para medir o falso positivo da 3.3.

Um ponto que vale você observar quando rodar: a 3.4 no fixture 05 tem automountServiceAccountToken: true. A condição "quando não fala com a API" não é decidível pelo YAML, então cada implementação vai resolver diferente — reprovar, avisar ou pular. É a regra mais ambígua do padrão e um bom termômetro de como o script gerado lida com o que não dá para saber.

# resultados:
