# migrate_quimo_to_postgres.py
import sqlite3
import psycopg2
from psycopg2 import sql
import sys

# ==========================================
# CONFIGURACIÓN
# ==========================================

SQLITE_DB_PATH = "quimo.db"  # Ruta a tu archivo SQLite

POSTGRES_CONFIG = {
    "host": "192.168.1.24",  # Reemplaza con la IP real
    "port": 5432,
    "database": "quimo_db",
    "user": "quimo_user",
    "password": "1234"  # Déjalo vacío si no usaste contraseña
}

# ==========================================
# MAPEO DE TIPOS ESPECÍFICO PARA QUIMO
# ==========================================

def map_sqlite_to_postgres_type(sqlite_type, is_primary_key=False):
    """Mapeo mejorado de tipos SQLite a PostgreSQL"""
    sqlite_type = str(sqlite_type).upper()
    
    # Manejar tipos compuestos
    if 'INTEGER' in sqlite_type and is_primary_key:
        return "SERIAL PRIMARY KEY"
    elif 'INTEGER' in sqlite_type:
        return "INTEGER"
    elif 'TEXT' in sqlite_type:
        return "TEXT"
    elif 'REAL' in sqlite_type or 'FLOAT' in sqlite_type or 'DOUBLE' in sqlite_type:
        return "REAL"
    elif 'DATETIME' in sqlite_type:
        return "TIMESTAMP"
    elif 'DATE' in sqlite_type:
        return "DATE"
    elif 'BOOLEAN' in sqlite_type or 'BOOL' in sqlite_type:
        return "BOOLEAN"
    else:
        return "TEXT"

# ==========================================
# ORDEN DE MIGRACIÓN (PARA EVITAR PROBLEMAS DE FK)
# ==========================================

MIGRATION_ORDER = [
    # Tablas base sin dependencias
    'proveedor',
    'clientes',
    'envases_etiquetas',
    'materiasprimas',
    'productos',
    'productosreventa',
    'configuracion',
    
    # Tablas con dependencias
    'formulas',           # Depende de productos y materiasprimas
    'presentaciones',     # Depende de productos y envases_etiquetas
    'lotes',              # Depende de productos
    'comprasmateriaprima', # Depende de materiasprimas y proveedor
    'produccion',         # Depende de productos
    'fondo',
    'ventas',             # Depende de clientes
    'venta_reventa',      # Depende de productosreventa
    'ventas_archivadas'   # Depende de clientes
]

# ==========================================
# FUNCIÓN PRINCIPAL DE MIGRACIÓN
# ==========================================

