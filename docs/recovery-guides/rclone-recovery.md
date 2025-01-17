# Recovery with Rclone

This guide covers how to recover files using rclone from S3-compatible storage. These methods work with both encrypted and unencrypted backups - the only difference is which remote configuration you use. For remote setup, including encryption configuration, see [rclone-setup.md](../rclone-setup.md).

## Understanding Version Recovery

When recovering with rclone, you can:
- List all versions of files
- Recover files and directories as they existed at a point in time
- Filter recoveries by path

## Common Recovery Commands

### Listing Versions
```bash
# List all versions of all files
rclone ls remote:bucket --s3-versions

# List versions in a specific path
rclone ls remote:bucket/path --s3-versions

# Show sizes and timestamps
rclone lsl remote:bucket --s3-versions
```

### Point-in-Time Recovery
```bash
# Recover entire bucket as it existed at a specific time
rclone copy remote:bucket local/path --s3-version-at "2024-01-17 21:10:00"

# Recover specific folder
rclone copy remote:bucket/folder local/path --s3-version-at "2024-01-17 21:10:00"

# Preview what would be recovered
rclone copy remote:bucket local/path --s3-version-at "2024-01-17 21:10:00" --dry-run
```

## Recovery Scenarios

### Full Directory Recovery
Best when you need to restore everything to a previous state:
```bash
# First, list available files to find timestamp
rclone lsl remote:bucket/folder --s3-versions

# Then recover to that point
rclone copy remote:bucket/folder local/path --s3-version-at "2024-01-17 21:10:00"
```

### Partial Path Recovery
Best when you need to recover specific paths:
```bash
# List versions in specific path
rclone ls remote:bucket/path/to/recover --s3-versions

# Recover that path to a point in time
rclone copy remote:bucket/path/to/recover local/path --s3-version-at "2024-01-17 21:10:00"
```

## Important Considerations

### Before Recovery
- Verify you have sufficient local storage space
- Use --dry-run to preview operations
- Consider creating a new directory for recovered files
- Check rclone remote is properly configured

### During Recovery
- Large recoveries may take significant time
- Network interruptions can be resumed
- Use --progress to monitor large operations
- Consider using --transfers flag for parallel operations

### After Recovery
- Verify file integrity
- Check file timestamps
- Ensure all needed files were recovered
- Verify file permissions if important

## Troubleshooting

### Common Issues
1. Access denied
   - Verify credentials
   - Check bucket permissions
   - Ensure API key has necessary permissions

2. No versions shown
   - Verify versioning is enabled
   - Check if files have multiple versions
   - Ensure --s3-versions flag is used

### Recovery Verification
Always verify recovered files:
```bash
# Compare local and remote sizes
rclone check local/path remote:bucket/path

# Show differences between local and remote
rclone check local/path remote:bucket/path --combined

# Get detailed file listing
rclone lsl local/path
```

## Additional Notes

### Performance Tips
- Use --transfers=N to set number of parallel transfers
- Use --checkers=N to set number of version checkers
- Consider --fast-list for large directories
- Use --progress to monitor large operations

### For Encrypted Remotes
- Commands are identical
- Just use your encrypted remote name
- Verify decryption by checking file contents
- See [rclone-setup.md](../rclone-setup.md) for configuration