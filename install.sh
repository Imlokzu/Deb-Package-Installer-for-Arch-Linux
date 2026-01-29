#!/bin/bash
# Installation script for Deb Package Installer

set -e

echo "🚀 Installing Deb Package Installer for Arch Linux..."
echo "Features: Auto-install debtap, GUI interface, drag & drop support"
echo "=" * 60

# Check if running on Arch Linux
if ! grep -q "arch" /etc/os-release 2>/dev/null; then
    echo "⚠️  Warning: This installer is designed for Arch Linux"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for Python and PyQt5
echo "🔍 Checking dependencies..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Installing..."
    sudo pacman -S --needed python
    
    # Verify installation
    if ! command -v python3 &> /dev/null; then
        echo "❌ Error: Failed to install Python 3"
        echo "Please install manually with: sudo pacman -S python"
        exit 1
    fi
    echo "✅ Python 3 installed successfully"
else
    echo "✅ Python 3 found"
fi

# Check for PyQt5
if ! python3 -c "import PyQt5" 2>/dev/null; then
    echo "📦 PyQt5 not found. Installing..."
    sudo pacman -S --needed python-pyqt5
    
    # Verify PyQt5 installation
    if ! python3 -c "import PyQt5" 2>/dev/null; then
        echo "❌ Error: Failed to install PyQt5"
        echo "Please install manually with: sudo pacman -S python-pyqt5"
        exit 1
    fi
    echo "✅ PyQt5 installed successfully"
else
    echo "✅ PyQt5 found"
fi

# Install the main application
echo "📥 Installing application..."

# Install main GUI application
sudo cp deb_installer_gui.py /usr/local/bin/
sudo chmod +x /usr/local/bin/deb_installer_gui.py

echo "✅ Application installed"

# Create desktop entry
echo "🔗 Setting up file associations..."

cat > /tmp/deb-installer.desktop << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=Deb Package Installer
Comment=Install .deb packages on Arch Linux using debtap
Exec=/usr/local/bin/deb_installer_gui.py %f
Icon=package-x-generic
StartupNotify=true
NoDisplay=false
MimeType=application/vnd.debian.binary-package;
Categories=System;PackageManager;
EOF

sudo cp /tmp/deb-installer.desktop /usr/share/applications/
sudo update-desktop-database
rm /tmp/deb-installer.desktop
echo "✅ File associations created"

# Create command shortcuts
echo "🔗 Creating command shortcuts..."
sudo ln -sf /usr/local/bin/deb_installer_gui.py /usr/local/bin/deb-installer
sudo ln -sf /usr/local/bin/deb_installer_gui.py /usr/local/bin/deb-installer-gui

echo "✅ Command shortcuts created"

# Check for AUR helper
echo "🔍 Checking for AUR helper..."
if command -v yay &> /dev/null; then
    echo "✅ yay found - debtap can be auto-installed"
elif command -v paru &> /dev/null; then
    echo "✅ paru found - debtap can be auto-installed"
elif command -v pamac &> /dev/null; then
    echo "✅ pamac found - debtap can be auto-installed"
else
    echo "⚠️  No AUR helper found (yay, paru, pamac)"
    echo "💡 Install one for automatic debtap installation:"
    echo "   sudo pacman -S --needed base-devel git"
    echo "   git clone https://aur.archlinux.org/yay.git"
    echo "   cd yay && makepkg -si"
fi

echo ""
echo "🎉 Installation complete!"
echo "=" * 60
echo ""
echo "📋 Usage:"
echo "  • deb-installer                     - Launch GUI to select .deb file"
echo "  • deb-installer <file.deb>          - Install specific .deb file"
echo "  • Right-click .deb file → Open with → Deb Package Installer"
echo ""
echo "✨ Features:"
echo "  • 🔧 Automatic debtap installation with progress tracking"
echo "  • 🖱️  Drag & drop support for .deb files"
echo "  • 📊 Real-time installation progress and console output"
echo "  • 🔐 GUI sudo password prompt (no terminal needed)"
echo "  • ✅ Automatic conflict resolution and error handling"
echo "  • 🎯 Clean, user-friendly interface"
echo ""
echo "💡 The app will automatically install debtap when you first run it!"
echo "    Just launch the installer and it will guide you through everything."