def migrate_database():
    print("=" * 60)
    print("MIGRACIÓN DE QUIMO.DB A POSTGRESQL")
    print("=" * 60)
    
    # Conectar a SQLite
    print(f"\n1. Conectando a SQLite: {SQLITE_DB_PATH}")
    try:
        sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
        sqlite_cursor = sqlite_conn.cursor()
        print("   ✓ Conexión SQLite exitosa")
    except Exception as e:
        print(f"   ✗ Error conectando a SQLite: {e}")
        return False
    
    # Conectar a PostgreSQL
    print(f"\n2. Conectando a PostgreSQL: {POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}")
    try:
        pg_conn = psycopg2.connect(**POSTGRES_CONFIG)
        pg_cursor = pg_conn.cursor()
        print("   ✓ Conexión PostgreSQL exitosa")
    except Exception as e:
        print(f"   ✗ Error conectando a PostgreSQL: {e}")
        print("   Verifica que:")
        print("   - PostgreSQL esté corriendo")
        print("   - La IP y puerto sean correctos")
        print("   - El usuario y contraseña sean correctos")
        return False
    
    # Migrar tablas en orden específico
    print(f"\n3. Migrando {len(MIGRATION_ORDER)} tablas en orden...")
    
    for table_name in MIGRATION_ORDER:
        print(f"\n   → Procesando tabla: {table_name}")
        
        try:
            # Verificar si la tabla existe en SQLite
            sqlite_cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not sqlite_cursor.fetchone():
                print(f"     ⓘ Tabla {table_name} no existe en SQLite, saltando...")
                continue
            
            # Obtener esquema de la tabla
            sqlite_cursor.execute(f"PRAGMA table_info({table_name})")
            columns_info = sqlite_cursor.fetchall()
            
            # Crear tabla en PostgreSQL
            columns_def = []
            primary_keys = []
            
            for col in columns_info:
                col_id, col_name, col_type, not_null, default_val, pk = col
                
                # Determinar si es primary key
                is_pk = (pk == 1)
                
                # Mapear tipo
                pg_type = map_sqlite_to_postgres_type(col_type, is_pk)
                
                # Construir definición de columna
                if "PRIMARY KEY" in pg_type:
                    # Ya incluye PRIMARY KEY
                    col_def = f'"{col_name}" {pg_type}'
                    primary_keys.append(f'"{col_name}"')
                else:
                    col_def = f'"{col_name}" {pg_type}'
                    if not_null:
                        col_def += ' NOT NULL'
                    if default_val is not None:
                        col_def += f' DEFAULT {default_val}'
                    if is_pk:
                        primary_keys.append(f'"{col_name}"')
                
                columns_def.append(col_def)
            
            # Agregar PRIMARY KEY si es compuesta
            if primary_keys and "PRIMARY KEY" not in " ".join(columns_def):
                columns_def.append(f'PRIMARY KEY ({", ".join(primary_keys)})')
            
            create_table_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(columns_def)});'
            
            print(f"     - Creando estructura...")
            pg_cursor.execute(create_table_sql)
            pg_conn.commit()
            print(f"     ✓ Estructura creada")
            
            # Copiar datos (excepto para clientes si quieres vaciarla)
            print(f"     - Copiando datos...")
            sqlite_cursor.execute(f'SELECT * FROM "{table_name}"')
            rows = sqlite_cursor.fetchall()
            
            if rows:
                # Obtener nombres de columnas
                columns = [f'"{col[1]}"' for col in columns_info]
                placeholders = ', '.join(['%s'] * len(columns))
                insert_sql = f'INSERT INTO "{table_name}" ({", ".join(columns)}) VALUES ({placeholders})'
                
                # Insertar filas
                success_count = 0
                for row in rows:
                    try:
                        pg_cursor.execute(insert_sql, row)
                        success_count += 1
                    except Exception as e:
                        print(f"     ⚠ Error insertando fila: {e}")
                        print(f"     SQL: {insert_sql}")
                        print(f"     Valores: {row}")
                        continue
                
                pg_conn.commit()
                print(f"     ✓ {success_count}/{len(rows)} filas copiadas")
                
                # Si es la tabla clientes y quieres vaciarla después de migrar
                if table_name == 'clientes':
                    print(f"     - Vaciar tabla clientes...")
                    pg_cursor.execute(f'DELETE FROM "{table_name}"')
                    pg_conn.commit()
                    print(f"     ✓ Tabla clientes vaciada")
            else:
                print(f"     ⓘ Tabla vacía")
            
        except Exception as e:
            print(f"     ✗ Error migrando {table_name}: {e}")
            pg_conn.rollback()
            continue
    
    # Cerrar conexiones
    sqlite_conn.close()
    pg_conn.close()
    
    print("\n" + "=" * 60)
    print("MIGRACIÓN COMPLETADA")
    print("=" * 60)
    print("\n✓ Todos los datos han sido migrados a PostgreSQL")
    print(f"✓ Servidor: {POSTGRES_CONFIG['host']}")
    print(f"✓ Base de datos: {POSTGRES_CONFIG['database']}")
    print(f"✓ Usuario: {POSTGRES_CONFIG['user']}")
    
    return True

# ==========================================
# FUNCIÓN PARA VACIAR SOLO CLIENTES
# ==========================================

def vaciar_tabla_clientes():
    """Vacía solo la tabla clientes en PostgreSQL"""
    try:
        pg_conn = psycopg2.connect(**POSTGRES_CONFIG)
        pg_cursor = pg_conn.cursor()
        
        print("Vaciando tabla clientes...")
        pg_cursor.execute('DELETE FROM "clientes"')
        pg_conn.commit()
        
        print("✓ Tabla clientes vaciada completamente")
        pg_conn.close()
        
    except Exception as e:
        print(f"✗ Error vaciando tabla clientes: {e}")

# ==========================================
# EJECUTAR MIGRACIÓN
# ==========================================

if __name__ == "__main__":
    print("\n⚠ MIGRACIÓN DE QUIMO A POSTGRESQL")
    print("=" * 50)
    
    # Mostrar configuración (sin contraseña por seguridad)
    config_display = POSTGRES_CONFIG.copy()
    if config_display['password']:
        config_display['password'] = '***'
    print(f"Configuración PostgreSQL: {config_display}")
    
    print("\nOpciones:")
    print("1. Migrar TODA la base de datos (incluyendo clientes)")
    print("2. Migrar pero VACIAR tabla clientes después")
    print("3. Solo vaciar tabla clientes (si ya migraste)")
    
    opcion = input("\nSelecciona opción (1-3): ").strip()
    
    if opcion == "1":
        success = migrate_database()
        if success:
            print("\n🎉 ¡Migración completada! Ahora puedes:")
            print("1. Probar tu aplicación con PostgreSQL")
            print("2. Verificar que todos los datos estén correctos")
        else:
            print("\n❌ La migración falló. Revisa los errores anteriores")
    
    elif opcion == "2":
        success = migrate_database()
        if success:
            vaciar_tabla_clientes()
            print("\n🎉 ¡Migración completada y clientes vaciados!")
        else:
            print("\n❌ La migración falló.")
    
    elif opcion == "3":
        vaciar_tabla_clientes()
        print("\n✓ Tabla clientes vaciada")
    
    else:
        print("\n❌ Opción no válida")