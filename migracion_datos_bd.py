# clean_database.py
from database_manager import db

def limpiar_tablas_operativas():
    """Limpia las tablas de operaciones diarias"""
    tablas_limpiar = ['fondo', 'produccion', 'ventas', 'venta_reventa', 'ventas_archivadas']
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        print("🧹 LIMPIANDO TABLAS OPERATIVAS...")
        print("=" * 50)
        
        total_eliminados = 0
        for tabla in tablas_limpiar:
            # Contar registros antes de limpiar
            cursor.execute(f'SELECT COUNT(*) FROM "{tabla}"')
            count_antes = cursor.fetchone()[0]
            
            # Limpiar tabla
            cursor.execute(f'DELETE FROM "{tabla}"')
            
            # Contar registros después de limpiar
            cursor.execute(f'SELECT COUNT(*) FROM "{tabla}"')
            count_despues = cursor.fetchone()[0]
            
            eliminados = count_antes - count_despues
            total_eliminados += eliminados
            
            print(f"✅ {tabla}: {eliminados} registros eliminados")
        
        conn.commit()
        conn.close()
        
        print(f"\n📊 RESUMEN: {total_eliminados} registros eliminados de {len(tablas_limpiar)} tablas")
        print("🎯 Tablas operativas limpiadas exitosamente")
        
    except Exception as e:
        print(f"❌ Error limpiando tablas: {e}")

def limpiar_solo_clientes():
    """Limpia solo la tabla clientes"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        print("🧹 LIMPIANDO TABLA CLIENTES...")
        print("=" * 50)
        
        # Contar antes
        cursor.execute('SELECT COUNT(*) FROM "clientes"')
        count_antes = cursor.fetchone()[0]
        
        # Limpiar tabla
        cursor.execute('DELETE FROM "clientes"')
        
        # Contar después
        cursor.execute('SELECT COUNT(*) FROM "clientes"')
        count_despues = cursor.fetchone()[0]
        
        eliminados = count_antes - count_despues
        
        conn.commit()
        conn.close()
        
        print(f"✅ Clientes: {eliminados} registros eliminados")
        print("🎯 Tabla clientes limpiada exitosamente")
        
    except Exception as e:
        print(f"❌ Error limpiando clientes: {e}")

def limpiar_todo():
    """Limpia todas las tablas operativas y clientes"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        print("🧹 LIMPIANDO TODAS LAS TABLAS OPERATIVAS Y CLIENTES...")
        print("=" * 50)
        
        # Tablas a limpiar
        tablas = ['fondo', 'produccion', 'ventas', 'venta_reventa', 'ventas_archivadas', 'clientes']
        
        total_eliminados = 0
        for tabla in tablas:
            # Contar registros antes de limpiar
            cursor.execute(f'SELECT COUNT(*) FROM "{tabla}"')
            count_antes = cursor.fetchone()[0]
            
            # Limpiar tabla
            cursor.execute(f'DELETE FROM "{tabla}"')
            
            # Contar registros después de limpiar
            cursor.execute(f'SELECT COUNT(*) FROM "{tabla}"')
            count_despues = cursor.fetchone()[0]
            
            eliminados = count_antes - count_despues
            total_eliminados += eliminados
            
            print(f"✅ {tabla}: {eliminados} registros eliminados")
        
        conn.commit()
        conn.close()
        
        print(f"\n📊 RESUMEN: {total_eliminados} registros eliminados de {len(tablas)} tablas")
        print("🎯 Todas las tablas limpiadas exitosamente")
        
    except Exception as e:
        print(f"❌ Error limpiando todo: {e}")

def mostrar_estado_actual():
    """Muestra el estado actual de las tablas antes de limpiar"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        print("📊 ESTADO ACTUAL DE LAS TABLAS")
        print("=" * 50)
        
        tablas_verificar = [
            'fondo', 'produccion', 'ventas', 'venta_reventa', 
            'ventas_archivadas', 'clientes', 'productos', 
            'productosreventa', 'materiasprimas'
        ]
        
        for tabla in tablas_verificar:
            try:
                cursor.execute(f'SELECT COUNT(*) FROM "{tabla}"')
                count = cursor.fetchone()[0]
                print(f"   {tabla}: {count} registros")
            except:
                print(f"   {tabla}: No existe o error")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error mostrando estado: {e}")

def menu_principal():
    """Menú principal interactivo"""
    print("\n" + "=" * 60)
    print("🧹 SISTEMA DE LIMPIEZA DE BASE DE DATOS QUIMO")
    print("=" * 60)
    
    while True:
        print("\nOpciones disponibles:")
        print("1. 📊 Mostrar estado actual de las tablas")
        print("2. 🧹 Limpiar tablas operativas (fondo, producción, ventas)")
        print("3. 👥 Limpiar solo tabla clientes")
        print("4. 💥 Limpiar TODO (tablas operativas + clientes)")
        print("5. ❌ Salir")
        
        opcion = input("\nSelecciona opción (1-5): ").strip()
        
        if opcion == "1":
            mostrar_estado_actual()
        
        elif opcion == "2":
            print("\n⚠ ¿Estás seguro de limpiar las tablas operativas?")
            print("   Esto eliminará: fondo, producción, ventas, venta_reventa, ventas_archivadas")
            confirmar = input("   Escribe 'SI' para confirmar: ").strip().upper()
            if confirmar == "SI":
                limpiar_tablas_operativas()
            else:
                print("   Operación cancelada")
        
        elif opcion == "3":
            print("\n⚠ ¿Estás seguro de limpiar la tabla clientes?")
            confirmar = input("   Escribe 'SI' para confirmar: ").strip().upper()
            if confirmar == "SI":
                limpiar_solo_clientes()
            else:
                print("   Operación cancelada")
        
        elif opcion == "4":
            print("\n🚨 ¡ALTO PELIGRO! ¿Estás seguro de limpiar TODO?")
            print("   Esto eliminará: fondo, producción, ventas, venta_reventa, ventas_archivadas Y clientes")
            confirmar = input("   Escribe 'LIMPIAR TODO' para confirmar: ").strip().upper()
            if confirmar == "LIMPIAR TODO":
                limpiar_todo()
            else:
                print("   Operación cancelada")
        
        elif opcion == "5":
            print("👋 ¡Hasta luego!")
            break
        
        else:
            print("❌ Opción no válida")

if __name__ == "__main__":
    menu_principal()