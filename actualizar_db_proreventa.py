import sqlite3

ruta_db = "quimo.db"

conn = sqlite3.connect(ruta_db)
cursor = conn.cursor()

# 1️⃣ Verificar si la columna ya existe
cursor.execute("PRAGMA table_info(venta_reventa)")
columnas = [col[1] for col in cursor.fetchall()]

if "id_prev" not in columnas:
    print("🛠️ Agregando columna 'id_prev' a la tabla 'venta_reventa'...")
    cursor.execute("ALTER TABLE venta_reventa ADD COLUMN id_prev INTEGER;")
    conn.commit()
    print("✅ Columna agregada correctamente.")
else:
    print("ℹ️ La columna 'id_prev' ya existe. No se hicieron cambios.")

# 2️⃣ (Opcional) activar modo de claves foráneas (si se va a usar luego)
cursor.execute("PRAGMA foreign_keys = ON;")

conn.close()
