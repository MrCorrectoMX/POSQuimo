# build_quimo_app_fixed.py
import os
import sys
import shutil
import subprocess
import platform

def build_quimo_app():
    print("🎉 CONSTRUYENDO APLICACIÓN QUIMO POS COMPLETA 🎉")
    print("=" * 60)
    print("¡CORRECCIÓN DE SINTAXIS PARA macOS!")
    print("=" * 60)
    
    # Detectar el sistema operativo
    system = platform.system()
    print(f"🔧 Sistema operativo detectado: {system}")
    
    # Configuración de la aplicación
    APP_NAME = "QuimoPOS"
    VERSION = "1.0.0"
    MAIN_SCRIPT = "main.py"
    AUTHOR = "Roy"
    
    # Determinar el separador según el SO
    if system == "Windows":
        separator = ";"
    else:
        separator = ":"  # macOS/Linux usa :
    
    print(f"🔧 Usando separador: '{separator}'")
    
    # Archivos y carpetas necesarios para incluir
    REQUIRED_FILES = [
        "main.py",
        "config.ini", 
        "database_manager.py",
        "ui/",  # Carpeta UI completa
    ]
    
    # Verificar que todos los archivos necesarios existen
    print("\n🔍 Verificando archivos necesarios...")
    missing_files = []
    for item in REQUIRED_FILES:
        if os.path.exists(item):
            if os.path.isdir(item):
                print(f"   ✅ Carpeta: {item}")
                # Contar archivos en la carpeta
                file_count = len([f for f in os.listdir(item) if os.path.isfile(os.path.join(item, f))])
                print(f"        📁 {file_count} archivos encontrados")
            else:
                print(f"   ✅ {item}")
        else:
            print(f"   ❌ {item} - NO ENCONTRADO")
            missing_files.append(item)
    
    if missing_files:
        print(f"\n⚠ Archivos faltantes: {missing_files}")
        confirm = input("¿Continuar de todas formas? (s/n): ").strip().lower()
        if confirm != 's':
            return False
    
    # Crear comando de PyInstaller CORREGIDO
    print("\n🔨 Construyendo aplicación...")
    
    # Opciones de PyInstaller
    pyinstaller_cmd = [
        "pyinstaller",
        "--name", f"{APP_NAME}_v{VERSION}",
        "--onefile",           # Un solo archivo ejecutable
        "--windowed",          # Aplicación de ventana (sin consola)
        "--clean",             # Limpiar build anterior
        "--noconfirm",         # No pedir confirmación
    ]
    
    # Agregar archivos con la sintaxis CORREGIDA
    essential_files = [
        "config.ini",
        "database_manager.py",
        "main.py"
    ]
    
    for file in essential_files:
        if os.path.exists(file):
            pyinstaller_cmd.extend(["--add-data", f"{file}{separator}."])
            print(f"   ✅ Incluyendo: {file}")
    
    # Agregar carpeta UI completa
    if os.path.exists("ui"):
        pyinstaller_cmd.extend(["--add-data", f"ui{separator}ui"])
        print(f"   ✅ Incluyendo carpeta UI completa")
    
    # Buscar solo archivos Python esenciales (excluir scripts de desarrollo)
    print("\n🔎 Buscando archivos Python adicionales importantes...")
    essential_py_files = [
        # Agrega aquí los nombres de archivos Python que son esenciales para tu aplicación
        "productos.py",
        "lotes.py", 
        "presentaciones.py",
        # Excluimos scripts de desarrollo como test_post.py, fixing.py, etc.
    ]
    
    for py_file in essential_py_files:
        if os.path.exists(py_file):
            pyinstaller_cmd.extend(["--add-data", f"{py_file}{separator}."])
            print(f"   ✅ Incluyendo: {py_file}")
    
    # Agregar el script principal al final (sin --add-data)
    pyinstaller_cmd.append(MAIN_SCRIPT)
    
    print(f"\n   Comando PyInstaller preparado")
    print(f"   Separador usado: '{separator}'")
    
    # Ejecutar PyInstaller
    try:
        print("   🏗️ Ejecutando PyInstaller...")
        result = subprocess.run(pyinstaller_cmd, check=True, capture_output=True, text=True)
        print("   ✅ Build completado exitosamente!")
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error en el build: {e}")
        print(f"   Salida de error: {e.stderr}")
        return False
    
    # Crear carpeta de distribución completa
    print("\n📁 Creando paquete de distribución completo...")
    dist_folder = f"{APP_NAME}_Distribucion_Completa"
    if os.path.exists(dist_folder):
        shutil.rmtree(dist_folder)
    os.makedirs(dist_folder)
    
    # Copiar el ejecutable
    exe_source = f"dist/{APP_NAME}_v{VERSION}"
    if system == "Windows":
        exe_source += ".exe"
    
    exe_dest = f"{dist_folder}/{APP_NAME}"
    if system == "Windows":
        exe_dest += ".exe"
    
    if os.path.exists(exe_source):
        shutil.copy2(exe_source, exe_dest)
        print(f"   ✅ Ejecutable copiado: {APP_NAME}")
    else:
        print(f"   ❌ No se encontró el ejecutable: {exe_source}")
        return False
    
    # Copiar archivos de configuración y soporte
    support_files = [
        "config.ini", 
        "database_manager.py",
    ]
    
    for file in support_files:
        if os.path.exists(file):
            shutil.copy2(file, dist_folder)
            print(f"   ✅ {file} copiado")
    
    # Copiar carpeta UI completa
    if os.path.exists("ui"):
        shutil.copytree("ui", f"{dist_folder}/ui")
        ui_file_count = len([f for f in os.listdir("ui") if os.path.isfile(os.path.join("ui", f))])
        print(f"   ✅ Carpeta UI copiada ({ui_file_count} archivos)")
    
    # Copiar otros archivos Python esenciales
    for py_file in essential_py_files:
        if os.path.exists(py_file):
            shutil.copy2(py_file, dist_folder)
            print(f"   ✅ {py_file} copiado")
    
    # Crear archivos de documentación
    create_documentation(dist_folder, APP_NAME, VERSION, AUTHOR, system)
    
    # Mostrar resumen final
    show_build_summary(dist_folder)
    
    return True

