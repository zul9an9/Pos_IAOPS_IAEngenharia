A Hill Valley Tech é uma empresa fictícia que serve de palco para este desafio.
Tem cinco sistemas em produção, cada um com seu papel bem definido.

-  O Chronos é o API gateway e a plataforma core, ponto de entrada de todo tráfego da empresa.
-  Por trás dele, o Ledger é um data warehouse em PostgreSQL que guarda histórico de transações e eventos,
-  enquanto o Reactor toca o processamento assíncrono por filas de mensagens.
-  Em paralelo a tudo isso, o Beacon mantém a observabilidade do ambiente inteiro, métricas, logs e alertas, e
é por ele que o plantão enxerga o que está acontecendo.
-  Fora do core principal, o Lift é um produto em beta que o time vem amadurecendo à parte.

Quero utilizar o framework RTF

[ROLE]
Você é um Engenheiro de Confiabilidade de Sites (SRE) sênior com profunda
expertise em administração de PostgreSQL, scripting Bash e operações AWS.
Você escreve scripts shell de nível produção seguindo práticas de
programação defensiva: tratamento rigoroso de erros, logging estruturado
e exit codes limpos.

[TASK]
Escreva um script Bash de backup para um banco de dados PostgreSQL com
os seguintes requisitos exatos:

Conexão
- Host: ledger-db.internal.hvt.io  |  Porta: 5432
- Banco: ledger_prod                |  Usuário: backup_user
- Senha: lida da variável de ambiente PGPASSWORD
  (injetada pelo AWS Secrets Manager via IAM role da instância –
  NÃO coloque credenciais hard-coded)

Etapas do backup (nesta ordem)
1. Exportar o banco com pg_dump (formato custom ou plain, à sua
   escolha – justifique brevemente em um comentário dentro do script).
2. Compactar a saída com gzip. Diretório de trabalho com ~80 GB
   livres: /var/backups/ledger. Tamanho esperado compactado: ~12 GB.
3. Subir o arquivo .sql.gz resultante para o bucket S3
   hvt-ledger-backups (região AWS us-east-1) usando aws s3 cp.
4. Aplicar política de retenção de 30 dias no bucket, removendo
   objetos mais antigos via AWS CLI.
5. Registrar uma entrada de log estruturada (timestamp + etapa +
   resultado) em /var/log/ledger-backup.log após cada etapa relevante.
6. Sair com exit code 0 em caso de sucesso total; sair com código
   não-zero (e mensagem de log clara) em qualquer falha. Não engula
   erros silenciosamente.

Ambiente
- SO: Ubuntu 22.04 LTS
- Ferramentas disponíveis: bash, pg_dump, gzip, aws CLI v2

[FORMAT]
Retorne um único script Bash autocontido (shebang #!/usr/bin/env bash).
Requisitos para o output:
- Ativar strict mode (set -euo pipefail) no topo.
- Usar uma função auxiliar log() para que todas as linhas de log
  sejam uniformes.
- Organizar o script em seções claramente rotuladas com comentários:
  CONFIGURAÇÃO, AUXILIARES, VERIFICAÇÕES PRÉ-VOO, DUMP, COMPRESSÃO,
  UPLOAD S3, RETENÇÃO, CONCLUÍDO.
- Após o script, adicionar um bloco curto de "Notas de Implantação"
  (texto simples, não código) cobrindo: entrada de crontab para
  execução diária às 02:00 UTC, permissões IAM necessárias para a
  role da instância e recomendação de rotação de logs.
