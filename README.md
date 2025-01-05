# S3 Version Restore Tool

⚠️ **IMPORTANT: PROOF OF CONCEPT STATUS** ⚠️

This tool is currently in an early proof-of-concept stage and while initial testing has been promising, it has not been extensively tested in production environments. Users should exercise caution and thoroughly test in a safe environment before any critical use. Community feedback and testing reports are highly welcomed and appreciated.

## Overview

A Python script for bulk restoration of deleted files from S3-compatible buckets that have versioning enabled. It uses server-side copy operations to avoid the need for downloading and reuploading files. This tool only works with buckets that have:

- Versioning enabled
- Previous versions still intact
- Files in a deleted state with previous versions available

## Primary Use Case

This tool was developed in response to a need identified by Tom Lawrence ([Lawrence Systems](https://lawrencesystems.com)) to address scenarios where files become "hidden" (deleted) but their versions are still intact, which could prevent them from being restored easily in some applications.

A specific use case is recovering from TrueNAS cloud sync scenarios where credentials with limited permissions may have deleted the most recent versions of files (whether through user error, malicious action, or otherwise), but didn't have permission to purge all versions.

This tool can restore the newest available version of each file, making them accessible again for TrueNAS cloud sync to restore to the NAS. It works with AWS S3, Backblaze B2, Storj, and likely other S3-compatible services.

## Features

- Restores deleted files in S3-compatible buckets using server-side operations
- Works with multiple S3-compatible services (AWS S3, B2, Storj, etc.)
- Supports restoring entire buckets or specific paths
- Dry-run mode to preview what would be restored
- Detailed file information including sizes and timestamps
- Only attempts to restore currently deleted files

## Prerequisites

### Python Requirements

- Python 3.9 or higher
- boto3 (`pip install boto3`)

### Account Requirements

- S3-compatible account with API access
- Access credentials with appropriate permissions (varies by service):

  - List buckets (may be a separate permission)
  - List files and their versions
  - Read file contents
  - Write/create new files

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
- `--endpoint-url URL`: S3-compatible endpoint URL (required for non-AWS services)
- `--path PREFIX`: Optional path prefix to restore (e.g., "folder/")
- `--execute`: Execute the restore operation. Without this flag, performs a dry run
- `-v, --verbose`: Show detailed information about files to be restored

### Examples

```bash
# List available buckets
python s3-version-restore.py --list-buckets --endpoint-url https://s3.us-west-004.backblazeb2.com

# Do a dry run showing what would be restored from a bucket
python s3-version-restore.py my-bucket

# Restore all files in a bucket
python s3-version-restore.py my-bucket --execute

# Show what would be restored from a specific folder
python s3-version-restore.py my-bucket --path docs/reports/

# Show detailed information about files to be restored
python s3-version-restore.py my-bucket -v

# Restore only files from a specific folder
python s3-version-restore.py my-bucket --path docs/reports/ --execute

# Use with a specific S3-compatible endpoint
python s3-version-restore.py my-bucket --endpoint-url https://gateway.us1.storjshare.io
```

## How It Works

The script:

1. Connects to the S3-compatible service using your credentials
2. Verifies bucket versioning is enabled
3. Lists all versions of files in the specified bucket/path
4. Identifies the most recent non-deleted version of each deleted file
5. Uses server-side copy operations to restore files by creating new versions
6. Skips files that aren't currently deleted

## Important Notes

- The bucket must have versioning enabled and supported
- The path prefix uses prefix matching (e.g., 'docs/' matches both 'docs/file.txt' and 'docs/subfolder/file.txt')
- By default, runs in dry-run mode showing what would be restored
- Always shows total size and file count before executing restore
- Requires confirmation before performing actual restore operations
- Creates new versions of files rather than "undeleting" them
- Cannot restore files where all versions have been permanently deleted
- Best suited for recovery from delete operations where versions still exist
- While the script includes error handling, edge cases may still exist that haven't been discovered
- Testing in a non-production environment is strongly recommended

## Service-Specific Notes

### AWS S3

- Endpoint URL: Not needed (default AWS endpoints will be used)
- Bucket names are used as-is
- Example:
  ```bash
  export S3_ACCESS_KEY_ID='AKIAXXXXXXXXXXXXXXXX'
  export S3_SECRET_ACCESS_KEY='XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
  python s3-version-restore.py my-bucket-name
  ```

### Backblaze B2

- Endpoint URL format: https://s3.{region}.backblazeb2.com
  - Example: https://s3.us-west-000.backblazeb2.com
- Bucket names must be the full bucket name (not the bucket ID)
- Example:
  ```bash
  export S3_ACCESS_KEY_ID='000xxxxxxxxxxxxx0000000001'
  export S3_SECRET_ACCESS_KEY='K000xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
  python s3-version-restore.py my-bucket --endpoint-url https://s3.us-west-000.backblazeb2.com
  ```

### Storj

- Endpoint URL: https://gateway.storjshare.io
- Bucket names are used as-is
- Example:
  ```bash
  export S3_ACCESS_KEY_ID='jw....................................'
  export S3_SECRET_ACCESS_KEY='jk............................................'
  python s3-version-restore.py my-bucket --endpoint-url https://gateway.storjshare.io
  ```

## Contributing

Contributions are welcome! Please submit pull requests or report issues on GitHub.
