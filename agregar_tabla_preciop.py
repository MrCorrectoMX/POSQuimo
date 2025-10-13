import sqlite3
import os

def agregar_columna_precio():
    """
    Se conecta a la base de datos quimo.db y agrega la columna 'precio_venta'
    a la tabla 'productos' si no existe.
    """
    # Nombre del archivo de la base de datos.
    # El script asume que la base de datos está en la misma carpeta.
    db_file = 'quimo.db'

    if not os.path.exists(db_file):
        print(f"Error: No se encontró el archivo '{db_file}'.")
        print("Asegúrate de que este script esté en la misma carpeta que tu base de datos.")
        return

    conn = None  # Inicializar la variable de conexión
    try:
        # 1. Conectar a la base de datos
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        print(f"Conectado a la base de datos: {db_file}")

        # 2. Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(productos)")
        columnas = [info[1] for info in cursor.fetchall()]

        if 'precio_venta' in columnas:
            print("La columna 'precio_venta' ya existe en la tabla 'productos'. No se necesita hacer nada.")
        else:
            # 3. Si no existe, agregar la columna
            print("La columna 'precio_venta' no existe. Agregándola...")
            sql_command = "ALTER TABLE productos ADD COLUMN precio_venta REAL DEFAULT 0.0;"
            cursor.execute(sql_command)
            conn.commit()
            print("¡Columna 'precio_venta' agregada exitosamente!")

    except sqlite3.Error as e:
        print(f"Ocurrió un error de base de datos: {e}")
    finally:
        # 4. Cerrar la conexión
        if conn:
            conn.close()
            print("Conexión cerrada.")

if __name__ == "__main__":
    agregar_columna_precio()