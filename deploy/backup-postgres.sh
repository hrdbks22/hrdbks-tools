#!/usr/bin/env bash
set -euo pipefail

# Run on the database host. Store backups outside the repository and restrict
# access to the destination directory. For encryption, use the organization's
# approved secret-management/KMS process.
: "${DATABASE_URL:?Set DATABASE_URL}"
DEST="${BACKUP_DIR:-/var/backups/hrd-tools}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$DEST"
chmod 700 "$DEST"
umask 077
FILE="$DEST/hrd-tools-$STAMP.dump"

pg_dump --format=custom --no-owner --no-acl "$DATABASE_URL" > "$FILE"
pg_restore --list "$FILE" > /dev/null
find "$DEST" -type f -name 'hrd-tools-*.dump' -mtime +30 -delete

echo "Backup verified: $FILE"
