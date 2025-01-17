# S3 Version Recovery Reference

A practical guide for protecting and recovering data when using S3-compatible storage (like Backblaze B2 or Storj) with TrueNAS Cloud Sync or other rclone-based backup tools.

## The Challenge

When using S3-compatible storage for backups:

- Compromised credentials could lead to data loss
- Syncing tools like TrueNAS Cloud Sync can't directly access previous versions
- Protection and recovery options vary by storage provider
- Object lock and versioning settings have important implications

## Available Recovery Methods

### 🔄 Quick Undelete

Best for: Restoring deleted files without downloading directly from storage

- Files were only deleted (not overwritten)
- You need to make files visible to TrueNAS Cloud Sync again
- This repository includes a Python script that performs server-side operations to remove delete markers, restoring access to previous versions of your files
- Works with both encrypted and unencrypted files since it only restores visibility at the storage level
- [Learn more about quick undelete](docs/recovery-guides/quick-undelete.md)

### ⏱️ Recovery with rclone

Best for: Recovering files, folders, or entire buckets from any point in version history

- Restores from any point in version history
- Should work with any S3-compatible service
- Supports both encrypted and unencrypted backups with proper config
- [Learn more about rclone recovery](docs/recovery-guides/rclone-recovery.md)

## Setting Up for Success

Before disaster strikes:

- [Understand bucket security options and trade-offs](docs/bucket-setup.md)
- [Configure rclone properly](docs/rclone-setup.md) (including encryption setup)

## Quick Start

For common scenarios:

```bash
# Quick undelete with provided script
python scripts/s3-restore-deleted.py my-bucket

# Point-in-time recovery with rclone
rclone copy remote:bucket/path local/path --s3-version-at "2024-01-17 21:10:00"
```

## Community Origins

This guide evolved from a need identified by Tom Lawrence ([Lawrence Systems](https://lawrencesystems.com)) to address S3 version recovery scenarios. Thanks to user jkv on the [Lawrence Systems Forums](https://forums.lawrencesystems.com/t/bulk-point-in-time-restore-from-versioned-b2-or-s3-or-s3-compatible-object-storage/23721) for highlighting the rclone approach.

## Contributing

Issues and pull requests are welcome! Please help us expand this knowledge base with:

- Additional recovery scenarios
- New protection strategies
- Service-specific notes
- Configuration examples
