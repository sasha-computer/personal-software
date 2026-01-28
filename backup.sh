#!/usr/bin/env bash
#
# Immich Backup Script
# Backs up Immich photos from NAS to LUKS-encrypted USB via local staging
#

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

NAS_IP="192.168.50.235"
NAS_TAILSCALE="nas"
IMMICH_PATH="/mnt/user/immichphotos"
LOCAL_STAGE="$HOME/Documents/immich-stage"
USB_SEARCH_PATH="/run/media/sasha"
BACKUP_SUBDIR="immich-backups"
MAX_BACKUPS=2
MAX_WAIT_MINUTES=30
CHECK_INTERVAL_SECONDS=300  # 5 minutes
LOG_DIR="$HOME/.local/share/immich-backup/logs"
MIN_FREE_SPACE_GB=400

# =============================================================================
# State
# =============================================================================

DRY_RUN=false
IMMICH_WAS_STOPPED=false
NAS_HOST=""
USB_MOUNT=""
BACKUP_DATE=$(date +%Y%m%d)
BACKUP_FILENAME="immich-backup-${BACKUP_DATE}.tar"

# =============================================================================
# Functions
# =============================================================================

log() {
    local level="$1"
    shift
    local msg="$*"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $msg" | tee -a "$LOG_FILE"
}

info()  { log "INFO" "$@"; }
warn()  { log "WARN" "$@"; }
error() { log "ERROR" "$@"; }

notify() {
    local urgency="${1:-normal}"
    local title="$2"
    local body="$3"

    if command -v notify-send &>/dev/null; then
        notify-send -u "$urgency" "$title" "$body" || true
    fi

    if [[ "$urgency" == "critical" ]]; then
        error "$title: $body"
    else
        info "$title: $body"
    fi
}

cleanup() {
    local exit_code=$?

    # Restart Immich if we stopped it
    if [[ "$IMMICH_WAS_STOPPED" == "true" ]]; then
        warn "Cleanup: Restarting Immich after unexpected exit"
        if [[ "$DRY_RUN" == "false" ]]; then
            ssh "$NAS_HOST" "docker start immich" || true
        fi
    fi

    # Remove local tar file on failure (keep on success for verification)
    if [[ $exit_code -ne 0 ]] && [[ -f "$LOCAL_STAGE/../$BACKUP_FILENAME" ]]; then
        info "Cleanup: Removing incomplete tar file"
        rm -f "$LOCAL_STAGE/../$BACKUP_FILENAME"
    fi

    exit $exit_code
}

trap cleanup EXIT

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Backup Immich photos from NAS to LUKS-encrypted USB.

Options:
    --dry-run       Show what would be done without making changes
    --help          Show this help message

Exit codes:
    0   Success
    1   USB not found
    2   NAS unreachable
    3   Insufficient disk space
    4   Tar/backup failed
EOF
    exit 0
}

detect_nas_host() {
    info "Detecting best route to NAS..."

    # Try Tailscale first
    if command -v tailscale &>/dev/null; then
        if tailscale status &>/dev/null && tailscale ping "$NAS_TAILSCALE" --timeout=3s &>/dev/null 2>&1; then
            NAS_HOST="root@$NAS_TAILSCALE"
            info "Using Tailscale connection: $NAS_HOST"
            return 0
        fi
    fi

    # Fall back to local IP
    if ping -c 1 -W 3 "$NAS_IP" &>/dev/null; then
        NAS_HOST="root@$NAS_IP"
        info "Using local network connection: $NAS_HOST"
        return 0
    fi

    error "Cannot reach NAS via Tailscale ($NAS_TAILSCALE) or local IP ($NAS_IP)"
    return 1
}

check_nas_reachable() {
    info "Checking NAS SSH connectivity..."

    if ! ssh -o ConnectTimeout=10 -o BatchMode=yes "$NAS_HOST" "echo 'SSH OK'" &>/dev/null; then
        error "Cannot SSH to NAS at $NAS_HOST"
        notify "critical" "Immich Backup Failed" "Cannot connect to NAS via SSH"
        exit 2
    fi

    info "NAS is reachable via SSH"
}

