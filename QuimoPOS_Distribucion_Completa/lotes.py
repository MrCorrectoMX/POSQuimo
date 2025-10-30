from sqlalchemy import create_engine, text

# --- Conexión a SQLite ---
engine = create_engine("sqlite:///quimo.db")

# --- Lotes que ya tienes ---
lotes_existentes = [
    ("AMINA JB", "AMJB003-0259.1"),
    ("AMINA JAF", "AMJA002"),
    ("ENZIM REM", "EZRE030"),
    ("ENZIM PEL", "EZPE011"),
    ("ENZIM RND", "EZRN012"),
    ("DESENGRAS BIO 78", "DG78009-0261"),
    ("DESLIZANTE", "DSZT031-0260"),
    ("IMPEOIL SOFT", "IMSF020-0264"),
    ("IMPEHUM HB", "IMHB017-0264"),
    ("BACTERICIDA 80", "BT80004-0215"),
    ("BACTERICIDA 60", "BT80004-0260"),
    ("IMPEFAST FM", "IMFM035-222"),
    ("SECUESTRON CC", "SECC026-0238"),
    ("IMPEFAST GM", "IMPGM-0260"),
    ("IMPEFAST NP", "IMNP016-0246"),
    ("IMPEFAST NP C", "IMNP016-0259"),
    ("IMPEACRIL AR", "IMAR014-230"),
    ("SULPHODEP 13", "SLPH13-0252"),
    ("RECURTAN JF 95", "RE95023-020"),
    ("RECURTAN JF 22", "RE22104-023"),
    ("DESENGRAS BIO 78 QC", "DGQ78-0261"),
    ("QUIMO OXILIFT", "DMQB01-0180"),
    ("DESENGRAS 05", "DGQ78-0216"),
    ("PINOL", "PNLB-0250"),
    ("PINOL CONCENTRADO", "PNC-0252"),
    ("FRICCIÓN", "FRICCION-0230"),
    ("SARRIGEL", "SAGEL-0251"),
    ("MÁS NEGRO", "MASCN"),
    ("ACEITE PARA MOP", "ACPM-0195"),
    ("CLORO CLEAN", "CLC8-0257"),
    ("CLORO AL 8", "CLCP-0250"),
    ("CLORO AL 6", "CLC6-0250"),
    ("JABÓN PARA TRASTES LÍQUIDO LIMÓN", "JPTL-0260"),
    ("DETERGENTE LÍQUIDO PARA ROPA DE COLOR", "DLRC-358"),
    ("DETERCON", "DTCN-0260"),
    ("IMPEFAST SP", "IMSPST-0215"),
    ("FARAÓN", "FRN-0244"),
    ("FANTÁSTICO PRIMAVERA", "FANP-0250"),
    ("FANTÁSTICO LAVANDA", "FASL-0259"),
    ("FANTÁSTICO GREEN BAMBÚ", "FANGB-0232"),
    ("FANTÁSTICO LIMÓN", "FASLI-0250"),
    ("FANTÁSTICO TORONJA", "FANTR-0216"),
    ("FANTÁSTICO CANELA", "FANC-0205"),
    ("FANTÁSTICO MENTA", "FASM-0195"),
    ("FANTÁSTICO CITRONELA", "FASCI-0201"),
    ("FASCINANTE PRIMAVERA", "FASCPR-0203"),
    ("SHAMPOO CON CERA", "SPC-0208"),
    ("GEL ANTIBACTERIAL", "GELA-0187"),
    ("SOSA LÍQUIDA", "HDSD-0264"),
    ("SAPONE BLANCO", "SPM-0252"),
    ("SAPONE TRANSPARENTE", "SPMB-0250"),
    ("SAPONE ESPUMA", "SPNS-"),
    ("SAPONE DURAZNO", "SPND"),
    ("SAPONE MENTA", "SPMT"),
    ("SAPONE MANZANA", "SPMZ"),
    ("SAPONE MARACUYÁ", "SPMR"),
    ("SAPONE PALMOLIVE", "SPP"),
    ("SAPONE DOVE", "SPDV"),
    ("SAPONE COCO", "SPCC"),
    ("SAPONE GREEN BAMBU", "SPGB"),
    ("DESENGRAS 2000", "DSG2-0194"),
    ("DESENGRAS PLUS", "DGPLS-"),
    ("JABÓN QUIMO LÍQUIDO", "JQL-0260"),
    ("JABÓN QUIMO RAYADO", "JBRY"),
    ("JABÓN BARRA 400 g", "JBQ400"),
    ("JABÓN BARRA 180 G", "JBQ180"),
    ("JABÓN RAYADO 250 g", "JRQ250"),
    ("JABÓN RAYADO 1 Kg", "JRQ1"),
    ("JABÓN RAYADO 500 g", "JRQ500"),
    ("FINISH", "FINI-0201"),
    ("TIPO VANISH LÍQUIDO", "TPVN-0180"),
    ("FINATELA FLOR DE LUNA", "SVFL-0212"),
    ("FINATELA PRIMAVERA", "SVP-0187"),
    ("AROMATIZANTE CITRONELA", "AROMCT-0136.1"),
    ("AROMATIZANTE HUGO BOSS", "ARHB"),
    ("AROMATIZANTE ONE MILLION", "ARON"),
    ("AROMATIZANTE LAVANDA", "ARLV"),
    ("AROMATIZANTE GREEN BAMBU", "ARGB"),
    ("AROMATIZANTE LACOSTE BLANCO", "ARLB"),
    ("AROMATIZANTE SAUVAGE", "ARSV"),
    ("AROMATIZANTE CHANCE", "ARCH"),
    ("AROMATIZANTE RECARGADO", "AROMR-0232"),
    ("AROMATIZANTE RECARGADO HUGO BOSS", "AROMHB"),
    ("AROMATIZANTE RECARGADO LIMÓN", "AROMLI"),
    ("VINIL INTERIORES", "AVIN-0150"),
    ("VINIL PARA LLANTAS", "VNPLL-073"),
    ("FRESH GLASS", "FRSGL-0111"),
    ("MÁS COLOR", "MASC-0257"),
    ("PINOL VERDE", "PNLV-0231"),

]


with engine.begin() as conn:
    for nombre_producto, codigo_lote in lotes_existentes:
        # Buscar id del producto
        result = conn.execute(
            text("SELECT id_producto FROM productos WHERE nombre_producto = :nombre"),
            {"nombre": nombre_producto}
        ).fetchone()

        if result:
            id_producto = result[0]
            cantidad = 0  # <-- Aquí decides el valor inicial
            conn.execute(
                text(
                    "INSERT INTO lotes (id_producto, codigo_lote, cantidad) "
                    "VALUES (:id, :lote, :cantidad)"
                ),
                {"id": id_producto, "lote": codigo_lote, "cantidad": cantidad}
            )
            print(f"✅ Insertado lote {codigo_lote} para {nombre_producto}")
        else:
            print(f"⚠️ Producto no encontrado en BD: {nombre_producto}")
