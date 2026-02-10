#!/usr/bin/env bash
#
# Install Immich backup systemd timer
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

echo "Installing Immich backup service..."

# Create required directories
mkdir -p "$SYSTEMD_USER_DIR"
mkdir -p "$HOME/Documents/immich-stage"
mkdir -p "$HOME/.local/share/immich-backup/logs"

# Make backup script executable
chmod +x "$SCRIPT_DIR/backup.sh"

# Install systemd units
cp "$SCRIPT_DIR/immich-backup.service" "$SYSTEMD_USER_DIR/"
cp "$SCRIPT_DIR/immich-backup.timer" "$SYSTEMD_USER_DIR/"

# Reload systemd
systemctl --user daemon-reload

# Enable and start timer
systemctl --user enable immich-backup.timer
systemctl --user start immich-backup.timer

echo ""
echo "Installation complete!"
echo ""
echo "Timer status:"
systemctl --user status immich-backup.timer --no-pager || true
echo ""
echo "Next scheduled run:"
systemctl --user list-timers immich-backup.timer --no-pager || true
echo ""
echo "To run a backup manually:"
echo "  $SCRIPT_DIR/backup.sh"
echo ""
echo "To run via systemd:"
echo "  systemctl --user start immich-backup.service"
echo ""
echo "To view logs:"
echo "  journalctl --user -u immich-backup.service"
echo "  ls -la ~/.local/share/immich-backup/logs/"
