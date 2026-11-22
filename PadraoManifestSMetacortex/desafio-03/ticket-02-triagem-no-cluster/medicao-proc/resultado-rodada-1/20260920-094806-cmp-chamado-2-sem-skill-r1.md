# cmp-chamado-2-sem-skill-r1

**Prompt:** Chamado do cliente orion: a loja do fake-shop em orion-stg parou depois de uma publicação do Loom; a tag foi anunciada e o deploy aplicado, mas o pod nunca trocou. Faz a triagem e me diz a causa.

**Lab:** lab-sem-skills

**Skills:** nenhuma

**Ferramentas:** 14 chamadas

**Tentativas de escrita:** nenhuma

---

Para confirmar a causa exata (tag inexistente vs. outro erro de pull), preciso checar o registry publicamente. Posso rodar `curl` para consultar as tags do Docker Hub do `fabricioveronez/fake-shop`?
