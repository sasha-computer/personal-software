# Immich Backup System

Automated weekly backup of Immich photos from NAS to LUKS-encrypted USB drive.

## Architecture

```
NAS (192.168.x.x)          Local Machine              USB (LUKS encrypted)
/mnt/user/immichphotos/  -->  ~/Documents/immich-stage/  -->  /run/media/<user>/<label>/
                                   (tar here)                  immich-backups/
```

## What Gets Backed Up

Per Immich documentation, all essential directories:
- `upload/` - user-uploaded content
- `library/` - original assets
- `profile/` - user avatars
- `backups/` - database dumps (auto-generated daily)
- `thumbs/` - preview thumbnails
- `encoded-video/` - transcoded videos

## Quick Start

```bash
# Test connectivity and paths (no changes made)
./backup.sh --dry-run

# Run a manual backup
./backup.sh

# Install weekly timer (Wednesdays at 2pm)
./install.sh
```

## Requirements

- SSH access to NAS as root (key-based auth)
- LUKS-encrypted USB drive
- ~400GB free local disk space for staging
- `notify-send` for desktop notifications (optional)

## Configuration

Edit the top of `backup.sh` to customize:

```bash
NAS_IP="192.168.x.x"          # Local network IP
NAS_TAILSCALE="nas"               # Tailscale hostname
IMMICH_PATH="/mnt/user/immichphotos"
LOCAL_STAGE="$HOME/Documents/immich-stage"
USB_SEARCH_PATH="/run/media/<user>"
BACKUP_SUBDIR="immich-backups"
MAX_BACKUPS=2                     # Keep N most recent on USB
MAX_WAIT_MINUTES=30               # Wait for USB before aborting
```

## USB Drive Setup

The script searches `/run/media/<user>/` for:
1. Any mounted volume containing an `immich-backups/` directory
2. Or any writable volume with >100GB free (creates the directory)

To prepare a new USB:
1. Encrypt with LUKS via GNOME Disks or `cryptsetup`
2. Mount and unlock the drive
3. Create directory: `mkdir /run/media/<user>/<label>/immich-backups`

## Backup Process

1. **Pre-flight checks**: NAS reachable, USB mounted, space available
2. **Stop Immich**: `docker stop immich` (prevents sync issues)
3. **Rsync to local**: Fast incremental sync to NVMe staging
4. **Start Immich**: Back online while we process locally
5. **Create tar**: Archive the staged files
6. **Verify**: Check tar integrity
7. **Copy to USB**: Transfer verified backup
8. **Rotate**: Keep only 2 most recent backups
9. **Cleanup**: Remove local tar (keep staged files for faster next sync)

## Scheduling

Installed via systemd user timer:
- **When**: Wednesdays at 2pm
- **Persistent**: Runs missed backups on next boot

```bash
# View timer status
systemctl --user list-timers immich-backup.timer

# View service logs
journalctl --user -u immich-backup.service -f

# Trigger manually via systemd
systemctl --user start immich-backup.service
```

## Logs

- systemd: `journalctl --user -u immich-backup.service`
- Script: `~/.local/share/immich-backup/logs/backup-YYYYMMDD.log`

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | USB not found after timeout |
| 2 | NAS unreachable |
| 3 | Insufficient local disk space |
| 4 | Backup failed (tar/rsync error) |

## Network

The script auto-detects the best route to NAS:
- **At home**: Uses local IP (192.168.x.x)
- **Away**: Uses Tailscale (nas)

## Restoration

To restore from backup:

```bash
# Mount and unlock USB drive
# Extract to desired location
tar -xvf /run/media/<user>/<label>/immich-backups/immich-backup-YYYYMMDD.tar

# Stop Immich on NAS
ssh root@<nas-ip> "docker stop immich"

# Sync back to NAS
rsync -avz immich-stage/ root@<nas-ip>:/mnt/user/immichphotos/

# Start Immich
ssh root@<nas-ip> "docker start immich"
```

## Uninstall

```bash
./uninstall.sh
```

This removes the systemd timer but preserves staged files and logs.
