import argparse
import sys
import os
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

def initialize_s3(endpoint_url=None):
    """Initialize S3 client with credentials and optional endpoint"""
    access_key = os.environ.get('S3_ACCESS_KEY_ID')
    secret_key = os.environ.get('S3_SECRET_ACCESS_KEY')

    if not access_key or not secret_key:
        print("Error: Missing S3 credentials. Please set S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY environment variables.")
        sys.exit(1)

    try:
        session = boto3.session.Session()
        s3_client = session.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        s3_client.list_buckets()  # Test credentials
        return s3_client
    except ClientError as e:
        print(f"Authorization error: Invalid credentials or insufficient permissions")
        sys.exit(1)
    except Exception as e:
        print(f"Connection error: {e}")
        sys.exit(1)

def list_buckets(s3_client):
    """List all available buckets"""
    try:
        response = s3_client.list_buckets()
        print("\nAvailable buckets:")
        for bucket in response['Buckets']:
            print(f"  {bucket['Name']}")
        print()
    except Exception as e:
        print(f"Error listing buckets: {e}")
        sys.exit(1)

def check_versioning_status(s3_client, bucket_name):
    """Check if bucket versioning is enabled and supported"""
    try:
        response = s3_client.get_bucket_versioning(Bucket=bucket_name)
        status = response.get('Status', '').lower()

        if status == 'enabled':
            return True
        elif status == 'suspended':
            print("Warning: Bucket versioning is suspended. Only existing versions are available.")
            return True
        elif not status:
            print("Error: Bucket versioning is not enabled. Cannot restore versions.")
            return False
        else:
            print(f"Error: Unexpected versioning status: {status}")
            return False
    except ClientError as e:
        if e.response['Error']['Code'] == 'NotImplemented':
            print("Error: Versioning is not supported on this bucket.")
            return False
        raise

def format_size(size_in_bytes):
    """Format file size in bytes to human readable format"""
    if size_in_bytes >= 1024 * 1024 * 1024:  # GB range
        return f"{size_in_bytes / (1024 * 1024 * 1024):.2f} GB"
    elif size_in_bytes >= 1024 * 1024:  # MB range
        return f"{size_in_bytes / (1024 * 1024):.2f} MB"
    elif size_in_bytes >= 1024:  # KB range
        return f"{size_in_bytes / 1024:.2f} KB"
    else:  # Bytes
        return f"{size_in_bytes} B"

def format_timestamp(timestamp):
    """Convert timestamp to readable date"""
    return timestamp.strftime('%Y-%m-%d %H:%M:%S')

def get_restorable_files(s3_client, bucket_name, prefix=None, restore_previous=False):
    """Get files that can be restored based on the selected mode

    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the bucket
        prefix: Optional path prefix to filter files
        restore_previous: If True, look for files with multiple versions to restore previous version
                         If False, look for files with delete markers

    Returns:
        Dictionary of files that can be restored with their version information
    """
    restorable_files = {}
    params = {'Bucket': bucket_name}
    if prefix:
        params['Prefix'] = prefix

    try:
        paginator = s3_client.get_paginator('list_object_versions')

        for page in paginator.paginate(**params):
            if restore_previous:
                # Process regular versions for previous version restoration
                for version in page.get('Versions', []):
                    key = version['Key']
                    if version['IsLatest']:
                        # Start tracking this file if we find a latest version
                        restorable_files[key] = {
                            'current_version_id': version['VersionId'],
                            'current_size': version['Size'],
                            'current_modified': version['LastModified']
                        }
                    elif key in restorable_files and 'previous_version_id' not in restorable_files[key]:
                        # Add previous version info if we haven't found one yet
                        restorable_files[key].update({
                            'previous_version_id': version['VersionId'],
                            'previous_size': version['Size'],
                            'previous_modified': version['LastModified']
                        })
            else:
                # Process delete markers for undelete operation
                for marker in page.get('DeleteMarkers', []):
                    key = marker['Key']
                    if marker['IsLatest']:
                        restorable_files[key] = {
                            'delete_marker_id': marker['VersionId'],
                            'deleted_at': marker['LastModified']
                        }

                # Find the latest real version before the delete marker
                for version in page.get('Versions', []):
                    key = version['Key']
                    if key in restorable_files and not version['IsLatest']:
                        restorable_files[key].update({
                            'previous_version_id': version['VersionId'],
                            'size': version['Size'],
                            'last_modified': version['LastModified']
                        })

    except ClientError as e:
        if e.response['Error']['Code'] == 'NotImplemented':
            print("Error: This endpoint doesn't support versioning operations.")
            sys.exit(1)
        raise

    # Clean up entries that don't have all required information
    if restore_previous:
        return {k: v for k, v in restorable_files.items() if 'previous_version_id' in v}
    else:
        return {k: v for k, v in restorable_files.items() if 'previous_version_id' in v}

