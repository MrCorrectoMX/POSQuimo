import sqlite3

def listar_tablas_y_columnas():
    conexion = sqlite3.connect("quimo.db")
    cursor = conexion.cursor()

    # Obtener todas las tablas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tablas = cursor.fetchall()

    print("Tablas en la base de datos:\n")
    for (tabla,) in tablas:
        print(f"=== Tabla: {tabla} ===")

        # Obtener columnas de la tabla actual
        cursor.execute(f"PRAGMA table_info({tabla});")
        columnas = cursor.fetchall()

        for col in columnas:
            # col[1] = nombre de la columna, col[2] = tipo de dato
            print(f"- {col[1]} (tipo: {col[2]})")
        print()

    conexion.close()

if __name__ == "__main__":
    listar_tablas_y_columnas()
