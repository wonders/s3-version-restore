import argparse
import sys
import os
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

def initialize_s3(endpoint_url=None):
    """Initialize S3 client with credentials and optional endpoint"""
    try:
        session = boto3.session.Session()
        s3_client = session.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=os.environ.get('S3_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('S3_SECRET_ACCESS_KEY')
        )
        return s3_client
    except Exception as e:
        print(f"Authorization error: {e}")
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
            print("Error: Bucket versioning is not enabled. Cannot restore previous versions.")
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
    if size_in_bytes >= 1024 * 1024:  # MB range
        return f"{size_in_bytes / (1024 * 1024):.2f} MB"
    elif size_in_bytes >= 1024:  # KB range
        return f"{size_in_bytes / 1024:.2f} KB"
    else:  # Bytes
        return f"{size_in_bytes} B"

def format_timestamp(timestamp):
    """Convert timestamp to readable date"""
    return timestamp.strftime('%Y-%m-%d %H:%M:%S')

def get_file_versions(s3_client, bucket_name, prefix=None):
    """Get all file versions from the bucket"""
    versions = {}
    params = {'Bucket': bucket_name}
    if prefix:
        params['Prefix'] = prefix

    try:
        while True:
            response = s3_client.list_object_versions(**params)

            # Process regular versions
            for version in response.get('Versions', []):
                key = version['Key']
                if key not in versions:
                    versions[key] = []
                versions[key].append({
                    'version_id': version['VersionId'],
                    'file_name': key,
                    'timestamp': version['LastModified'],
                    'size': version['Size'],
                    'is_latest': version['IsLatest'],
                    'is_delete_marker': False
                })

            # Process delete markers
            for marker in response.get('DeleteMarkers', []):
                key = marker['Key']
                if key not in versions:
                    versions[key] = []
                versions[key].append({
                    'version_id': marker['VersionId'],
                    'file_name': key,
                    'timestamp': marker['LastModified'],
                    'size': 0,
                    'is_latest': marker['IsLatest'],
                    'is_delete_marker': True
                })

            if not response.get('IsTruncated'):
                break

            # Update pagination markers for next request
            params['KeyMarker'] = response.get('NextKeyMarker')
            params['VersionIdMarker'] = response.get('NextVersionIdMarker')

    except ClientError as e:
        if e.response['Error']['Code'] == 'NotImplemented':
            print("Error: This endpoint doesn't support versioning operations.")
            sys.exit(1)
        raise

    return versions

def get_latest_live_versions(versions):
    """Find the latest non-deleted version of each file, but only for deleted files"""
    latest_versions = {}
    total_size = 0

    for file_name, file_versions in versions.items():
        # Sort versions by timestamp, newest first
        sorted_versions = sorted(file_versions,
                               key=lambda x: x['timestamp'],
                               reverse=True)

        # Check if the most recent version is a delete marker
        if not sorted_versions or not sorted_versions[0]['is_delete_marker']:
            # File is currently live, skip it
            continue

        # Find the latest version before deletion
        for version in sorted_versions:
            if not version['is_delete_marker']:
                latest_versions[file_name] = version
                total_size += version['size']
                break

    return latest_versions, total_size

def restore_versions(s3_client, bucket_name, latest_versions, dry_run=True, verbose=False):
    """Restore the latest versions of files by copying them over the delete marker"""
    restored = 0
    failed = 0

    for file_name, version in latest_versions.items():
        if dry_run:
            if verbose:
                print(f"Would restore: {file_name}")
                print(f"  Last modified: {format_timestamp(version['timestamp'])}")
                print(f"  Size: {format_size(version['size'])}")
            continue

        try:
            print(f"Restoring: {file_name}")
            # Copy the object over itself to make it the latest version
            s3_client.copy_object(
                Bucket=bucket_name,
                Key=file_name,
                CopySource={
                    'Bucket': bucket_name,
                    'Key': file_name,
                    'VersionId': version['version_id']
                }
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
        description='Restore deleted files from an S3-compatible bucket',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    # List available buckets
    %(prog)s --list-buckets --endpoint-url https://s3.us-west-004.backblazeb2.com

    # Do a dry run showing what would be restored from a bucket
    %(prog)s my-bucket

    # Restore all files in a bucket
    %(prog)s my-bucket --execute

    # Use with a custom S3-compatible endpoint
    %(prog)s my-bucket --endpoint-url https://s3.us-west-004.backblazeb2.com

    # Show what would be restored from a specific folder
    %(prog)s my-bucket --path docs/reports/

    # Show detailed information about files to be restored
    %(prog)s my-bucket -v

    # Restore only files from a specific folder
    %(prog)s my-bucket --path docs/reports/ --execute

Notes:
    - The script requires S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY environment variables
    - Bucket must have versioning enabled
    - Path is optional and uses prefix matching
    - By default, runs in dry-run mode showing what would be restored
    - Use --execute to actually perform the restore
    - Use -v or --verbose to see detailed information about each file
''')

    parser.add_argument(
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

    # If no arguments provided or missing required args, show help and exit
    if len(sys.argv) == 1 or (not args.list_buckets and not args.bucket_name):
        parser.print_help()
        sys.exit(0)

    print("Initializing S3 client...")
    s3_client = initialize_s3(args.endpoint_url)

    if args.list_buckets:
        list_buckets(s3_client)
        return

    try:
        # Test bucket access
        s3_client.head_bucket(Bucket=args.bucket_name)
        print(f"Connected to bucket: {args.bucket_name}")
    except ClientError as e:
        print(f"Error accessing bucket: {e}")
        sys.exit(1)

    # Check versioning status
    if not check_versioning_status(s3_client, args.bucket_name):
        sys.exit(1)

    if args.path:
        print(f"Using path prefix: {args.path}")

    print("Getting file versions...")
    versions = get_file_versions(s3_client, args.bucket_name, args.path)

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

    restore_versions(s3_client, args.bucket_name, latest_versions,
                    dry_run=not args.execute, verbose=args.verbose)

if __name__ == '__main__':
    main()