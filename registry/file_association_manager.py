import os
import sys
import ctypes
import winreg
import subprocess

class FileAssociationManager:
    def __init__(self):
        self.file_extension = ".node"
        self.prog_id = "NodeFile"
        self.description = "Node Archive File"
        self.addon_dir = os.path.dirname(os.path.dirname(__file__))
        self.icon_path = os.path.join(self.addon_dir, "icons", "logo_xwz_ne.ico")
        
    def find_archive_application(self):
        print("[DEBUG] Searching for archive applications...")
        
        seven_zip_paths = [
            r"C:\Program Files\7-Zip\7zFM.exe",
            r"C:\Program Files (x86)\7-Zip\7zFM.exe"
        ]
        
        for path in seven_zip_paths:
            if os.path.exists(path):
                print(f"[DEBUG] Found 7-Zip at: {path}")
                return path
        
        try:
            result = subprocess.run(["where", "7zFM.exe"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                seven_zip_path = result.stdout.strip().split('\n')[0]
                print(f"[DEBUG] Found 7-Zip in PATH at: {seven_zip_path}")
                return seven_zip_path
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
            pass
        
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\7-Zip") as key:
                install_path, _ = winreg.QueryValueEx(key, "Path")
                seven_zip_exe = os.path.join(install_path, "7zFM.exe")
                if os.path.exists(seven_zip_exe):
                    print(f"[DEBUG] Found 7-Zip via registry at: {seven_zip_exe}")
                    return seven_zip_exe
        except (FileNotFoundError, OSError):
            pass
        
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\7-Zip", access=winreg.KEY_READ | winreg.KEY_WOW64_32KEY) as key:
                install_path, _ = winreg.QueryValueEx(key, "Path")
                seven_zip_exe = os.path.join(install_path, "7zFM.exe")
                if os.path.exists(seven_zip_exe):
                    print(f"[DEBUG] Found 7-Zip via 32-bit registry at: {seven_zip_exe}")
                    return seven_zip_exe
        except (FileNotFoundError, OSError):
            pass
        
        winrar_paths = [
            r"C:\Program Files\WinRAR\WinRAR.exe",
            r"C:\Program Files (x86)\WinRAR\WinRAR.exe"
        ]
        
        for path in winrar_paths:
            if os.path.exists(path):
                print(f"[DEBUG] Found WinRAR at: {path}")
                return path
        
        print("[DEBUG] No dedicated archive application found, using Windows default handling")
        return "rundll32.exe shell32.dll,OpenAs_RunDLL"
    
    def check_existing_association(self):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{self.file_extension}") as key:
                existing_prog_id = winreg.QueryValue(key, "")
                return existing_prog_id
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"Error checking existing association: {e}")
            return None
    
    def validate_icon_path(self):
        if not os.path.exists(self.icon_path):
            return False, f"Icon file not found: {self.icon_path}"
        
        if not os.access(self.icon_path, os.R_OK):
            return False, f"Icon file not readable: {self.icon_path}"
            
        return True, "Icon file is valid"
    
    def create_command_string(self, archive_app):
        if "7z" in archive_app.lower():
            return f'"{archive_app}" "%1"'
        elif "winrar" in archive_app.lower():
            return f'"{archive_app}" "%1"'
        elif "rundll32" in archive_app.lower():
            return f'{archive_app} "%1"'
        else:
            return f'"{archive_app}" "%1"'
    
    def perform_file_association(self):
        print("=" * 60)
        print("[DEBUG] STARTING FILE ASSOCIATION REGISTRATION")
        print("=" * 60)
        
        try:
            archive_app = self.find_archive_application()
            print(f"[DEBUG] Selected archive application: {archive_app}")
            
            command = self.create_command_string(archive_app)
            
            print(f"[DEBUG] File extension: {self.file_extension}")
            print(f"[DEBUG] Addon directory: {self.addon_dir}")
            print(f"[DEBUG] Icon path: {self.icon_path}")
            print(f"[DEBUG] Icon path absolute: {os.path.abspath(self.icon_path)}")
            print(f"[DEBUG] Icon exists: {os.path.exists(self.icon_path)}")
            print(f"[DEBUG] ProgID: {self.prog_id}")
            print(f"[DEBUG] Command: {command}")
            print(f"[DEBUG] Current working directory: {os.getcwd()}")
            
            icons_dir = os.path.join(self.addon_dir, "icons")
            print(f"[DEBUG] Icons directory: {icons_dir}")
            print(f"[DEBUG] Icons directory exists: {os.path.exists(icons_dir)}")
            if os.path.exists(icons_dir):
                print(f"[DEBUG] Icons directory contents: {os.listdir(icons_dir)}")
            
            # Validate icon file
            is_valid, message = self.validate_icon_path()
            if not is_valid:
                print(f"[DEBUG] ERROR: {message}")
                return False
                
            print(f"[DEBUG] Icon file validation: PASSED")
            
            # Check if association already exists
            existing_prog_id = self.check_existing_association()
            self._log_existing_association(existing_prog_id)
            
            # Create the registry keys
            success = self._create_registry_entries(command)
            if not success:
                return False
            
            # Verify the registration
            self._verify_registration()
            
            # Notify Windows about the change
            self._notify_windows_of_changes()
            
            print("=" * 60)
            print("[DEBUG] REGISTRATION COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print(f"[DEBUG] Archive application used: {archive_app}")
            print(f"[DEBUG] To test:")
            print(f"[DEBUG] 1. Create a test file with .node extension")
            print(f"[DEBUG] 2. Double-click it in Windows Explorer")
            print(f"[DEBUG] 3. It should open with {archive_app}")
            print(f"[DEBUG] 4. Check if it shows the custom icon")
            print(f"[DEBUG] 5. Look in registry at HKEY_CURRENT_USER\\Software\\Classes\\.node")
            print(f"[DEBUG] 6. Look in registry at HKEY_CURRENT_USER\\Software\\Classes\\NodeFile")
            print("=" * 60)

            return True
            
        except PermissionError:
            error_msg = "Permission denied. Please run Blender as administrator to register file associations."
            print(f"[DEBUG] ERROR: {error_msg}")
            return False
        except Exception as e:
            error_msg = f"Failed to register file association: {str(e)}"
            print(f"[DEBUG] ERROR: {error_msg}")
            return False
    
    def _log_existing_association(self, existing_prog_id):
        print(f"[DEBUG] Checking existing association...")
        
        if existing_prog_id == self.prog_id:
            print(f"[DEBUG] Association already exists with our ProgID: {self.prog_id}")
            print(f"[DEBUG] But we'll update it anyway to ensure latest configuration...")
            
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{self.prog_id}") as key:
                    try:
                        with winreg.OpenKey(key, "DefaultIcon") as icon_key:
                            current_icon, _ = winreg.QueryValueEx(icon_key, "")
                            print(f"[DEBUG] Current icon in registry: {current_icon}")
                    except FileNotFoundError:
                        print(f"[DEBUG] No DefaultIcon key found - will create it")
                        
            except Exception as e:
                print(f"[DEBUG] Error checking existing ProgID: {e}")
        elif existing_prog_id:
            print(f"[DEBUG] Association exists with different ProgID: {existing_prog_id} - will overwrite")
        else:
            print(f"[DEBUG] No existing association found - creating new one")
    
    def _create_registry_entries(self, command):
        try:
            print(f"[DEBUG] Creating/updating registry entries...")
            print(f"[DEBUG] Using HKEY_CURRENT_USER\\Software\\Classes (no admin required)")
            
            print(f"[DEBUG] Step 1: Creating file extension key")
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{self.file_extension}") as key:
                winreg.SetValue(key, "", winreg.REG_SZ, self.prog_id)
                print(f"[DEBUG] ✓ Set {self.file_extension} -> {self.prog_id}")
            
            print(f"[DEBUG] Step 2: Creating ProgID key")
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{self.prog_id}") as key:
                winreg.SetValue(key, "", winreg.REG_SZ, self.description)
                print(f"[DEBUG] ✓ Set {self.prog_id} description to '{self.description}'")
                
                # Create DefaultIcon subkey (NOT value!)
                print(f"[DEBUG] Step 3: Creating DefaultIcon subkey")
                abs_icon_path = os.path.abspath(self.icon_path)
                with winreg.CreateKey(key, "DefaultIcon") as icon_key:
                    winreg.SetValue(icon_key, "", winreg.REG_SZ, abs_icon_path)
                    print(f"[DEBUG] ✓ Set DefaultIcon to: {abs_icon_path}")
                
                print(f"[DEBUG] Step 4: Creating shell\\open\\command subkey")
                with winreg.CreateKey(key, "shell\\open\\command") as subkey:
                    winreg.SetValue(subkey, "", winreg.REG_SZ, command)
                    print(f"[DEBUG] ✓ Set command to: {command}")
            
            return True
            
        except Exception as e:
            print(f"[DEBUG] Error creating registry entries: {e}")
            return False
    
    def _verify_registration(self):
        print(f"[DEBUG] Step 5: Verifying registration...")
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{self.file_extension}") as key:
                verify_prog_id, _ = winreg.QueryValueEx(key, "")
                print(f"[DEBUG] ✓ Extension verification: {self.file_extension} -> {verify_prog_id}")
            
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{self.prog_id}") as key:
                verify_desc, _ = winreg.QueryValueEx(key, "")
                print(f"[DEBUG] ✓ ProgID verification: {self.prog_id} -> {verify_desc}")
                
                with winreg.OpenKey(key, "DefaultIcon") as icon_key:
                    verify_icon, _ = winreg.QueryValueEx(icon_key, "")
                    print(f"[DEBUG] ✓ Icon verification: {verify_icon}")
                
                with winreg.OpenKey(key, "shell\\open\\command") as cmd_key:
                    verify_cmd, _ = winreg.QueryValueEx(cmd_key, "")
                    print(f"[DEBUG] ✓ Command verification: {verify_cmd}")
                    
        except Exception as e:
            print(f"[DEBUG] ⚠ Verification failed: {e}")
    
    def _notify_windows_of_changes(self):
        print(f"[DEBUG] Step 6: Notifying Windows of changes...")
        try:
            print(f"[DEBUG] Sending SHCNE_ASSOCCHANGED notification...")
            ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)  # SHCNE_ASSOCCHANGED
            
            print(f"[DEBUG] Sending SHCNE_UPDATEIMAGE notification...")
            ctypes.windll.shell32.SHChangeNotify(0x00008000, 0x0000, None, None)  # SHCNE_UPDATEIMAGE
            
            print(f"[DEBUG] Sending additional refresh notifications...")
            ctypes.windll.shell32.SHChangeNotify(0x00002000, 0x0000, None, None)  # SHCNE_UPDATEDIR
            
            print(f"[DEBUG] ✓ Sent multiple Windows notifications for icon refresh")
            
            print(f"[DEBUG] IMPORTANT: If icons don't update immediately, try:")
            print(f"[DEBUG] 1. Press F5 in File Explorer to refresh")
            print(f"[DEBUG] 2. Change folder view size (View > Icons > Medium/Large/Extra Large)")
            print(f"[DEBUG] 3. Navigate away and back to the folder")
            print(f"[DEBUG] 4. If still not working, manually refresh icon cache:")
            print(f"[DEBUG]    - Open Command Prompt as Administrator")
            print(f"[DEBUG]    - Run: taskkill /f /im explorer.exe")
            print(f"[DEBUG]    - Run: del /a %userprofile%\\AppData\\Local\\IconCache.db")
            print(f"[DEBUG]    - Run: del /a %userprofile%\\AppData\\Local\\Microsoft\\Windows\\Explorer\\iconcache_*.db")
            print(f"[DEBUG]    - Run: start explorer.exe")
            
        except Exception as e:
            print(f"[DEBUG] ⚠ Failed to send some notifications: {e}")
