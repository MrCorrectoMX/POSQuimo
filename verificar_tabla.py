# PARA_NUEVAS_PRESENTACIONES.py
from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///quimo.db", echo=True)

# FACTORES (capacidad + 10)
FACTORES = {
    "BARRIL 120 KG": 130,
    "COSTAL CON ETIQUETA": 35,
    "ENVASE ALCOHOLERO 1 L": 11,
    "ENVASE PET 1 L": 11,
    "ENVASE BOSTON 1 L": 11,
    "ENVASE PET 5 L": 15,
    "ENVASE PET 20 L": 30,
    "ENVASE MUESTRA 250 mL": 10.25,
    "ENVASE MUESTRA 500 mL": 10.5,
    "BOLSA BLANCA": 11,
    "BOLSA TRANSPARENTE": 11,
}

try:
    with engine.connect() as conn:
        with conn.begin():
            print("🚀 CALCULANDO PRECIOS PARA NUEVAS PRESENTACIONES...")
            
            # Solo calcular precios para presentaciones sin precio
            update_query = """
            UPDATE presentaciones 
            SET precio_venta = ROUND(
                (SELECT SUM(f.porcentaje * mp.costo_unitario_mp / 100) 
                 FROM formulas f JOIN materiasprimas mp ON f.id_mp = mp.id_mp 
                 WHERE f.id_producto = presentaciones.id_producto)
                + (costo_envase / CASE 
                    %s
                    ELSE 1 END
                ), 2)
            WHERE precio_venta IS NULL
            """
            
            # Construir los CASE para cada presentación
            cases = []
            for presentacion, factor in FACTORES.items():
                cases.append(f"WHEN nombre_presentacion = '{presentacion}' THEN {factor}")
            
            update_query = update_query % " ".join(cases)
            
            filas = conn.execute(text(update_query)).rowcount
            print(f"✅ {filas} nuevas presentaciones con precio calculado")

except Exception as e:
    print(f"❌ Error: {e}")

print("🎯 EJECUTA ESTO CUANDO AGREGUE NUEVAS PRESENTACIONES")