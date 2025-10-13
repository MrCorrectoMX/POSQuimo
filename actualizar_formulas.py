import pandas as pd
from sqlalchemy import create_engine, text
import openpyxl

# --- CONFIGURACIÓN ---
RUTA_DB = "sqlite:///quimo.db"
RUTA_EXCEL = "formulas.xlsx"
engine = create_engine(RUTA_DB)

# --- CARGAR EXCEL ---
df = pd.read_excel(RUTA_EXCEL)

# --- COLUMNAS BASE ---
col_producto = "MATERIAL / PRODUCTO"

# --- DETECTAR COLUMNAS DE MATERIAS PRIMAS ---
mp_cols = []
for i in range(1, 12):
    mp = f"MP {i}"
    porc_col = f"%"
    precio_col = f"$"
    # Las columnas vienen repetidas, así que necesitamos indexarlas
    # Ejemplo: MP 1 | % | $ | MP 2 | % | $ ...
    # Vamos a buscar por posición
    try:
        mp_idx = df.columns.get_loc(mp)
        mp_cols.append((mp, df.columns[mp_idx + 1], df.columns[mp_idx + 2]))
    except KeyError:
        continue
    except IndexError:
        continue

print("🔍 Columnas detectadas de materias primas:")
for c in mp_cols:
    print("   ", c)

# --- PROCESAR FILAS ---
with engine.begin() as conn:
    for _, row in df.iterrows():
        producto = str(row[col_producto]).strip()

        if not producto or producto.lower() == "nan":
            continue

        # Buscar el producto en la tabla productos
        result = conn.execute(
            text("SELECT id_producto FROM productos WHERE nombre_producto = :nombre"),
            {"nombre": producto}
        ).fetchone()

        if not result:
            print(f"⚠️ Producto '{producto}' no encontrado en la base de datos, se omite.")
            continue

        id_producto = result[0]

        # Eliminar fórmulas anteriores
        conn.execute(
            text("DELETE FROM formulas WHERE id_producto = :id"),
            {"id": id_producto}
        )

        # Insertar nuevas fórmulas
        total_insertadas = 0
        for mp_col, porc_col, precio_col in mp_cols:
            nombre_mp = str(row[mp_col]).strip() if mp_col in row else None
            porcentaje = row[porc_col] if porc_col in row else None

            if not nombre_mp or str(nombre_mp).lower() == "nan" or porcentaje in [None, 0, ""]:
                continue

            # Buscar id de la materia prima
            result_mp = conn.execute(
                text("SELECT id_mp FROM materiasprimas WHERE nombre_mp = :nombre"),
                {"nombre": nombre_mp}
            ).fetchone()

            if not result_mp:
                print(f"⚠️ Materia prima '{nombre_mp}' no encontrada para '{producto}'")
                continue

            id_mp = result_mp[0]

            # Insertar la fórmula
            conn.execute(
                text("""
                    INSERT INTO formulas (id_producto, id_mp, porcentaje)
                    VALUES (:id_producto, :id_mp, :porcentaje)
                """),
                {"id_producto": id_producto, "id_mp": id_mp, "porcentaje": porcentaje}
            )

            total_insertadas += 1

        if total_insertadas > 0:
            print(f"✅ '{producto}' actualizado con {total_insertadas} fórmulas.")
        else:
            print(f"⚠️ '{producto}' no tiene fórmulas válidas en el Excel.")

print("\n✅ Actualización completada.")
