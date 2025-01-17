# Understanding Bucket Security and Protection Options

When setting up S3-compatible storage for backups, especially with tools like TrueNAS Cloud Sync or rclone, it's crucial to understand how different security features and limitations affect your data protection strategy. This guide explores practical approaches to protecting your backups against accidental or malicious deletion.

## Permission-Based Protection

Different S3-compatible services handle permissions in ways that significantly impact backup security. When versioning is enabled, both Backblaze B2 and Storj will create delete markers (soft deletes) when files are deleted, preserving the previous versions. However, the key difference lies in how granular permissions can be:

### Backblaze B2's Unique Advantage
- Can create API keys without the `deleteFiles` permission
- Sync tools like TrueNAS Cloud Sync work normally without this permission
- Files remain recoverable until cleaned up by lifecycle rules
- Even if backup credentials are compromised, data can't be permanently deleted
- Required permissions: `listBuckets`, `listFiles`, `readFiles`, `writeFiles`
- See below for how to create these keys using the API (not available in the GUI)

### Storj's Current Model
- Requires delete permission for sync tools to function
- When versioning is enabled, deletes still create delete markers
- However, compromised credentials could wipe versions since delete permission is required
- Required permissions: `Read`, `Write`, `List`, `Delete`
- Do not grant Object Lock management permissions to backup keys

## Object Lock Protection

Object Lock provides another layer of protection, available on both B2 and Storj (and other S3-compatible services that support the full spec).

### Understanding Object Lock Modes
- **Governance Mode**
  - Prevents deletion during lock period
  - Account owner/admin can override if needed
  - Good balance of protection and flexibility
  - Similar protection level to B2's permission model

- **Compliance Mode**
  - Cannot be overridden by anyone
  - Files cannot be deleted until lock expires
  - Could require account deletion to remove locked files
  - Generally too restrictive for most backup scenarios

## Understanding Lifecycle Rules

Lifecycle rules automatically manage version cleanup and are essential for cost control:
- Set rules to delete old versions after a specific period
- Must set longer periods than any Object Lock retention periods
- Consider cost vs. retention time trade-offs
- Different rules can apply to current vs. previous versions
- Good practice to always have lifecycle rules defined

### Important Object Lock Considerations

- Lock duration is tied to when files are created or modified in the storage bucket
- Not tied to when local backups or syncs occur
- For files that rarely change in the bucket:
  - Once initial lock period expires, files become vulnerable
  - New locks aren't applied unless files are modified
  - This affects file server syncs more than backup archives
- For backup archives or files that create new versions:
  - Each new file gets a new lock period
  - Provides continuous protection

## Practical Strategy Recommendations

### For File Server Syncs (e.g., TrueNAS SMB Shares)
1. **If using B2:**
   - Create API keys without `deleteFiles` permission
   - See below for how to create these keys using the API (not available in the GUI)
   - Enable versioning
   - Set appropriate lifecycle rules (must exceed any Object Lock periods)
   - Optionally add Governance mode Object Lock for additional protection

2. **If using Storj:**
   - Enable versioning
   - Set appropriate lifecycle rules (must exceed any Object Lock periods)
   - Use Governance mode Object Lock with extended duration
   - Consider scripting periodic Object Lock renewal for critical data

### For Backup Archives / Full Backups
Better suited for Object Lock protection because:
- Each backup creates new files in the bucket
- New lock periods apply to each backup
- Lock expiration aligns with backup retention needs
- Works well with both versioning and Object Lock

## Important Security Notes

### Credential Protection
- Keep admin credentials separate and secure for both services
- Admin access (via API or web interface) can:
  - Override Governance mode locks
  - Permanently delete versions
  - Modify bucket settings
- Rotate any master keys used for setup
- Store backup API keys securely

### Protection Verification
For both services:
1. Test file uploads work normally
2. Verify deleted files become previous versions
3. Confirm versioning shows delete markers
4. Test recovery procedures work
5. If using Object Lock, verify retention periods

## Monitoring and Maintenance

Regardless of protection strategy:

1. Monitor storage usage for unexpected changes
2. Regularly verify backup integrity
3. Test recovery procedures periodically
4. Keep offline copies of critical data
5. Document your security configuration

## Looking Ahead

Protection options may evolve as services add features:
- Storj may add more granular permissions
- New protection mechanisms may become available
- Check service documentation for current capabilities
- Consider reassessing protection strategy periodically

## Creating Restricted B2 API Keys

These steps create a restricted API key for backups using the B2 API. Note: Create a new master key for this process and discard it after key creation for better security.

1. **Generate Authorization Token**
```bash
curl https://api.backblazeb2.com/b2api/v2/b2_authorize_account \
  -u "<accountId>:<masterApplicationKey>"
```

2. **Create Restricted Key**
```bash
curl -X POST \
  -H "Authorization: <authorizationToken>" \
  -d '{
    "accountId": "<accountId>",
    "capabilities": [
      "listBuckets",
      "listFiles",
      "readFiles",
      "writeFiles"
    ],
    "keyName": "restricted-backup-key",
    "bucketId": "<bucketId>"
  }' \
  "<apiUrl>/b2api/v2/b2_create_key"
```

3. **Important Security Steps**
- Save the returned `applicationKeyId` and `applicationKey`
- Delete or securely store the master key used for creation
- Store credentials securely
- Set a reminder to rotate keys periodically