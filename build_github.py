# build_github.py
import os
import sys
import platform
import subprocess

def build_for_github():
    """Script de construcción optimizado para GitHub Actions"""
    print(f"🏗️ Building QuimoPOS for {platform.system()} on GitHub Actions")
    
    # Configuración
    app_name = "QuimoPOS"
    system = platform.system().lower()
    
    # Determinar separador según el SO
    separator = ";" if system == "windows" else ":"
    
    # Archivos esenciales (verificar existencia)
    essential_files = [
        "main.py",
        "config.ini", 
        "database_manager.py",
        "ui/",
        "productos.py",
        "lotes.py",
        "presentaciones.py"
    ]
    
    print("🔍 Verifying essential files...")
    for item in essential_files:
        if os.path.exists(item):
            if os.path.isdir(item):
                file_count = len([f for f in os.listdir(item) if os.path.isfile(os.path.join(item, f))])
                print(f"   ✅ {item} ({file_count} files)")
            else:
                print(f"   ✅ {item}")
        else:
            print(f"   ⚠ {item} not found - this might cause issues")
    
    # Comando PyInstaller optimizado para CI
    cmd = [
        "pyinstaller",
        "--name", app_name,
        "--onefile",
        "--windowed" if system == "windows" else "--noconsole",
        "--clean",
        "--noconfirm",
        f"--add-data=config.ini{separator}.",
        f"--add-data=database_manager.py{separator}.",
        f"--add-data=ui{separator}ui",
        f"--add-data=productos.py{separator}.",
        f"--add-data=lotes.py{separator}.",
        f"--add-data=presentaciones.py{separator}.",
        "--hidden-import", "pg8000",
        "--hidden-import", "psycopg2",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL._tkinter_finder",
        "--hidden-import", "pkg_resources.py2_warn",
        "main.py"
    ]
    
    print("🚀 Running PyInstaller...")
    try:
        # Ejecutar con timeout de 10 minutos
        result = subprocess.run(cmd, check=True, timeout=600)
        print("✅ Build completed successfully!")
        return True
    except subprocess.TimeoutExpired:
        print("❌ Build timed out after 10 minutes")
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed with error: {e}")
        return False

if __name__ == "__main__":
    success = build_for_github()
    sys.exit(0 if success else 1)