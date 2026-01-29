#!/bin/bash
# Uninstall script for Deb Package Installer

echo "🗑️  Uninstalling Deb Package Installer..."

# Remove applications
echo "📥 Removing applications..."
sudo rm -f /usr/local/bin/deb_installer_console.py
sudo rm -f /usr/local/bin/deb_installer_gui.py
sudo rm -f /usr/local/bin/deb_installer_enhanced.py
sudo rm -f /usr/local/bin/debug_debtap.py

# Remove symlinks
echo "🔗 Removing command shortcuts..."
sudo rm -f /usr/local/bin/deb-installer
sudo rm -f /usr/local/bin/deb-installer-gui
sudo rm -f /usr/local/bin/deb-installer-enhanced
sudo rm -f /usr/local/bin/deb-debug

# Remove desktop entry
echo "🖱️  Removing file associations..."
sudo rm -f /usr/share/applications/deb-installer.desktop
sudo update-desktop-database

echo ""
echo "✅ Uninstallation complete!"
echo ""
echo "Note: debtap was not removed (you might want to keep it for manual use)"
echo "To remove debtap: yay -R debtap"