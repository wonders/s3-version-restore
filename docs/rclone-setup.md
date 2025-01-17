# Rclone Setup Guide

This guide focuses on configuring rclone with S3-compatible storage services. While both Backblaze B2 and Storj have their own rclone interfaces, using the S3 interface provides:
- Consistent commands across services
- Better compatibility with TrueNAS Cloud Sync
- Potential compatibility with other S3-compatible services

## Configuration Methods

You can configure rclone either by:
1. Using the interactive `rclone config` command
2. Directly editing the rclone config file

Both methods achieve the same result. We'll cover both approaches for each configuration type.

## Basic S3 Configuration

### Method 1: Manual Configuration

Create or edit `~/.config/rclone/rclone.conf`:

```ini
# For Backblaze B2
[b2-backup]
type = s3
provider = B2
access_key_id = your-key-id
secret_access_key = your-application-key
endpoint = s3.us-west-000.backblazeb2.com
# Replace region in endpoint URL with your bucket's region

# For Storj
[storj-backup]
type = s3
provider = Other
access_key_id = your-key-id
secret_access_key = your-secret-key
endpoint = gateway.storjshare.io
```

### Method 2: Interactive Setup

Run `rclone config` and follow these steps:

```
n) New remote
name> backup-name
Storage> s3
provider> Other
env_auth> false (or 1)
access_key_id> your-key-id
secret_access_key> your-application-key
region> leave blank for B2/Storj
endpoint> your-endpoint
location_constraint> leave blank
acl> private
```

Important settings:
- Always use `type = s3``
- For B2 and Storj, use `provider = Other`
- Don't set region unless specifically required (like using actual AWS S3)
- Use complete endpoint URLs for providers like B2 and Storj

## Adding Encryption

Encryption can be added to any existing remote. The encrypted remote becomes a new configuration that points to your base remote.

Note: If you're recovering files from an existing TrueNAS Cloud Sync setup, you can get the encryption password and salt from your TrueNAS configuration if you haven't stored them separately.
### Method 1: Manual Encrypted Configuration

Add to your `rclone.conf`:

```ini
# Define encrypted remote on top of existing remote
[b2-backup-crypt]
type = crypt
remote = b2-backup:bucket-name
filename_encryption = standard
directory_name_encryption = true
password = your-password-hash
password2 = your-salt-hash
```

To generate password hashes:
```bash
# Get password hash
rclone obscure "your-master-password"

# Get salt hash 
rclone obscure "your-salt-value"
```

### Method 2: Interactive Encryption Setup

Run `rclone config` and follow these steps:

```
n) New remote
name> backup-name-crypt
Storage> crypt
remote> existing-remote:bucket-name
filename_encryption> standard
directory_name_encryption> true
Option password> Yes, type in my own password
password> your-master-password
Option password2> Yes, type in my own password
password2> your-salt-value
```

## Important Notes

### Configuration Security
- Keep your rclone.conf file secure (600 permissions)
- Store encryption passwords safely
- Consider using environment variables for keys
- Backup your configuration and credentials

### B2-Specific Notes
- Use the correct regional endpoint
- Don't set region parameter
- Use your restricted API keys

### Storj-Specific Notes
- Endpoint can be gateway.storjshare.io
- Use S3 credential type
- Don't set region parameter

## Testing Your Configuration

Test basic remote:
```bash
# List buckets
rclone lsd remote:

# List files
rclone ls remote:bucket-name

# List versions
rclone ls remote:bucket-name --s3-versions
```

Test encrypted remote:
```bash
# Should show decrypted names
rclone ls remote-crypt:

# Verify encryption
rclone cryptdecode remote-crypt: "encrypted-filename"
```

## Using with TrueNAS

TrueNAS Cloud Sync typically needs:

- S3 credentials and endpoint
- Encryption password and salt if using encryption
- Bucket name and path

When setting up Cloud Sync:

1. Choose S3 compatible storage
2. Use the same endpoint format shown above
3. If encrypting, use same password and salt values
4. Test connection before saving

Note: The rclone commands shown above assume encryption of filenames is enabled.