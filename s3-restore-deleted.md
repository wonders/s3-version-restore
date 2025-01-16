# S3 Quick Undelete Tool

## Before You Begin

This tool has been tested with various file sizes and quantities, but like any software dealing with file operations, edge cases may exist. Always:

- Test in a non-production environment first
- Use the dry-run mode to preview changes
- Maintain separate backups of critical data
- Verify results after operation

## Overview

A Python script for restoring deleted files from S3-compatible buckets that have versioning enabled by removing delete markers. It uses server-side operations to avoid downloading and reuploading files. This tool requires buckets that have:

- Versioning enabled
- Previous versions still intact
- Files in a deleted state with previous versions available

## Features

- Restores deleted files by removing delete markers
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
  - Delete objects or versions (for removing delete markers)
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
python s3-restore-deleted.py BUCKET_NAME [options]
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
python s3-restore-deleted.py --list-buckets --endpoint-url https://s3.us-west-004.backblazeb2.com

# Show deleted files that could be restored
python s3-restore-deleted.py my-bucket

# Restore all deleted files in a bucket
python s3-restore-deleted.py my-bucket --execute

# Show what would be restored from a specific folder
python s3-restore-deleted.py my-bucket --path docs/reports/

# Show detailed information about files to be restored
python s3-restore-deleted.py my-bucket -v

# Use with a specific S3-compatible endpoint
python s3-restore-deleted.py my-bucket --endpoint-url https://gateway.us1.storjshare.io
```

## How It Works

1. Connects to the S3-compatible service using your credentials
2. Verifies bucket versioning is enabled
3. Lists all versions of files in the specified bucket/path
4. Identifies files with delete markers
5. Removes delete markers to expose the previous version
6. Restores access to previously deleted files

## Important Notes

- The bucket must have versioning enabled and supported
- Files that were intentionally deleted will be restored when using delete marker removal
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
  python s3-restore-deleted.py my-bucket
  ```

### Backblaze B2

- Endpoint URL format: https://s3.{region}.backblazeb2.com
  - Example: https://s3.us-west-000.backblazeb2.com
- Bucket names must be the full bucket name (not the bucket ID)
- Example:

  ```bash
  export S3_ACCESS_KEY_ID='000xxxxxxxxxxxxx0000000001'
  export S3_SECRET_ACCESS_KEY='K000xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
  python s3-restore-deleted.py my-bucket --endpoint-url https://s3.us-west-000.backblazeb2.com
  ```

### Storj

- Endpoint URL: https://gateway.storjshare.io
- Bucket names are used as-is
- Example:

  ```bash
  export S3_ACCESS_KEY_ID='jw....................................'
  export S3_SECRET_ACCESS_KEY='jk............................................'
  python s3-restore-deleted.py my-bucket --endpoint-url https://gateway.storjshare.io
  ```

## TODO

### Testing

- [ ] Validate minimum permission sets with each service
- [ ] Test behavior with network interruptions during large restores
- [ ] Verify memory usage and performance with 10,000+ file operations

Contributions to help test these scenarios are welcome!