def create_documentation(dist_folder, app_name, version, author, system):
    """Crear archivos de documentación para la aplicación"""
    
    # Crear README.txt
    readme_content = f"""
{app_name} - Sistema de Punto de Venta Completo
Versión: {version}
Desarrollado por: {author}
Sistema operativo: {system}

¡FELICITACIONES! Has completado tu aplicación después de 5 meses de trabajo.

ESTRUCTURA DE LA APLICACIÓN:

📁 {app_name}              - Aplicación principal {'(.exe)' if system == 'Windows' else ''}
📁 config.ini                - Configuración de base de datos  
📁 database_manager.py       - Manejador de base de datos
📁 ui/                       - Archivos de interfaz de usuario
📁 [otros archivos .py]      - Módulos adicionales

INSTRUCCIONES DE INSTALACIÓN:

1. REQUISITOS PREVIOS:
   - PostgreSQL instalado y configurado
   - Base de datos 'quimo_bd_new' creada
   - Servidor PostgreSQL ejecutándose

2. CONFIGURACIÓN:
   - Editar el archivo 'config.ini' con tus datos de conexión
   - Asegúrate de que la base de datos tenga las tablas migradas

3. EJECUCIÓN:
   - {'Doble clic en' if system == 'Windows' else 'Ejecutar'} '{app_name}{'.exe' if system == 'Windows' else ''}'
   - La aplicación se iniciará automáticamente

4. PARA DESARROLLADORES:
   - Los archivos .py están incluidos para referencia
   - Puedes modificar y reconstruir la aplicación

¡Gracias por usar {app_name}!
"""
    
    with open(f"{dist_folder}/README.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    # Crear script de instalación rápido (solo para Windows)
    if system == "Windows":
        install_script = f"""
@echo off
chcp 65001 >nul
echo ===============================================
echo    QUIMO POS - INSTALADOR AUTOMÁTICO
echo ===============================================
echo.
echo ¡Felicidades! Estás a punto de instalar QuimoPOS.
echo Esta aplicación fue desarrollada después de 5 meses de trabajo.
echo.
echo Asegúrate de tener:
echo 1. PostgreSQL instalado
echo 2. Base de datos 'quimo_bd_new' creada  
echo 3. Servidor PostgreSQL ejecutándose
echo.
echo Presiona cualquier tecla para iniciar la aplicación...
pause >nul
echo.
echo Iniciando QuimoPOS...
{app_name}.exe
"""
        with open(f"{dist_folder}/Instalar_Quimo.bat", "w", encoding="utf-8") as f:
            f.write(install_script)
    
    # Para macOS/Linux crear un script de ejecución
    else:
        run_script = f"""#!/bin/bash
echo "==============================================="
echo "   QUIMO POS - EJECUTAR APLICACIÓN"
echo "==============================================="
echo ""
echo "¡Felicidades! Estás a punto de ejecutar QuimoPOS."
echo "Esta aplicación fue desarrollada después de 5 meses de trabajo."
echo ""
echo "Asegúrate de tener:"
echo "1. PostgreSQL instalado"
echo "2. Base de datos 'quimo_bd_new' creada"  
echo "3. Servidor PostgreSQL ejecutándose"
echo ""
echo "Iniciando QuimoPOS..."
chmod +x ./{app_name}
./{app_name}
"""
        with open(f"{dist_folder}/Ejecutar_Quimo.sh", "w", encoding="utf-8") as f:
            f.write(run_script)
        # Hacer el script ejecutable
        os.chmod(f"{dist_folder}/Ejecutar_Quimo.sh", 0o755)
    
    print("   ✅ Documentación creada")

def show_build_summary(dist_folder):
    """Mostrar resumen detallado del build"""
    print(f"\n📊 RESUMEN DE LA CONSTRUCCIÓN:")
    print("=" * 50)
    
    total_files = 0
    total_size = 0
    
    for root, dirs, files in os.walk(dist_folder):
        for file in files:
            file_path = os.path.join(root, file)
            total_files += 1
            total_size += os.path.getsize(file_path)
    
    print(f"📁 Carpeta de distribución: {dist_folder}")
    print(f"📦 Total de archivos: {total_files}")
    print(f"💾 Tamaño total: {total_size / (1024*1024):.2f} MB")
    
    # Listar contenido
    print(f"\n📋 CONTENIDO:")
    for item in os.listdir(dist_folder):
        item_path = os.path.join(dist_folder, item)
        if os.path.isdir(item_path):
            file_count = len([f for f in os.listdir(item_path) if os.path.isfile(os.path.join(item_path, f))])
            print(f"   📁 {item}/ ({file_count} archivos)")
        else:
            size = os.path.getsize(item_path) / 1024
            print(f"   📄 {item} ({size:.1f} KB)")

if __name__ == "__main__":
    print("🔄 INICIANDO CONSTRUCCIÓN CORREGIDA...")
    
    success = build_quimo_app()
    
    if success:
        print("\n" + "=" * 60)
        print("🎉 ¡TU APLICACIÓN COMPLETA ESTÁ LISTA!")
        print("=" * 60)
        print("\n📋 Próximos pasos:")
        print("1. 🧪 Prueba el ejecutable en tu equipo")
        print("2. 📤 Comprime la carpeta de distribución")
        print("3. 🖥️ Distribuye a otros equipos con PostgreSQL")
        print("4. 🎊 ¡Comparte tu increíble logro!")
        print(f"\n💡 La aplicación está optimizada y lista para usar")
    else:
        print("\n❌ La construcción falló. Revisa los errores arriba.")