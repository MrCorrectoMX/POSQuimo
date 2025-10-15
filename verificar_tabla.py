# debug_presentaciones.py
from sqlalchemy import create_engine, text, inspect

# Ajusta el nombre de tu archivo .db
engine = create_engine("sqlite:///quimo.db", echo=True)

try:
    with engine.connect() as conn:
        print("\n=== VERIFICACIÓN TABLA PRESENTACIONES ===")
        
        # Verificar si la tabla existe
        inspector = inspect(conn)
        tablas = inspector.get_table_names()
        
        if 'presentaciones' not in tablas:
            print("❌ La tabla 'presentaciones' NO existe en la base de datos")
        else:
            print("✅ La tabla 'presentaciones' existe")
            
            # Mostrar estructura de la tabla
            columnas = inspector.get_columns('presentaciones')
            print("\n📋 Estructura de la tabla:")
            for col in columnas:
                print(f"  - {col['name']} ({col['type']})")
            
            # Contar registros
            count_result = conn.execute(text("SELECT COUNT(*) FROM presentaciones")).scalar()
            print(f"\n🔢 Total de registros en 'presentaciones': {count_result}")
            
            if count_result > 0:
                # Mostrar todos los registros
                print("\n📝 Registros en 'presentaciones':")
                registros = conn.execute(text("""
                    SELECT p.id_presentacion, p.id_producto, pr.nombre_producto, 
                           p.nombre_presentacion, p.factor, p.precio_venta
                    FROM presentaciones p
                    LEFT JOIN productos pr ON p.id_producto = pr.id_producto
                    ORDER BY p.id_producto, p.id_presentacion
                """)).fetchall()
                
                for registro in registros:
                    print(f"  ID: {registro[0]}, Producto ID: {registro[1]}, Producto: '{registro[2]}'")
                    print(f"    Presentación: '{registro[3]}', Factor: {registro[4]}, Precio: ${registro[5]:.2f}")
                    print("")
            else:
                print("❌ La tabla 'presentaciones' está VACÍA")
                
                # Mostrar productos disponibles para crear presentaciones
                print("\n📦 Productos disponibles para crear presentaciones:")
                productos = conn.execute(text("""
                    SELECT id_producto, nombre_producto, precio_venta 
                    FROM productos 
                    WHERE estatus_producto = 1
                    ORDER BY nombre_producto
                """)).fetchall()
                
                if productos:
                    for producto in productos:
                        print(f"  ID: {producto[0]}, Nombre: '{producto[1]}', Precio base: ${producto[2]:.2f}")
                    
                    print("\n💡 Para probar la funcionalidad, puedes insertar presentaciones:")
                    print("   Ejemplo para el primer producto:")
                    if productos:
                        primer_producto = productos[0]
                        print(f"   INSERT INTO presentaciones (id_producto, nombre_presentacion, factor, precio_venta)")
                        print(f"   VALUES ({primer_producto[0]}, 'Chico', 1, {primer_producto[2] * 0.8:.2f});")
                        print(f"   INSERT INTO presentaciones (id_producto, nombre_presentacion, factor, precio_venta)")
                        print(f"   VALUES ({primer_producto[0]}, 'Mediano', 2, {primer_producto[2]:.2f});")
                        print(f"   INSERT INTO presentaciones (id_producto, nombre_presentacion, factor, precio_venta)")
                        print(f"   VALUES ({primer_producto[0]}, 'Grande', 3, {primer_producto[2] * 1.2:.2f});")
                else:
                    print("  ❌ No hay productos activos en la base de datos")

except Exception as e:
    print(f"\n❌ [ERROR] No pude consultar la BD: {e}")