# B2 Bulk Restore Tool

⚠️ **IMPORTANT: PROOF OF CONCEPT STATUS** ⚠️

This tool is currently in an early proof-of-concept stage and while initial testing has been promising, it has not been extensively tested in production environments. Users should exercise caution and thoroughly test in a safe environment before any critical use. Community feedback and testing reports are highly welcomed and appreciated.

## Primary Use Case

This tool was developed primarily to address scenarios where B2 bucket files become "hidden" (deleted) but their versions are still intact. A specific use case is recovering from TrueNAS cloud sync scenarios where credentials with limited permissions may have deleted the most recent versions of files (whether through user error, malicious action, or otherwise), but didn't have permission to purge all versions. This tool can restore the newest available version of each file, making them accessible again for TrueNAS cloud sync to restore to the NAS.

## Overview

A Python script for bulk restoration of deleted files from Backblaze B2 buckets that have versioning enabled. It uses server-side copy operations to avoid the need for downloading and reuploading files. This tool only works with buckets that have:

- Versioning enabled
- Previous versions still intact
- Files in a "hidden" rather than permanently deleted state

## Features

- Restores deleted files in B2 buckets using server-side operations
- Supports restoring entire buckets or specific paths
- Dry-run mode to preview what would be restored
- Detailed file information including sizes and timestamps
- Only attempts to restore currently deleted files
- No local downloading/uploading of files

## Prerequisites

### Python Requirements

- Python 3.9 or higher
- b2sdk v2 (`pip install b2sdk`)

### B2 Account Requirements

- B2 Account with API access
- Application Key with at least the following capabilities:
  - `listBuckets`
  - `listFiles`
  - `readFiles`
  - `writeFiles`

You can create an application key in the B2 web interface under "App Keys". Make sure to save both the key ID and the application key itself.

## Environment Setup

The script requires two environment variables:

```bash
export B2_APPLICATION_KEY_ID='your_application_key_id'
export B2_APPLICATION_KEY='your_application_key'
```

## Usage

```bash
python b2-bulk-restore.py BUCKET_ID [options]
```

### Options

- `--path PREFIX`: Optional path prefix to restore (e.g., "folder/")
- `--execute`: Execute the restore operation. Without this flag, performs a dry run
- `-v, --verbose`: Show detailed information about files to be restored

### Examples

```bash
# Do a dry run showing what would be restored from a bucket
python b2-bulk-restore.py 4a5b6c7d8e9f

# Restore all files in a bucket
python b2-bulk-restore.py 4a5b6c7d8e9f --execute

# Show what would be restored from a specific folder
python b2-bulk-restore.py 4a5b6c7d8e9f --path docs/reports/

# Show detailed information about files to be restored
python b2-bulk-restore.py 4a5b6c7d8e9f -v

# Restore only files from a specific folder
python b2-bulk-restore.py 4a5b6c7d8e9f --path docs/reports/ --execute
```

## Finding Your Bucket ID

You can find your bucket ID in one of two ways:

1. In the B2 web interface under "Buckets"
2. Using the B2 command-line tool: `b2 list-buckets`

## How It Works

The script:

1. Connects to B2 using your application key
2. Lists all versions of files in the specified bucket/path
3. Identifies the most recent non-hidden version of each deleted file
4. Uses B2's server-side copy operation to restore files by creating new versions
5. Skips files that aren't currently deleted

## Important Notes

- The script requires the bucket ID, not the bucket name
- The path prefix uses prefix matching (e.g., 'docs/' matches both 'docs/file.txt' and 'docs/subfolder/file.txt')
- By default, runs in dry-run mode showing what would be restored
- Always shows total size and file count before executing restore
- Requires confirmation before performing actual restore operations
- Creates new versions of files rather than "undeleting" them
- Only works with buckets that have versioning enabled
- Cannot restore files where all versions have been permanently deleted
- Best suited for recovery from "hide" or "delete" operations where versions still exist
- While the script includes error handling, edge cases may still exist that haven't been discovered
- Testing in a non-production environment is strongly recommended

## Contributing

Contributions are welcome! Please submit pull requests or report issues on GitHub.
