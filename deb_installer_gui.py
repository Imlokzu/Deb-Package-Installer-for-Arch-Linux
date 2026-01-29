#!/usr/bin/env python3
"""
GUI Deb Package Installer for Arch Linux using debtap
Clean, working version for "Open with" workflow
"""

import sys
import os
import subprocess
import tempfile
import shutil
import time
import select
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QWidget, QLabel, QProgressBar, QMessageBox, QTextEdit, QPushButton,
                             QDialog, QLineEdit, QDialogButtonBox, QFileDialog)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont


class SudoPasswordDialog(QDialog):
    """Dialog to get sudo password"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Administrator Access Required")
        self.setModal(True)
        self.setFixedSize(400, 150)
        
        layout = QVBoxLayout(self)
        
        # Icon and message
        msg_layout = QHBoxLayout()
        
        # Use system icon if available
        icon_label = QLabel()
        icon_label.setPixmap(self.style().standardIcon(self.style().SP_MessageBoxQuestion).pixmap(48, 48))
        msg_layout.addWidget(icon_label)
        
        msg_label = QLabel("Administrator privileges are required to install packages.\nPlease enter your password:")
        msg_label.setWordWrap(True)
        msg_layout.addWidget(msg_label)
        
        layout.addLayout(msg_layout)
        
        # Password input
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter your password...")
        layout.addWidget(self.password_input)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Focus on password input
        self.password_input.setFocus()
    
    def get_password(self):
        return self.password_input.text()


class InstallWorker(QThread):
    """Worker thread for package installation with detailed progress"""
    
    progress_update = pyqtSignal(str)  # Status message
    progress_value = pyqtSignal(int)   # Progress percentage
    time_update = pyqtSignal(str)      # Time information
    console_output = pyqtSignal(str)   # Console output
    finished = pyqtSignal(bool, str)   # Success, message
    
    def __init__(self, deb_file_path, sudo_password=None):
        super().__init__()
        self.deb_file_path = deb_file_path
        self.sudo_password = sudo_password
        self.temp_dir = None
        self.start_time = None
    
    def run(self):
        """Main installation process with detailed progress"""
        self.start_time = time.time()
        
        try:
            # Get file size for estimates
            file_size_mb = os.path.getsize(self.deb_file_path) / (1024 * 1024)
            conversion_time = max(10, int(file_size_mb * 2))
            install_time = max(5, int(file_size_mb * 0.5))
            total_estimated = conversion_time + install_time + 5
            
            self.console_output.emit(f"📦 Package: {os.path.basename(self.deb_file_path)}")
            self.console_output.emit(f"📏 Size: {file_size_mb:.1f} MB")
            self.console_output.emit(f"⏱️  Estimated time: ~{total_estimated} seconds\n")
            self.time_update.emit(f"Estimated time: ~{total_estimated} seconds")
            
            # Step 1: Check if debtap is installed
            self.progress_update.emit("Checking for debtap...")
            self.progress_value.emit(5)
            self.console_output.emit("="*50)
            self.console_output.emit("STEP 1/4: Checking debtap")
            self.console_output.emit("="*50)
            
            step_start = time.time()
            if not self.check_debtap():
                self.console_output.emit("❌ debtap setup failed!")
                self.finished.emit(False, "debtap setup failed! Please check the console output for details.")
                return
            
            step_time = time.time() - step_start
            self.console_output.emit(f"✅ debtap ready! ({step_time:.1f}s)\n")
            self.time_update.emit(f"debtap check completed in {step_time:.1f}s")
            
            # Step 2: Create temporary directory
            self.progress_update.emit("Preparing workspace...")
            self.progress_value.emit(10)
            self.console_output.emit("="*50)
            self.console_output.emit("STEP 2/4: Preparing workspace")
            self.console_output.emit("="*50)
            
            self.temp_dir = tempfile.mkdtemp(prefix="deb_installer_")
            self.console_output.emit(f"📁 Working directory: {self.temp_dir}")
            
            # Step 3: Copy file
            self.progress_update.emit("Copying package file...")
            self.progress_value.emit(15)
            
            step_start = time.time()
            deb_filename = os.path.basename(self.deb_file_path)
            temp_deb_path = os.path.join(self.temp_dir, deb_filename)
            shutil.copy2(self.deb_file_path, temp_deb_path)
            step_time = time.time() - step_start
            self.console_output.emit(f"✅ File copied in {step_time:.1f}s\n")
            self.time_update.emit(f"File copied in {step_time:.1f}s")
            
            # Step 4: Convert .deb to Arch package
            self.progress_update.emit(f"Converting package... (est. {conversion_time}s)")
            self.progress_value.emit(20)
            self.console_output.emit("="*50)
            self.console_output.emit("STEP 3/4: Converting package")
            self.console_output.emit("="*50)
            self.console_output.emit(f"🔄 Converting {deb_filename} to Arch package...")
            self.console_output.emit(f"📝 Running: debtap -q {deb_filename}")
            self.console_output.emit("-" * 50)
            
            step_start = time.time()
            arch_package = self.convert_deb_package(temp_deb_path)
            step_time = time.time() - step_start
            
            if not arch_package:
                self.console_output.emit(f"❌ Conversion failed after {step_time:.1f}s")
                self.finished.emit(False, f"Failed to convert .deb package after {step_time:.1f}s")
                return
            
            pkg_size_mb = os.path.getsize(arch_package) / (1024 * 1024)
            self.console_output.emit("-" * 50)
            self.console_output.emit(f"✅ Conversion completed in {step_time:.1f}s")
            self.console_output.emit(f"📦 Generated: {os.path.basename(arch_package)} ({pkg_size_mb:.1f} MB)\n")
            self.time_update.emit(f"Conversion completed in {step_time:.1f}s")
            self.progress_value.emit(70)
            
            # Step 5: Install the converted package
            self.progress_update.emit(f"Installing package... ({pkg_size_mb:.1f} MB)")
            self.progress_value.emit(75)
            self.console_output.emit("="*50)
            self.console_output.emit("STEP 4/4: Installing package")
            self.console_output.emit("="*50)
            self.console_output.emit(f"📥 Installing {os.path.basename(arch_package)}...")
            self.console_output.emit("🔐 Running: sudo pacman -U --noconfirm")
            self.console_output.emit("-" * 50)
            
            step_start = time.time()
            if self.install_arch_package(arch_package):
                step_time = time.time() - step_start
                total_time = time.time() - self.start_time
                
                self.console_output.emit("-" * 50)
                self.console_output.emit(f"✅ Installation completed in {step_time:.1f}s")
                self.console_output.emit("\n" + "="*50)
                self.console_output.emit("🎉 SUCCESS!")
                self.console_output.emit("="*50)
                self.console_output.emit(f"⏱️  Total time: {total_time:.1f} seconds")
                
                self.progress_update.emit("Installation completed!")
                self.progress_value.emit(100)
                self.time_update.emit(f"Total time: {total_time:.1f}s")
                self.finished.emit(True, f"Package installed successfully!\nTotal time: {total_time:.1f} seconds")
            else:
                step_time = time.time() - step_start
                self.console_output.emit("-" * 50)
                self.console_output.emit(f"❌ Installation failed after {step_time:.1f}s")
                self.finished.emit(False, f"Failed to install package after {step_time:.1f}s")
                
        except Exception as e:
            total_time = time.time() - self.start_time if self.start_time else 0
            self.console_output.emit(f"\n❌ Error after {total_time:.1f}s: {str(e)}")
            self.finished.emit(False, f"Error after {total_time:.1f}s: {str(e)}")
        finally:
            # Cleanup
            if self.temp_dir and os.path.exists(self.temp_dir):
                self.console_output.emit(f"\n🧹 Cleaning up temporary files...")
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                self.console_output.emit("✅ Cleanup complete")
    
    def run_sudo_command(self, cmd):
        """Run command with sudo using provided password"""
        if not self.sudo_password:
            return None
        
        # Create sudo command
        sudo_cmd = ['sudo', '-S'] + cmd
        
        process = subprocess.Popen(
            sudo_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Send password
        process.stdin.write(self.sudo_password + '\n')
        process.stdin.flush()
        
        return process
    
    def check_debtap(self):
        """Check if debtap is installed, install if not found"""
        try:
            result = subprocess.run(['which', 'debtap'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.console_output.emit("✅ debtap found and ready!")
                return True
            else:
                self.console_output.emit("❌ debtap not found, attempting auto-install...")
                return self.install_debtap()
        except Exception as e:
            self.console_output.emit(f"❌ Error checking debtap: {e}")
            self.console_output.emit("🔧 Attempting to install debtap...")
            return self.install_debtap()
    
    def install_debtap(self):
        """Auto-install debtap using available package managers"""
        self.console_output.emit("🔧 Auto-installing debtap...")
        
        # Try different package managers in order of preference
        package_managers = [
            (['yay', '-S', '--noconfirm', 'debtap'], "yay"),
            (['paru', '-S', '--noconfirm', 'debtap'], "paru"),
            (['pamac', 'install', '--no-confirm', 'debtap'], "pamac")
        ]
        
        for cmd, manager_name in package_managers:
            try:
                # Check if package manager exists
                check_result = subprocess.run(['which', cmd[0]], 
                                            capture_output=True, text=True)
                if check_result.returncode != 0:
                    continue  # Package manager not found, try next
                
                self.console_output.emit(f"📦 Found {manager_name}, installing debtap...")
                
                # Run installation with sudo and password
                process = self.run_sudo_command(cmd)
                if not process:
                    self.console_output.emit("❌ Could not start installation process")
                    continue
                
                # Stream output
                install_output = []
                while True:
                    line = process.stdout.readline()
                    if line:
                        line = line.rstrip()
                        if line and 'password' not in line.lower():
                            self.console_output.emit(f"  {line}")
                            install_output.append(line)
                    
                    if process.poll() is not None:
                        remaining = process.stdout.read()
                        if remaining:
                            for line in remaining.split('\n'):
                                if line.strip() and 'password' not in line.lower():
                                    self.console_output.emit(f"  {line.rstrip()}")
                        break
                
                if process.returncode == 0:
                    self.console_output.emit("✅ debtap installation completed!")
                    
                    # Verify installation worked
                    verify_result = subprocess.run(['which', 'debtap'], 
                                                 capture_output=True, text=True)
                    if verify_result.returncode == 0:
                        self.console_output.emit("✅ debtap installation verified!")
                        
                        # Update debtap database
                        self.console_output.emit("🔄 Updating debtap database...")
                        try:
                            update_process = self.run_sudo_command(['debtap', '-u'])
                            if not update_process:
                                self.console_output.emit("⚠️  Could not start database update")
                                return True
                            
                            # Stream database update output
                            while True:
                                line = update_process.stdout.readline()
                                if line:
                                    line = line.rstrip()
                                    if line and 'password' not in line.lower():
                                        self.console_output.emit(f"  {line}")
                                
                                if update_process.poll() is not None:
                                    remaining = update_process.stdout.read()
                                    if remaining:
                                        for line in remaining.split('\n'):
                                            if line.strip() and 'password' not in line.lower():
                                                self.console_output.emit(f"  {line.rstrip()}")
                                    break
                            
                            if update_process.returncode == 0:
                                self.console_output.emit("✅ debtap database updated successfully!")
                            else:
                                self.console_output.emit("⚠️  Database update had issues, but debtap is installed")
                                self.console_output.emit("💡 You can update manually later with: sudo debtap -u")
                        except Exception as e:
                            self.console_output.emit(f"⚠️  Database update error: {e}")
                        
                        return True
                    else:
                        self.console_output.emit("❌ Installation completed but debtap still not found")
                        continue
                else:
                    self.console_output.emit(f"❌ {manager_name} installation failed (exit code: {process.returncode})")
                    continue
                    
            except Exception as e:
                self.console_output.emit(f"❌ Error with {manager_name}: {e}")
                continue
        
        # If all package managers failed
        self.console_output.emit("❌ Auto-installation failed with all package managers")
        self.console_output.emit("💡 Please install debtap manually:")
        self.console_output.emit("   yay -S debtap")
        self.console_output.emit("   sudo debtap -u")
        self.console_output.emit("")
        self.console_output.emit("🔍 Available package managers checked:")
        for cmd, name in package_managers:
            try:
                subprocess.run(['which', cmd[0]], check=True, capture_output=True)
                self.console_output.emit(f"   ✅ {name} - available")
            except:
                self.console_output.emit(f"   ❌ {name} - not found")
        
        return False
    
    def convert_deb_package(self, temp_deb_path):
        """Convert .deb package to Arch package using debtap with live output"""
        try:
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir)
            
            # Get package name for better debtap handling
            deb_filename = os.path.basename(temp_deb_path)
            package_name = deb_filename.split('_')[0]  # Extract base package name
            
            self.console_output.emit(f"📦 Detected package name: {package_name}")
            
            # Run debtap conversion with better error handling
            # Use -Q for quieter mode but still get important output
            cmd = ['debtap', '-Q', deb_filename]
            
            # Set environment to avoid interactive prompts
            env = os.environ.copy()
            env['DEBTAP_NOCOLOR'] = '1'
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,
                env=env
            )
            
            # Provide default answers to common debtap prompts
            default_answers = f"{package_name}\n\n\n"  # Package name, maintainer (empty), license (empty)
            
            try:
                stdout, _ = process.communicate(input=default_answers, timeout=300)  # 5 minute timeout
                
                for line in stdout.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('==>'):  # Filter out some noise
                        self.console_output.emit(line)
                        
            except subprocess.TimeoutExpired:
                process.kill()
                self.console_output.emit("❌ Conversion timed out after 5 minutes")
                return None
            
            os.chdir(original_cwd)
            
            if process.returncode != 0:
                self.console_output.emit(f"❌ debtap failed with return code: {process.returncode}")
                return None
            
            # Find the generated package file
            pkg_files = []
            for file in os.listdir(self.temp_dir):
                if file.endswith('.pkg.tar.zst') or file.endswith('.pkg.tar.xz'):
                    pkg_files.append(file)
            
            if not pkg_files:
                self.console_output.emit("❌ No package file generated")
                # List all files for debugging
                self.console_output.emit("Files in temp directory:")
                for file in os.listdir(self.temp_dir):
                    self.console_output.emit(f"  - {file}")
                return None
            
            # Use the first (and usually only) package file
            pkg_file = pkg_files[0]
            self.console_output.emit(f"✅ Found generated package: {pkg_file}")
            
            return os.path.join(self.temp_dir, pkg_file)
            
        except Exception as e:
            self.console_output.emit(f"Exception during conversion: {str(e)}")
            return None
    
    def install_arch_package(self, package_path):
        """Install the converted Arch package with better prompt handling"""
        try:
            # Use sudo with password
            cmd = ['pacman', '-U', '--noconfirm', '--needed', package_path]
            
            self.console_output.emit(f"🔐 Running: sudo {' '.join(cmd)}")
            
            # Use run_sudo_command method
            process = self.run_sudo_command(cmd)
            if not process:
                self.console_output.emit("❌ Could not start installation process")
                return False
            
            # Read output in real-time
            output_lines = []
            while True:
                line = process.stdout.readline()
                if line:
                    line = line.rstrip()
                    self.console_output.emit(line)
                    output_lines.append(line)
                    
                    # Check for common stuck situations
                    if any(phrase in line.lower() for phrase in [
                        'proceed with installation',
                        'continue?',
                        '[y/n]',
                        'replace',
                        'conflict'
                    ]):
                        # Send 'y' to continue
                        try:
                            process.stdin.write('y\n')
                            process.stdin.flush()
                            self.console_output.emit("→ Automatically answered 'y'")
                        except:
                            pass
                
                # Check if process finished
                if process.poll() is not None:
                    # Read any remaining output
                    remaining = process.stdout.read()
                    if remaining:
                        for line in remaining.split('\n'):
                            if line.strip():
                                self.console_output.emit(line.rstrip())
                                output_lines.append(line)
                    break
            
            return_code = process.wait()
            
            if return_code == 0:
                self.console_output.emit("✅ Package installed successfully!")
                return True
            else:
                self.console_output.emit(f"❌ Installation failed with return code: {return_code}")
                
                # Check for common issues and provide helpful messages
                output_text = '\n'.join(output_lines).lower()
                if 'conflicting files' in output_text:
                    self.console_output.emit("💡 Tip: Package conflicts with existing files")
                elif 'dependency' in output_text:
                    self.console_output.emit("💡 Tip: Missing dependencies - try installing them first")
                elif 'signature' in output_text:
                    self.console_output.emit("💡 Tip: Signature issues - package might be corrupted")
                elif 'disk space' in output_text or 'no space' in output_text:
                    self.console_output.emit("💡 Tip: Insufficient disk space")
                
                return False
                
        except Exception as e:
            self.console_output.emit(f"Exception during installation: {str(e)}")
            return False


class DebInstallerGUI(QMainWindow):
    """Simple installer window for 'Open with' workflow"""
    
    def __init__(self, deb_file_path=None):
        super().__init__()
        self.deb_file_path = deb_file_path
        self.sudo_password = None
        self.worker = None
        self.init_ui()
        
        # Get sudo password first
        QTimer.singleShot(500, self.get_sudo_password)
    
    def init_ui(self):
        """Initialize UI with enhanced progress display and console"""
        self.setWindowTitle("Installing Deb Package" if self.deb_file_path else "Deb Package Installer")
        self.setFixedSize(600, 500)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        
        # Center the window
        self.move(
            QApplication.desktop().screen().rect().center() - self.rect().center()
        )
        
        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Package name
        if self.deb_file_path:
            package_name = os.path.basename(self.deb_file_path)
            file_size_mb = os.path.getsize(self.deb_file_path) / (1024 * 1024)
            
            title = QLabel(f"Installing: {package_name}")
            title.setFont(QFont("Arial", 12, QFont.Bold))
            title.setAlignment(Qt.AlignCenter)
            title.setWordWrap(True)
            layout.addWidget(title)
            
            # File size info
            size_label = QLabel(f"Size: {file_size_mb:.1f} MB")
            size_label.setAlignment(Qt.AlignCenter)
            size_label.setStyleSheet("color: #666; font-size: 10px;")
            layout.addWidget(size_label)
        else:
            title = QLabel("Deb Package Installer")
            title.setFont(QFont("Arial", 12, QFont.Bold))
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)
            
            # File selection button
            self.select_btn = QPushButton("Select .deb Package")
            self.select_btn.setMinimumHeight(35)
            self.select_btn.clicked.connect(self.select_file)
            layout.addWidget(self.select_btn)
        
        # Status label
        self.status_label = QLabel("Preparing installation...")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Time label
        self.time_label = QLabel("")
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(self.time_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Console output area
        console_label = QLabel("Console Output:")
        console_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(console_label)
        
        self.console_text = QTextEdit()
        self.console_text.setReadOnly(True)
        self.console_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Courier New', monospace;
                font-size: 10px;
                border: 1px solid #3e3e3e;
                border-radius: 3px;
            }
        """)
        self.console_text.setMinimumHeight(200)
        layout.addWidget(self.console_text)
        
        # Info label
        info = QLabel("Converting .deb package to Arch format using debtap")
        info.setStyleSheet("color: #666; font-size: 10px;")
        info.setAlignment(Qt.AlignCenter)
        info.setWordWrap(True)
        layout.addWidget(info)
    
    def get_sudo_password(self):
        """Get sudo password from user with proper validation"""
        dialog = SudoPasswordDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.sudo_password = dialog.get_password()
            
            # Validate password with multiple checks
            self.console_text.append("🔐 Validating administrator credentials...")
            
            if not self.sudo_password.strip():
                QMessageBox.critical(self, "Invalid Password", "Password cannot be empty.")
                QTimer.singleShot(500, self.get_sudo_password)
                return
            
            # Test password with a more comprehensive check
            try:
                # Test 1: Basic sudo test
                process = subprocess.Popen(
                    ['sudo', '-S', '-v'],  # -v validates and extends timeout
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                
                stdout, stderr = process.communicate(input=self.sudo_password + '\n')
                
                if process.returncode == 0:
                    self.console_text.append("✅ Password validation successful")
                    
                    # Test 2: Verify we can actually run sudo commands
                    test_process = subprocess.Popen(
                        ['sudo', '-S', 'whoami'],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )
                    
                    test_stdout, test_stderr = test_process.communicate(input=self.sudo_password + '\n')
                    
                    if test_process.returncode == 0 and 'root' in test_stdout:
                        self.console_text.append("✅ Administrator access confirmed")
                        
                        # Continue with original flow
                        if self.deb_file_path:
                            QTimer.singleShot(500, self.confirm_and_install)
                        else:
                            QTimer.singleShot(500, self.select_file)
                    else:
                        self.console_text.append("❌ Failed to execute sudo commands")
                        QMessageBox.critical(self, "Authentication Failed", 
                                           "Password accepted but cannot execute sudo commands.\n"
                                           "Please check your sudo permissions.")
                        QTimer.singleShot(500, self.get_sudo_password)
                else:
                    # Handle different error cases
                    error_msg = stderr.strip() if stderr else "Unknown error"
                    self.console_text.append(f"❌ Authentication failed: {error_msg}")
                    
                    if "incorrect password" in error_msg.lower() or "sorry" in error_msg.lower():
                        QMessageBox.critical(self, "Incorrect Password", 
                                           "The password you entered is incorrect.\nPlease try again.")
                    elif "not in the sudoers file" in error_msg.lower():
                        QMessageBox.critical(self, "Permission Denied", 
                                           "Your user account is not in the sudoers file.\n"
                                           "Please contact your system administrator.")
                        QApplication.quit()
                        return
                    else:
                        QMessageBox.critical(self, "Authentication Failed", 
                                           f"Authentication failed: {error_msg}\nPlease try again.")
                    
                    QTimer.singleShot(500, self.get_sudo_password)
                    
            except Exception as e:
                self.console_text.append(f"❌ Authentication error: {e}")
                QMessageBox.critical(self, "Error", f"Authentication error: {e}\nPlease try again.")
                QTimer.singleShot(500, self.get_sudo_password)
        else:
            QMessageBox.information(self, "Access Required", 
                                  "Administrator access is required to install packages.")
            QApplication.quit()
    
    def select_file(self):
        """Select .deb file to install"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Debian Package",
            os.path.expanduser("~/Downloads"),
            "Debian Packages (*.deb);;All Files (*)"
        )
        
        if file_path and file_path.endswith('.deb'):
            self.deb_file_path = file_path
            
            # Update UI with selected file
            package_name = os.path.basename(file_path)
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            
            # Update title
            self.setWindowTitle(f"Installing: {package_name}")
            
            # Hide select button and show file info
            if hasattr(self, 'select_btn'):
                self.select_btn.setVisible(False)
            
            self.console_text.append(f"📦 Selected: {package_name} ({file_size_mb:.1f} MB)\n")
            
            # Start installation
            QTimer.singleShot(500, self.confirm_and_install)
        elif not file_path:
            # User cancelled
            QApplication.quit()
        else:
            QMessageBox.warning(self, "Invalid File", "Please select a .deb package file.")
            QTimer.singleShot(500, self.select_file)
    
    def confirm_and_install(self):
        """Show confirmation and start installation"""
        if not self.deb_file_path:
            return
            
        package_name = os.path.basename(self.deb_file_path)
        
        reply = QMessageBox.question(
            self, "Install Package",
            f"Install {package_name}?\n\n"
            "This will:\n"
            "• Check/install debtap if needed\n"
            "• Convert the .deb package using debtap\n"
            "• Install the converted package\n\n"
            "Note: You'll be prompted for sudo password",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.start_installation()
        else:
            QApplication.quit()
    
    def start_installation(self):
        """Start the installation process"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.console_text.append("🚀 Starting installation process...\n")
        
        # Start worker thread with sudo password
        self.worker = InstallWorker(self.deb_file_path, self.sudo_password)
        self.worker.progress_update.connect(self.update_status)
        self.worker.progress_value.connect(self.update_progress)
        self.worker.time_update.connect(self.update_time)
        self.worker.console_output.connect(self.update_console)
        self.worker.finished.connect(self.installation_finished)
        self.worker.start()
    
    def update_status(self, message):
        """Update status label"""
        self.status_label.setText(message)
    
    def update_progress(self, value):
        """Update progress bar"""
        self.progress_bar.setValue(value)
    
    def update_time(self, message):
        """Update time label"""
        self.time_label.setText(message)
    
    def update_console(self, message):
        """Update console output"""
        self.console_text.append(message)
        # Auto-scroll to bottom
        scrollbar = self.console_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def installation_finished(self, success, message):
        """Handle installation completion"""
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)
        
        # Close application
        QApplication.quit()


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Deb Package Installer")
    
    # Check if .deb file was provided
    deb_file = None
    if len(sys.argv) > 1 and sys.argv[1].endswith('.deb'):
        deb_file = sys.argv[1]
        if not os.path.exists(deb_file):
            QMessageBox.critical(None, "Error", f"File not found: {deb_file}")
            sys.exit(1)
    
    # Check if running on Arch Linux
    try:
        with open('/etc/os-release', 'r') as f:
            os_info = f.read()
            if 'arch' not in os_info.lower():
                reply = QMessageBox.question(None, "Warning", 
                                           "This application is designed for Arch Linux.\n"
                                           "Continue anyway?",
                                           QMessageBox.Yes | QMessageBox.No,
                                           QMessageBox.No)
                if reply != QMessageBox.Yes:
                    sys.exit(1)
    except:
        pass
    
    window = DebInstallerGUI(deb_file)
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()