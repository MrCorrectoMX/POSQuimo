# debug_sqlite_completo.py
from sqlalchemy import create_engine, text, inspect

# Ajusta el nombre de tu archivo .db
engine = create_engine("sqlite:///quimo.db", echo=True)

try:
    with engine.connect() as conn:
        inspector = inspect(conn)

        # Listar todas las tablas
        print("\n=== TABLAS DISPONIBLES ===")
        tablas = inspector.get_table_names()
        for t in tablas:
            print("-", t)

        # Para cada tabla, listar columnas y mostrar 5 registros
        for tabla in tablas:
            print(f"\n=== TABLA: {tabla} ===")
            
            columnas = inspector.get_columns(tabla)
            print("Columnas:")
            for col in columnas:
                print(f"  - {col['name']} ({col['type']})")
            
            # Mostrar 5 registros de ejemplo
            try:
                registros = conn.execute(text(f"SELECT * FROM {tabla} LIMIT 5;")).fetchall()
                print("Registros de ejemplo:")
                for r in registros:
                    print(" ", dict(r))
            except Exception as e:
                print("  [ERROR] No se pudieron obtener registros:", e)

except Exception as e:
    print("\n[ERROR CRÍTICO] No pude consultar la BD:", e)
