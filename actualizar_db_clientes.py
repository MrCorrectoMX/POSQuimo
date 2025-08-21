import sqlite3
import os

DB_FILENAME = 'quimo.db'

def setup_database_for_clients():
    """
    Prepara la base de datos: crea tabla de clientes, tabla de ventas
    y actualiza el estatus de todos los productos a 'disponible'.
    """
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_FILENAME)
    
    if not os.path.exists(db_path):
        print(f"Error: No se encontró el archivo '{DB_FILENAME}'.")
        return

    print(f"Abriendo la base de datos: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Iniciar una transacción para que todo se haga de una vez
        cursor.execute("BEGIN TRANSACTION;")

        # 1. Crear la tabla de clientes si no existe
        print(" -> Creando tabla 'clientes' (si no existe)...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_cliente TEXT NOT NULL UNIQUE,
            telefono TEXT,
            email TEXT
        );
        """)

        # 2. Crear la tabla de ventas para registrar las salidas
        print(" -> Creando tabla 'ventas' (si no existe)...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id_venta INTEGER PRIMARY KEY AUTOINCREMENT,
            id_cliente INTEGER NOT NULL,
            codigo_producto TEXT NOT NULL,
            descripcion_producto TEXT,
            cantidad REAL NOT NULL,
            fecha_venta TEXT NOT NULL,
            FOREIGN KEY (id_cliente) REFERENCES clientes (id_cliente)
        );
        """)

        
    except Exception as e:
        print(f"\nOcurrió un error. Se revirtieron los cambios. Error: {e}")
        conn.rollback()
    finally:
        conn.close()
        print("Conexión cerrada.")

if __name__ == "__main__":
    setup_database_for_clients()