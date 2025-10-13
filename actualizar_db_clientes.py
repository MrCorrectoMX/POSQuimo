# verificar_formulas.py
from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///quimo.db")

print("🔎 Verificando fórmulas de productos...\n")

with engine.connect() as conn:
    # Obtener todos los productos
    productos = conn.execute(text("SELECT id_producto, nombre_producto FROM productos")).fetchall()

    for id_producto, nombre_producto in productos:
        print(f"📦 Producto: {nombre_producto} (ID: {id_producto})")
        
        # Obtener las materias primas y porcentaje para este producto
        sql_formula = """
        SELECT mp.nombre_mp, f.porcentaje
        FROM formulas f
        LEFT JOIN materiasprimas mp ON f.id_mp = mp.id_mp
        WHERE f.id_producto = :id_producto;
        """
        formulas = conn.execute(text(sql_formula), {"id_producto": id_producto}).fetchall()

        if not formulas:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
            print("   ❌ No tiene fórmula asignada.")
        else:
            for nombre_mp, porcentaje in formulas:
                print(f"   - {nombre_mp}: {porcentaje}%")

        print()
