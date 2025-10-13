# crear_tabla_presentaciones.py
from sqlalchemy import create_engine, text, inspect

# Ajusta el nombre de tu archivo .db
engine = create_engine("sqlite:///quimo.db", echo=True)

try:
    with engine.connect() as conn:
        inspector = inspect(conn)

        # Verificar si la tabla 'presentaciones' ya existe
        if "presentaciones" not in inspector.get_table_names():
            # Crear la tabla
            conn.execute(text("""
                CREATE TABLE presentaciones (
                    id_presentacion INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_producto INTEGER NOT NULL,
                    nombre_presentacion TEXT NOT NULL,
                    factor REAL NOT NULL DEFAULT 1,
                    precio_venta REAL,
                    FOREIGN KEY(id_producto) REFERENCES productos(id_producto)
                );
            """))
            print("[OK] Tabla 'presentaciones' creada correctamente.")
        else:
            print("[INFO] La tabla 'presentaciones' ya existe.")

except Exception as e:
    print("[ERROR CRÍTICO] No se pudo crear la tabla 'presentaciones':", e)
