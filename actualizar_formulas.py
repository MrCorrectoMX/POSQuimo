# corregir_tabla_venta_reventa.py

from sqlalchemy import text, create_engine
import os

def diagnosticar_tabla_venta_reventa(engine):
    """Diagnostica la estructura actual de la tabla venta_reventa"""
    try:
        with engine.connect() as conn:
            # Verificar estructura de la tabla
            query_estructura = text("PRAGMA table_info(venta_reventa)")
            estructura = conn.execute(query_estructura).fetchall()
            
            print("=" * 80)
            print("ESTRUCTURA ACTUAL DE VENTA_REVENTA")
            print("=" * 80)
            
            columnas = []
            for col in estructura:
                print(f"Columna: {col[1]} | Tipo: {col[2]} | Puede ser nulo: {col[3]}")
                columnas.append(col[1])
            
            # Verificar si existe id_prev
            if 'id_prev' not in columnas:
                print("\n❌ PROBLEMA: La columna 'id_prev' no existe en la tabla")
                return False, columnas
            else:
                print("\n✅ La columna 'id_prev' existe correctamente")
                return True, columnas
                
    except Exception as e:
        print(f"❌ Error al diagnosticar tabla: {e}")
        return False, []

def corregir_tabla_venta_reventa(engine):
    """Corrige la estructura de la tabla venta_reventa"""
    try:
        with engine.connect() as conn:
            with conn.begin() as trans:
                # Verificar estructura actual
                query_estructura = text("PRAGMA table_info(venta_reventa)")
                estructura = conn.execute(query_estructura).fetchall()
                columnas = [col[1] for col in estructura]
                
                cambios_realizados = []
                
                # Agregar columna id_prev si no existe
                if 'id_prev' not in columnas:
                    print("🔄 Agregando columna 'id_prev'...")
                    query_alter = text("ALTER TABLE venta_reventa ADD COLUMN id_prev INTEGER")
                    conn.execute(query_alter)
                    cambios_realizados.append("id_prev agregada")
                
                # Agregar otras columnas que puedan faltar
                columnas_necesarias = [
                    'id_prev', 'nombre_producto', 'cantidad', 'precio_unitario', 
                    'total', 'fecha_venta', 'proveedor', 'area'
                ]
                
                for columna in columnas_necesarias:
                    if columna not in columnas:
                        print(f"🔄 Agregando columna '{columna}'...")
                        
                        if columna in ['id_prev', 'cantidad']:
                            tipo = "INTEGER"
                        elif columna in ['precio_unitario', 'total']:
                            tipo = "REAL"
                        else:
                            tipo = "TEXT"
                            
                        query_alter = text(f"ALTER TABLE venta_reventa ADD COLUMN {columna} {tipo}")
                        conn.execute(query_alter)
                        cambios_realizados.append(f"{columna} agregada")
                
                if cambios_realizados:
                    print(f"✅ Cambios realizados: {', '.join(cambios_realizados)}")
                else:
                    print("✅ La tabla ya tiene la estructura correcta")
                
                return True
                
    except Exception as e:
        print(f"❌ Error al corregir tabla: {e}")
        return False

def crear_tabla_venta_reventa_correcta(engine):
    """Crea la tabla venta_reventa con la estructura correcta (si no existe)"""
    try:
        with engine.connect() as conn:
            with conn.begin() as trans:
                # Crear tabla con estructura completa
                query_create = text("""
                    CREATE TABLE IF NOT EXISTS venta_reventa (
                        id_venta INTEGER PRIMARY KEY AUTOINCREMENT,
                        id_prev INTEGER,
                        nombre_producto TEXT,
                        cantidad REAL,
                        precio_unitario REAL,
                        total REAL,
                        fecha_venta TEXT,
                        proveedor TEXT,
                        area TEXT,
                        FOREIGN KEY (id_prev) REFERENCES productosreventa(id_prev)
                    )
                """)
                conn.execute(query_create)
                print("✅ Tabla venta_reventa creada/verificada correctamente")
                return True
                
    except Exception as e:
        print(f"❌ Error al crear tabla: {e}")
        return False