find_usb_mount() {
    info "Searching for backup USB drive..."

    local attempt=1
    local max_attempts=$((MAX_WAIT_MINUTES * 60 / CHECK_INTERVAL_SECONDS))

    while [[ $attempt -le $max_attempts ]]; do
        # Search for any mounted volume with our backup directory
        for mount_point in "$USB_SEARCH_PATH"/*; do
            if [[ -d "$mount_point/$BACKUP_SUBDIR" ]]; then
                USB_MOUNT="$mount_point"
                info "Found backup USB at: $USB_MOUNT"
                return 0
            fi
        done

        # Also check if any mount exists where we could create the directory
        for mount_point in "$USB_SEARCH_PATH"/*; do
            if [[ -d "$mount_point" ]] && [[ -w "$mount_point" ]]; then
                # Check if this looks like a backup drive (has enough space)
                local free_gb
                free_gb=$(df -BG "$mount_point" | awk 'NR==2 {gsub(/G/,"",$4); print $4}')
                if [[ "$free_gb" -gt 100 ]]; then
                    USB_MOUNT="$mount_point"
                    info "Found suitable USB at: $USB_MOUNT (will create $BACKUP_SUBDIR)"
                    mkdir -p "$USB_MOUNT/$BACKUP_SUBDIR"
                    return 0
                fi
            fi
        done

        if [[ $attempt -eq 1 ]]; then
            notify "normal" "Immich Backup" "Please plug in and unlock your backup USB drive"
        fi

        info "USB not found, waiting ${CHECK_INTERVAL_SECONDS}s... (attempt $attempt/$max_attempts)"
        sleep "$CHECK_INTERVAL_SECONDS"
        ((attempt++))
    done

    error "USB drive not found after $MAX_WAIT_MINUTES minutes"
    notify "critical" "Immich Backup Failed" "USB drive not available after $MAX_WAIT_MINUTES minutes"
    exit 1
}

check_local_space() {
    info "Checking local disk space..."

    local stage_dir
    stage_dir=$(dirname "$LOCAL_STAGE")

    local free_gb
    free_gb=$(df -BG "$stage_dir" | awk 'NR==2 {gsub(/G/,"",$4); print $4}')

    if [[ "$free_gb" -lt "$MIN_FREE_SPACE_GB" ]]; then
        error "Insufficient disk space: ${free_gb}GB free, need ${MIN_FREE_SPACE_GB}GB"
        notify "critical" "Immich Backup Failed" "Insufficient disk space: ${free_gb}GB free"
        exit 3
    fi

    info "Local disk has ${free_gb}GB free (need ${MIN_FREE_SPACE_GB}GB)"
}

stop_immich() {
    info "Stopping Immich container on NAS..."

    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY-RUN] Would stop immich container"
        return 0
    fi

    if ssh "$NAS_HOST" "docker stop immich"; then
        IMMICH_WAS_STOPPED=true
        info "Immich stopped successfully"
    else
        error "Failed to stop Immich container"
        notify "critical" "Immich Backup Failed" "Could not stop Immich container"
        exit 4
    fi
}

start_immich() {
    info "Starting Immich container on NAS..."

    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY-RUN] Would start immich container"
        return 0
    fi

    if ssh "$NAS_HOST" "docker start immich"; then
        IMMICH_WAS_STOPPED=false
        info "Immich started successfully"
    else
        warn "Failed to start Immich container - manual intervention may be required"
        notify "critical" "Immich Backup Warning" "Could not restart Immich - please check manually"
    fi
}

rsync_from_nas() {
    info "Syncing from NAS to local staging..."

    mkdir -p "$LOCAL_STAGE"

    local rsync_opts="-avz --delete --progress"

    if [[ "$DRY_RUN" == "true" ]]; then
        rsync_opts="$rsync_opts --dry-run"
    fi

    info "Running: rsync $rsync_opts $NAS_HOST:$IMMICH_PATH/ $LOCAL_STAGE/"

    if ! rsync $rsync_opts "$NAS_HOST:$IMMICH_PATH/" "$LOCAL_STAGE/"; then
        error "Rsync from NAS failed"
        notify "critical" "Immich Backup Failed" "Failed to sync files from NAS"
        exit 4
    fi

    local stage_size
    stage_size=$(du -sh "$LOCAL_STAGE" | cut -f1)
    info "Staging complete: $stage_size"
}

create_tar_archive() {
    info "Creating tar archive..."

    local tar_path
    tar_path="$(dirname "$LOCAL_STAGE")/$BACKUP_FILENAME"

    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY-RUN] Would create: $tar_path"
        return 0
    fi

    cd "$(dirname "$LOCAL_STAGE")"

    if ! tar -cvf "$BACKUP_FILENAME" "$(basename "$LOCAL_STAGE")" 2>&1 | tee -a "$LOG_FILE"; then
        error "Tar creation failed"
        notify "critical" "Immich Backup Failed" "Failed to create tar archive"
        exit 4
    fi

    local tar_size
    tar_size=$(du -sh "$tar_path" | cut -f1)
    info "Tar archive created: $tar_size"
}

verify_tar_integrity() {
    info "Verifying tar archive integrity..."

    local tar_path
    tar_path="$(dirname "$LOCAL_STAGE")/$BACKUP_FILENAME"

    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY-RUN] Would verify: $tar_path"
        return 0
    fi

    if tar -tvf "$tar_path" > /dev/null 2>&1; then
        info "Tar integrity verified OK"
    else
        error "Tar integrity check failed"
        notify "critical" "Immich Backup Failed" "Tar archive is corrupted"
        exit 4
    fi
}

copy_to_usb() {
    info "Copying backup to USB..."

    local tar_path
    tar_path="$(dirname "$LOCAL_STAGE")/$BACKUP_FILENAME"
    local usb_dest="$USB_MOUNT/$BACKUP_SUBDIR/"

    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY-RUN] Would copy: $tar_path -> $usb_dest"
        return 0
    fi

    if ! rsync -avP "$tar_path" "$usb_dest"; then
        error "Failed to copy backup to USB"
        notify "critical" "Immich Backup Failed" "Failed to copy backup to USB drive"
        exit 4
    fi

    info "Backup copied to USB successfully"
}

rotate_backups() {
    info "Rotating old backups (keeping $MAX_BACKUPS most recent)..."

    local backup_dir="$USB_MOUNT/$BACKUP_SUBDIR"

    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY-RUN] Would rotate backups in: $backup_dir"
        ls -t "$backup_dir"/immich-backup-*.tar 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) || true
        return 0
    fi

    local old_backups
    old_backups=$(ls -t "$backup_dir"/immich-backup-*.tar 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) || true)

    if [[ -n "$old_backups" ]]; then
        echo "$old_backups" | while read -r old_backup; do
            info "Removing old backup: $old_backup"
            rm -f "$old_backup"
        done
    else
        info "No old backups to remove"
    fi
}

cleanup_local_tar() {
    info "Cleaning up local tar file..."

    local tar_path
    tar_path="$(dirname "$LOCAL_STAGE")/$BACKUP_FILENAME"

    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY-RUN] Would remove: $tar_path"
        return 0
    fi

    rm -f "$tar_path"
    info "Local tar file removed (staged files kept for faster incremental sync)"
}

# =============================================================================
# Main
# =============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help)
                usage
                ;;
            *)
                error "Unknown option: $1"
                usage
                ;;
        esac
    done

    # Setup logging
    mkdir -p "$LOG_DIR"
    LOG_FILE="$LOG_DIR/backup-${BACKUP_DATE}.log"

    info "=========================================="
    info "Immich Backup Starting"
    info "=========================================="

    if [[ "$DRY_RUN" == "true" ]]; then
        info "DRY-RUN MODE - No changes will be made"
    fi

    local start_time
    start_time=$(date +%s)

    notify "normal" "Immich Backup" "Backup starting..."

    # Pre-flight checks
    detect_nas_host || exit 2
    check_nas_reachable
    find_usb_mount
    check_local_space

    # Stop Immich for consistent backup
    stop_immich

    # Sync from NAS to local staging
    rsync_from_nas

    # Restart Immich ASAP (before tar/copy operations)
    start_immich

    # Create and verify tar archive
    create_tar_archive
    verify_tar_integrity

    # Copy to USB and rotate
    copy_to_usb
    rotate_backups

    # Cleanup
    cleanup_local_tar

    local end_time duration_min
    end_time=$(date +%s)
    duration_min=$(( (end_time - start_time) / 60 ))

    # Get backup size
    local backup_size="unknown"
    if [[ -f "$USB_MOUNT/$BACKUP_SUBDIR/$BACKUP_FILENAME" ]]; then
        backup_size=$(du -sh "$USB_MOUNT/$BACKUP_SUBDIR/$BACKUP_FILENAME" | cut -f1)
    fi

    info "=========================================="
    info "Backup Complete!"
    info "Duration: ${duration_min} minutes"
    info "Backup size: $backup_size"
    info "Location: $USB_MOUNT/$BACKUP_SUBDIR/$BACKUP_FILENAME"
    info "=========================================="

    notify "normal" "Immich Backup Complete" "Backup finished in ${duration_min}min ($backup_size)"
}

main "$@"
