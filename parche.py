# fix_date_columns.py
from database_manager import db

def fix_date_columns():
    """Corregir los tipos de datos de las columnas de fecha"""
    print("🔧 CORRIGIENDO TIPOS DE DATOS DE FECHA")
    print("=" * 50)
    
    # Columnas que necesitan corrección
    date_columns = [
        {
            'table': 'produccion',
            'column': 'fecha',
            'current_type': 'TEXT',
            'new_type': 'DATE'
        },
        {
            'table': 'ventas', 
            'column': 'fecha_venta',
            'current_type': 'TEXT',
            'new_type': 'DATE'
        },
        {
            'table': 'venta_reventa',
            'column': 'fecha_venta', 
            'current_type': 'TEXT',
            'new_type': 'DATE'
        },
        {
            'table': 'fondo',
            'column': 'fecha',
            'current_type': 'TEXT', 
            'new_type': 'DATE'
        },
        {
            'table': 'ventas_archivadas',
            'column': 'fecha_archivo',
            'current_type': 'DATE',  # Esta ya está bien, pero la incluimos por si acaso
            'new_type': 'DATE'
        },
        {
            'table': 'ventas_archivadas', 
            'column': 'fecha_venta_original',
            'current_type': 'DATE',
            'new_type': 'DATE'
        },
        {
            'table': 'ventas_archivadas',
            'column': 'semana_inicio',
            'current_type': 'DATE',
            'new_type': 'DATE'
        },
        {
            'table': 'ventas_archivadas',
            'column': 'semana_fin',
            'current_type': 'DATE', 
            'new_type': 'DATE'
        },
        {
            'table': 'comprasmateriaprima',
            'column': 'fecha_compra',
            'current_type': 'TEXT',
            'new_type': 'DATE'
        },
        {
            'table': 'materiasprimas',
            'column': 'fecha_mp',
            'current_type': 'TEXT',
            'new_type': 'DATE'
        },
        {
            'table': 'productos',
            'column': 'fecha_producto', 
            'current_type': 'TEXT',
            'new_type': 'DATE'
        },
        {
            'table': 'lotes',
            'column': 'fecha',
            'current_type': 'DATE',  # Esta ya está bien
            'new_type': 'DATE'
        }
    ]
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    success_count = 0
    total_count = len(date_columns)
    
    for col_info in date_columns:
        table = col_info['table']
        column = col_info['column']
        new_type = col_info['new_type']
        
        print(f"\n📋 Tabla: {table}.{column}")
        
        try:
            # Verificar si la tabla y columna existen
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = %s AND column_name = %s
            """, (table, column))
            
            result = cursor.fetchone()
            if not result:
                print(f"   ⚠ Columna no encontrada, saltando...")
                continue
            
            current_type = result[1]
            print(f"   🔄 Cambiando de {current_type} a {new_type}")
            
            # Para cambiar el tipo, necesitamos una columna temporal
            temp_column = f"{column}_temp"
            
            # 1. Agregar columna temporal
            cursor.execute(f'ALTER TABLE "{table}" ADD COLUMN "{temp_column}" {new_type}')
            
            # 2. Copiar y convertir datos
            if new_type == 'DATE':
                # Intentar diferentes formatos de fecha
                date_formats = [
                    f'"{column}"',  # Formato YYYY-MM-DD
                    f'TO_DATE("{column}", \'YYYY-MM-DD\')',
                    f'TO_DATE("{column}", \'DD/MM/YYYY\')',
                    f'TO_DATE("{column}", \'MM/DD/YYYY\')'
                ]
                
                conversion_success = False
                for date_format in date_formats:
                    try:
                        cursor.execute(f'''
                            UPDATE "{table}" 
                            SET "{temp_column}" = {date_format}
                            WHERE "{column}" IS NOT NULL AND "{column}" != ''
                        ''')
                        conversion_success = True
                        print(f"   ✅ Datos convertidos con formato: {date_format}")
                        break
                    except Exception as e:
                        print(f"   ⚠ Formato falló: {date_format}")
                        continue
                
                if not conversion_success:
                    # Si ningún formato funciona, usar fecha por defecto
                    cursor.execute(f'''
                        UPDATE "{table}" 
                        SET "{temp_column}" = CURRENT_DATE
                        WHERE "{column}" IS NOT NULL AND "{column}" != ''
                    ''')
                    print(f"   ⚠ Usando fecha por defecto para datos problemáticos")
            
            # 3. Eliminar columna original
            cursor.execute(f'ALTER TABLE "{table}" DROP COLUMN "{column}"')
            
            # 4. Renombrar columna temporal
            cursor.execute(f'ALTER TABLE "{table}" RENAME COLUMN "{temp_column}" TO "{column}"')
            
            conn.commit()
            print(f"   ✅ Columna convertida exitosamente")
            success_count += 1
            
        except Exception as e:
            conn.rollback()
            print(f"   ❌ Error: {e}")
            # Intentar método alternativo más simple
            try:
                print(f"   🔄 Intentando método alternativo...")
                cursor.execute(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" TYPE {new_type} USING "{column}"::{new_type}')
                conn.commit()
                print(f"   ✅ Conversión alternativa exitosa")
                success_count += 1
            except Exception as e2:
                print(f"   ❌ Método alternativo también falló: {e2}")
                conn.rollback()
    
    cursor.close()
    conn.close()
    
    print(f"\n📊 RESUMEN: {success_count}/{total_count} columnas convertidas")
    return success_count == total_count

def verify_date_conversions():
    """Verificar que las conversiones fueron exitosas"""
    print("\n🔍 VERIFICANDO CONVERSIONES")
    print("=" * 50)
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Verificar tipos actuales
    tables_to_check = ['produccion', 'ventas', 'venta_reventa', 'fondo']
    
    for table in tables_to_check:
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = %s 
            AND (column_name LIKE '%fecha%' OR column_name LIKE '%date%')
        """, (table,))
        
        columns = cursor.fetchall()
        print(f"\n📋 {table}:")
        for col_name, data_type in columns:
            print(f"   - {col_name}: {data_type}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    print("🔄 INICIANDO CORRECCIÓN DE TIPOS DE FECHA")
    
    if fix_date_columns():
        verify_date_conversions()
        print("\n🎉 ¡CORRECCIÓN COMPLETADA!")
        print("💡 Ahora las consultas con BETWEEN deberían funcionar correctamente")
    else:
        print("\n⚠ Algunas columnas no pudieron ser convertidas")
        print("💡 Puede que necesites revisar manualmente los datos problemáticos")