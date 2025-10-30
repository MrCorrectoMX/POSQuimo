# buscar_sqlite_en_presentaciones.py
import os
import re

def buscar_conexiones_sqlite():
    """Buscar conexiones SQLite específicas en el código de presentaciones"""
    print("🔍 BUSCANDO CONEXIONES SQLITE EN CÓDIGO DE PRESENTACIONES")
    print("=" * 60)
    
    problemas_encontrados = []
    
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    contenido = f.read()
                    
                    # Buscar patrones que indiquen conexión a SQLite
                    patrones = [
                        r'sqlite3\.connect',
                        r'sqlite:///',
                        r'create_engine.*sqlite',
                        r'\.db["\']',
                        r'quimo\.db'
                    ]
                    
                    for patron in patrones:
                        if re.search(patron, contenido, re.IGNORECASE):
                            lineas = contenido.split('\n')
                            for num_linea, linea in enumerate(lineas, 1):
                                if re.search(patron, linea, re.IGNORECASE):
                                    problemas_encontrados.append({
                                        'archivo': filepath,
                                        'linea': num_linea,
                                        'codigo': linea.strip(),
                                        'patron': patron
                                    })
    
    if problemas_encontrados:
        print("❌ SE ENCONTRARON CONEXIONES SQLITE:")
        for problema in problemas_encontrados:
            print(f"\n📄 Archivo: {problema['archivo']}")
            print(f"📍 Línea {problema['linea']}: {problema['codigo']}")
            print(f"🔍 Patrón: {problema['patron']}")
    else:
        print("✅ No se encontraron conexiones SQLite explícitas")
    
    return problemas_encontrados

def buscar_funciones_presentaciones():
    """Buscar funciones específicas de presentaciones"""
    print("\n🔍 BUSCANDO FUNCIONES DE PRESENTACIONES")
    print("=" * 60)
    
    funciones_presentaciones = []
    
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    contenido = f.read()
                    
                    # Buscar funciones relacionadas con presentaciones
                    if 'presentacion' in contenido.lower():
                        lineas = contenido.split('\n')
                        for i, linea in enumerate(lineas):
                            if 'def ' in linea and 'presentacion' in linea.lower():
                                # Encontrar el nombre de la función
                                match = re.search(r'def (\w+.*presentacion\w*)', linea, re.IGNORECASE)
                                if match:
                                    nombre_funcion = match.group(1)
                                    funciones_presentaciones.append({
                                        'archivo': filepath,
                                        'funcion': nombre_funcion,
                                        'linea': i + 1
                                    })
    
    print("📋 Funciones de presentaciones encontradas:")
    for func in funciones_presentaciones:
        print(f"   - {func['funcion']} (en {func['archivo']}:{func['linea']})")
    
    return funciones_presentaciones

if __name__ == "__main__":
    conexiones = buscar_conexiones_sqlite()
    funciones = buscar_funciones_presentaciones()
    
    print(f"\n📊 RESUMEN:")
    print(f"   Conexiones SQLite encontradas: {len(conexiones)}")
    print(f"   Funciones de presentaciones: {len(funciones)}")