# database_manager.py
import pg8000
import configparser
import sys

class DatabaseManager:
    def __init__(self):
        self.config = self.load_config()
    
    def load_config(self):
        """Cargar configuración desde config.ini"""
        config = configparser.ConfigParser()
        config.read('config.ini')
        
        return {
            'host': config['database']['host'],
            'port': int(config['database']['port']),
            'database': config['database']['dbname'],
            'user': config['database']['user'],
            'password': config['database']['password']
        }
    
    def get_connection(self):
        """Obtener conexión a PostgreSQL usando pg8000"""
        try:
            conn = pg8000.connect(**self.config)
            return conn
        except Exception as e:
            print(f"❌ Error de conexión: {e}")
            raise
    
    def test_connection(self):
        """Probar la conexión"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            return True
        except:
            return False

# Instancia global para usar en la aplicación
db = DatabaseManager()

if __name__ == "__main__":
    if db.test_connection():
        print("✅ ¡Sistema de base de datos listo!")
    else:
        print("❌ Error en la conexión")