def restore_versions(s3_client, bucket_name, files_to_restore, restore_previous=False, dry_run=True, verbose=False):
    """Restore files by either removing delete markers or current versions

    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the bucket
        files_to_restore: Dictionary of files to restore with their version information
        restore_previous: If True, restore previous versions by removing current versions
                         If False, restore by removing delete markers
        dry_run: If True, only show what would be done
        verbose: If True, show detailed information about each file
    """
    restored = 0
    failed = 0

    for file_name, info in files_to_restore.items():
        if dry_run:
            if verbose:
                print(f"\nWould restore: {file_name}")
                if restore_previous:
                    print(f"  Current version:")
                    print(f"    Modified: {format_timestamp(info['current_modified'])}")
                    print(f"    Size: {format_size(info['current_size'])}")
                    print(f"  Previous version:")
                    print(f"    Modified: {format_timestamp(info['previous_modified'])}")
                    print(f"    Size: {format_size(info['previous_size'])}")
                else:
                    print(f"  Deleted at: {format_timestamp(info['deleted_at'])}")
                    print(f"  Original size: {format_size(info['size'])}")
                    print(f"  Last modified: {format_timestamp(info['last_modified'])}")
            continue

        try:
            print(f"Restoring: {file_name}")
            # Remove either the current version or delete marker
            version_id = info['current_version_id'] if restore_previous else info['delete_marker_id']
            s3_client.delete_object(
                Bucket=bucket_name,
                Key=file_name,
                VersionId=version_id
            )
            print(f"Successfully restored: {file_name}")
            restored += 1
        except Exception as e:
            print(f"Error restoring {file_name}: {e}")
            failed += 1
            continue

    if not dry_run:
        print(f"\nRestore summary:")
        print(f"Successfully restored: {restored} files")
        if failed > 0:
            print(f"Failed to restore: {failed} files")

