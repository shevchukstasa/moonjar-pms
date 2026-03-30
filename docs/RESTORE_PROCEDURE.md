# Moonjar PMS -- Database Restore Procedure

## Overview

Moonjar PMS creates daily backups via `api/scheduler.py`:
- **Format:** pg_dump custom format (`--format=custom`)
- **Encryption:** AES-256-GCM (if `BACKUP_ENCRYPTION_KEY` is set)
- **Storage:** S3 bucket (path: `moonjar-backups/YYYY-MM-DD/moonjar_YYYY-MM-DD_HHMMSS.dump[.enc]`)
- **Retention:** Configurable via data retention policy

---

## Prerequisites

- **AWS CLI** (`aws s3 cp`) -- configured with access to the backup bucket
- **PostgreSQL client** (`pg_restore`, version matching the server)
- **Python 3.10+** with `cryptography` package (only if backups are encrypted)
- Access to the following environment variables:
  - `S3_BACKUP_BUCKET` -- S3 bucket name
  - `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`
  - `AWS_DEFAULT_REGION` (default: `ap-southeast-1`)
  - `BACKUP_ENCRYPTION_KEY` (if encrypted)
  - `DATABASE_URL` of the target database

---

## Step 1: Download from S3

List available backups:

```bash
aws s3 ls s3://$S3_BACKUP_BUCKET/moonjar-backups/ --recursive | sort -k1,2
```

Download the desired backup:

```bash
# Pick the timestamp you need
BACKUP_DATE="2026-03-30"
BACKUP_FILE="moonjar_2026-03-30_030000.dump.enc"

aws s3 cp \
  "s3://$S3_BACKUP_BUCKET/moonjar-backups/$BACKUP_DATE/$BACKUP_FILE" \
  /tmp/restore/$BACKUP_FILE
```

If the file ends with `.dump` (no `.enc`), skip Step 2.

---

## Step 2: Decrypt (if encrypted)

Encrypted backups use AES-256-GCM. The file format is:

```
[12-byte nonce][ciphertext with 16-byte auth tag appended]
```

The encryption key is derived from `BACKUP_ENCRYPTION_KEY` via SHA-256.

### Python decryption script

```python
#!/usr/bin/env python3
"""Decrypt a Moonjar PMS backup file."""

import hashlib
import sys
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ENCRYPTION_KEY = "YOUR_BACKUP_ENCRYPTION_KEY_HERE"  # from env

def decrypt_backup(encrypted_path: str, output_path: str):
    # Derive 256-bit key (same as scheduler.py)
    derived_key = hashlib.sha256(ENCRYPTION_KEY.encode()).digest()
    aesgcm = AESGCM(derived_key)

    with open(encrypted_path, "rb") as f:
        data = f.read()

    # First 12 bytes = nonce, rest = ciphertext + auth tag
    nonce = data[:12]
    ciphertext = data[12:]

    plaintext = aesgcm.decrypt(nonce, ciphertext, None)

    with open(output_path, "wb") as f:
        f.write(plaintext)

    print(f"Decrypted: {output_path} ({len(plaintext)} bytes)")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python decrypt_backup.py <encrypted.dump.enc> <output.dump>")
        sys.exit(1)
    decrypt_backup(sys.argv[1], sys.argv[2])
```

Run:

```bash
pip install cryptography
python decrypt_backup.py /tmp/restore/moonjar_2026-03-30_030000.dump.enc /tmp/restore/moonjar.dump
```

---

## Step 3: Restore with pg_restore

**WARNING:** This will overwrite the target database. Double-check the `DATABASE_URL`.

### Option A: Restore to existing database (drop + recreate objects)

```bash
pg_restore \
  --host=$PGHOST \
  --port=$PGPORT \
  --username=$PGUSER \
  --dbname=$PGDATABASE \
  --no-owner \
  --no-privileges \
  --clean \
  --if-exists \
  --single-transaction \
  /tmp/restore/moonjar.dump
```

### Option B: Restore to a fresh database

```bash
# Create empty database first
createdb -h $PGHOST -p $PGPORT -U $PGUSER moonjar_restored

pg_restore \
  --host=$PGHOST \
  --port=$PGPORT \
  --username=$PGUSER \
  --dbname=moonjar_restored \
  --no-owner \
  --no-privileges \
  /tmp/restore/moonjar.dump
```

### Railway-specific notes

On Railway, connect via the internal network URL (not public proxy):

```bash
# Parse DATABASE_URL from Railway
export PGPASSWORD="..."
pg_restore \
  -h containers-us-west-XXX.railway.app \
  -p 5432 \
  -U postgres \
  -d railway \
  --no-owner --no-privileges --clean --if-exists \
  /tmp/restore/moonjar.dump
```

---

## Step 4: Verify

After restore, run these checks:

```bash
# 1. Health check
curl -s https://moonjar-pms-production.up.railway.app/api/health
# Expected: {"status": "ok", ...}

# 2. Check key table row counts (requires admin JWT)
curl -s -H "Authorization: Bearer $TOKEN" \
  https://moonjar-pms-production.up.railway.app/api/health/seed-status

# 3. Verify a recent order exists
curl -s -H "Authorization: Bearer $TOKEN" \
  https://moonjar-pms-production.up.railway.app/api/orders?limit=1
# Expected: 401 (if no token) or 200 with data

# 4. Check no migration drift
# The app runs _ensure_schema() on startup, which adds missing columns.
# Restart the Railway service after restore to trigger this.
```

---

## Emergency Contacts

| Role | Contact | When |
|------|---------|------|
| DevOps / Owner | Telegram: @sheffclaude_bot | First responder for any restore |
| Railway Support | railway.app/help | Platform issues |
| AWS Support | aws.amazon.com/support | S3 access issues |

---

## Checklist

- [ ] Identified the correct backup timestamp
- [ ] Downloaded from S3
- [ ] Decrypted (if `.enc`)
- [ ] Verified dump file integrity (`pg_restore --list` to inspect TOC)
- [ ] Restored to target database
- [ ] Restarted application service
- [ ] Verified health endpoint
- [ ] Verified key data is present
- [ ] Notified team of restore completion
