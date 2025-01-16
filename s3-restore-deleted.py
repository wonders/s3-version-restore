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

def get_restorable_files(s3_client, bucket_name, prefix=None):
    """Get files that can be restored by removing delete markers

    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the bucket
        prefix: Optional path prefix to filter files

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
            # Process delete markers
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

    # Return only files that have both delete markers and previous versions
    return {k: v for k, v in restorable_files.items() if 'previous_version_id' in v}

def restore_versions(s3_client, bucket_name, files_to_restore, dry_run=True, verbose=False):
    """Restore files by removing delete markers

    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the bucket
        files_to_restore: Dictionary of files to restore with their version information
        dry_run: If True, only show what would be done
        verbose: If True, show detailed information about each file
    """
    restored = 0
    failed = 0

    for file_name, info in files_to_restore.items():
        if dry_run:
            if verbose:
                print(f"\nWould restore: {file_name}")
                print(f"  Deleted at: {format_timestamp(info['deleted_at'])}")
                print(f"  Original size: {format_size(info['size'])}")
                print(f"  Last modified: {format_timestamp(info['last_modified'])}")
            continue

        try:
            print(f"Restoring: {file_name}")
            s3_client.delete_object(
                Bucket=bucket_name,
                Key=file_name,
                VersionId=info['delete_marker_id']
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
        description='S3 Quick Undelete Tool - Restores access to deleted files by removing delete markers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    # List available buckets
    %(prog)s --list-buckets --endpoint-url https://s3.us-west-004.backblazeb2.com

    # Show deleted files that could be restored
    %(prog)s my-bucket

    # Restore files using path prefix
    %(prog)s my-bucket --path docs/reports/

    # Show detailed information
    %(prog)s my-bucket -v

    # Execute restoration
    %(prog)s my-bucket --execute

Notes:
    - The script requires S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY environment variables
    - Bucket must have versioning enabled
    - Path is optional and uses prefix matching
    - Default is dry-run mode; use --execute to perform operations
    - Use -v or --verbose to see detailed information about each file
''')

    parser.add_argument(
        'bucket_name',
        nargs='?',
        help='Name of the S3 bucket to restore files from'
    )

    parser.add_argument(
        '--list-buckets',
        action='store_true',
        help='List all available buckets and exit'
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

    print("\nFinding deleted files that can be restored...")
    files = get_restorable_files(
        s3_client,
        args.bucket_name,
        args.path
    )

    if not files:
        print(f"No deleted files found in bucket" + (f" at path: {args.path}" if args.path else "."))
        return

    print(f"\nFound {len(files)} deleted files that can be restored")
    total_size = sum(info['size'] for info in files.values())
    print(f"Total size of files to restore: {format_size(total_size)}")

    if args.execute:
        print("\nThis will remove delete markers to restore the most recent version of each file.")
        confirm = input("Continue with restoration? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Operation aborted.")
            return

    restore_versions(
        s3_client,
        args.bucket_name,
        files,
        dry_run=not args.execute,
        verbose=args.verbose
    )

if __name__ == '__main__':
    main()