# ui/ui_panel_ventas.py (VERSIÓN CON REINICIO SEMANAL Y EXPORTACIÓN AUTOMÁTICA)

from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QMessageBox, QHBoxLayout, QTabWidget,
    QComboBox, QDialog, QFrame, QGroupBox, QSplitter, QScrollArea, QDateEdit,
    QTextEdit, QProgressDialog
)
from PyQt5.QtCore import Qt, QDate
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
import os


class TarjetaMetricaVentas(QFrame):
    """Widget tipo tarjeta para mostrar métricas de ventas"""
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


class DialogoCorteSemanal(QDialog):
    """Diálogo para mostrar el reporte detallado del corte semanal"""
    def __init__(self, reporte_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📊 Reporte de Corte Semanal")
        self.setMinimumSize(600, 500)
        self.reporte_data = reporte_data
        
        layout = QVBoxLayout(self)
        
        # Título
        titulo = QLabel("REPORTE DE CORTE SEMANAL")
        titulo.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; text-align: center;")
        layout.addWidget(titulo)
        
        # Período
        periodo = QLabel(f"Período: {reporte_data['periodo']}")
        periodo.setStyleSheet("font-size: 14px; color: #7f8c8d; text-align: center;")
        layout.addWidget(periodo)
        
        # Separador
        separador = QLabel("─" * 50)
        separador.setStyleSheet("color: #bdc3c7; text-align: center;")
        layout.addWidget(separador)
        
        # Métricas principales
        metricas_layout = QHBoxLayout()
        
        metrica_ingresos = QLabel(f"<b>INGRESOS TOTALES:</b><br><span style='font-size: 24px; color: #27ae60;'>${reporte_data['total_ingresos']:,.2f}</span>")
        metrica_ingresos.setAlignment(Qt.AlignCenter)
        metrica_ingresos.setStyleSheet("background-color: #d5f4e6; padding: 15px; border-radius: 8px;")
        
        metrica_ventas = QLabel(f"<b>TOTAL VENTAS:</b><br><span style='font-size: 20px;'>{reporte_data['total_ventas']}</span>")
        metrica_ventas.setAlignment(Qt.AlignCenter)
        metrica_ventas.setStyleSheet("background-color: #d6eaf8; padding: 15px; border-radius: 8px;")
        
        metricas_layout.addWidget(metrica_ingresos)
        metricas_layout.addWidget(metrica_ventas)
        layout.addLayout(metricas_layout)
        
        # Desglose por tipo de producto
        layout.addWidget(QLabel("<b>DESGLOSE POR TIPO DE PRODUCTO:</b>"))
        
        desglose_text = QTextEdit()
        desglose_text.setReadOnly(True)
        desglose_text.setHtml(f"""
            <table width="100%" cellpadding="5" style="border-collapse: collapse;">
                <tr style="background-color: #34495e; color: white;">
                    <th align="left">TIPO</th>
                    <th align="right">CANTIDAD</th>
                    <th align="right">INGRESOS</th>
                    <th align="right">% DEL TOTAL</th>
                </tr>
                <tr style="background-color: #ecf0f1;">
                    <td>Productos Normales</td>
                    <td align="right">{reporte_data['productos_normales']['cantidad']}</td>
                    <td align="right">${reporte_data['productos_normales']['ingresos']:,.2f}</td>
                    <td align="right">{reporte_data['productos_normales']['porcentaje']}%</td>
                </tr>
                <tr style="background-color: #f8f9fa;">
                    <td>Productos Reventa</td>
                    <td align="right">{reporte_data['productos_reventa']['cantidad']}</td>
                    <td align="right">${reporte_data['productos_reventa']['ingresos']:,.2f}</td>
                    <td align="right">{reporte_data['productos_reventa']['porcentaje']}%</td>
                </tr>
                <tr style="background-color: #2c3e50; color: white; font-weight: bold;">
                    <td>TOTAL</td>
                    <td align="right">{reporte_data['total_ventas']}</td>
                    <td align="right">${reporte_data['total_ingresos']:,.2f}</td>
                    <td align="right">100%</td>
                </tr>
            </table>
        """)
        layout.addWidget(desglose_text)
        
        # Top 5 productos más vendidos
        if reporte_data['top_productos']:
            layout.addWidget(QLabel("<b>TOP 5 PRODUCTOS MÁS VENDIDOS:</b>"))
            
            top_text = QTextEdit()
            top_text.setReadOnly(True)
            top_text.setMaximumHeight(150)
            
            top_html = """
            <table width="100%" cellpadding="5" style="border-collapse: collapse;">
                <tr style="background-color: #34495e; color: white;">
                    <th align="left">PRODUCTO</th>
                    <th align="right">CANTIDAD</th>
                    <th align="right">INGRESOS</th>
                </tr>
            """
            for i, producto in enumerate(reporte_data['top_productos']):
                color = "#ecf0f1" if i % 2 == 0 else "#f8f9fa"
                top_html += f"""
                <tr style="background-color: {color};">
                    <td>{producto['nombre']}</td>
                    <td align="right">{producto['cantidad']}</td>
                    <td align="right">${producto['ingresos']:,.2f}</td>
                </tr>
                """
            top_html += "</table>"
            top_text.setHtml(top_html)
            layout.addWidget(top_text)
        
        # Información importante
        info_label = QLabel(
            "⚠️ <b>ATENCIÓN:</b> Al confirmar, las ventas de esta semana se archivarán "
            "y se reiniciarán los contadores para la nueva semana. "
            "Se generará un archivo Excel con el reporte completo."
        )
        info_label.setStyleSheet("background-color: #fff3cd; color: #856404; padding: 10px; border-radius: 5px; border: 1px solid #ffeaa7;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_exportar = QPushButton("💾 Exportar a Excel")
        btn_exportar.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 8px;")
        btn_exportar.clicked.connect(self.exportar_excel)
        
        btn_confirmar = QPushButton("✅ Confirmar Corte")
        btn_confirmar.setStyleSheet("background-color: #007bff; color: white; font-weight: bold; padding: 8px;")
        btn_confirmar.clicked.connect(self.confirmar_corte)
        
        btn_cancelar = QPushButton("❌ Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_exportar)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_confirmar)
        btn_layout.addWidget(btn_cancelar)
        layout.addLayout(btn_layout)
    
    def exportar_excel(self):
        """Exporta el reporte a Excel"""
        try:
            # Crear nombre de archivo con fecha
            fecha_actual = datetime.now().strftime("%Y-%m-%d")
            nombre_archivo = f"corte_semanal_{fecha_actual}.xlsx"
            
            with pd.ExcelWriter(nombre_archivo, engine='openpyxl') as writer:
                # Hoja de resumen
                resumen_data = {
                    'Métrica': [
                        'Período', 'Ingresos Totales', 'Total Ventas',
                        'Productos Normales - Cantidad', 'Productos Normales - Ingresos', 
                        'Productos Reventa - Cantidad', 'Productos Reventa - Ingresos'
                    ],
                    'Valor': [
                        self.reporte_data['periodo'],
                        f"${self.reporte_data['total_ingresos']:,.2f}",
                        self.reporte_data['total_ventas'],
                        self.reporte_data['productos_normales']['cantidad'],
                        f"${self.reporte_data['productos_normales']['ingresos']:,.2f}",
                        self.reporte_data['productos_reventa']['cantidad'],
                        f"${self.reporte_data['productos_reventa']['ingresos']:,.2f}"
                    ]
                }
                pd.DataFrame(resumen_data).to_excel(writer, sheet_name='Resumen', index=False)
                
                # Hoja de top productos
                if self.reporte_data['top_productos']:
                    top_df = pd.DataFrame(self.reporte_data['top_productos'])
                    top_df.to_excel(writer, sheet_name='Top Productos', index=False)
            
            QMessageBox.information(
                self, 
                "Exportación Exitosa", 
                f"✅ Reporte exportado correctamente:\n\n{nombre_archivo}\n\n"
                f"El archivo se guardó en la carpeta actual de la aplicación."
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar el reporte:\n{str(e)}")
    
    def confirmar_corte(self):
        """Confirma el corte semanal y cierra el diálogo"""
        self.accept()


class PanelVentas(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__()
        self.engine = engine
        self.df_ventas = pd.DataFrame()

        # Layout principal
        main_layout = QVBoxLayout(self)
        
        # --- Filtros y controles ---
        filtros_group = QGroupBox("Filtros de Ventas")
        filtros_layout = QHBoxLayout(filtros_group)
        
        filtros_layout.addWidget(QLabel("Desde:"))
        self.date_desde = QDateEdit()
        self.date_desde.setDate(QDate.currentDate().addDays(-7))
        self.date_desde.setCalendarPopup(True)
        filtros_layout.addWidget(self.date_desde)
        
        filtros_layout.addWidget(QLabel("Hasta:"))
        self.date_hasta = QDateEdit()
        self.date_hasta.setDate(QDate.currentDate())
        self.date_hasta.setCalendarPopup(True)
        filtros_layout.addWidget(self.date_hasta)
        
        self.btn_aplicar = QPushButton("Aplicar Filtros")
        self.btn_aplicar.clicked.connect(self.cargar_ventas_desde_db)
        filtros_layout.addWidget(self.btn_aplicar)
        
        # BOTÓN DE CORTE SEMANAL
        self.btn_corte_semanal = QPushButton("📅 Corte Semanal")
        self.btn_corte_semanal.setStyleSheet("background-color: #f5b041; color: black; font-weight: bold; padding: 8px;")
        self.btn_corte_semanal.clicked.connect(self.realizar_corte_semanal)
        self.btn_corte_semanal.setToolTip("Generar reporte y reiniciar semana")
        filtros_layout.addWidget(self.btn_corte_semanal)
        
        self.btn_exportar = QPushButton("📊 Exportar Excel")
        self.btn_exportar.clicked.connect(self.exportar_a_excel)
        filtros_layout.addWidget(self.btn_exportar)
        
        filtros_layout.addStretch()
        main_layout.addWidget(filtros_group)
        
        # --- Métricas de Ventas ---
        self.metricas_layout = QHBoxLayout()
        
        self.metrica_ventas_totales = TarjetaMetricaVentas("Ventas Totales", "$0.00", "#e8f5e9")
        self.metrica_productos_vendidos = TarjetaMetricaVentas("Productos Vendidos", "0", "#e3f2fd")
        self.metrica_clientes_atendidos = TarjetaMetricaVentas("Clientes Atendidos", "0", "#fff3e0")
        self.metrica_ticket_promedio = TarjetaMetricaVentas("Ticket Promedio", "$0.00", "#ffebee")
        
        self.metricas_layout.addWidget(self.metrica_ventas_totales)
        self.metricas_layout.addWidget(self.metrica_productos_vendidos)
        self.metricas_layout.addWidget(self.metrica_clientes_atendidos)
        self.metricas_layout.addWidget(self.metrica_ticket_promedio)
        
        main_layout.addLayout(self.metricas_layout)
        
        # --- Tabs de Detalles ---
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Pestaña 1: Resumen de Ventas por Producto
        self.tab_resumen = QWidget()
        self.tabs.addTab(self.tab_resumen, "📈 Resumen por Producto")
        self._setup_tab_resumen()
        
        # Pestaña 2: Detalle de Ventas
        self.tab_detalle = QWidget()
        self.tabs.addTab(self.tab_detalle, "📋 Detalle de Ventas")
        self._setup_tab_detalle()
        
        # Pestaña 3: Ventas por Cliente
        self.tab_clientes = QWidget()
        self.tabs.addTab(self.tab_clientes, "👥 Ventas por Cliente")
        self._setup_tab_clientes()

        # Pestaña 4: Ventas por Día
        self.tab_diario = QWidget()
        self.tabs.addTab(self.tab_diario, "📅 Ventas por Día")
        self._setup_tab_diario()
        
        # Cargar datos iniciales
        self.cargar_ventas_desde_db()

    def _setup_tab_resumen(self):
        layout = QVBoxLayout(self.tab_resumen)
        
        self.tabla_resumen = QTableWidget()
        self.tabla_resumen.setColumnCount(6)
        self.tabla_resumen.setHorizontalHeaderLabels([
            "Producto", "Tipo", "Cantidad Vendida", "Total Vendido", 
            "Precio Promedio", "% del Total"
        ])
        self.tabla_resumen.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.tabla_resumen)

    def _setup_tab_detalle(self):
        layout = QVBoxLayout(self.tab_detalle)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.tabla_detalle = QTableWidget()
        scroll_area.setWidget(self.tabla_detalle)
        
        self.tabla_detalle.setColumnCount(7)
        self.tabla_detalle.setHorizontalHeaderLabels([
            "Fecha", "Cliente", "Producto", "Tipo", "Cantidad", "Precio Unitario", "Total"
        ])
        self.tabla_detalle.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(scroll_area)

    def _setup_tab_clientes(self):
        layout = QVBoxLayout(self.tab_clientes)
        
        self.tabla_clientes = QTableWidget()
        self.tabla_clientes.setColumnCount(4)
        self.tabla_clientes.setHorizontalHeaderLabels([
            "Cliente", "Total Compras", "Cantidad de Compras", "Promedio por Compra"
        ])
        self.tabla_clientes.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tabla_clientes)

    def _setup_tab_diario(self):
        layout = QVBoxLayout(self.tab_diario)
        
        self.tabla_diario = QTableWidget()
        self.tabla_diario.setColumnCount(4)
        self.tabla_diario.setHorizontalHeaderLabels([
            "Fecha", "Total Ventas", "Cantidad Ventas", "Ticket Promedio"
        ])
        self.tabla_diario.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tabla_diario)

    def realizar_corte_semanal(self):
        """
        Realiza el corte semanal completo: reporte + archivo + reinicio
        """
        # Calcular fecha de inicio de la semana (lunes)
        hoy = datetime.now().date()
        inicio_semana = hoy - timedelta(days=hoy.weekday())
        
        try:
            # Obtener todas las ventas en un bloque separado
            with self.engine.connect() as conn:
                query_todas_ventas = text("""
                    SELECT 
                        tipo_tabla as tipo,
                        nombre_producto,
                        cantidad,
                        total,
                        fecha_venta
                    FROM ventas 
                    
                    UNION ALL
                    
                    SELECT 
                        'Reventa' as tipo_tabla,
                        nombre_producto,
                        cantidad,
                        total,
                        fecha_venta
                    FROM venta_reventa
                    
                    ORDER BY fecha_venta
                """)
                
                df_todas_ventas = pd.read_sql_query(query_todas_ventas, conn)
            
            if df_todas_ventas.empty:
                QMessageBox.information(self, "Sin ventas", "No hay ventas registradas en el sistema.")
                return
            
            print(f"DEBUG: Se encontraron {len(df_todas_ventas)} ventas para archivar")
            
            # 2. GENERAR REPORTE CON TODAS LAS VENTAS
            reporte_data = self._generar_reporte(df_todas_ventas, "Todas las ventas acumuladas", hoy)
            
            # 3. MOSTRAR DIÁLOGO DE CONFIRMACIÓN
            dialogo = DialogoCorteSemanal(reporte_data, self)
            if dialogo.exec_() == QDialog.Accepted:
                # 4. ARCHIVAR TODAS LAS VENTAS Y REINICIAR
                self._archivar_y_reiniciar_semana(inicio_semana, hoy, df_todas_ventas)
                
                # 5. ACTUALIZAR INTERFAZ
                self.cargar_ventas_desde_db()
                
                QMessageBox.information(
                    self, 
                    "Corte Completado", 
                    f"✅ Corte semanal realizado con éxito.\n\n"
                    f"• {len(df_todas_ventas)} ventas archivadas en la base de datos\n"
                    f"• Contadores reiniciados para nueva semana\n"
                    f"• Reporte guardado en archivo Excel"
                )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo realizar el corte:\n{str(e)}")

    def _obtener_ventas_semana(self, inicio_semana, hoy):
        """Obtiene todas las ventas de la semana actual"""
        query_ventas_semana = text("""
            SELECT 
                tipo_tabla as tipo,
                nombre_producto,
                cantidad,
                total,
                fecha_venta
            FROM ventas 
            WHERE fecha_venta BETWEEN :inicio_semana AND :hoy
            
            UNION ALL
            
            SELECT 
                'Reventa' as tipo_tabla,
                nombre_producto,
                cantidad,
                total,
                fecha_venta
            FROM venta_reventa 
            WHERE fecha_venta BETWEEN :inicio_semana AND :hoy
        """)
        
        return pd.read_sql_query(
            query_ventas_semana, self.engine,
            params={"inicio_semana": inicio_semana, "hoy": hoy}
        )

    def _generar_reporte(self, df_ventas, periodo_descripcion, hoy):
        """Genera los datos para el reporte"""
        total_ingresos = df_ventas['total'].sum()
        total_ventas = len(df_ventas)
        
        productos_normales = df_ventas[df_ventas['tipo'] != 'Reventa']
        productos_reventa = df_ventas[df_ventas['tipo'] == 'Reventa']
        
        ingresos_normales = productos_normales['total'].sum()
        ingresos_reventa = productos_reventa['total'].sum()
        
        top_productos = df_ventas.groupby('nombre_producto').agg({
            'cantidad': 'sum',
            'total': 'sum'
        }).nlargest(5, 'total').reset_index()
        
        return {
            'periodo': f"{periodo_descripcion} (hasta {hoy})",
            'total_ingresos': total_ingresos,
            'total_ventas': total_ventas,
            'productos_normales': {
                'cantidad': len(productos_normales),
                'ingresos': ingresos_normales,
                'porcentaje': round((ingresos_normales / total_ingresos * 100), 2) if total_ingresos > 0 else 0
            },
            'productos_reventa': {
                'cantidad': len(productos_reventa),
                'ingresos': ingresos_reventa,
                'porcentaje': round((ingresos_reventa / total_ingresos * 100), 2) if total_ingresos > 0 else 0
            },
            'top_productos': [
                {
                    'nombre': row['nombre_producto'],
                    'cantidad': row['cantidad'],
                    'ingresos': row['total']
                }
                for _, row in top_productos.iterrows()
            ]
        }

    def _archivar_y_reiniciar_semana(self, inicio_semana, hoy, df_ventas):
        """Archiva las ventas y reinicia la semana - VERSIÓN SIMPLIFICADA"""
        try:
            # Usar el engine directamente sin gestión manual de transacciones
            with self.engine.begin() as conn:
                # 1. CREAR TABLA DE ARCHIVO SI NO EXISTE
                crear_tabla_query = text("""
                    CREATE TABLE IF NOT EXISTS ventas_archivadas (
                        id_venta_archivada INTEGER PRIMARY KEY AUTOINCREMENT,
                        fecha_archivo DATE DEFAULT CURRENT_DATE,
                        fecha_venta_original DATE,
                        id_cliente INTEGER,
                        nombre_producto TEXT,
                        tipo_tabla TEXT,
                        cantidad REAL,
                        total REAL,
                        semana_inicio DATE,
                        semana_fin DATE
                    )
                """)
                conn.execute(crear_tabla_query)

                # 2. ARCHIVAR TODAS LAS VENTAS
                archivar_query = text("""
                    INSERT INTO ventas_archivadas 
                    (fecha_venta_original, id_cliente, nombre_producto, tipo_tabla, cantidad, total, semana_inicio, semana_fin)
                    SELECT fecha_venta, id_cliente, nombre_producto, tipo_tabla, cantidad, total, :semana_inicio, :semana_fin
                    FROM ventas
                """)
                result_archivar = conn.execute(archivar_query, {
                    "semana_inicio": inicio_semana,
                    "semana_fin": hoy
                })
                print(f"DEBUG: Ventas archivadas: {result_archivar.rowcount}")

                # 3. ARCHIVAR TODA LA REVENTA
                archivar_reventa_query = text("""
                    INSERT INTO ventas_archivadas 
                    (fecha_venta_original, nombre_producto, tipo_tabla, cantidad, total, semana_inicio, semana_fin)
                    SELECT fecha_venta, nombre_producto, 'Reventa', cantidad, total, :semana_inicio, :semana_fin
                    FROM venta_reventa
                """)
                result_archivar_reventa = conn.execute(archivar_reventa_query, {
                    "semana_inicio": inicio_semana,
                    "semana_fin": hoy
                })
                print(f"DEBUG: Reventa archivada: {result_archivar_reventa.rowcount}")

                # 4. ELIMINAR TODAS LAS VENTAS
                eliminar_ventas_query = text("DELETE FROM ventas")
                result_eliminar_ventas = conn.execute(eliminar_ventas_query)
                print(f"DEBUG: Ventas eliminadas: {result_eliminar_ventas.rowcount}")

                eliminar_reventa_query = text("DELETE FROM venta_reventa")
                result_eliminar_reventa = conn.execute(eliminar_reventa_query)
                print(f"DEBUG: Reventa eliminada: {result_eliminar_reventa.rowcount}")

            print("DEBUG: Transacción completada exitosamente")

            # 5. REINICIAR FILTROS
            self.date_desde.setDate(QDate.currentDate())
            self.date_hasta.setDate(QDate.currentDate().addDays(7))
            
            # 6. LIMPIAR INTERFAZ
            self.limpiar_tablas()
            self.actualizar_metricas(0, 0, 0, 0)
            
            # 7. VERIFICAR QUE NO HAY DATOS EN EL DATAFRAME
            self.df_ventas = pd.DataFrame()
            print(f"DEBUG: DataFrame vacío: {self.df_ventas.empty}")
            
        except Exception as e:
            print(f"ERROR en _archivar_y_reiniciar_semana: {e}")
            raise

    def cargar_ventas_desde_db(self):
        """Carga todas las ventas desde la base de datos"""
        try:
            fecha_desde = self.date_desde.date().toPyDate()
            fecha_hasta = self.date_hasta.date().toPyDate()
            
            print(f"DEBUG cargar_ventas: Fechas {fecha_desde} a {fecha_hasta}")
            
            # Combinar ventas de productos normales y reventa
            query_ventas = text("""
                SELECT 
                    v.fecha_venta as fecha,
                    COALESCE(c.nombre_cliente, 'Cliente General') as cliente,
                    v.nombre_producto as producto,
                    v.tipo_tabla as tipo,
                    v.cantidad as cantidad,
                    v.total as total,
                    (v.total / NULLIF(v.cantidad, 0)) as precio_unitario
                FROM ventas v
                LEFT JOIN clientes c ON v.id_cliente = c.id_cliente
                WHERE v.fecha_venta BETWEEN :start_date AND :end_date
                
                UNION ALL
                
                SELECT 
                    vr.fecha_venta as fecha,
                    'Cliente General' as cliente,
                    vr.nombre_producto as producto,
                    'Reventa' as tipo,
                    vr.cantidad as cantidad,
                    vr.total as total,
                    vr.precio_unitario as precio_unitario
                FROM venta_reventa vr
                WHERE vr.fecha_venta BETWEEN :start_date AND :end_date
                
                ORDER BY fecha DESC
            """)
            
            self.df_ventas = pd.read_sql_query(
                query_ventas, self.engine,
                params={"start_date": fecha_desde, "end_date": fecha_hasta}
            )
            
            print(f"DEBUG: DataFrame cargado con {len(self.df_ventas)} registros")
            if not self.df_ventas.empty:
                print("DEBUG: Primeras filas del DataFrame:")
                print(self.df_ventas.head())
            
            if self.df_ventas.empty:
                self.limpiar_tablas()
                self.actualizar_metricas(0, 0, 0, 0)
                print("DEBUG: No hay ventas en el período")
                return
            
            self.actualizar_vistas()
            
        except Exception as e:
            print(f"ERROR en cargar_ventas_desde_db: {e}")
            QMessageBox.critical(self, "Error", f"No se pudieron cargar las ventas: {e}")

    def actualizar_vistas(self):
        """Actualiza todas las vistas con los datos de ventas"""
        self.actualizar_tabla_resumen()
        self.actualizar_tabla_detalle()
        self.actualizar_tabla_clientes()
        self.actualizar_tabla_diario()
        self.actualizar_metricas_globales()

    def actualizar_tabla_resumen(self):
        """Actualiza el resumen por producto"""
        if self.df_ventas.empty:
            return
            
        resumen = self.df_ventas.groupby(['producto', 'tipo']).agg({
            'cantidad': 'sum',
            'total': 'sum'
        }).reset_index()
        
        total_general = resumen['total'].sum()
        resumen['precio_promedio'] = resumen['total'] / resumen['cantidad']
        resumen['porcentaje_total'] = (resumen['total'] / total_general * 100).round(2)
        
        self.tabla_resumen.setRowCount(len(resumen))
        for i, row in resumen.iterrows():
            self.tabla_resumen.setItem(i, 0, QTableWidgetItem(str(row['producto'])))
            self.tabla_resumen.setItem(i, 1, QTableWidgetItem(str(row['tipo'])))
            self.tabla_resumen.setItem(i, 2, QTableWidgetItem(f"{row['cantidad']:.2f}"))
            self.tabla_resumen.setItem(i, 3, QTableWidgetItem(f"${row['total']:,.2f}"))
            self.tabla_resumen.setItem(i, 4, QTableWidgetItem(f"${row['precio_promedio']:,.2f}"))
            self.tabla_resumen.setItem(i, 5, QTableWidgetItem(f"{row['porcentaje_total']}%"))

    def actualizar_tabla_detalle(self):
        """Actualiza el detalle completo de ventas"""
        self.tabla_detalle.setRowCount(len(self.df_ventas))
        for i, row in self.df_ventas.iterrows():
            self.tabla_detalle.setItem(i, 0, QTableWidgetItem(str(row['fecha'])))
            self.tabla_detalle.setItem(i, 1, QTableWidgetItem(str(row['cliente'])))
            self.tabla_detalle.setItem(i, 2, QTableWidgetItem(str(row['producto'])))
            self.tabla_detalle.setItem(i, 3, QTableWidgetItem(str(row['tipo'])))
            self.tabla_detalle.setItem(i, 4, QTableWidgetItem(f"{row['cantidad']:.2f}"))
            self.tabla_detalle.setItem(i, 5, QTableWidgetItem(f"${row['precio_unitario']:,.2f}"))
            self.tabla_detalle.setItem(i, 6, QTableWidgetItem(f"${row['total']:,.2f}"))

    def actualizar_tabla_clientes(self):
        """Actualiza las ventas por cliente"""
        if self.df_ventas.empty:
            return
            
        clientes = self.df_ventas.groupby('cliente').agg({
            'total': ['sum', 'count'],
        }).reset_index()
        
        clientes.columns = ['cliente', 'total_compras', 'cantidad_compras']
        clientes['promedio_compra'] = clientes['total_compras'] / clientes['cantidad_compras']
        
        self.tabla_clientes.setRowCount(len(clientes))
        for i, row in clientes.iterrows():
            self.tabla_clientes.setItem(i, 0, QTableWidgetItem(str(row['cliente'])))
            self.tabla_clientes.setItem(i, 1, QTableWidgetItem(f"${row['total_compras']:,.2f}"))
            self.tabla_clientes.setItem(i, 2, QTableWidgetItem(f"{row['cantidad_compras']}"))
            self.tabla_clientes.setItem(i, 3, QTableWidgetItem(f"${row['promedio_compra']:,.2f}"))

    def actualizar_tabla_diario(self):
        """Actualiza las ventas por día"""
        if self.df_ventas.empty:
            return
            
        diario = self.df_ventas.groupby('fecha').agg({
            'total': ['sum', 'count'],
        }).reset_index()
        
        diario.columns = ['fecha', 'total_ventas', 'cantidad_ventas']
        diario['ticket_promedio'] = diario['total_ventas'] / diario['cantidad_ventas']
        
        self.tabla_diario.setRowCount(len(diario))
        for i, row in diario.iterrows():
            self.tabla_diario.setItem(i, 0, QTableWidgetItem(str(row['fecha'])))
            self.tabla_diario.setItem(i, 1, QTableWidgetItem(f"${row['total_ventas']:,.2f}"))
            self.tabla_diario.setItem(i, 2, QTableWidgetItem(f"{row['cantidad_ventas']}"))
            self.tabla_diario.setItem(i, 3, QTableWidgetItem(f"${row['ticket_promedio']:,.2f}"))

    def actualizar_metricas_globales(self):
        """Actualiza las métricas globales"""
        if self.df_ventas.empty:
            self.actualizar_metricas(0, 0, 0, 0)
            return
            
        total_ventas = self.df_ventas['total'].sum()
        total_productos = self.df_ventas['cantidad'].sum()
        clientes_unicos = self.df_ventas['cliente'].nunique()
        ticket_promedio = total_ventas / len(self.df_ventas) if len(self.df_ventas) > 0 else 0
        
        self.actualizar_metricas(total_ventas, total_productos, clientes_unicos, ticket_promedio)

    def actualizar_metricas(self, total_ventas, total_productos, clientes_unicos, ticket_promedio):
        """Actualiza las tarjetas de métricas"""
        self.metrica_ventas_totales.valor_label.setText(f"${total_ventas:,.2f}")
        self.metrica_productos_vendidos.valor_label.setText(f"{total_productos:,.0f}")
        self.metrica_clientes_atendidos.valor_label.setText(f"{clientes_unicos}")
        self.metrica_ticket_promedio.valor_label.setText(f"${ticket_promedio:,.2f}")

    def limpiar_tablas(self):
        """Limpia completamente todas las tablas"""
        for tabla in [self.tabla_resumen, self.tabla_detalle, self.tabla_clientes, self.tabla_diario]:
            tabla.setRowCount(0)
            tabla.clearContents()

    def exportar_a_excel(self):
        """Exporta los datos de ventas a Excel"""
        try:
            if self.df_ventas.empty:
                QMessageBox.warning(self, "Sin datos", "No hay datos para exportar.")
                return
                
            fecha_actual = datetime.now().strftime("%Y-%m-%d")
            nombre_archivo = f"reporte_ventas_{fecha_actual}.xlsx"
            
            with pd.ExcelWriter(nombre_archivo, engine='openpyxl') as writer:
                # Hoja de detalle
                self.df_ventas.to_excel(writer, sheet_name='Detalle Ventas', index=False)
                
                # Hoja de resumen por producto
                resumen = self.df_ventas.groupby(['producto', 'tipo']).agg({
                    'cantidad': 'sum',
                    'total': 'sum'
                }).reset_index()
                resumen['precio_promedio'] = resumen['total'] / resumen['cantidad']
                total_general = resumen['total'].sum()
                resumen['porcentaje_total'] = (resumen['total'] / total_general * 100).round(2)
                resumen.to_excel(writer, sheet_name='Resumen Productos', index=False)
                
                # Hoja de métricas
                metricas_data = {
                    'Métrica': ['Ventas Totales', 'Productos Vendidos', 'Clientes Atendidos', 'Ticket Promedio'],
                    'Valor': [
                        self.metrica_ventas_totales.valor_label.text(),
                        self.metrica_productos_vendidos.valor_label.text(),
                        self.metrica_clientes_atendidos.valor_label.text(),
                        self.metrica_ticket_promedio.valor_label.text()
                    ]
                }
                pd.DataFrame(metricas_data).to_excel(writer, sheet_name='Métricas', index=False)
            
            QMessageBox.information(self, "Éxito", f"Reporte de ventas exportado como:\n{nombre_archivo}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar el reporte: {e}")