# main.py - Aplicación Quimo con PostgreSQL
from database_manager import db
from PyQt5.QtWidgets import QApplication
import sys
from ui.ui_inventario import InventarioApp



def main():
    print("🚀 Iniciando aplicación Quimo...")
    
    try:
        # Probar conexión
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Información del sistema
        cursor.execute("SELECT current_database(), version()")
        info = cursor.fetchone()
        print(f"✅ Conectado a: {info[0]}")
        
        # Listar algunas tablas disponibles
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()[:10]]  # Primeras 10 tablas
        print(f"📋 Tablas disponibles: {len(tables)}")
        for table in tables:
            print(f"   - {table}")
        
        # Ejemplo: contar productos
        try:
            cursor.execute("SELECT COUNT(*) FROM productos")
            product_count = cursor.fetchone()[0]
            print(f"📦 Total de productos: {product_count}")
        except:
            print("📦 No se pudo contar productos")
        
        cursor.close()
        conn.close()
        
        print("🎉 ¡Aplicación ejecutada correctamente!")
        
    except Exception as e:
        print(f"❌ Error en la aplicación: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = InventarioApp()
    ventana.show()
    sys.exit(app.exec())
