from sqlalchemy import create_engine, text

# --- Configura tu conexión ---
# Ejemplo SQLite: "sqlite:///tu_base_de_datos.db"
# Ejemplo PostgreSQL: "postgresql+psycopg2://user:pass@localhost:5432/tu_bd"
engine = create_engine("sqlite:///quimo.db")  

# --- Lista de productos a verificar ---
lista_productos = [
    "AMINA JB", "DESENGRAS BIO 78", "AMINA JAF", "ENZIM REM", "ENZIM PEL", "ENZIM RND",
    "DESLIZANTE", "IMPEOIL SOFT", "IMPEACRIL AR", "IMPEHUM HB", "BACTERICIDA 80",
    "BACTERICIDA 60", "IMPEFAST FM", "SECUESTRON CC", "IMPEFAST GM", "RECURTAN JF 22",
    "IMPEFAST NP", "IMPEFAST NP C", "RECURTAN JF 95", "SULPHODEP 13", "DESENGRAS BIO 78 QC",
    "QUIMO OXILIFT", "DESENGRAS 05", "DESENGRAS PLUS", "PINOL", "PINOL CONCENTRADO",
    "FRICCION", "SARRIGEL", "MÁS NEGRO", "ACEITE PARA MOP", "CLORO CLEAN", 
    "CLORO CLEAN 8 %", "CLORO CLEAN 6 %", "JABÓN PARA TRASTES LÍQUIDO LIMÓN",
    "DETERGENTE LÍQUIDO PARA ROPA DE COLOR", "DETERCON", "IMPEFAST SP", "FANTÁSTICO PRIMAVERA",
    "FANTÁSTICO LIMÓN",
"FANTÁSTICO LAVANDA",
"FANTÁSTICO CANELA",
"FANTÁSTICO GREEN BAMBÚ",
"FANTÁSTICO CITRONELA",
"FANTÁSTICO MENTA",
"FANTÁSTICO TORONJA",
"FASCINANTE PRIMAVERA",
"FASCINANTE LIMÓN",
"FASCINANTE LAVANDA",
"FASCINANTE CANELA",
"FASCINANTE GREEN BAMBÚ",
"FASCINANTE CITRONELA",
"FASCINANTE MENTA",
"FASCINANTE TORONJA",
"SHAMPOO CON CERA",
"GEL ANTIBACTERIAL",
"SOSA LÍQUIDA",
"DESENGRAS 2000",
"JABÓN QUIMO LÍQUIDO",
"FINISH",
"FINISH RECARGADO",
"TIPO VANISH LÍQUIDO",
"FINATELA FLOR DE LUNA",
"FINATELA PRIMAVERA",
"AROMATIZANTE CITRONELA",
"AROMATIZANTE 500 mL",
"AROMATIZANTE RECARGADO",  
"VINIL INTERIORES",
"VINIL PARA LLANTAS",
"FRESH GLASS",
"MÁS COLOR",
"PINOL VERDE",
"CONCENTRADO FANTÁSTICO LIMÓN",
"CONCENTRADO FANTÁSTICO LAVANDA",
"CONCENTRADO FANTÁSTICO PRIMAVERA",
"CONCENTRADO FANTÁSTICO CANELA",
"CONCENTRADO FANTÁSTICO CITRONELA",
"CONCENTRADO FANTÁSTICO MENTA",
"CONCENTRADO FANTÁSTICO GREEN BAMBÚ",
"CONCENTRADO FANTÁSTICO TORONJA",
"CONCENTRADO FASCINANTE LIMÓN",
"CONCENTRADO FASCINANTE LAVANDA",
"CONCENTRADO FASCINANTE PRIMAVERA",
"CONCENTRADO FASCINANTE CANELA",
"CONCENTRADO FASCINANTE CITRONELA",
"CONCENTRADO FASCINANTE MENTA",
"CONCENTRADO FASCINANTE GREEN BAMBÚ",
"CONCENTRADO FASCINANTE TORONJA",
"FARAÓN",
"FULMINANTE",
"SUAVIZANTE DE ROPA",
"VELO ROSITA",
"JABÓN BARRA 400 g",
"JABÓN BARRA 180 G",
"JABÓN RAYADO 250 g",
"JABÓN RAYADO 1 Kg",
"JABÓN RAYADO 500 g",
"SAPONE DURAZNO",
"SAPONE MENTA",
"SAPONE MANZANA",
"SAPONE MARACUYÁ",
"SAPONE PALMOLIVE",
"SAPONE DOVE",
"SAPONE COCO",
"SAPONE GREEN BAMBU"
]

def obtener_productos_activos(table_name, nombre_col, estado_col):
    with engine.connect() as conn:
        query = text(f"SELECT {nombre_col} AS nombre FROM {table_name} WHERE {estado_col} = 1")
        result = conn.execute(query).fetchall()
        return [r[0].strip().upper() for r in result if r[0] and r[0].strip() != ""]

# Obtener productos activos de cada tabla
productos = obtener_productos_activos("productos", "nombre_producto", "estatus_producto")
productos_reventa = obtener_productos_activos("productosreventa", "nombre_prev", "estatus_prev")

# Preparar sets para comparación
set_productos = set(productos)
set_reventa = set(productos_reventa)
set_verificar = set([p.strip().upper() for p in lista_productos])

# Productos registrados en 'productos'
registrados_productos = set_verificar & set_productos

# Productos registrados en 'productosreventa'
registrados_reventa = set_verificar & set_reventa

# Productos NO registrados
no_registrados = set_verificar - (registrados_productos | registrados_reventa)

# Mostrar resultados
print("=== Productos registrados en 'productos' ✅ ===")
for p in sorted(registrados_productos):
    print(p)

print("\n=== Productos registrados en 'productosreventa' ✅ ===")
for p in sorted(registrados_reventa):
    print(p)

print("\n=== Productos NO registrados ❌ ===")
for p in sorted(no_registrados):
    print(p)