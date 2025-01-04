import argparse
from b2sdk.v2 import *
import sys
import os
from datetime import datetime

def initialize_b2():
    """Initialize B2 SDK with explicit credentials"""
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)

    key_id = os.environ.get('B2_APPLICATION_KEY_ID')
    key = os.environ.get('B2_APPLICATION_KEY')

    if not key_id or not key:
        print("Error: B2_APPLICATION_KEY_ID and B2_APPLICATION_KEY environment variables must be set")
        sys.exit(1)

    try:
        b2_api.authorize_account("production", key_id, key)
        return b2_api
    except Exception as e:
        print(f"Authorization error: {e}")
        sys.exit(1)

def format_size(size_in_bytes):
    """Format file size in bytes to human readable format"""
    if size_in_bytes >= 1024 * 1024:  # MB range
        return f"{size_in_bytes / (1024 * 1024):.2f} MB"
    elif size_in_bytes >= 1024:  # KB range
        return f"{size_in_bytes / 1024:.2f} KB"
    else:  # Bytes
        return f"{size_in_bytes} B"

def format_timestamp(timestamp):
    """Convert milliseconds timestamp to readable date"""
    dt = datetime.fromtimestamp(timestamp / 1000)  # Convert ms to seconds
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def get_file_versions(bucket, prefix=None):
    """Get all file versions from the bucket"""
    versions = {}

    try:
        for file_info, _ in bucket.ls(latest_only=False, recursive=True):
            file_name = file_info.file_name

            # Skip files not in the specified path if prefix is set
            if prefix and not file_name.startswith(prefix):
                continue

            if file_name not in versions:
                versions[file_name] = []
            versions[file_name].append({
                'file_id': file_info.id_,
                'file_name': file_name,
                'timestamp': file_info.upload_timestamp,
                'action': 'hide' if file_info.action == 'hide' else 'upload',
                'size': file_info.size
            })
    except Exception as e:
        print(f"Error listing files: {e}")
        print(f"Full error details: {str(e)}")
        sys.exit(1)

    return versions

def get_latest_live_versions(versions):
    """Find the latest non-hidden version of each file, but only for deleted files"""
    latest_versions = {}
    total_size = 0

    for file_name, file_versions in versions.items():
        # Sort versions by timestamp, newest first
        sorted_versions = sorted(file_versions,
                               key=lambda x: x['timestamp'],
                               reverse=True)

        # Check if the most recent version is a 'hide' action
        if sorted_versions and sorted_versions[0]['action'] != 'hide':
            # File is currently live, skip it
            continue

        # Find the latest version before hide/delete
        for version in sorted_versions:
            if version['action'] == 'upload':
                latest_versions[file_name] = version
                total_size += version['size']
                break

    return latest_versions, total_size

def unhide_versions(api, bucket, latest_versions, dry_run=True, verbose=False):
    """Unhide the latest versions of files"""
    restored = 0
    failed = 0

    for file_name, version in latest_versions.items():
        if dry_run and verbose:
            print(f"Would restore: {file_name}")
            print(f"  Size: {format_size(version['size'])}")
            print(f"  Last modified: {format_timestamp(version['timestamp'])}")
            continue
        elif dry_run:
            continue

        try:
            print(f"Restoring: {file_name}")
            # Use bucket.copy() with just the essential parameters
            bucket.copy(
                file_id=version['file_id'],
                new_file_name=file_name
            )
            print(f"Successfully restored: {file_name}")
            restored += 1
        except Exception as e:
            print(f"Error restoring {file_name}: {e}")
            print(f"Full error details: {str(e)}")
            failed += 1
            continue

    if not dry_run:
        print(f"\nRestore summary:")
        print(f"Successfully restored: {restored} files")
        if failed > 0:
            print(f"Failed to restore: {failed} files")

def main():
    parser = argparse.ArgumentParser(
        description='Restore deleted files from a Backblaze B2 bucket',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    # Do a dry run showing what would be restored from a bucket
    %(prog)s 4a5b6c7d8e9f

    # Restore all files in a bucket
    %(prog)s 4a5b6c7d8e9f --execute

    # Show what would be restored from a specific folder
    %(prog)s 4a5b6c7d8e9f --path docs/reports/

    # Show detailed information about files to be restored
    %(prog)s 4a5b6c7d8e9f -v

    # Restore only files from a specific folder
    %(prog)s 4a5b6c7d8e9f --path docs/reports/ --execute

Notes:
    - The script requires B2_APPLICATION_KEY_ID and B2_APPLICATION_KEY environment variables
    - Bucket must be specified by its ID (found in B2 web interface or using `b2 list-buckets`)
    - Path is optional and uses prefix matching (e.g., 'docs/' matches 'docs/file.txt' and 'docs/subfolder/file.txt')
    - By default, runs in dry-run mode showing what would be restored
    - Use --execute to actually perform the restore
    - Files are restored in place (no downloading/uploading required)
    - Use -v or --verbose to see detailed information about each file
''')

    parser.add_argument(
        'bucket_id',
        help='ID of the B2 bucket to restore files from'
    )

    parser.add_argument(
        '--path',
        help='Optional path prefix to restore (e.g., "folder/"). If not specified, looks at entire bucket',
        metavar='PREFIX'
    )

    parser.add_argument(
        '--execute',
        action='store_true',
        help='Execute the restore operation. Without this flag, performs a dry run'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed information about files to be restored'
    )

    args = parser.parse_args()

    # If no arguments provided, show help and exit
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    print("Initializing B2 SDK...")
    b2_api = initialize_b2()

    try:
        bucket = Bucket(b2_api, args.bucket_id)
        print(f"Connected to bucket: {bucket.id_}")
    except Exception as e:
        print(f"Error accessing bucket: {e}")
        sys.exit(1)

    if args.path:
        print(f"Using path prefix: {args.path}")

    print("Getting file versions...")
    versions = get_file_versions(bucket, args.path)

    if not versions:
        print("No files found in bucket" + (f" at path: {args.path}" if args.path else "."))
        return

    print("Finding latest live versions...")
    latest_versions, total_size = get_latest_live_versions(versions)

    print(f"\nFound {len(latest_versions)} files to restore")
    print(f"Total restore size: {format_size(total_size)}")

    if args.execute:
        confirm = input("\nAre you sure you want to restore these files? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Aborting restore.")
            return

    unhide_versions(b2_api, bucket, latest_versions, dry_run=not args.execute, verbose=args.verbose)

if __name__ == '__main__':
    main()