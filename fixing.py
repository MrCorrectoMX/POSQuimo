# diagnose_migration.py
import sqlite3
import psycopg2
import traceback
from datetime import datetime

# Configuración
SQLITE_DB_PATH = "quimo.db"
POSTGRES_CONFIG = {
    "host": "192.168.1.24",
    "port": 5432,
    "database": "quimo_bd_new", 
    "user": "quimo_user",
    "password": "1234"
}

def test_sqlite_connection():
    """Diagnóstico completo de SQLite"""
    print("=" * 60)
    print("🔍 DIAGNÓSTICO SQLITE")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        
        # Listar tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📊 Tablas encontradas: {len(tables)}")
        for table in tables:
            print(f"   - {table}")
        
        # Verificar datos en cada tabla
        print(f"\n📈 Verificando datos por tabla:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   - {table}: {count} filas")
            
            # Mostrar algunas filas de ejemplo
            if count > 0:
                try:
                    cursor.execute(f"SELECT * FROM {table} LIMIT 1")
                    sample = cursor.fetchone()
                    print(f"     Ejemplo: {sample}")
                except Exception as e:
                    print(f"     ❌ Error leyendo muestra: {e}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error en SQLite: {e}")
        return False

def test_postgres_connection():
    """Diagnóstico completo de PostgreSQL"""
    print("\n" + "=" * 60)
    print("🔍 DIAGNÓSTICO POSTGRESQL")
    print("=" * 60)
    
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        
        # Verificar versión
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ PostgreSQL: {version.split(',')[0]}")
        
        # Listar tablas
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📊 Tablas en PostgreSQL: {len(tables)}")
        for table in tables:
            print(f"   - {table}")
        
        # Verificar datos
        print(f"\n📈 Verificando datos en PostgreSQL:")
        for table in tables:
            cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
            count = cursor.fetchone()[0]
            print(f"   - {table}: {count} filas")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error en PostgreSQL: {e}")
        print(f"   Detalle: {traceback.format_exc()}")
        return False

def test_table_migration():
    """Probar migración de una tabla específica"""
    print("\n" + "=" * 60)
    print("🧪 PRUEBA DE MIGRACIÓN (tabla 'proveedor')")
    print("=" * 60)
    
    try:
        # Conectar a SQLite
        sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
        sqlite_cursor = sqlite_conn.cursor()
        
        # Verificar datos en SQLite
        sqlite_cursor.execute("SELECT COUNT(*) FROM proveedor")
        sqlite_count = sqlite_cursor.fetchone()[0]
        print(f"📊 Filas en SQLite (proveedor): {sqlite_count}")
        
        if sqlite_count > 0:
            sqlite_cursor.execute("SELECT * FROM proveedor LIMIT 3")
            samples = sqlite_cursor.fetchall()
            print(f"   Muestras: {samples}")
        
        # Conectar a PostgreSQL
        pg_conn = psycopg2.connect(**POSTGRES_CONFIG)
        pg_cursor = pg_conn.cursor()
        
        # Crear tabla en PostgreSQL si no existe
        create_sql = """
            CREATE TABLE IF NOT EXISTS proveedor (
                id_proveedor SERIAL PRIMARY KEY,
                nombre_proveedor TEXT,
                telefono_proveedor TEXT,
                email_proveedor TEXT
            )
        """
        pg_cursor.execute(create_sql)
        pg_conn.commit()
        print("✅ Tabla 'proveedor' creada en PostgreSQL")
        
        # Intentar migrar datos
        if sqlite_count > 0:
            sqlite_cursor.execute("SELECT * FROM proveedor")
            rows = sqlite_cursor.fetchall()
            
            success = 0
            for row in rows:
                try:
                    # Convertir valores None a NULL de PostgreSQL
                    safe_row = [None if value is None else value for value in row]
                    
                    insert_sql = """
                        INSERT INTO proveedor (id_proveedor, nombre_proveedor, telefono_proveedor, email_proveedor) 
                        VALUES (%s, %s, %s, %s)
                    """
                    pg_cursor.execute(insert_sql, safe_row)
                    success += 1
                except Exception as e:
                    print(f"   ❌ Error insertando fila {row}: {e}")
                    break
            
            pg_conn.commit()
            print(f"✅ {success}/{len(rows)} filas migradas a 'proveedor'")
        
        # Verificar datos en PostgreSQL
        pg_cursor.execute("SELECT COUNT(*) FROM proveedor")
        pg_count = pg_cursor.fetchone()[0]
        print(f"📊 Filas en PostgreSQL (proveedor): {pg_count}")
        
        sqlite_conn.close()
        pg_conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba de migración: {e}")
        print(f"   Detalle: {traceback.format_exc()}")
        return False

def check_encoding_issues():
    """Verificar problemas de codificación específicos"""
    print("\n" + "=" * 60)
    print("🔤 VERIFICACIÓN DE CODIFICACIÓN")
    print("=" * 60)
    
    try:
        sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
        sqlite_cursor = sqlite_conn.cursor()
        
        # Revisar todas las tablas para datos binarios/problemáticos
        sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in sqlite_cursor.fetchall()]
        
        for table in tables:
            print(f"\n🔍 Revisando tabla: {table}")
            sqlite_cursor.execute(f"PRAGMA table_info({table})")
            columns = sqlite_cursor.fetchall()
            
            for col in columns:
                col_name = col[1]
                # Buscar datos problemáticos en esta columna
                sqlite_cursor.execute(f"SELECT {col_name} FROM {table} WHERE typeof({col_name}) = 'blob' LIMIT 1")
                blob_data = sqlite_cursor.fetchone()
                
                if blob_data:
                    print(f"   ⚠ Columna '{col_name}' contiene datos BLOB")
                    try:
                        # Intentar decodificar como texto
                        decoded = blob_data[0].decode('utf-8')
                        print(f"     ✅ Se puede decodificar como UTF-8")
                    except UnicodeDecodeError:
                        try:
                            decoded = blob_data[0].decode('latin-1')
                            print(f"     ✅ Se puede decodificar como Latin-1")
                        except:
                            print(f"     ❌ No se puede decodificar como texto")
        
        sqlite_conn.close()
        
    except Exception as e:
        print(f"❌ Error en verificación de codificación: {e}")

if __name__ == "__main__":
    print("🚀 INICIANDO DIAGNÓSTICO COMPLETO")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Ejecutar diagnósticos
    sqlite_ok = test_sqlite_connection()
    postgres_ok = test_postgres_connection()
    migration_test_ok = test_table_migration()
    check_encoding_issues()
    
    print("\n" + "=" * 60)
    print("📋 RESUMEN DEL DIAGNÓSTICO")
    print("=" * 60)
    print(f"✅ SQLite: {'OK' if sqlite_ok else 'PROBLEMA'}")
    print(f"✅ PostgreSQL: {'OK' if postgres_ok else 'PROBLEMA'}")
    print(f"✅ Prueba migración: {'OK' if migration_test_ok else 'PROBLEMA'}")
    
    if not (sqlite_ok and postgres_ok and migration_test_ok):
        print("\n❌ SE DETECTARON PROBLEMAS - Revisa los mensajes arriba")
    else:
        print("\n🎉 TODOS LOS DIAGNÓSTICOS PASARON - Puedes intentar la migración completa")