def verificar_datos_venta_reventa(engine):
    """Verifica los datos existentes en la tabla venta_reventa"""
    try:
        with engine.connect() as conn:
            query_count = text("SELECT COUNT(*) FROM venta_reventa")
            count = conn.execute(query_count).scalar()
            
            print(f"📊 Registros en venta_reventa: {count}")
            
            if count > 0:
                query_sample = text("SELECT * FROM venta_reventa LIMIT 5")
                sample = conn.execute(query_sample).fetchall()
                
                print("\n📋 Muestra de registros:")
                for row in sample:
                    print(f"  {row}")
                    
            return count
            
    except Exception as e:
        print(f"❌ Error al verificar datos: {e}")
        return 0

# Función para corregir el código en ui_pos.py
def generar_parche_ui_pos():
    """Genera el código corregido para ui_pos.py"""
    parche_codigo = '''
# EN LA FUNCIÓN _add_product_to_ticket, REEMPLAZAR ESTA PARTE:

# 🔸 2. Registrar venta en la tabla venta_reventa
try:
    # Verificar si la tabla tiene las columnas correctas
    insert_query = text("""
        INSERT INTO venta_reventa (id_prev, nombre_producto, cantidad, precio_unitario, total, fecha_venta)
        VALUES (:id_prev, :nombre_producto, :cantidad, :precio_unitario, :total, DATE('now'))
    """)
    conn.execute(insert_query, {
        "id_prev": id_prev,
        "nombre_producto": product_name,
        "cantidad": 1,
        "precio_unitario": product_price,
        "total": product_price
    })
    conn.commit()
except Exception as e:
    print(f"⚠️ Error al registrar venta_reventa: {e}")
    # Intentar con estructura alternativa si falla
    try:
        insert_query_alt = text("""
            INSERT INTO venta_reventa (nombre_producto, cantidad, precio_unitario, total, fecha_venta)
            VALUES (:nombre_producto, :cantidad, :precio_unitario, :total, DATE('now'))
        """)
        conn.execute(insert_query_alt, {
            "nombre_producto": product_name,
            "cantidad": 1,
            "precio_unitario": product_price,
            "total": product_price
        })
        conn.commit()
    except Exception as e2:
        print(f"⚠️ Error alternativo al registrar venta_reventa: {e2}")
'''

    print("=" * 80)
    print("PARCHE PARA ui_pos.py")
    print("=" * 80)
    print(parche_codigo)
    return parche_codigo

def main():
    # Conectar a la base de datos
    db_path = os.path.join(os.path.dirname(__file__), 'quimo.db')
    engine = create_engine(f"sqlite:///{db_path}")
    
    print("🔧 DIAGNÓSTICO Y CORRECCIÓN DE TABLA VENTA_REVENTA")
    print("=" * 60)
    
    # 1. Diagnosticar problema
    tabla_ok, columnas = diagnosticar_tabla_venta_reventa(engine)
    
    if not tabla_ok:
        print("\n" + "=" * 60)
        print("🔄 CORRIGIENDO ESTRUCTURA DE LA TABLA")
        print("=" * 60)
        
        # Intentar corregir la tabla existente
        if not corregir_tabla_venta_reventa(engine):
            print("\n🔄 Creando tabla nueva...")
            crear_tabla_venta_reventa_correcta(engine)
    
    # 2. Verificar datos
    print("\n" + "=" * 60)
    print("📊 VERIFICANDO DATOS EXISTENTES")
    print("=" * 60)
    verificar_datos_venta_reventa(engine)
    
    # 3. Generar parche para el código
    print("\n" + "=" * 60)
    print("🔧 PARCHE PARA EL CÓDIGO")
    print("=" * 60)
    generar_parche_ui_pos()
    
    print("\n✅ PROCESO COMPLETADO")
    print("\n📝 INSTRUCCIONES:")
    print("1. Ejecuta este script primero para corregir la base de datos")
    print("2. Luego aplica el parche mostrado en tu archivo ui_pos.py")
    print("3. Reinicia tu aplicación")

if __name__ == "__main__":
    main()