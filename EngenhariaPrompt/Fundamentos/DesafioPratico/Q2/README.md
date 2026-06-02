
CRONTAB (daily at 02:00 UTC – add to root or the backup service account):
  0 2 * * * /usr/local/bin/ledger-backup.sh >> /var/log/ledger-backup.log 2>&1

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