def main():
    parser = argparse.ArgumentParser(
        description='S3 Version Recovery Tool - Requires selecting ONE recovery mode:\n'
                   '1. Remove delete markers to restore deleted files\n'
                   '2. Remove current versions to restore previous versions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Operation Modes:
    This tool requires explicitly choosing one of two operation modes:

    1. Delete Marker Removal (--restore-deleted):
       - Recovers files by removing delete markers
       - Exposes the most recent version before deletion
       - Note: Will restore ALL deleted files, including those
         intentionally deleted before any unwanted changes

    2. Version Reversion (--restore-previous-versions):
       - PERMANENTLY REMOVES current versions of files
       - Makes previous versions become the current versions
       - Cannot be undone - current versions are permanently deleted
       - Only use if current versions are confirmed unwanted
       - Consider backing up current versions first

Examples:
    # List available buckets
    %(prog)s --list-buckets --endpoint-url https://s3.us-west-004.backblazeb2.com

    # Show deleted files that could be restored
    %(prog)s my-bucket --restore-deleted

    # Show files that could be reverted to previous versions
    %(prog)s my-bucket --restore-previous-versions

    # Remove delete markers to restore files
    %(prog)s my-bucket --restore-deleted --execute

    # PERMANENTLY remove current versions to restore previous versions
    %(prog)s my-bucket --restore-previous-versions --execute

    # Use with path prefix (works with either mode)
    %(prog)s my-bucket --restore-deleted --path docs/reports/
    %(prog)s my-bucket --restore-previous-versions --path docs/reports/

    # Show detailed information (works with either mode)
    %(prog)s my-bucket --restore-deleted -v
    %(prog)s my-bucket --restore-previous-versions -v

Notes:
    - The script requires S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY environment variables
    - Bucket must have versioning enabled
    - Path is optional and uses prefix matching
    - Default is dry-run mode; use --execute to perform operations
    - Use -v or --verbose to see detailed information about each file
    - Version reversion PERMANENTLY DELETES current versions
''')

    # Create mutually exclusive group for mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        '--restore-deleted',
        action='store_true',
        help='Restore files by removing delete markers (recovers intentionally deleted files)'
    )
    mode_group.add_argument(
        '--restore-previous-versions',
        action='store_true',
        help='Revert to previous versions by PERMANENTLY REMOVING current versions (cannot be undone)'
    )
    mode_group.add_argument(
        '--list-buckets',
        action='store_true',
        help='List all available buckets and exit'
    )

    parser.add_argument(
        'bucket_name',
        nargs='?',
        help='Name of the S3 bucket to restore files from'
    )

    parser.add_argument(
        '--endpoint-url',
        help='S3-compatible endpoint URL (e.g., for B2, Storj, etc.)'
    )

    parser.add_argument(
        '--path',
        help='Optional path prefix to restore (e.g., "folder/")',
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

    # Validate required arguments
    if not args.list_buckets and not args.bucket_name:
        parser.error("Bucket name is required unless using --list-buckets")

    print("Initializing S3 client...")
    s3_client = initialize_s3(args.endpoint_url)

    if args.list_buckets:
        list_buckets(s3_client)
        return

    try:
        s3_client.head_bucket(Bucket=args.bucket_name)
        print(f"Connected to bucket: {args.bucket_name}")
    except ClientError as e:
        print(f"Error accessing bucket: {e}")
        sys.exit(1)

    if not check_versioning_status(s3_client, args.bucket_name):
        sys.exit(1)

    if args.path:
        print(f"Using path prefix: {args.path}")

    if args.restore_deleted:
        print("\nMODE: Restoring deleted files by removing delete markers")
        print("Note: This will restore ALL deleted files, including those deleted intentionally")
    else:
        print("\nMODE: Version Reversion - Will PERMANENTLY remove current versions")
        print("WARNING: This operation CANNOT be undone!")
        print("Current versions will be PERMANENTLY DELETED")

    print("\nFinding restorable files...")
    files = get_restorable_files(
        s3_client,
        args.bucket_name,
        args.path,
        restore_previous=args.restore_previous_versions
    )

    if not files:
        mode_str = "deleted files" if args.restore_deleted else "files with previous versions"
        print(f"No {mode_str} found in bucket" + (f" at path: {args.path}" if args.path else "."))
        return

    print(f"\nFound {len(files)} files to process")

    if args.restore_previous_versions:
        total_current_size = sum(info['current_size'] for info in files.values())
        total_previous_size = sum(info['previous_size'] for info in files.values())
        print(f"Total size of current versions to be DELETED: {format_size(total_current_size)}")
        print(f"Total size of previous versions to restore: {format_size(total_previous_size)}")
    else:
        total_size = sum(info['size'] for info in files.values())
        print(f"Total size of files to restore: {format_size(total_size)}")

    if args.execute:
        if args.restore_previous_versions:
            print("\n" + "!"*80)
            print("WARNING: DESTRUCTIVE OPERATION - VERSION REVERSION")
            print("This will PERMANENTLY DELETE the current version of all listed files!")
            print("Previous versions will become the current versions.")
            print("This operation CANNOT be undone!")
            print("Make sure you have backed up current versions if needed.")
            print("!"*80 + "\n")
            confirm = input("Type 'PERMANENTLY DELETE VERSIONS' to proceed: ")
            if confirm != "PERMANENTLY DELETE VERSIONS":
                print("Operation aborted.")
                return
        else:
            print("\nThis will remove delete markers to restore the most recent version of each file.")
            print("Note: This includes files that may have been intentionally deleted.")
            confirm = input("Continue with restoration? (yes/no): ")
            if confirm.lower() != 'yes':
                print("Operation aborted.")
                return

    restore_versions(
        s3_client,
        args.bucket_name,
        files,
        restore_previous=args.restore_previous_versions,
        dry_run=not args.execute,
        verbose=args.verbose
    )

if __name__ == '__main__':
    main()