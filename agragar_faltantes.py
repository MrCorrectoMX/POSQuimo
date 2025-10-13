import pandas as pd
from sqlalchemy import create_engine, text
import openpyxl
from difflib import get_close_matches

# --- CONFIGURACIÓN ---
DB_PATH = "sqlite:///quimo.db"
EXCEL_PATH = "formulas.xlsx"  # <-- cambia al nombre real de tu archivo
SIMILARITY_THRESHOLD = 0.8

engine = create_engine(DB_PATH)

# --- 1. Cargar Excel ---
df = pd.read_excel(EXCEL_PATH)
print("📘 Archivo Excel cargado correctamente.")

# Detectar columnas MP dinámicamente
mp_columns = [col for col in df.columns if col.strip().startswith("MP")]
print(f"🔍 Columnas de MP detectadas: {mp_columns}")

# --- 2. Cargar productos y materias primas existentes ---
with engine.connect() as conn:
    productos_db = {
        p.lower(): pid
        for pid, p in conn.execute(text("SELECT id_producto, nombre_producto FROM productos"))
    }
    materias_db = {
        m.lower(): mid
        for mid, m in conn.execute(text("SELECT id_mp, nombre_mp FROM materiasprimas"))
    }

# --- 3. Función para buscar coincidencias aproximadas ---
def find_best_match(name, existing_names):
    name_lower = name.lower().strip()
    matches = get_close_matches(name_lower, existing_names, n=1, cutoff=SIMILARITY_THRESHOLD)
    return matches[0] if matches else None

# --- 4. Procesar fila por fila ---
with engine.begin() as conn:  # begin() = auto commit/rollback
    for _, row in df.iterrows():
        producto_nombre = str(row["MATERIAL / PRODUCTO"]).strip()
        if not producto_nombre:
            continue

        # Buscar el producto en DB (coincidencia parcial)
        producto_match = find_best_match(producto_nombre, productos_db.keys())
        if not producto_match:
            print(f"⚠️ Producto '{producto_nombre}' no encontrado en base de datos.")
            continue

        id_producto = productos_db[producto_match]

        # Eliminar fórmulas anteriores
        conn.execute(text("DELETE FROM formulas WHERE id_producto = :idp"), {"idp": id_producto})

        # --- Procesar cada MP ---
        for mp_col in mp_columns:
            mp_nombre = row.get(mp_col)
            if pd.isna(mp_nombre) or str(mp_nombre).strip() == "":
                continue

            porcentaje_col = f"{mp_col.split()[0]} %"
            porcentaje = row.get(porcentaje_col, 0) or 0

            if porcentaje == 0:
                continue

            mp_match = find_best_match(str(mp_nombre), materias_db.keys())
            if not mp_match:
                print(f"⚠️ MP '{mp_nombre}' no encontrada en base. Revisar manualmente.")
                continue

            id_mp = materias_db[mp_match]

            # Insertar nueva fórmula
            conn.execute(
                text("""
                    INSERT INTO formulas (id_producto, id_mp, porcentaje)
                    VALUES (:idp, :idmp, :pct)
                """),
                {"idp": id_producto, "idmp": id_mp, "pct": porcentaje},
            )

        print(f"✅ Fórmulas actualizadas para '{producto_nombre}'")

print("🏁 Sincronización completada con coincidencia parcial.")
