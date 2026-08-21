bash
#!/usr/bin/env bash
# =============================================================================
# ledger-backup.sh
# Daily PostgreSQL backup for ledger_prod → S3 (hvt-ledger-backups)
#
# Format choice: pg_dump -Fc (custom/binary) is faster and produces a smaller
# dump than plain SQL, but requires pg_restore to read. For disaster-recovery
# purposes where a DBA will run the restore, this is the right trade-off.
# The file is then passed through gzip for an additional ~10-15 % size saving.
# =============================================================================
set -euo pipefail

# ─── CONFIGURATION ───────────────────────────────────────────────────────────
DB_HOST="ledger-db.internal.hvt.io"
DB_PORT="5432"
DB_NAME="ledger_prod"
DB_USER="backup_user"
# PGPASSWORD must be set externally (AWS Secrets Manager via IAM role)

BACKUP_DIR="/var/backups/ledger"
LOG_FILE="/var/log/ledger-backup.log"
S3_BUCKET="hvt-ledger-backups"
S3_REGION="us-east-1"
RETENTION_DAYS=30

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DUMP_FILE="${BACKUP_DIR}/ledger_prod_${TIMESTAMP}.dump"
GZ_FILE="${DUMP_FILE}.gz"
S3_KEY="ledger_prod_${TIMESTAMP}.dump.gz"

# ─── HELPERS ─────────────────────────────────────────────────────────────────
log() {
    local level="$1"; shift
    printf '%s [%-7s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${level}" "$*" \
        | tee -a "${LOG_FILE}"
}

die() {
    log "ERROR" "$*"
    exit 1
}

# ─── PRE-FLIGHT CHECKS ───────────────────────────────────────────────────────
log "INFO" "=== Ledger backup started ==="

[[ -n "${PGPASSWORD:-}" ]] \
    || die "PGPASSWORD is not set. Aborting to avoid unauthenticated connection."

for cmd in pg_dump gzip aws; do
    command -v "${cmd}" &>/dev/null \
        || die "Required command not found: ${cmd}"
done

mkdir -p "${BACKUP_DIR}" \
    || die "Cannot create backup directory: ${BACKUP_DIR}"

# Disk-space guard: require at least 20 GB free (in 1 K-blocks)
REQUIRED_KB=$(( 20 * 1024 * 1024 ))
AVAILABLE_KB=$(df -k "${BACKUP_DIR}" | awk 'NR==2 {print $4}')
(( AVAILABLE_KB >= REQUIRED_KB )) \
    || die "Insufficient disk space: ${AVAILABLE_KB} KB available, ${REQUIRED_KB} KB required."

log "INFO" "Pre-flight checks passed."

# ─── DUMP ────────────────────────────────────────────────────────────────────
log "INFO" "Starting pg_dump → ${DUMP_FILE}"
pg_dump \
    --host="${DB_HOST}" \
    --port="${DB_PORT}" \
    --username="${DB_USER}" \
    --format=custom \
    --no-password \
    --file="${DUMP_FILE}" \
    "${DB_NAME}" \
    || die "pg_dump failed for ${DB_NAME}."
log "INFO" "pg_dump completed. Size: $(du -sh "${DUMP_FILE}" | cut -f1)"

# ─── COMPRESS ────────────────────────────────────────────────────────────────
log "INFO" "Compressing → ${GZ_FILE}"
gzip -9 "${DUMP_FILE}" \
    || die "gzip compression failed for ${DUMP_FILE}."
log "INFO" "Compression done. Size: $(du -sh "${GZ_FILE}" | cut -f1)"

# ─── S3 UPLOAD ───────────────────────────────────────────────────────────────
log "INFO" "Uploading to s3://${S3_BUCKET}/${S3_KEY}"
aws s3 cp "${GZ_FILE}" "s3://${S3_BUCKET}/${S3_KEY}" \
    --region "${S3_REGION}" \
    --storage-class STANDARD_IA \
    || die "aws s3 cp failed for s3://${S3_BUCKET}/${S3_KEY}."
log "INFO" "Upload successful."

# Clean up local compressed file after confirmed upload
rm -f "${GZ_FILE}"
log "INFO" "Local temp file removed: ${GZ_FILE}"

# ─── RETENTION ───────────────────────────────────────────────────────────────
log "INFO" "Enforcing ${RETENTION_DAYS}-day retention on s3://${S3_BUCKET}"

CUTOFF_DATE="$(date -u -d "-${RETENTION_DAYS} days" +%Y-%m-%dT%H:%M:%SZ)"

# List all objects, filter those older than the cutoff, delete them
aws s3api list-objects-v2 \
    --bucket "${S3_BUCKET}" \
    --region "${S3_REGION}" \
    --query "Contents[?LastModified<='${CUTOFF_DATE}'].Key" \
    --output text \
| tr '\t' '\n' \
| grep -v '^$' \
| while IFS= read -r old_key; do
    log "INFO" "Deleting expired object: ${old_key}"
    aws s3api delete-object \
        --bucket "${S3_BUCKET}" \
        --key "${old_key}" \
        --region "${S3_REGION}" \
        || log "WARN" "Failed to delete ${old_key} – will retry on next run."
done

log "INFO" "Retention cleanup complete."

# ─── DONE ────────────────────────────────────────────────────────────────────
log "INFO" "=== Ledger backup finished successfully ==="
exit 0
