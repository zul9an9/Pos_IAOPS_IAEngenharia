# Modelo utilizado: Sonnet 4.6
Claude Sonnet 4.6 (ou GPT-4o) — modelos de raciocínio intermediário-avançado
são ideais aqui: o prompt é técnico e estruturado, não exige raciocínio multi-etapa
profundo (descartando Opus/o1), mas precisa de coerência entre seções de código,
o que modelos menores entregam com menos consistência.

# Framework utilizado: RTF
Contexto técnico denso exige que o modelo saiba quem está respondendo (sênior, não júnior), o que entregar (script completo, não pseudocódigo) e como formatar (seções, helper, notas). Sem o Role, o modelo poderia omitir as guards; sem o Format explícito, entregaria um bloco monolítico difícil de auditar em produção.

# CRONTAB

CRONTAB (daily at 02:00 UTC – add to root or the backup service account):
  0 2 * * * /usr/local/bin/ledger-backup.sh >> /var/log/ledger-backup.log 2>&1

# IAM Permissions

IAM permissions required on the EC2 instance role:
  s3:PutObject    – s3://hvt-ledger-backups/*
  s3:GetObject    – s3://hvt-ledger-backups/*   (optional, for verification)
  s3:ListBucket   – s3://hvt-ledger-backups
  s3:DeleteObject – s3://hvt-ledger-backups/*
  secretsmanager:GetSecretValue – arn:aws:secretsmanager:us-east-1:*:secret:ledger/*

Log rotation (add to /etc/logrotate.d/ledger-backup):
  /var/log/ledger-backup.log {
      daily
      rotate 90
      compress
      missingok
      notifempty
  }
