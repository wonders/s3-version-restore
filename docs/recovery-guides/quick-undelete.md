# Quick Undelete Guide

## Before You Begin

This tool has been tested with various file sizes and quantities, but like any software dealing with file operations, edge cases may exist. Always:

- Test in a non-production environment first
- Use the dry-run mode to preview changes
- Maintain separate backups of critical data
- Verify results after operation

## Overview

This guide covers using the s3-restore-deleted.py script to restore access to deleted files directly in your S3-compatible storage. This method is best when:
- Files were only deleted (not overwritten)
- You want to restore access without downloading
- You need to make files visible to TrueNAS Cloud Sync again

## How It Works

The script:
1. Identifies files with delete markers
2. Finds their most recent previous versions
3. Removes the delete markers to restore access
4. Performs all operations server-side (no downloading)

## Prerequisites

### Python Requirements
- Python 3.9 or higher
- boto3 (`pip install boto3`)

### Account Requirements
- S3-compatible account with API access
- Credentials with permissions to:
  - List buckets
  - List files and versions
  - Delete objects (for removing delete markers)
  - Read file metadata

## Environment Setup

Set required environment variables:
```bash
export S3_ACCESS_KEY_ID='your_access_key_id'
export S3_SECRET_ACCESS_KEY='your_secret_access_key'
```

## Basic Usage

```bash
# List available buckets
python s3-restore-deleted.py --list-buckets --endpoint-url https://s3.us-west-004.backblazeb2.com

# Show deleted files that could be restored
python s3-restore-deleted.py my-bucket

# Show files to restore from specific path
python s3-restore-deleted.py my-bucket --path docs/reports/

# Show detailed information
python s3-restore-deleted.py my-bucket -v

# Execute restoration after verifying
python s3-restore-deleted.py my-bucket --execute
```

## Important Notes

### Before Restoration
- Script runs in dry-run mode by default
- Always review what will be restored first
- Verify bucket versioning is enabled
- Check you have sufficient permissions

### During Restoration
- Operations are performed server-side
- No files are downloaded or uploaded
- Progress is shown for each operation
- Can be interrupted safely

### After Restoration
- Files become visible in the bucket
- Previous versions remain intact
- TrueNAS Cloud Sync can see files again
- Original delete markers become versions

## Service-Specific Notes

### Backblaze B2
- Endpoint format: https://s3.{region}.backblazeb2.com
- Example: https://s3.us-west-000.backblazeb2.com
- Use full bucket name (not bucket ID)

### Storj
- Endpoint: https://gateway.storjshare.io
- Bucket names used as-is

## Common Issues

### Authorization Errors
- Verify credentials are set correctly
- Check API key permissions
- Ensure bucket access is allowed

### No Files Found
- Verify files were only deleted (not overwritten)
- Check if versioning was enabled when deleted
- Verify correct path prefix if specified

### Operation Failures
- Check delete marker removal permissions
- Verify versioning is still enabled
- Ensure previous versions exist

## Monitoring Progress

The script provides feedback about:
- Number of files found
- Total size to be restored
- Operation progress
- Success/failure counts

## When to Use Other Methods

Consider [Recovery with rclone](rclone-recovery.md) instead when:
- Files were overwritten (not just deleted)
- You need a specific past version
- You want to recover to a point in time
- You need to download files locally

## TODO

### Testing
- [ ] Validate minimum permission sets with each service
- [ ] Test behavior with network interruptions during large restores
- [ ] Verify memory usage and performance with 10,000+ file operations

Contributions to help test these scenarios are welcome!