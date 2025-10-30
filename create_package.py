# create_package.py
import os
import sys
import shutil
import platform

def create_package(artifact_name, binary_name):
    """Crear paquete de distribución completo"""
    print(f"📦 Creating distribution package: {artifact_name}")
    
    # Crear carpeta de distribución
    if os.path.exists(artifact_name):
        shutil.rmtree(artifact_name)
    os.makedirs(artifact_name)
    
    # Copiar el ejecutable
    exe_source = f"dist/{binary_name}"
    if os.path.exists(exe_source):
        shutil.copy2(exe_source, f"{artifact_name}/{binary_name}")
        print(f"✅ {binary_name} copied")
    else:
        print(f"❌ Executable not found: {exe_source}")
        return False
    
    # Copiar archivos esenciales
    essential_files = [
        "config.ini",
        "database_manager.py", 
        "productos.py",
        "lotes.py",
        "presentaciones.py"
    ]
    
    for file in essential_files:
        if os.path.exists(file):
            shutil.copy2(file, f"{artifact_name}/{file}")
            print(f"✅ {file} copied")
    
    # Copiar carpeta UI
    if os.path.exists("ui"):
        shutil.copytree("ui", f"{artifact_name}/ui")
        ui_count = len([f for f in os.listdir("ui") if os.path.isfile(os.path.join("ui", f))])
        print(f"✅ ui/ folder copied ({ui_count} files)")
    
    # Crear scripts de instalación según la plataforma
    create_installation_scripts(artifact_name, binary_name)
    
    # Crear documentación
    create_documentation(artifact_name, platform.system())
    
    print(f"🎉 Package {artifact_name} created successfully!")
    return True

def create_installation_scripts(artifact_name, binary_name):
    """Crear scripts de instalación específicos para cada plataforma"""
    system = platform.system().lower()
    
    if system == "windows":
        # Script batch para Windows
        bat_content = f"""@echo off
chcp 65001 >nul
echo ===============================================
echo    QuimoPOS - Auto Installer
echo ===============================================
echo.
echo This will install and run QuimoPOS on your system.
echo.
echo System: Windows
echo Executable: {binary_name}
echo.
echo Make sure you have:
echo - PostgreSQL installed and running
echo - Database 'quimo_bd_new' created
echo.
echo Press any key to continue...
pause >nul
echo.
echo Starting QuimoPOS...
{binary_name}
"""
        with open(f"{artifact_name}/Install_QuimoPOS.bat", "w", encoding="utf-8") as f:
            f.write(bat_content)
        print("✅ Install_QuimoPOS.bat created")
        
    else:
        # Script shell para Linux/macOS
        sh_content = f"""#!/bin/bash
echo "==============================================="
echo "   QuimoPOS - Auto Installer"
echo "==============================================="
echo ""
echo "This will install and run QuimoPOS on your system."
echo ""
echo "System: {platform.system()}"
echo "Executable: {binary_name}"
echo ""
echo "Make sure you have:"
echo "- PostgreSQL installed and running" 
echo "- Database 'quimo_bd_new' created"
echo ""
echo "Making executable executable..."
chmod +x ./{binary_name}
echo ""
echo "Starting QuimoPOS..."
./{binary_name}
"""
        with open(f"{artifact_name}/Install_QuimoPOS.sh", "w") as f:
            f.write(sh_content)
        # Hacer ejecutable
        os.chmod(f"{artifact_name}/Install_QuimoPOS.sh", 0o755)
        print("✅ Install_QuimoPOS.sh created")

def create_documentation(artifact_name, system):
    """Crear documentación del paquete"""
    doc_content = f"""QuimoPOS - Point of Sale System
===============================

Package: {artifact_name}
System: {system}
Build Date: {os.popen('date').read().strip()}

INSTRUCTIONS:
1. Ensure PostgreSQL is installed and running
2. Create database 'quimo_bd_new'
3. Edit config.ini with your PostgreSQL credentials
4. Run the installation script:
   - Windows: Double-click Install_QuimoPOS.bat
   - Linux/macOS: Run ./Install_QuimoPOS.sh

FILES INCLUDED:
- {artifact_name}/{binary_name if 'binary_name' in locals() else 'Executable'}: Main application
- config.ini: Database configuration
- database_manager.py: Database handler
- ui/: User interface files
- productos.py, lotes.py, presentaciones.py: Application modules

SUPPORT:
For issues with the application, check:
1. PostgreSQL connection in config.ini
2. Database exists and is accessible
3. All required files are present

Thank you for using QuimoPOS!
"""
    
    with open(f"{artifact_name}/README.txt", "w", encoding="utf-8") as f:
        f.write(doc_content)
    print("✅ README.txt created")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python create_package.py <artifact_name> <binary_name>")
        sys.exit(1)
    
    artifact_name = sys.argv[1]
    binary_name = sys.argv[2]
    create_package(artifact_name, binary_name)