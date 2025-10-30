# ui/ui_panel_inferior_redisenado.py (VERSIÓN CON GESTIÓN DE PRESENTACIONES)

from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QMessageBox, QHBoxLayout, QTabWidget,
    QComboBox, QDialog, QFrame, QGroupBox, QSplitter, QScrollArea, QDateEdit
)
from PyQt5.QtCore import Qt, QDate
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
from .ui_deshacer_produccion import VentanaDeshacerProduccion
from .ui_gestion_presentaciones import GestionPresentacionesDialog  # NUEVO IMPORT



class TarjetaMetrica(QFrame):
    """Widget tipo tarjeta para mostrar métricas importantes"""
    def __init__(self, titulo, valor, color_fondo="#f8f9fa", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {color_fondo};
                border-radius: 8px;
                padding: 10px;
                border: 1px solid #dee2e6;
            }}
        """)
        
        layout = QVBoxLayout(self)
        self.titulo_label = QLabel(titulo)
        self.titulo_label.setStyleSheet("font-weight: bold; color: #6c757d;")
        self.valor_label = QLabel(valor)
        self.valor_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #343a40;")
        
        layout.addWidget(self.titulo_label)
        layout.addWidget(self.valor_label)
        layout.addStretch()


class PanelInferiorRedisenado(QWidget):
    def __init__(self, engine, refrescar_tabla_principal_callback=None):
        super().__init__()
        self.engine = engine
        self.refrescar_tabla_principal_callback = refrescar_tabla_principal_callback
        self.df_produccion = pd.DataFrame()
        self.df_mp = pd.DataFrame()
        self.df_reventa = pd.DataFrame()

        # Layout principal
        main_layout = QVBoxLayout(self)
        
        # --- Panel superior: Resumen y métricas ---
        self.panel_superior = QWidget()
        panel_superior_layout = QVBoxLayout(self.panel_superior)
        
        # Selector de período
        periodo_group = QGroupBox("Período de Análisis - Producción")
        periodo_layout = QHBoxLayout(periodo_group)
        
        periodo_layout.addWidget(QLabel("Desde:"))
        self.date_desde = QDateEdit()
        self.date_desde.setDate(QDate.currentDate().addDays(-7))
        self.date_desde.setCalendarPopup(True)
        periodo_layout.addWidget(self.date_desde)
        
        periodo_layout.addWidget(QLabel("Hasta:"))
        self.date_hasta = QDateEdit()
        self.date_hasta.setDate(QDate.currentDate())
        self.date_hasta.setCalendarPopup(True)
        periodo_layout.addWidget(self.date_hasta)
        
        self.btn_aplicar_fechas = QPushButton("Aplicar")
        self.btn_aplicar_fechas.clicked.connect(self.cargar_datos_desde_db)
        periodo_layout.addWidget(self.btn_aplicar_fechas)
        
        periodo_layout.addStretch()
        
        self.btn_exportar = QPushButton("Exportar Excel")
        self.btn_exportar.clicked.connect(self.exportar_a_excel)
        periodo_layout.addWidget(self.btn_exportar)
        
        panel_superior_layout.addWidget(periodo_group)
        
        # Tarjetas de métricas
        self.metricas_layout = QHBoxLayout()
        self.metrica_produccion = TarjetaMetrica("Productos Producidos", "0.00", "#e3f2fd")
        self.metrica_costo_produccion = TarjetaMetrica("Costo Producción", "$0.00", "#ffebee")
        self.metrica_stock_mp = TarjetaMetrica("Stock MP", "0.00", "#e8f5e9")
        self.metrica_stock_reventa = TarjetaMetrica("Stock Reventa", "0.00", "#fff3e0")
        
        self.metricas_layout.addWidget(self.metrica_produccion)
        self.metricas_layout.addWidget(self.metrica_costo_produccion)
        self.metricas_layout.addWidget(self.metrica_stock_mp)
        self.metricas_layout.addWidget(self.metrica_stock_reventa)
        
        panel_superior_layout.addLayout(self.metricas_layout)
        main_layout.addWidget(self.panel_superior)
        
        # --- Panel inferior: Tabs con detalles ---
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Pestaña de Producción
        self.tab_produccion = QWidget()
        self.tabs.addTab(self.tab_produccion, "Producción de Productos")
        tab_produccion_layout = QVBoxLayout(self.tab_produccion)
        
        # Tabla de producción con scroll
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.tabla_produccion = QTableWidget()
        scroll_area.setWidget(self.tabla_produccion)
        tab_produccion_layout.addWidget(scroll_area)
        
        self.tabla_produccion.setColumnCount(8)
        self.tabla_produccion.setHorizontalHeaderLabels(
            ["Fecha", "Producto (unidad)", "L", "Ma", "Mi", "J", "V", "Total Producido"]
        )
        self.tabla_produccion.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        # Botones de acción
        btn_layout = QHBoxLayout()
        btn_cargar = QPushButton("Recargar")
        btn_cargar.clicked.connect(self.cargar_datos_desde_db)
        btn_layout.addWidget(btn_cargar)
        
        self.btn_deshacer = QPushButton("Deshacer Producción")
        self.btn_deshacer.setStyleSheet("background-color: #5dade2; color: white;")
        self.btn_deshacer.clicked.connect(self.abrir_ventana_deshacer)
        btn_layout.addWidget(self.btn_deshacer)

        # NUEVO BOTÓN: Gestionar Presentaciones
        # En el __init__, cambia el botón a:
        self.btn_gestionar_presentaciones = QPushButton("Gestionar Presentaciones")
        self.btn_gestionar_presentaciones.setStyleSheet("background-color: #28a745; color: white;")
        self.btn_gestionar_presentaciones.clicked.connect(self.gestionar_presentaciones)
        btn_layout.addWidget(self.btn_gestionar_presentaciones)

        tab_produccion_layout.addLayout(btn_layout)
        
        # Pestaña de Inventario
        self.tab_inventario = QWidget()
        self.tabs.addTab(self.tab_inventario, "Inventario MP y Reventa")
        tab_inventario_layout = QVBoxLayout(self.tab_inventario)
        
        # Tabla de Materias Primas
        self.tabla_mp = QTableWidget()
        self.tabla_mp.setColumnCount(4)
        self.tabla_mp.setHorizontalHeaderLabels([
            "Materia Prima", "Stock", "Costo Unitario", "Costo Total"
        ])
        self.tabla_mp.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        
        # Tabla de Productos Reventa
        self.tabla_reventa = QTableWidget()
        self.tabla_reventa.setColumnCount(4)
        self.tabla_reventa.setHorizontalHeaderLabels([
            "Producto Reventa", "Stock", "Costo Compra", "Costo Total"
        ])
        self.tabla_reventa.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        
        # Layout para las dos tablas de inventario
        tab_inventario_layout.addWidget(QLabel("<b>Materias Primas:</b>"))
        tab_inventario_layout.addWidget(self.tabla_mp)
        tab_inventario_layout.addWidget(QLabel("<b>Productos de Reventa:</b>"))
        tab_inventario_layout.addWidget(self.tabla_reventa)
        
        # Cargar datos iniciales
        self.cargar_datos_desde_db()

    # NUEVO MÉTODO: Gestión de Presentaciones
    def gestionar_presentaciones(self):
        """Abre el diálogo para gestionar presentaciones - VERSIÓN SQLITE PURO"""
        current_row = self.tabla_produccion.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Selección requerida", 
                            "Por favor, seleccione un producto de la tabla de producción.")
            return

        producto_item = self.tabla_produccion.item(current_row, 1)
        if not producto_item:
            return

        producto_text = producto_item.text()
        producto_nombre = producto_text.split(" (")[0]

        try:
            # Obtener la ruta de la base de datos directamente
            db_path = str(self.engine.url).replace('sqlite:///', '')
            
            # Usar SQLite directamente para obtener datos
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # 1. Obtener el ID del producto
            cursor.execute("SELECT id_producto FROM productos WHERE nombre_producto = ?", (producto_nombre,))
            result = cursor.fetchone()
            if not result:
                QMessageBox.warning(self, "Error", "No se encontró el producto seleccionado.")
                conn.close()
                return
            producto_id = result[0]

            # 2. Obtener las presentaciones actuales
            cursor.execute("""
                SELECT id_presentacion, nombre_presentacion, factor, id_envase, costo_envase
                FROM presentaciones 
                WHERE id_producto = ?
                ORDER BY nombre_presentacion
            """, (producto_id,))
            
            presentaciones_actuales_raw = cursor.fetchall()
            presentaciones_actuales = [
                {
                    'id_presentacion': row[0],
                    'nombre_presentacion': row[1],
                    'factor': row[2],
                    'id_envase': row[3],
                    'costo_envase': row[4] or 0.0
                }
                for row in presentaciones_actuales_raw
            ]

            # 3. Obtener envases disponibles
            cursor.execute("""
                SELECT id_envase, nombre_envase, costo_envase
                FROM envases_etiquetas
                ORDER BY nombre_envase
            """)
            
            envases_disponibles_raw = cursor.fetchall()
            envases_disponibles = [
                {
                    'id_envase': row[0],
                    'nombre_envase': row[1],
                    'costo_envase': row[2] or 0.0
                }
                for row in envases_disponibles_raw
            ]

            conn.close()

            # 4. Mostrar diálogo
            dialogo = GestionPresentacionesDialog(
                producto_nombre, 
                producto_id, 
                presentaciones_actuales, 
                envases_disponibles, 
                self
            )
            
            if dialogo.exec_() == QDialog.Accepted:
                nuevas_presentaciones = dialogo.get_presentaciones()
                
                # 5. Guardar usando SQLite directamente
                self._guardar_con_sqlite_directo(db_path, producto_id, nuevas_presentaciones, presentaciones_actuales)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron gestionar las presentaciones: {e}")

    def _guardar_con_sqlite_directo(self, db_path, producto_id, nuevas_presentaciones, presentaciones_actuales):
        """Guarda presentaciones usando SQLite directamente - SIN SQLAlchemy"""
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            try:
                # Identificar presentaciones a eliminar
                nombres_actuales = {pres['nombre_presentacion'] for pres in presentaciones_actuales}
                nombres_nuevos = {pres['nombre_presentacion'] for pres in nuevas_presentaciones}
                
                presentaciones_a_eliminar = nombres_actuales - nombres_nuevos
                for nombre_eliminar in presentaciones_a_eliminar:
                    cursor.execute(
                        "DELETE FROM presentaciones WHERE id_producto = ? AND nombre_presentacion = ?",
                        (producto_id, nombre_eliminar)
                    )

                # Insertar o actualizar presentaciones
                for pres in nuevas_presentaciones:
                    # Verificar si ya existe
                    cursor.execute(
                        "SELECT id_presentacion FROM presentaciones WHERE id_producto = ? AND nombre_presentacion = ?",
                        (producto_id, pres['nombre_presentacion'])
                    )
                    existe = cursor.fetchone()

                    if existe:
                        # Actualizar
                        cursor.execute(
                            "UPDATE presentaciones SET factor = ?, id_envase = ?, costo_envase = ? WHERE id_presentacion = ?",
                            (pres['factor'], pres['id_envase'], pres['costo_envase'], existe[0])
                        )
                    else:
                        # Insertar nuevo
                        cursor.execute(
                            "INSERT INTO presentaciones (id_producto, nombre_presentacion, factor, id_envase, costo_envase) VALUES (?, ?, ?, ?, ?)",
                            (producto_id, pres['nombre_presentacion'], pres['factor'], pres['id_envase'], pres['costo_envase'])
                        )
                
                conn.commit()
                
                QMessageBox.information(self, "Éxito", "Presentaciones actualizadas correctamente.")
                self.cargar_datos_desde_db()
                
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron guardar las presentaciones: {e}")

    def _guardar_presentaciones_simple(self, producto_id, nuevas_presentaciones, presentaciones_actuales):
        """Guarda presentaciones - VERSIÓN CONEXIÓN DIRECTA"""
        try:
            # Obtener una conexión directa del pool
            raw_connection = self.engine.raw_connection()
            try:
                cursor = raw_connection.cursor()
                
                # Identificar presentaciones a eliminar
                nombres_actuales = {pres['nombre_presentacion'] for pres in presentaciones_actuales}
                nombres_nuevos = {pres['nombre_presentacion'] for pres in nuevas_presentaciones}
                
                presentaciones_a_eliminar = nombres_actuales - nombres_nuevos
                for nombre_eliminar in presentaciones_a_eliminar:
                    cursor.execute(
                        "DELETE FROM presentaciones WHERE id_producto = ? AND nombre_presentacion = ?",
                        (producto_id, nombre_eliminar)
                    )

                # Insertar o actualizar presentaciones
                for pres in nuevas_presentaciones:
                    cursor.execute(
                        "SELECT id_presentacion FROM presentaciones WHERE id_producto = ? AND nombre_presentacion = ?",
                        (producto_id, pres['nombre_presentacion'])
                    )
                    existe = cursor.fetchone()

                    if existe:
                        cursor.execute(
                            "UPDATE presentaciones SET factor = ?, id_envase = ?, costo_envase = ? WHERE id_presentacion = ?",
                            (pres['factor'], pres['id_envase'], pres['costo_envase'], existe[0])
                        )
                    else:
                        cursor.execute(
                            "INSERT INTO presentaciones (id_producto, nombre_presentacion, factor, id_envase, costo_envase) VALUES (?, ?, ?, ?, ?)",
                            (producto_id, pres['nombre_presentacion'], pres['factor'], pres['id_envase'], pres['costo_envase'])
                        )
                
                raw_connection.commit()
                
                QMessageBox.information(self, "Éxito", "Presentaciones actualizadas correctamente.")
                self.cargar_datos_desde_db()
                
            except Exception as e:
                raw_connection.rollback()
                raise e
            finally:
                raw_connection.close()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron guardar las presentaciones: {e}")




    def abrir_ventana_deshacer(self):
        """Abre la ventana de diálogo para seleccionar y deshacer una producción."""
        dialogo = VentanaDeshacerProduccion(self.engine, self)
        
        if dialogo.exec_() == QDialog.Accepted:
            print("Acción de deshacer completada. Refrescando datos...")
            self.cargar_datos_desde_db()
            if self.refrescar_tabla_principal_callback:
                self.refrescar_tabla_principal_callback()

    def registrar_produccion_con_costo(self, producto_nombre, cantidad, area, costo):
        """Registra producción de productos terminados"""
        fecha_actual = datetime.now().date()
        dias_semana = ["L", "Ma", "Mi", "J", "V"]
        dia_str = dias_semana[fecha_actual.weekday()]
        
        try:
            with self.engine.connect() as conn:
                with conn.begin() as trans:
                    query_id = text("SELECT id_producto FROM productos WHERE nombre_producto = :nombre")
                    result = conn.execute(query_id, {"nombre": producto_nombre}).fetchone()
                    if not result:
                        QMessageBox.critical(self, "Error", f"No se encontró el producto '{producto_nombre}'.")
                        return
                    producto_id = result[0]

                    query_insert = text("""
                        INSERT INTO produccion (producto_id, cantidad, fecha, dia, area, costo)
                        VALUES (:producto_id, :cantidad, :fecha, :dia, :area, :costo)
                        ON CONFLICT(fecha, producto_id) DO UPDATE SET
                        cantidad = produccion.cantidad + :cantidad,
                        costo = produccion.costo + :costo;
                    """)
                    conn.execute(query_insert, {
                        "producto_id": producto_id,
                        "cantidad": cantidad, "fecha": fecha_actual, "dia": dia_str,
                        "area": area, "costo": costo
                    })
            
            QMessageBox.information(self, "Éxito", f"Producción de '{producto_nombre}' registrada.")
            self.cargar_datos_desde_db()
            
        except Exception as e:
            QMessageBox.critical(self, "Error de Base de Datos", f"Error al registrar producción: {e}")

    def cargar_datos_desde_db(self):
        """Carga los datos desde la base de datos"""
        try:
            fecha_desde = self.date_desde.date().toPyDate()
            fecha_hasta = self.date_hasta.date().toPyDate()
            
            # 1. CARGAR PRODUCCIÓN
            query_produccion = text("""
                SELECT 
                    p.nombre_producto AS producto, 
                    p.unidad_medida_producto AS unidad,
                    pr.dia, pr.fecha, pr.cantidad, pr.costo, pr.area
                FROM produccion pr
                JOIN productos p ON pr.producto_id = p.id_producto
                WHERE pr.fecha BETWEEN :start_date AND :end_date
                ORDER BY pr.fecha, p.nombre_producto
            """)
            
            # PROBLEMA: pandas.read_sql_query puede estar iniciando transacciones automáticamente
            self.df_produccion = pd.read_sql_query(
                query_produccion, self.engine, 
                params={"start_date": fecha_desde, "end_date": fecha_hasta}
            )

            # 2. CARGAR MATERIAS PRIMAS (stock actual)
            query_mp = text("""
                SELECT 
                    nombre_mp,
                    cantidad_comprada_mp as stock,
                    costo_unitario_mp as costo_unitario,
                    (cantidad_comprada_mp * costo_unitario_mp) as costo_total
                FROM materiasprimas
                WHERE estatus_mp = 1
                ORDER BY nombre_mp
            """)
            
            self.df_mp = pd.read_sql_query(query_mp, self.engine)

            # 3. CARGAR PRODUCTOS REVENTA (stock actual)
            query_reventa = text("""
                SELECT 
                    nombre_prev,
                    cantidad_prev as stock,
                    precio_compra as costo_unitario,
                    (cantidad_prev * precio_compra) as costo_total
                FROM productosreventa
                WHERE estatus_prev = 1
                ORDER BY nombre_prev
            """)
            
            self.df_reventa = pd.read_sql_query(query_reventa, self.engine)

            # Actualizar todas las vistas
            self.actualizar_vista_produccion()
            self.actualizar_vista_inventario()
            self.actualizar_metricas()

        except Exception as e:
            QMessageBox.critical(self, "Error de Carga", f"No se pudo leer la base de datos: {e}")

    def actualizar_metricas(self):
        """Actualiza las métricas globales"""
        # Métricas de producción
        total_produccion = self.df_produccion['cantidad'].sum() if not self.df_produccion.empty else 0
        costo_produccion = self.df_produccion['costo'].sum() if not self.df_produccion.empty else 0
        
        # Métricas de inventario
        total_stock_mp = self.df_mp['stock'].sum() if not self.df_mp.empty else 0
        total_stock_reventa = self.df_reventa['stock'].sum() if not self.df_reventa.empty else 0
        
        self.metrica_produccion.valor_label.setText(f"{total_produccion:,.2f}")
        self.metrica_costo_produccion.valor_label.setText(f"${costo_produccion:,.2f}")
        self.metrica_stock_mp.valor_label.setText(f"{total_stock_mp:,.2f}")
        self.metrica_stock_reventa.valor_label.setText(f"{total_stock_reventa:,.2f}")

    def actualizar_vista_produccion(self):
        """Actualiza la tabla de producción"""
        if self.df_produccion.empty:
            self.tabla_produccion.setRowCount(0)
            return
            
        df = self.df_produccion.copy()
        df_pivot = df.pivot_table(
            index=["producto", "unidad"], 
            columns="dia", 
            values="cantidad", 
            aggfunc='sum'
        ).fillna(0)
        
        df_totales = df.groupby(['producto', 'unidad']).agg(
            Total_Cantidad=('cantidad', 'sum'),
            Fecha=('fecha', 'max')
        ).reset_index()

        df_merged = pd.merge(df_pivot.reset_index(), df_totales, on=['producto', 'unidad'])

        dias_orden = ["L", "Ma", "Mi", "J", "V", "S", "D"]
        for d in dias_orden:
            if d not in df_merged.columns: 
                df_merged[d] = 0
        
        df_merged = df_merged.rename(columns={'Total_Cantidad': 'Total'})
        
        self.mostrar_tabla_produccion(df_merged)

    def actualizar_vista_inventario(self):
        """Actualiza las tablas de inventario"""
        # Materias Primas
        if not self.df_mp.empty:
            self.tabla_mp.setRowCount(len(self.df_mp))
            for i, row in self.df_mp.iterrows():
                self.tabla_mp.setItem(i, 0, QTableWidgetItem(str(row['nombre_mp'])))
                self.tabla_mp.setItem(i, 1, QTableWidgetItem(f"{row['stock']:.2f}"))
                self.tabla_mp.setItem(i, 2, QTableWidgetItem(f"${row['costo_unitario']:,.2f}"))
                self.tabla_mp.setItem(i, 3, QTableWidgetItem(f"${row['costo_total']:,.2f}"))
        else:
            self.tabla_mp.setRowCount(0)
        
        # Productos Reventa
        if not self.df_reventa.empty:
            self.tabla_reventa.setRowCount(len(self.df_reventa))
            for i, row in self.df_reventa.iterrows():
                self.tabla_reventa.setItem(i, 0, QTableWidgetItem(str(row['nombre_prev'])))
                self.tabla_reventa.setItem(i, 1, QTableWidgetItem(f"{row['stock']:.2f}"))
                self.tabla_reventa.setItem(i, 2, QTableWidgetItem(f"${row['costo_unitario']:,.2f}"))
                self.tabla_reventa.setItem(i, 3, QTableWidgetItem(f"${row['costo_total']:,.2f}"))
        else:
            self.tabla_reventa.setRowCount(0)

    def mostrar_tabla_produccion(self, df):
        """Muestra la tabla de producción"""
        self.tabla_produccion.clearContents()
        self.tabla_produccion.setRowCount(0)
        
        if df.empty:
            return
            
        df['producto_unidad'] = df['producto'] + " (" + df['unidad'] + ")"
        self.tabla_produccion.setRowCount(df.shape[0])

        for i, row in df.iterrows():
            fecha_str = pd.to_datetime(row["Fecha"]).strftime('%Y-%m-%d') if pd.notna(row["Fecha"]) else "N/A"
            self.tabla_produccion.setItem(i, 0, QTableWidgetItem(fecha_str))
            self.tabla_produccion.setItem(i, 1, QTableWidgetItem(row["producto_unidad"]))
            
            dias_ordenados = ["L", "Ma", "Mi", "J", "V", "S", "D", "Total"]
            for j, dia in enumerate(dias_ordenados, start=2):
                val = row.get(dia, 0)
                item = QTableWidgetItem(f"{val:.2f}")
                self.tabla_produccion.setItem(i, j, item)

    def exportar_a_excel(self):
        """Exporta los datos a Excel"""
        try:
            fecha_actual = datetime.now().strftime("%Y-%m-%d")
            nombre_archivo = f"reporte_produccion_{fecha_actual}.xlsx"
            
            with pd.ExcelWriter(nombre_archivo, engine='openpyxl') as writer:
                if not self.df_produccion.empty:
                    self.df_produccion.to_excel(writer, sheet_name='Producción', index=False)
                
                if not self.df_mp.empty:
                    self.df_mp.to_excel(writer, sheet_name='Materias Primas', index=False)
                
                if not self.df_reventa.empty:
                    self.df_reventa.to_excel(writer, sheet_name='Productos Reventa', index=False)
                
                # Crear hoja de resumen
                resumen_data = {
                    'Métrica': ['Productos Producidos', 'Costo Producción', 'Stock MP', 'Stock Reventa'],
                    'Valor': [
                        self.metrica_produccion.valor_label.text(),
                        self.metrica_costo_produccion.valor_label.text(),
                        self.metrica_stock_mp.valor_label.text(),
                        self.metrica_stock_reventa.valor_label.text()
                    ]
                }
                pd.DataFrame(resumen_data).to_excel(writer, sheet_name='Resumen', index=False)
            
            QMessageBox.information(self, "Éxito", f"Reporte exportado como {nombre_archivo}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar el reporte: {e}")

