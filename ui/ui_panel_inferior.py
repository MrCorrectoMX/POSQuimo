# ui/ui_panel_inferior_redisenado.py (VERSIÓN CORREGIDA)

from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QMessageBox, QHBoxLayout, QTabWidget,
    QComboBox, QDialog, QFrame, QGroupBox, QSplitter, QScrollArea, QDateEdit
)
from PyQt5.QtCore import Qt, QDate
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from sqlalchemy import text
from .ui_deshacer_produccion import VentanaDeshacerProduccion


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

        # Layout principal con splitter para mayor flexibilidad
        main_layout = QVBoxLayout(self)
        self.splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(self.splitter)
        
        # --- Panel superior: Resumen y métricas ---
        self.panel_superior = QWidget()
        self.panel_superior_layout = QVBoxLayout(self.panel_superior)
        
        # Selector de período mejorado
        periodo_group = QGroupBox("Período de Análisis")
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
        
        self.btn_exportar = QPushButton("📊 Exportar Excel")
        self.btn_exportar.clicked.connect(self.exportar_a_excel)
        periodo_layout.addWidget(self.btn_exportar)
        
        self.panel_superior_layout.addWidget(periodo_group)
        
        # Tarjetas de métricas
        self.metricas_layout = QHBoxLayout()
        self.metrica_produccion = TarjetaMetrica("Producción Total", "0.00", "#e3f2fd")
        self.metrica_costo = TarjetaMetrica("Costo Total", "$0.00", "#ffebee")
        self.metrica_venta = TarjetaMetrica("Venta Total", "$0.00", "#e8f5e9")
        self.metrica_ganancia = TarjetaMetrica("Ganancia Total", "$0.00", "#fff3e0")
        
        self.metricas_layout.addWidget(self.metrica_produccion)
        self.metricas_layout.addWidget(self.metrica_costo)
        self.metricas_layout.addWidget(self.metrica_venta)
        self.metricas_layout.addWidget(self.metrica_ganancia)
        
        self.panel_superior_layout.addLayout(self.metricas_layout)
        self.splitter.addWidget(self.panel_superior)
        
        # --- Panel inferior: Tabs con detalles ---
        self.tabs = QTabWidget()
        self.splitter.addWidget(self.tabs)
        self.splitter.setSizes([200, 600])
        
        # Pestaña de Producción
        self.tab_produccion = QWidget()
        self.tabs.addTab(self.tab_produccion, "📋 Producción Detallada")
        self.tab_produccion.setLayout(QVBoxLayout())
        
        # Tabla de producción con scroll
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.tabla_produccion = QTableWidget()
        scroll_area.setWidget(self.tabla_produccion)
        self.tab_produccion.layout().addWidget(scroll_area)
        
        self.tabla_produccion.setColumnCount(13)
        self.tabla_produccion.setHorizontalHeaderLabels(
            ["Fecha", "Producto (unidad)", "L", "Ma", "Mi", "J", "V", "S", "D", "Total", "Costo Total", "Precio Venta", "Ganancia"]
        )
        self.tabla_produccion.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        # Botones de acción
        btn_layout = QHBoxLayout()
        btn_cargar = QPushButton("🔄 Recargar")
        btn_cargar.clicked.connect(self.cargar_datos_desde_db)
        btn_layout.addWidget(btn_cargar)
        
        self.btn_corte_semana = QPushButton("📅 Corte Semanal")
        self.btn_corte_semana.setStyleSheet("background-color: #f5b041; color: black;")
        self.btn_corte_semana.clicked.connect(self.realizar_corte_semana)
        btn_layout.addWidget(self.btn_corte_semana)

        self.btn_deshacer = QPushButton("↩️ Deshacer Producción")
        self.btn_deshacer.setStyleSheet("background-color: #5dade2; color: white;")
        self.btn_deshacer.clicked.connect(self.abrir_ventana_deshacer)
        btn_layout.addWidget(self.btn_deshacer)

        self.tab_produccion.layout().addLayout(btn_layout)
        
        # Cargar datos iniciales
        self.cargar_datos_desde_db()

    def realizar_corte_semana(self):
        """
        Marca todos los registros de producción abiertos como 'cerrados'.
        """
        confirm = QMessageBox.question(self, "Confirmar Corte",
                                       "¿Está seguro de que desea cerrar la semana actual?\n"
                                       "Esto reiniciará la vista de 'Última semana'. Esta acción no se puede deshacer.",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if confirm == QMessageBox.StandardButton.No:
            return

        try:
            with self.engine.connect() as conn:
                with conn.begin() as trans:
                    query = text("UPDATE produccion SET semana_cerrada = 1 WHERE semana_cerrada = 0")
                    result = conn.execute(query)
                    
                    QMessageBox.information(self, "Éxito",
                                            f"Corte de semana realizado.\n"
                                            f"{result.rowcount} registros de producción han sido archivados.")
            
            # Recargamos los datos para que la vista se actualice
            self.cargar_datos_desde_db()
            if self.refrescar_tabla_principal_callback:
                self.refrescar_tabla_principal_callback()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo realizar el corte de semana:\n{e}")

    def abrir_ventana_deshacer(self):
        """Abre la ventana de diálogo para seleccionar y deshacer una producción."""
        dialogo = VentanaDeshacerProduccion(self.engine, self)
        
        if dialogo.exec_() == QDialog.Accepted:
            print("Acción de deshacer completada. Refrescando datos...")
            # Si la acción fue exitosa, recargamos todas las vistas
            self.cargar_datos_desde_db()
            if self.refrescar_tabla_principal_callback:
                self.refrescar_tabla_principal_callback()

    def registrar_produccion_con_costo(self, producto_nombre, cantidad, area, costo):
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
        """Carga los datos desde la base de datos según el período seleccionado"""
        try:
            fecha_desde = self.date_desde.date().toPyDate()
            fecha_hasta = self.date_hasta.date().toPyDate()
            
            query = text("""
                SELECT 
                    p.nombre_producto AS producto, p.unidad_medida_producto AS unidad,
                    pr.dia, pr.fecha, pr.cantidad, pr.costo, pr.area
                FROM produccion pr
                JOIN productos p ON pr.producto_id = p.id_producto
                WHERE pr.fecha BETWEEN :start_date AND :end_date
                AND pr.semana_cerrada = 0
            """)
            
            self.df_produccion = pd.read_sql_query(
                query, self.engine, 
                params={"start_date": fecha_desde, "end_date": fecha_hasta}
            )

            if self.df_produccion.empty:
                self.tabla_produccion.setRowCount(0)
                self.actualizar_metricas(0, 0, 0, 0)
                return

            self.actualizar_vista_produccion()

        except Exception as e:
            QMessageBox.critical(self, "Error de Carga", f"No se pudo leer la base de datos: {e}")

    def actualizar_metricas(self, total_produccion, total_costo, total_venta, total_ganancia):
        """Actualiza las tarjetas de métricas con los nuevos valores"""
        self.metrica_produccion.valor_label.setText(f"{total_produccion:,.2f}")
        self.metrica_costo.valor_label.setText(f"${total_costo:,.2f}")
        self.metrica_venta.valor_label.setText(f"${total_venta:,.2f}")
        self.metrica_ganancia.valor_label.setText(f"${total_ganancia:,.2f}")

    def actualizar_vista_produccion(self):
        """Actualiza la tabla de producción y las métricas"""
        df = self.df_produccion.copy()
        df_pivot = df.pivot_table(
            index=["producto", "unidad"], 
            columns="dia", 
            values="cantidad", 
            aggfunc='sum'
        ).fillna(0)
        
        df_totales = df.groupby(['producto', 'unidad']).agg(
            Total_Cantidad=('cantidad', 'sum'),
            Total_Costo=('costo', 'sum'),
            Fecha=('fecha', 'max')
        ).reset_index()

        df_merged = pd.merge(df_pivot.reset_index(), df_totales, on=['producto', 'unidad'])

        dias_orden = ["L", "Ma", "Mi", "J", "V", "S", "D"]
        for d in dias_orden:
            if d not in df_merged.columns: 
                df_merged[d] = 0
        
        df_merged = df_merged.rename(columns={'Total_Cantidad': 'Total'})
        df_merged['Costo Total'] = df_merged['Total_Costo']
        df_merged["Precio Venta"] = df_merged["Costo Total"] * 1.30
        df_merged["Ganancia"] = df_merged["Precio Venta"] - df_merged["Costo Total"]
        
        self.mostrar_tabla_produccion(df_merged)
        
        # Actualizar métricas
        total_produccion = df_merged['Total'].sum()
        total_costo = df_merged['Costo Total'].sum()
        total_venta = df_merged['Precio Venta'].sum()
        total_ganancia = df_merged['Ganancia'].sum()
        
        self.actualizar_metricas(total_produccion, total_costo, total_venta, total_ganancia)

    def mostrar_tabla_produccion(self, df):
        # Forzamos un limpiado completo de la tabla antes de redibujarla.
        self.tabla_produccion.clearContents()
        self.tabla_produccion.setRowCount(0)
        df['producto_unidad'] = df['producto'] + " (" + df['unidad'] + ")"
        self.tabla_produccion.setRowCount(df.shape[0])
        total_produccion, total_costo, total_venta, total_ganancia = 0, 0, 0, 0

        for i, row in df.iterrows():
            fecha_str = pd.to_datetime(row["Fecha"]).strftime('%Y-%m-%d')
            self.tabla_produccion.setItem(i, 0, QTableWidgetItem(fecha_str))
            
            self.tabla_produccion.setItem(i, 1, QTableWidgetItem(row["producto_unidad"]))
            
            dias_ordenados = ["L", "Ma", "Mi", "J", "V", "S", "D", "Total"]
            for j, dia in enumerate(dias_ordenados, start=2):
                val = row.get(dia, 0)
                item = QTableWidgetItem(f"{val:.2f}")
                self.tabla_produccion.setItem(i, j, item)
                if dia == "Total": total_produccion += val
            
            for j, col in enumerate(["Costo Total", "Precio Venta", "Ganancia"], start=10):
                val = row[col]
                item = QTableWidgetItem(f"${val:,.2f}")
                self.tabla_produccion.setItem(i, j, item)
                if col == "Costo Total": total_costo += val
                elif col == "Precio Venta": total_venta += val
                elif col == "Ganancia": total_ganancia += val

        self.actualizar_metricas(total_produccion, total_costo, total_venta, total_ganancia)

    def exportar_a_excel(self):
        """Exporta los datos actuales a un archivo Excel"""
        try:
            fecha_actual = datetime.now().strftime("%Y-%m-%d")
            nombre_archivo = f"reporte_produccion_{fecha_actual}.xlsx"
            
            with pd.ExcelWriter(nombre_archivo, engine='openpyxl') as writer:
                self.df_produccion.to_excel(writer, sheet_name='Producción', index=False)
                
                # Crear hoja de resumen
                resumen_data = {
                    'Métrica': ['Producción Total', 'Costo Total', 'Venta Total', 'Ganancia Total'],
                    'Valor': [
                        self.metrica_produccion.valor_label.text(),
                        self.metrica_costo.valor_label.text(),
                        self.metrica_venta.valor_label.text(),
                        self.metrica_ganancia.valor_label.text()
                    ]
                }
                pd.DataFrame(resumen_data).to_excel(writer, sheet_name='Resumen', index=False)
            
            QMessageBox.information(self, "Éxito", f"Reporte exportado como {nombre_archivo}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar el reporte: {e}")