import psycopg2

try:
    conn = psycopg2.connect(
        host="192.168.1.24",
        port=5432,
        database="quimo_db",
        user="quimo_user",
        password="1234"
    )
    cursor = conn.cursor()
    
    # Verificar codificación de la base de datos
    cursor.execute("SELECT datname, encoding FROM pg_database WHERE datname = 'quimo_db';")
    db_info = cursor.fetchone()
    if db_info:
        print(f"Base de datos: {db_info[0]}")
        print(f"Codificación: {db_info[1]} (6 = UTF8)")
    
    # Verificar codificaciones del servidor y cliente
    cursor.execute("SHOW server_encoding;")
    print(f"Codificación del servidor: {cursor.fetchone()[0]}")
    
    cursor.execute("SHOW client_encoding;")
    print(f"Codificación del cliente: {cursor.fetchone()[0]}")
    
    conn.close()
    print("✅ Diagnóstico completado")
    
except Exception as e:
    print(f"❌ Error: {e}")