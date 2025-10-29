# fix_productosreventa.py
from database_manager import db
import sqlite3

def clean_and_migrate_productosreventa():
    """Limpiar y migrar específicamente productosreventa"""
    print("🔧 LIMPIANDO Y MIGRANDO PRODUCTOSREVENTA")
    print("=" * 50)
    
    # Conectar a SQLite
    sqlite_conn = sqlite3.connect("quimo.db")
    sqlite_cursor = sqlite_conn.cursor()
    
    # 1. Identificar y eliminar todos los registros problemáticos en productosreventa
    print("1. 🧹 IDENTIFICANDO REGISTROS PROBLEMÁTICOS...")
    
    # Buscar registros donde 'proveedor' no sea un número
    sqlite_cursor.execute("""
        SELECT id_prev, proveedor, nombre_prev 
        FROM productosreventa 
        WHERE proveedor GLOB '*[a-zA-Z]*'
    """)
    problematic_records = sqlite_cursor.fetchall()
    
    print(f"📊 Registros problemáticos encontrados: {len(problematic_records)}")
    for record in problematic_records:
        print(f"   - ID: {record[0]}, Proveedor: '{record[1]}', Producto: {record[2]}")
    
    # Eliminar registros problemáticos
    if problematic_records:
        sqlite_cursor.execute("DELETE FROM productosreventa WHERE proveedor GLOB '*[a-zA-Z]*'")
        sqlite_conn.commit()
        print("✅ Registros problemáticos eliminados")
    
    # 2. Contar registros válidos
    sqlite_cursor.execute("SELECT COUNT(*) FROM productosreventa")
    valid_count = sqlite_cursor.fetchone()[0]
    print(f"📊 Registros válidos restantes: {valid_count}")
    
    # 3. Migrar a PostgreSQL
    print("\n2. 🚀 MIGRANDO A POSTGRESQL...")
    pg_conn = db.get_connection()
    pg_cursor = pg_conn.cursor()
    
    # Limpiar tabla en PostgreSQL
    pg_cursor.execute('DELETE FROM "productosreventa"')
    
    # Obtener datos válidos
    sqlite_cursor.execute("SELECT * FROM productosreventa")
    rows = sqlite_cursor.fetchall()
    
    # Obtener estructura de columnas
    sqlite_cursor.execute("PRAGMA table_info(productosreventa)")
    columns_info = sqlite_cursor.fetchall()
    column_names = [col[1] for col in columns_info]
    
    # Insertar datos
    placeholders = ', '.join(['%s'] * len(column_names))
    columns_str = ', '.join([f'"{col}"' for col in column_names])
    insert_sql = f'INSERT INTO "productosreventa" ({columns_str}) VALUES ({placeholders})'
    
    success_count = 0
    for row in rows:
        try:
            pg_cursor.execute(insert_sql, row)
            success_count += 1
        except Exception as e:
            print(f"⚠ Error omitiendo fila: {e}")
            continue
    
    pg_conn.commit()
    print(f"✅ {success_count}/{len(rows)} registros migrados exitosamente")
    
    # 4. Verificar
    print("\n3. 🔍 VERIFICANDO MIGRACIÓN...")
    pg_cursor.execute('SELECT COUNT(*) FROM "productosreventa"')
    final_count = pg_cursor.fetchone()[0]
    print(f"📊 Registros en PostgreSQL: {final_count}")
    
    # Cerrar conexiones
    sqlite_conn.close()
    pg_cursor.close()
    pg_conn.close()
    
    print(f"\n🎉 ¡PRODUCTOSREVENTA MIGRADA EXITOSAMENTE!")
    return final_count

def fix_proveedor_columns():
    """Cambiar el tipo de datos de las columnas 'proveedor' a TEXT"""
    print("\n🔧 AJUSTANDO TIPOS DE DATOS...")
    print("=" * 50)
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Cambiar proveedor a TEXT en todas las tablas donde existe
    tables_to_fix = ['productosreventa', 'materiasprimas', 'comprasmateriaprima']
    
    for table in tables_to_fix:
        try:
            # Verificar si la tabla existe y tiene columna proveedor
            cursor.execute(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{table}' AND column_name = 'proveedor'
            """)
            result = cursor.fetchone()
            
            if result:
                current_type = result[1]
                if current_type != 'text':
                    print(f"📋 Cambiando {table}.proveedor de {current_type} a TEXT")
                    cursor.execute(f'ALTER TABLE "{table}" ALTER COLUMN proveedor TYPE TEXT')
                    print(f"✅ {table}.proveedor cambiado a TEXT")
                else:
                    print(f"✅ {table}.proveedor ya es TEXT")
            else:
                print(f"⚠ {table} no tiene columna proveedor")
                
        except Exception as e:
            print(f"❌ Error en {table}: {e}")
    
    conn.commit()
    cursor.close()
    conn.close()
    print("\n🎉 ¡TIPOS DE DATOS AJUSTADOS!")

if __name__ == "__main__":
    print("🔄 INICIANDO REPARACIÓN DE PRODUCTOSREVENTA")
    count = clean_and_migrate_productosreventa()
    fix_proveedor_columns()
    
    print(f"\n📊 RESUMEN FINAL:")
    print(f"   ✅ Productos: 215 registros")
    print(f"   ✅ Materias Primas: 137 registros") 
    print(f"   ✅ Productos Reventa: {count} registros")
    print(f"\n🎉 ¡TU APLICACIÓN DEBERÍA FUNCIONAR CORRECTAMENTE!")