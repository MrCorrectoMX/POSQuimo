import sqlite3
from difflib import get_close_matches

# Conexión a la base de datos
conn = sqlite3.connect("quimo.db")
cursor = conn.cursor()

# Diccionario de productos con su precio de compra
productos_reventa_compras = {
    "PAPEL HIGIENICO 180 MTS C/12 PZS": 264.45,
    "TOALLA ROLLO 160 MTS C/6 PZS": 289.34,
    "DALITAS TOALLA INTERDOBLAS C/20 PZS": 215.00,
    "TOALLA ROLLO TORK BCA. 6/180 MTS": 0.00,
    "TOALLA INTERDOBLADA CAFE": 260.08,
    "BASE P/MOP 60 CM": 0.00,
    "FUNDA P/MOP 60 CM": 32.50,
    "BASE P/MOP 90 CM": 84.50,
    "FUNDA P/MOP 90 CM": 41.60,
    "BASE P/MOP 120 CM": 94.50,
    "FUNDA P/MOP 120 CM": 62.40,
    "SCOTT ROLLOS DE TOALLAS": 0.00,
    "FIBRAS METALICA GRANDE": 5.9904,
    "FIBRAS DOBLE CARA ECONOMICA": 0.00,
    "FIBRA-ESPONJA SCOTCH BRITE P94": 15.61,
    "FIBRA BLANCA SCOTCH BRITE P66": 10.98,
    "FIBRA NEGRA SCOTCH BRITE P76": 16.34,
    "FIBRA VERDE SCOTCH BRITE P96": 12.40,
    "FIBRA ACERO INOXIDABLE CHICA": 7.59,
    "FIBRA ACERO INOXIDABLE GRANDE": 0.00,
    "BOLSA NEGRA 60 X 90": 27.61,
    "BOLSA NEGRA 90 X 120": 27.63,
    "BOLSA NEGRA TIPO CAMISETA 30 X 60": 36.78,
    "BOLSA TIPO CAMISETA 20 X 50": 38.24,
    "BOLSA TRANSPARENTE 90 X 120": 0.00,
    "ROLLO DE BOLSA NEGRA 90X120 CM": 34.52,
    "ROLLO DE BOLSA NEGRA 50X70 CM": 34.15,
    "ROLLO DE BOLSA NEGRA 60X90 CM": 38.24,
    "ROLLO DE BOLSA TRNASPARENTE 20X30 CM": 0.00,
    "TAPETE PARA MINGITORIO ANTI-SALPICADURA": 56.40,
    "PASTILLA AROMATIZANTE PARA WC WIESE": 9.50,
    "PASTILLA AROMATIZANTE PARA WC AZULES WIESE": 10.41,
    "PASTILLAS DE CLORO": 129.31,
    "AROMATIZANTE EN AEROSOL WIESE 400 ML": 37.64,
    "PAR DE GUANTES ROJO CH": 12.50,
    "PAR DE GUANTES ROJO MD": 12.50,
    "PAR DE GUANTES ROJO GD": 12.50,
    "PAR DE GUANTES VERDE CH": 28.00,
    "PAR DE GUANTES VERDE MD": 28.00,
    "PAR DE GUANTES VERDE GD": 28.00,
    "CUBETA FLEXIBLE #18": 61.12,
    "CUBETA ECO STA MARIA #18": 0.00,
    "ATOMIZADOR USO RUDO SIN ENVASE": 18.10,
    "ATOMIZADOR USO RUDO CON ENVASE": 0.00,
    "BOMBA PARA WC": 9.36,
    "CEPILLO PARA WC C/BASE": 25.86,
    "EMBUDO CHICO": 10.70,
    "EMBUDO MEDIANO": 30.00,
    "EMBUDO GRANDE": 37.20,
    "FRANELA MICROFIBRA 40 X 40 CM": 8.88,
    "RECOGEDOR DE PLASTICO ECONOMICO": 9.0517,
    "RECOGEDOR PLASTICO PERICO": 31.03,
    "RECOGEDOR DE METAL": 0.00,
    "RECOGEDOR DE METAL REFORZADO (INDUSTRIAL)": 38.98,
    "CEPILLO SUPER GRANDE": 35.50,
    "CEPILLO ECONOMICO": 31.00,
    "ABANICO LARGO GRANDE": 35.50,
    "PLUMERO": 27.10,
    "MIROSLAVA PAÑOS": 0.00,
    "FRANELA DE MICROFIBRA ROJA": 9.00,
    "CEPILLOS DE MANO": 0.00,
    "MICROFIBRA TELA MED": 78.00,
    "MICROFIBRA TELA GDE": 0.00,
    "PABILO MED": 39.00,
    "PABILO GDE": 0.00,
    "PABILAZA MED": 39.00,
    "PABILAZA GDE": 0.00,
    "HILAZA MED": 40.50,
    "HILAZA GDE": 0.00,
    "HILAZA COLORES": 43.50,
    "GASA (RAYON) MED": 0.00,
    "GASA (RAYON) GDE": 0.00,
    "MICROFIBRA ESPAÑOLA MED": 81.50,
    "MICROFIBRA ESPAÑOLA GDE": 0.00,
    "CEPILLO PARA TALLAR": 34.00,
    "JALADOR DE VIDRIO C/ESPONJA": 27.94,
    "JALADOR DE PISO 40 CM": 36.20,
    "JALADOR DE PISO 50 CM": 37.00,
    "JALADOR DE PISO 1 M REFORZADO": 207.00
}


# Obtener lista de productos existentes
def obtener_productos_reventa():
    cursor.execute("SELECT nombre_prev FROM productosreventa")
    return [row[0] for row in cursor.fetchall()]

# Buscar coincidencia por nombre
def encontrar_coincidencia(nombre, lista):
    coincidencias = get_close_matches(nombre, lista, n=1, cutoff=0.7)
    return coincidencias[0] if coincidencias else None

# Procesar los productos y agregarlos si no existen
def procesar_productos_reventa(diccionario_productos):
    lista_prod_reventa = obtener_productos_reventa()
    print("Consultando existencias en BD...\n")

    for nombre_prod, precio_compra in diccionario_productos.items():
        coincidencia_prod = encontrar_coincidencia(nombre_prod, lista_prod_reventa)

        if not coincidencia_prod:
            print(f" -> Producto NO EXISTE en BD: '{nombre_prod}'")
            print(f"    Insertando con precio de compra {precio_compra}...")

            cursor.execute("""
                INSERT INTO productosreventa 
                (nombre_prev, unidad_medida_prev, estatus_prev, proveedor, area_prev, cantidad_prev, precio_compra_prev, precio_venta_prev)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (nombre_prod, "pz", 1, "DESCONOCIDO", "QUIMO CLEAN", 0, precio_compra, 0))

            conn.commit()
            estado = "INSERTADO"
        else:
            print(f" -> Producto EXISTE en BD: '{coincidencia_prod}'")
            estado = "EXISTE"

        print(f"   Resultado: {nombre_prod} | Precio compra: {precio_compra} | Estado: {estado}\n")

if __name__ == "__main__":
    procesar_productos_reventa(productos_reventa_compras)
    conn.close()
    print("\n✅ Proceso completado.")
