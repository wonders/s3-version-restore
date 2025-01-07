# S3 Version Restore Tool

⚠️ **IMPORTANT: PROOF OF CONCEPT STATUS** ⚠️

This tool is currently in an early proof-of-concept stage and while initial testing has been promising, it has not been extensively tested in production environments. Users should exercise caution and thoroughly test in a safe environment before any critical use. Community feedback and testing reports are highly welcomed and appreciated.

## Overview

A Python script for restoring files from S3-compatible buckets that have versioning enabled, either by removing delete markers or by reverting to previous versions. It uses server-side operations to avoid downloading and reuploading files. This tool only works with buckets that have:

- Versioning enabled
- Previous versions still intact
- Either:
  - Files in a deleted state with previous versions available
  - Files with multiple versions where previous versions need to be restored

## Primary Use Case

This tool was developed in response to a need identified by Tom Lawrence ([Lawrence Systems](https://lawrencesystems.com)) to address scenarios where files become inaccessible but their versions are still intact. This can happen in two ways:

1. Files are marked as deleted but versions remain
2. Files are overwritten (accidentally or maliciously) but previous versions remain

A specific use case is recovering from TrueNAS cloud sync scenarios where credentials with limited permissions may have deleted or modified the most recent versions of files (whether through user error, malicious action, or otherwise), but didn't have permission to purge all versions.

This tool can either restore deleted files by removing delete markers or revert files to their previous versions, making them accessible again for TrueNAS cloud sync to restore to the NAS. It works with AWS S3, Backblaze B2, Storj, and likely other S3-compatible services.

## Features

- Two distinct restoration modes:
  - Remove delete markers to restore deleted files
  - Revert to previous versions by removing current versions
- Works with multiple S3-compatible services (AWS S3, B2, Storj, etc.)
- Supports restoring entire buckets or specific paths
- Dry-run mode to preview what would be restored
- Detailed file information including sizes and timestamps
- Path-specific restoration support

## Prerequisites

### Python Requirements

- Python 3.9 or higher
- boto3 (`pip install boto3`)

### Account Requirements

- S3-compatible account with API access
- Access credentials with appropriate permissions (varies by service):
  - List buckets (may be a separate permission)
  - List files and their versions
  - Delete objects or versions (for removing delete markers or current versions)
  - Read file metadata
- Note: Permission names and structures vary between services. For example, AWS S3 and Backblaze B2 use different permission models.

## Environment Setup

The script requires two environment variables:

```bash
export S3_ACCESS_KEY_ID='your_access_key_id'
export S3_SECRET_ACCESS_KEY='your_secret_access_key'
```

## Usage

```bash
python s3-version-restore.py BUCKET_NAME [options]
```

### Options

- `--list-buckets`: List all available buckets and exit
- `--restore-deleted`: Restore files by removing delete markers
- `--restore-previous-versions`: Revert to previous versions by removing current versions (destructive)
- `--endpoint-url URL`: S3-compatible endpoint URL (required for non-AWS services)
- `--path PREFIX`: Optional path prefix to restore (e.g., "folder/")
- `--execute`: Execute the restore operation. Without this flag, performs a dry run
- `-v, --verbose`: Show detailed information about files to be restored

### Examples

```bash
# List available buckets
python s3-version-restore.py --list-buckets --endpoint-url https://s3.us-west-004.backblazeb2.com

# Show deleted files that could be restored
python s3-version-restore.py my-bucket --restore-deleted

# Show files that could be reverted to previous versions
python s3-version-restore.py my-bucket --restore-previous-versions

# Restore all deleted files in a bucket
python s3-version-restore.py my-bucket --restore-deleted --execute

# DESTRUCTIVELY restore previous versions
python s3-version-restore.py my-bucket --restore-previous-versions --execute

# Show what would be restored from a specific folder
python s3-version-restore.py my-bucket --restore-deleted --path docs/reports/

# Show detailed information about files to be restored
python s3-version-restore.py my-bucket --restore-deleted -v

# Use with a specific S3-compatible endpoint
python s3-version-restore.py my-bucket --endpoint-url https://gateway.us1.storjshare.io --restore-deleted
```

## How It Works

The script operates in one of two modes:

### Delete Marker Removal Mode (`--restore-deleted`)

1. Connects to the S3-compatible service using your credentials
2. Verifies bucket versioning is enabled
3. Lists all versions of files in the specified bucket/path
4. Identifies files with delete markers
5. Removes delete markers to expose the previous version
6. Restores access to previously deleted files

### Version Reversion Mode (`--restore-previous-versions`)

1. Connects to the S3-compatible service using your credentials
2. Verifies bucket versioning is enabled
3. Lists all versions of files in the specified bucket/path
4. Identifies files with multiple versions
5. PERMANENTLY REMOVES the current version
6. Previous version becomes the current version
7. This operation CANNOT be undone

## Important Notes

- The bucket must have versioning enabled and supported
- Two distinct modes of operation:
  1. Delete Marker Removal: Removes delete markers to restore intentionally deleted files
  2. Version Reversion: Permanently removes current versions to restore previous versions
- Version Reversion mode permanently deletes current versions and cannot be undone
- Files that were intentionally deleted before malicious/accidental changes will be restored when using delete marker removal
- The path prefix uses prefix matching (e.g., 'docs/' matches both 'docs/file.txt' and 'docs/subfolder/file.txt')
- By default, runs in dry-run mode showing what would be restored
- Always shows total size and file count before executing restore
- Requires explicit confirmation before performing actual restore operations
- Cannot restore files where all versions have been permanently deleted
- Testing in a non-production environment is strongly recommended

## Service-Specific Notes

### AWS S3

- Endpoint URL: Not needed (default AWS endpoints will be used)
- Bucket names are used as-is
- Example:
  ```bash
  export S3_ACCESS_KEY_ID='AKIAXXXXXXXXXXXXXXXX'
  export S3_SECRET_ACCESS_KEY='XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
  python s3-version-restore.py my-bucket --restore-deleted
  ```

### Backblaze B2

- Endpoint URL format: https://s3.{region}.backblazeb2.com
  - Example: https://s3.us-west-000.backblazeb2.com
- Bucket names must be the full bucket name (not the bucket ID)
- Example:
  ```bash
  export S3_ACCESS_KEY_ID='000xxxxxxxxxxxxx0000000001'
  export S3_SECRET_ACCESS_KEY='K000xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
  python s3-version-restore.py my-bucket --endpoint-url https://s3.us-west-000.backblazeb2.com --restore-deleted
  ```

### Storj

- Endpoint URL: https://gateway.storjshare.io
- Bucket names are used as-is
- Example:
  ```bash
  export S3_ACCESS_KEY_ID='jw....................................'
  export S3_SECRET_ACCESS_KEY='jk............................................'
  python s3-version-restore.py my-bucket --endpoint-url https://gateway.storjshare.io --restore-deleted
  ```

## Contributing

Contributions are welcome! Please submit pull requests or report issues on GitHub.
