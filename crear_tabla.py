import sqlite3
import os

def crear_tabla_venta_reventa():
    """
    Crea la tabla 'venta_reventa' en la base de datos 'quimo.db' si no existe.
    La tabla registra las ventas de productos, incluyendo proveedor, cantidad y total.
    """
    db_file = 'quimo.db'

    if not os.path.exists(db_file):
        print(f"Error: No se encontró el archivo '{db_file}'.")
        print("Asegúrate de que este script esté en la misma carpeta que tu base de datos.")
        return

    conn = None
    try:
        # 1. Conectar a la base de datos
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        print(f"Conectado a la base de datos: {db_file}")

        # 2. Crear tabla venta_reventa si no existe
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS venta_reventa (
                id_venta INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_venta TEXT NOT NULL,
                nombre_producto TEXT NOT NULL,
                cantidad REAL NOT NULL,
                unidad_medida TEXT NOT NULL,
                precio_unitario REAL NOT NULL,
                total REAL NOT NULL,
                proveedor TEXT,
                area TEXT DEFAULT 'QUIMO CLEAN'
            );
        """)
        conn.commit()

        print("✅ Tabla 'venta_reventa' verificada o creada correctamente.")

    except sqlite3.Error as e:
        print(f"❌ Error al crear la tabla: {e}")
    finally:
        if conn:
            conn.close()
            print("Conexión cerrada.")

if __name__ == "__main__":
    crear_tabla_venta_reventa()
