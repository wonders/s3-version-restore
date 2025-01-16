# S3 Version Recovery Reference

## The Scenario

When files become inaccessible (whether through compromised credentials, accidental deletion, or backup system issues), proper object lock configuration can prevent permanent data loss by preserving previous versions. However, tools like TrueNAS Cloud Sync can't directly access these previous versions, creating a recovery challenge.

This guide provides approaches to recover access to versioned files in S3-compatible storage by restoring from a point in time or restoring visibility to deleted files.

## Community Origins

This guide evolved from a need identified by Tom Lawrence ([Lawrence Systems](https://lawrencesystems.com)) to address S3 version recovery scenarios. Thanks to user jkv on the [Lawrence Systems Forums](https://forums.lawrencesystems.com/t/bulk-point-in-time-restore-from-versioned-b2-or-s3-or-s3-compatible-object-storage/23721) for highlighting the rclone approach.

## Recovery Options

### 1. Quick Undelete with s3-restore-deleted

Best for scenarios where:

- Files were only deleted (not overwritten)
- You want to restore access without downloading
- You need to make files visible to TrueNAS Cloud Sync again

This repository includes a Python script that performs server-side operations to remove delete markers, restoring access to the previous versions of your files.

This works with both encrypted and unencrypted files since it only restores visibility at the storage level.

See [s3-restore-deleted.md](s3-restore-deleted.md) to learn how to use it.

---

### 2. Point-in-Time Recovery with rclone

Best for scenarios where:

- Files have been overwritten or deleted
- You need to recover the entire bucket or specific paths
- You want to download files to your local system for verification

For detailed instructions on setting up rclone with your S3-compatible service, see the [rclone S3 documentation](https://rclone.org/s3/). The quickest way to get started is:

```bash
rclone config
```

While rclone provides specific commands for services like B2 and Storj, we use the generic S3 commands here as they work across all S3-compatible services when configured with the appropriate endpoint URLs (see service-specific examples in the [s3-restore-deleted](s3-restore-deleted.md) documentation).

```bash
# List files as they existed at a specific time
rclone ls remote:bucket --s3-version-at "2024-11-01 21:10:00"

# Copy files as they existed at a specific time
rclone copy remote:bucket/path local/path --s3-version-at "2024-11-01 21:10:00" --progress
```

---

### 3. Encrypted File Recovery with rclone

Best for scenarios where:

- Files were encrypted by TrueNAS Cloud Sync
- You need to recover and decrypt files
- You have access to the original encryption credentials

If you used `rclone config` as mentioned in option #2 above, you can either:

- Run `rclone config` again to set up a new encrypted remote interactively
- Manually add an encrypted section to your existing configuration file

For manual configuration, first encode your credentials:

```bash
# Encode your encryption key
echo "your-encryption-key" | rclone obscure -

# Encode your salt
echo "your-encryption-salt" | rclone obscure -
```

Then add this section to your rclone configuration (typically `~/.config/rclone/rclone.conf`):

```ini
[encrypted]
type = crypt
remote = remote:bucket-name/
filename_encryption = standard
password = encoded-encryption-key
password2 = encoded-encryption-salt
```

#### Recovery Commands

```bash
# List encrypted files
rclone ls encrypted:/path

# Recover files to local storage (automatically decrypted)
rclone copy encrypted:/path local/path --progress

# Point-in-time recovery of encrypted files
rclone copy encrypted:/path local/path --s3-version-at "2024-11-01 21:10:00" --progress
```

## Contributing

Contributions are welcome! Please submit pull requests or report issues on GitHub.
