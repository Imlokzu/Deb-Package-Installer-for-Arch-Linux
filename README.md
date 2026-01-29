# Deb Package Installer for Arch Linux

A simple GUI application that converts and installs .deb packages on Arch Linux using debtap.

## Features

- 🖱️ **Easy GUI interface** - Just select your .deb file and install
- 🔧 **Auto-setup** - Automatically downloads and installs debtap via yay
- 🔐 **Secure** - Uses GUI password prompt for administrator access
- 📊 **Progress tracking** - Real-time installation progress and console output
- 🗂️ **File integration** - Right-click .deb files to install them

## Installation

```bash
git clone https://github.com/Imlokzu/Deb-Package-Installer-for-Arch-Linux.git
cd Deb-Package-Installer-for-Arch-Linux
chmod +x install.sh
./install.sh
```

## Usage

### Launch GUI
```bash
deb-installer
```

### Install specific file
```bash
deb-installer mypackage.deb
```

### Right-click integration
After installation, right-click any .deb file → "Open with Deb Package Installer"

## Requirements

- Arch Linux or Arch-based distribution
- AUR helper (yay, paru, or pamac) for automatic debtap installation
- Internet connection for initial setup

All other dependencies (Python, PyQt5, debtap) are installed automatically.

## How it works

1. **Password prompt** - Enter your sudo password once
2. **Auto-setup** - App installs debtap if not found (via yay)
3. **File selection** - Choose your .deb package
4. **Conversion** - Uses debtap to convert .deb to Arch package
5. **Installation** - Installs the converted package
6. **Done** - Your application is ready to use

## Uninstall

```bash
./uninstall.sh
```