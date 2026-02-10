#!/usr/bin/env bash
#
# Uninstall Immich backup systemd timer
#

set -euo pipefail

SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

echo "Uninstalling Immich backup service..."

# Stop and disable timer
systemctl --user stop immich-backup.timer 2>/dev/null || true
systemctl --user disable immich-backup.timer 2>/dev/null || true

# Stop service if running
systemctl --user stop immich-backup.service 2>/dev/null || true

# Remove systemd units
rm -f "$SYSTEMD_USER_DIR/immich-backup.service"
rm -f "$SYSTEMD_USER_DIR/immich-backup.timer"

# Reload systemd
systemctl --user daemon-reload

echo ""
echo "Uninstallation complete!"
echo ""
echo "Note: The following directories were NOT removed:"
echo "  ~/Documents/immich-stage/  (staged backup files)"
echo "  ~/.local/share/immich-backup/logs/  (log files)"
echo ""
echo "Remove them manually if no longer needed."
