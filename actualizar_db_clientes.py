# modificar_presentaciones_con_envases_corregido.py
from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///quimo.db", echo=True)

try:
    with engine.connect() as conn:
        # Primero, limpiar la tabla de presentaciones existente
        conn.execute(text("DELETE FROM presentaciones"))
        
        # Verificar si necesitamos agregar la columna id_envase a presentaciones
        try:
            conn.execute(text("ALTER TABLE presentaciones ADD COLUMN id_envase INTEGER"))
            conn.execute(text("ALTER TABLE presentaciones ADD COLUMN costo_envase REAL DEFAULT 0"))
            print("✅ Columnas agregadas a la tabla presentaciones")
        except Exception as e:
            print("ℹ️ Las columnas ya existen o no se pudieron agregar:", e)
        
        # Definir qué presentaciones usar para cada tipo de producto
        mapeo_presentaciones = {
            'liquidos': [
                ('ENVASE PET 1 L', 1),
                ('ENVASE PET 5 L', 5),
                ('BARRIL 120 KG', 120),
                ('ENVASE BOSTON 1 L', 1),
            ],
            'granel': [
                ('COSTAL CON ETIQUETA', 25),
                ('BOLSA BLANCA', 1),
                ('BOLSA TRANSPARENTE', 1),
            ],
            'especiales': [
                ('ENVASE ALCOHOLERO 1 L', 1),
                ('ENVASE MUESTRA 250 mL', 0.25),
                ('ENVASE MUESTRA 500 mL', 0.5),
            ]
        }
        
        # Obtener todos los productos
        productos = conn.execute(text("""
            SELECT id_producto, nombre_producto 
            FROM productos 
            WHERE estatus_producto = 1
        """)).fetchall()
        
        # Clasificación simplificada basada en el nombre
        def clasificar_producto(nombre):
            nombre_lower = nombre.lower()
            if any(palabra in nombre_lower for palabra in ['aromatizante', 'cloro', 'detergente', 'suavizante', 'jabon liquido', 'shampoo', 'limpiador', 'desengras']):
                return 'liquidos'
            elif any(palabra in nombre_lower for palabra in ['jabon', 'polvo', 'rayado', 'barra']):
                return 'granel'
            else:
                return 'especiales'
        
        # Insertar presentaciones para cada producto
        for producto in productos:
            id_producto, nombre_producto = producto
            tipo = clasificar_producto(nombre_producto)
            
            print(f"📦 Añadiendo presentaciones para: {nombre_producto} ({tipo})")
            
            # Obtener los envases para este tipo
            if tipo in mapeo_presentaciones:
                for nombre_envase, factor in mapeo_presentaciones[tipo]:
                    # Obtener el id_envase y costo_total
                    envase = conn.execute(text("""
                        SELECT id_envase, costo_total FROM envases_etiquetas 
                        WHERE nombre_envase = :nombre
                    """), {"nombre": nombre_envase}).fetchone()
                    
                    if envase:
                        id_envase, costo_envase = envase
                        
                        # Insertar en presentaciones
                        conn.execute(text("""
                            INSERT INTO presentaciones 
                            (id_producto, id_envase, nombre_presentacion, factor, costo_envase)
                            VALUES (:id_producto, :id_envase, :nombre_presentacion, :factor, :costo_envase)
                        """), {
                            "id_producto": id_producto,
                            "id_envase": id_envase,
                            "nombre_presentacion": f"{nombre_envase}",
                            "factor": factor,
                            "costo_envase": costo_envase
                        })
        
        conn.commit()
        print("✅ Presentaciones actualizadas correctamente")
        
        # Verificar
        result = conn.execute(text("""
            SELECT p.nombre_producto, pr.nombre_presentacion, pr.factor, pr.costo_envase
            FROM presentaciones pr
            JOIN productos p ON pr.id_producto = p.id_producto
            ORDER BY p.nombre_producto, pr.factor
            LIMIT 20
        """)).fetchall()
        
        print("\n📋 Ejemplo de presentaciones insertadas:")
        for row in result:
            print(f"  {row[0]} - {row[1]}: Factor {row[2]}, Envase: ${row[3]:.2f}")

except Exception as e:
    print(f"❌ Error: {e}")