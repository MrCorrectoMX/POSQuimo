# crear_tabla_envases.py
from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///quimo.db", echo=True)

try:
    with engine.connect() as conn:
        # Crear tabla de envases y etiquetas
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS envases_etiquetas (
                id_envase INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_envase TEXT NOT NULL,
                tipo_envase TEXT,
                costo_envase REAL DEFAULT 0,
                costo_etiqueta REAL DEFAULT 0,
                costo_adicional REAL DEFAULT 0,
                costo_total REAL DEFAULT 0,
                unidades_por_kg INTEGER DEFAULT 1,
                capacidad_ml REAL DEFAULT 0,
                capacidad_litros REAL DEFAULT 0,
                capacidad_kg REAL DEFAULT 0
            )
        """))
        
        # Insertar los envases que proporcionaste
        envases_data = [
            # BARRIL 120 KG
            ('BARRIL 120 KG', 'barril', 170.0, 2.4276, 0, 172.4276, 1, 0, 0, 120),
            
            # Costal
            ('COSTAL CON ETIQUETA', 'costal', 0, 0, 0, 8.29, 1, 0, 0, 25),
            
            # Bolsas
            ('BOLSA BLANCA', 'bolsa', 0, 0, 0, 3.948, 10, 0, 0, 1),
            ('BOLSA TRANSPARENTE', 'bolsa', 0, 0, 0, 1.912, 20, 0, 0, 1),
            
            # Envases PET
            ('ENVASE PET 1 L', 'pet', 2.92, 0.5, 0, 3.42, 1, 1000, 1, 0),
            ('ENVASE PET 1 L SAN JORGE', 'pet', 2.92, 0.5, 0.4, 3.82, 1, 1000, 1, 0),
            ('ENVASE PET 5 L', 'pet', 10.78, 1.25, 0, 12.03, 1, 5000, 5, 0),
            
            # Envases Boston
            ('ENVASE BOSTON 1 L', 'boston', 4.1, 0.625, 2.59, 7.315, 1, 1000, 1, 0),
            ('ENVASE BOSTÓN 500 mL', 'boston', 3.52, 0.238, 2.59, 6.348, 1, 500, 0.5, 0),
            ('ENVASE BOSTÓN 500 mL DESPACHADOR', 'boston', 3.52, 0.238, 8.0, 11.758, 1, 500, 0.5, 0),
            
            # Otros envases
            ('ENVASE ALCOHOLERO 1 L', 'alcoholero', 4.65, 0.5, 0, 5.15, 1, 1000, 1, 0),
            ('ENVASE MUESTRA 250 mL', 'muestra', 2.16, 0.238, 0, 2.398, 1, 250, 0.25, 0),
            ('ENVASE MUESTRA 500 mL', 'muestra', 2.14, 0.238, 0, 2.378, 1, 500, 0.5, 0),
            
            # Etiquetas
            ('ETIQUETA GRANDE', 'etiqueta', 0, 2.4276, 0, 2.4276, 1000, 0, 0, 0),
        ]
        
        for envase in envases_data:
            conn.execute(text("""
                INSERT INTO envases_etiquetas 
                (nombre_envase, tipo_envase, costo_envase, costo_etiqueta, costo_adicional, costo_total, unidades_por_kg, capacidad_ml, capacidad_litros, capacidad_kg)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """), envase)
        
        conn.commit()
        print("✅ Tabla 'envases_etiquetas' creada y datos insertados correctamente")
        
        # Verificar la inserción
        result = conn.execute(text("SELECT nombre_envase, costo_total FROM envases_etiquetas ORDER BY tipo_envase, nombre_envase")).fetchall()
        print("\n📦 Envases insertados:")
        for row in result:
            print(f"  {row[0]}: ${row[1]:.2f}")

except Exception as e:
    print(f"❌ Error: {e}")