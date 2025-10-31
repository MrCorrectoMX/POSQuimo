# ui_pos.py (con presentaciones para todos los productos y cálculo correcto de precios)

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QScrollArea, QFrame, QGridLayout, QSizePolicy, QMessageBox, QTabWidget, QMenu,
    QAction, QInputDialog, QDialog, QComboBox, QLineEdit, QTableWidget, QHeaderView, QTableWidgetItem,
    QApplication,QGroupBox, QDoubleSpinBox
)
from PyQt5.QtCore import Qt, QEvent, QTimer
from sqlalchemy import text
import functools
from ui.ui_panel_inferior import PanelInferiorRedisenado
from .ui_formula import FormulaDialog
from .ui_gestion_presentaciones import GestionPresentacionesDialog

class POSWindow(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine

        # Ticket
        self.current_ticket = {}
        self.current_total = 0.0

        # Cache de productos por tabla
        self.products_cache = {}

        # Map: viewport widget -> (table_name, grid_layout)
        self.viewport_map = {}

        # Anchura mínima deseada por "celda"
        self.min_button_width = 160
        self.min_button_height = 90

        # Variables para presentaciones
        self.current_product_with_presentaciones = None
        self.presentations_container = None

        self._init_ui()
        self._populate_grids()

        # Primer re-layout cuando el widget se muestre
        QTimer.singleShot(120, self._refresh_all_layouts)
        
        # Cargar clientes al inicio
        self._load_clients()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # --- Panel Izquierdo: Productos con Pestañas ---
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("<b>Seleccione una categoría</b>"))

        self.tabs_productos = QTabWidget()

        # Crear pestañas y sus QGridLayouts
        self.tab_productos = QWidget()
        self.grid_layout_productos = QGridLayout()
        self.grid_layout_productos.setContentsMargins(6, 6, 6, 6)
        self.grid_layout_productos.setSpacing(8)
        self.tab_productos.setLayout(self.grid_layout_productos)

        self.tab_reventa = QWidget()
        self.grid_layout_reventa = QGridLayout()
        self.grid_layout_reventa.setContentsMargins(6, 6, 6, 6)
        self.grid_layout_reventa.setSpacing(8)
        self.tab_reventa.setLayout(self.grid_layout_reventa)

        self.tab_materias_primas = QWidget()
        self.grid_layout_materias_primas = QGridLayout()
        self.grid_layout_materias_primas.setContentsMargins(6, 6, 6, 6)
        self.grid_layout_materias_primas.setSpacing(8)
        self.tab_materias_primas.setLayout(self.grid_layout_materias_primas)

        # Scroll areas
        for tab_widget, title, grid_layout, table_name in [
            (self.tab_productos, "Productos", self.grid_layout_productos, "productos"),
            (self.tab_reventa, "Productos Reventa", self.grid_layout_reventa, "productosreventa"),
            (self.tab_materias_primas, "Materias Primas", self.grid_layout_materias_primas, "materiasprimas")
        ]:
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setWidget(tab_widget)

            viewport = scroll_area.viewport()
            self.viewport_map[viewport] = (table_name, grid_layout)
            viewport.installEventFilter(self)

            # Contar artículos
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = result.scalar() or 0

            self.tabs_productos.addTab(scroll_area, f"{title} ({count})")

        left_panel.addWidget(self.tabs_productos)
        
        # --- CONTENEDOR PARA PRESENTACIONES (oculto inicialmente) ---
        self.presentations_container = QFrame()
        self.presentations_container.setVisible(False)
        self.presentations_container.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                margin: 5px;
                padding: 10px;
            }
        """)
        
        presentations_layout = QVBoxLayout(self.presentations_container)
        
        # Header con nombre del producto
        self.presentations_header = QLabel()
        self.presentations_header.setStyleSheet("font-weight: bold; font-size: 14px; color: #495057; margin-bottom: 8px;")
        presentations_layout.addWidget(self.presentations_header)
        
        # Layout horizontal para los botones de presentaciones
        self.presentations_layout = QHBoxLayout()
        self.presentations_layout.setSpacing(8)
        presentations_layout.addLayout(self.presentations_layout)
        
        # Botón para cerrar presentaciones
        btn_cerrar_presentaciones = QPushButton("Cerrar")
        btn_cerrar_presentaciones.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 4px;
                font-size: 12px;
                margin-top: 8px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        btn_cerrar_presentaciones.clicked.connect(self._ocultar_presentaciones)
        presentations_layout.addWidget(btn_cerrar_presentaciones)
        
        left_panel.addWidget(self.presentations_container)
        main_layout.addLayout(left_panel, 7)

        # --- Panel Derecho: Ticket ---
        right_panel = QVBoxLayout()

        # Sección del cliente
        cliente_layout = QHBoxLayout()
        cliente_layout.addWidget(QLabel("<b>Cliente:</b>"))
        self.cliente_combobox = QComboBox()
        self.cliente_combobox.setEditable(True)
        self.cliente_combobox.setInsertPolicy(QComboBox.NoInsert)
        self.cliente_combobox.setStyleSheet("background-color: white; border: 1px solid #ccc; padding: 5px;")
        self.cliente_combobox.completer().setFilterMode(Qt.MatchContains)
        self.cliente_combobox.completer().setCaseSensitivity(Qt.CaseInsensitive)
        cliente_layout.addWidget(self.cliente_combobox)
        right_panel.addLayout(cliente_layout)

        # --- Sección del área del producto ---
        self.area_combobox = QComboBox()
        self.area_combobox.setEditable(False)
        self.area_combobox.setToolTip("Selecciona el área de producción del producto")
        area_layout = QHBoxLayout()
        area_layout.addWidget(QLabel("<b>Área:</b>"))
        area_layout.addWidget(self.area_combobox)
        right_panel.addLayout(area_layout)

        # --- Ticket ---
        ticket_frame = QFrame()
        ticket_frame.setFrameShape(QFrame.Shape.StyledPanel)

        self.ticket_layout = QVBoxLayout(ticket_frame)
        self.ticket_layout.addWidget(QLabel("<b>Ticket de Venta</b>"))
        self.ticket_items_area = QVBoxLayout()
        self.ticket_layout.addLayout(self.ticket_items_area)
        self.ticket_layout.addStretch()
        self.total_label = QLabel("<b>Total: $0.00</b>")
        self.total_label.setAlignment(Qt.AlignRight)
        self.total_label.setStyleSheet("font-size: 16pt;")
        self.ticket_layout.addWidget(self.total_label)

        botones_ticket_layout = QHBoxLayout()
        btn_cobrar = QPushButton("Cobrar")
        btn_cobrar.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold; padding: 10px;")
        btn_cobrar.clicked.connect(self._process_sale)
        btn_cancelar = QPushButton("Cancelar Venta")
        btn_cancelar.clicked.connect(self._clear_ticket)
        botones_ticket_layout.addWidget(btn_cancelar)
        botones_ticket_layout.addWidget(btn_cobrar)

        right_panel.addWidget(ticket_frame)
        right_panel.addLayout(botones_ticket_layout)
        main_layout.addLayout(right_panel, 3)


    def _calcular_precio_desde_formulas(self, conn, producto_id, product_name):
        """Método alternativo para calcular precio desde fórmulas - MÁS ROBUSTO"""
        try:
            print(f"[ALTERNATIVO] Calculando precio para: {product_name}")
            
            # Obtener fórmula completa
            query_formula = text("""
                SELECT 
                    mp.nombre_mp,
                    mp.costo_unitario_mp,
                    f.porcentaje
                FROM formulas f
                JOIN materiasprimas mp ON f.id_mp = mp.id_mp
                WHERE f.id_producto = :id_producto
            """)
            
            ingredientes = conn.execute(query_formula, {"id_producto": producto_id}).fetchall()
            
            if not ingredientes:
                print(f"[ALTERNATIVO] No se encontró fórmula para: {product_name}")
                return 0.0
            
            costo_total = 0.0
            print(f"🔍 [ALTERNATIVO] Fórmula de {product_name}:")
            
            for nombre_mp, costo_mp, porcentaje in ingredientes:
                if costo_mp is None or porcentaje is None:
                    print(f"[ALTERNATIVO] Datos incompletos: {nombre_mp}")
                    continue
                    
                costo_contribucion = float(costo_mp) * (float(porcentaje) / 100.0)
                costo_total += costo_contribucion
                print(f"   - {nombre_mp}: ${costo_mp:.2f} × {porcentaje}% = ${costo_contribucion:.2f}")
            
            precio_final = costo_total * 1.30  # 30% de margen
            print(f"[ALTERNATIVO] Precio final para {product_name}: ${precio_final:.2f}")
            
            return precio_final
            
        except Exception as e:
            print(f"[ALTERNATIVO] Error calculando precio: {e}")
            return 0.0

    # -------------------------
    # Funciones para presentaciones (mejoradas)
    # -------------------------
    def _mostrar_presentaciones(self, table_name, product_name):
        """Muestra las presentaciones disponibles - VERSIÓN SISTEMA HÍBRIDO"""
        if table_name != "productos":
            self._add_product_to_ticket(table_name, product_name)
            return
            
        try:
            with self.engine.connect() as conn:
                # Obtener el ID del producto
                query_id = text("SELECT id_producto FROM productos WHERE nombre_producto = :nombre")
                producto = conn.execute(query_id, {"nombre": product_name}).fetchone()
                if not producto:
                    self._add_product_to_ticket(table_name, product_name)
                    return
                producto_id = producto[0]

                # CALCULAR PRECIO BASE
                precio_base = self._recalcular_precio_producto(conn, product_name)
                
                if precio_base == 0:
                    precio_base = self._calcular_precio_desde_formulas(conn, producto_id, product_name)
                
                if precio_base <= 0:
                    QMessageBox.warning(
                        self, 
                        "Precio No Calculado", 
                        f"El producto '{product_name}' no tiene fórmula definida o las materias primas no tienen costo."
                    )
                    return

                # Buscar presentaciones del producto
                query_presentaciones = text("""
                    SELECT id_presentacion, nombre_presentacion, factor, costo_envase, precio_venta
                    FROM presentaciones 
                    WHERE id_producto = :id_producto
                    ORDER BY factor
                """)
                presentaciones = conn.execute(query_presentaciones, {"id_producto": producto_id}).fetchall()
                
                if not presentaciones:
                    presentaciones = [('Unidad', 1, 0, None)]  # Presentación por defecto
                
                # Mostrar el contenedor de presentaciones
                self.current_product_with_presentaciones = product_name
                self.presentations_header.setText(f"{product_name} - Precio base: ${precio_base:.2f}")
                
                # Limpiar layout anterior
                while self.presentations_layout.count():
                    child = self.presentations_layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                
                # Crear botones para cada presentación - SISTEMA HÍBRIDO
                for pres in presentaciones:
                    id_pres, nombre_pres, factor, costo_envase, precio_venta_bd = pres
                    
                    #SISTEMA HÍBRIDO: Decidir qué precio usar 
                    if precio_venta_bd is not None:
                        # PRECIO MANUAL - Usar el precio fijo de la BD
                        precio_final = precio_venta_bd
                        tipo_precio = "PRECIO MANUAL"
                    else:
                        # PRECIO AUTOMÁTICO - Calcular con fórmula específica
                        precio_final = self._calcular_precio_presentacion(
                            nombre_pres, precio_base, costo_envase or 0, factor
                        )
                        tipo_precio = "PRECIO AUTOMÁTICO"
                    
                    # Texto informativo del botón
                    texto_boton = f"{nombre_pres}\n${precio_final:.2f}\n{tipo_precio}"
                    if factor != 1:
                        texto_boton += f"\n({factor}×)"
                    if costo_envase and costo_envase > 0:
                        texto_boton += f"\n+${costo_envase:.2f} envase"
                    
                    btn_pres = QPushButton(texto_boton)
                    
                    # Color diferente según tipo de precio
                    if precio_venta_bd is not None:
                        btn_pres.setStyleSheet("""
                            QPushButton {
                                background-color: #e3f2fd;
                                margin: 5px;
                                padding: 8px 15px;
                                border-radius: 6px;
                                font-size: 11px;
                                min-width: 90px;
                                min-height: 60px;
                                border: 2px solid #1976d2;
                            }
                            QPushButton:hover {
                                background-color: #bbdefb;
                            }
                        """)
                    else:
                        btn_pres.setStyleSheet("""
                            QPushButton {
                                background-color: #f0f0f0;
                                margin: 5px;
                                padding: 8px 15px;
                                border-radius: 6px;
                                font-size: 11px;
                                min-width: 90px;
                                min-height: 60px;
                            }
                            QPushButton:hover {
                                background-color: #007bff;
                                color: white;
                            }
                        """)
                    
                    btn_pres.clicked.connect(
                        functools.partial(self._seleccionar_presentacion, product_name, nombre_pres, precio_final)
                    )
                    self.presentations_layout.addWidget(btn_pres)
                
                # Mostrar el contenedor
                self.presentations_container.setVisible(True)
                
        except Exception as e:
            print(f"Error al cargar presentaciones: {e}")
            self._add_product_to_ticket(table_name, product_name)

    def _ocultar_presentaciones(self):
        """Oculta el contenedor de presentaciones"""
        self.presentations_container.setVisible(False)
        self.current_product_with_presentaciones = None

    def _seleccionar_presentacion(self, product_name, presentacion_nombre, precio_final):
        """Añade el producto con la presentación seleccionada - AHORA CON CANTIDAD"""
        # Usar cantidad pendiente si existe, sino 1
        cantidad = getattr(self, '_cantidad_pendiente', 1.0)
        
        nombre_completo = f"{product_name} ({presentacion_nombre})"
        
        # Actualizar el área del producto
        self.actualizar_area_producto(product_name, "productos")
        
        print(f"Añadiendo al ticket: {nombre_completo} - Precio: ${precio_final:.2f} - Cantidad: {cantidad}")
        
        # Calcular total
        total_linea = precio_final * cantidad
        
        # Añadir al ticket
        if nombre_completo in self.current_ticket:
            self.current_ticket[nombre_completo]['qty'] += cantidad
            qty = self.current_ticket[nombre_completo]['qty']
            price = self.current_ticket[nombre_completo]['price']
            self.current_ticket[nombre_completo]['label'].setText(f"{nombre_completo} x{qty:.2f}  ${price*qty:.2f}")
        else:
            # Crear fila del ticket
            item_widget = QWidget()
            layout = QHBoxLayout(item_widget)
            layout.setContentsMargins(5, 2, 5, 2)

            label = QLabel(f"{nombre_completo} x{cantidad:.2f}  ${total_linea:.2f}")
            layout.addWidget(label)

            delete_btn = QPushButton("–")
            delete_btn.setFixedSize(24, 24)
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff4d4d;
                    color: white;
                    border-radius: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #e60000;
                }
            """)
            delete_btn.hide()
            layout.addWidget(delete_btn)

            item_widget.enterEvent = lambda e: delete_btn.show()
            item_widget.leaveEvent = lambda e: delete_btn.hide()

            delete_btn.clicked.connect(lambda _, name=nombre_completo: self._decrement_ticket_product(name))

            self.ticket_items_area.addWidget(item_widget)

            self.current_ticket[nombre_completo] = {
                'qty': cantidad,
                'price': precio_final,
                'widget': item_widget,
                'label': label,
                'product_name_base': product_name,
                'table_name': "productos",
                'precio_calculado': precio_final
            }

        # Actualizar total y limpiar cantidad pendiente
        self.current_total += total_linea
        self._update_ticket_display()
        self._ocultar_presentaciones()
        
        # Limpiar la cantidad pendiente
        if hasattr(self, '_cantidad_pendiente'):
            del self._cantidad_pendiente

    def _diagnosticar_secuencia_presentaciones(self):
        """Diagnóstico para ver el estado actual de la secuencia"""
        try:
            with self.engine.connect() as conn:
                # 1. Ver el máximo ID actual en la tabla
                query_max_id = text("SELECT MAX(id_presentacion) FROM presentaciones")
                max_id = conn.execute(query_max_id).scalar()
                
                # 2. Ver el próximo valor de la secuencia
                query_next_val = text("SELECT nextval('presentaciones_id_presentacion_seq')")
                next_val = conn.execute(query_next_val).scalar()
                
                # 3. Ver el valor actual de la secuencia
                query_curr_val = text("SELECT currval('presentaciones_id_presentacion_seq')")
                try:
                    curr_val = conn.execute(query_curr_val).scalar()
                except:
                    curr_val = "No disponible"
                
                # 4. Ver cuántas presentaciones tiene el producto 121
                query_count_121 = text("SELECT COUNT(*) FROM presentaciones WHERE id_producto = 121")
                count_121 = conn.execute(query_count_121).scalar()
                
                diagnostico = f"""
                🔍 DIAGNÓSTICO DE SECUENCIA:
                
                Máximo ID en tabla: {max_id}
                Próximo valor de secuencia: {next_val}
                Valor actual de secuencia: {curr_val}
                Presentaciones para producto 121: {count_121}
                
                📊 ESTADO: {"❌ PROBLEMA - Secuencia desincronizada" if next_val <= max_id else "✅ OK - Secuencia sincronizada"}
                """
                
                QMessageBox.information(self, "Diagnóstico", diagnostico)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo realizar el diagnóstico: {str(e)}")


    # En ui_pos.py, añadir este nuevo método
    # En ui_pos.py, después del método _modificar_formula
    def _gestionar_presentaciones(self, product_name):
        """Abre el diálogo para gestionar presentaciones - VERSIÓN DEFINITIVA CON DIAGNÓSTICO"""
        try:
            
            with self.engine.connect() as conn:
                # 1. Obtener el ID del producto
                query_id = text("SELECT id_producto FROM productos WHERE nombre_producto = :nombre")
                producto_id = conn.execute(query_id, {"nombre": product_name}).scalar()
                if not producto_id:
                    QMessageBox.warning(self, "Error", "No se encontró el producto.")
                    return

                # 2. Obtener las presentaciones actuales del producto
                query_presentaciones = text("""
                    SELECT id_presentacion, nombre_presentacion, factor, id_envase, costo_envase
                    FROM presentaciones 
                    WHERE id_producto = :id_producto
                    ORDER BY nombre_presentacion
                """)
                presentaciones_actuales_raw = conn.execute(query_presentaciones, {"id_producto": producto_id}).fetchall()
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
                query_envases = text("""
                    SELECT id_envase, nombre_envase, costo_envase
                    FROM envases_etiquetas
                    ORDER BY nombre_envase
                """)
                envases_disponibles_raw = conn.execute(query_envases).fetchall()
                envases_disponibles = [
                    {
                        'id_envase': row[0],
                        'nombre_envase': row[1],
                        'costo_envase': row[2] or 0.0
                    }
                    for row in envases_disponibles_raw
                ]

            # 4. Crear y mostrar el diálogo
            dialogo = GestionPresentacionesDialog(
                product_name, 
                producto_id, 
                presentaciones_actuales, 
                envases_disponibles, 
                self
            )
            
            if dialogo.exec_() == QDialog.Accepted:
                nuevas_presentaciones = dialogo.get_presentaciones()
                
                # **SOLUCIÓN DEFINITIVA**: Usar el método que evita duplicados
                self._guardar_presentaciones_evitando_duplicados(producto_id, nuevas_presentaciones, product_name)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron gestionar las presentaciones: {e}")

    def _guardar_presentaciones_evitando_duplicados(self, producto_id, nuevas_presentaciones, product_name):
        """Guarda presentaciones evitando duplicados de forma agresiva"""
        try:
            with self.engine.connect() as conn:
                # **PASO 1: Obtener el próximo ID disponible manualmente**
                query_max_id = text("SELECT COALESCE(MAX(id_presentacion), 0) FROM presentaciones")
                max_id = conn.execute(query_max_id).scalar()
                next_id = max_id + 1
                
                # **PASO 2: Eliminar TODAS las presentaciones del producto**
                conn.execute(
                    text("DELETE FROM presentaciones WHERE id_producto = :id_p"),
                    {"id_p": producto_id}
                )
                
                # **PASO 3: Insertar nuevas presentaciones con IDs explícitos**
                for pres in nuevas_presentaciones:
                    # Verificar si este ID ya existe (por si acaso)
                    query_check_id = text("SELECT 1 FROM presentaciones WHERE id_presentacion = :id")
                    exists = conn.execute(query_check_id, {"id": next_id}).fetchone()
                    
                    if exists:
                        # Si el ID ya existe, buscar el siguiente disponible
                        while exists:
                            next_id += 1
                            exists = conn.execute(query_check_id, {"id": next_id}).fetchone()
                    
                    # Insertar con ID explícito
                    conn.execute(
                        text("""
                            INSERT INTO presentaciones (id_presentacion, id_producto, nombre_presentacion, factor, id_envase, costo_envase)
                            VALUES (:id_pres, :id_p, :nombre, :factor, :id_envase, :costo_envase)
                        """),
                        {
                            "id_pres": next_id,
                            "id_p": producto_id,
                            "nombre": pres['nombre_presentacion'],
                            "factor": pres['factor'],
                            "id_envase": pres['id_envase'],
                            "costo_envase": pres['costo_envase']
                        }
                    )
                    
                    next_id += 1
                
                # **PASO 4: Resetear la secuencia al máximo ID + 1**
                try:
                    query_reset_seq = text("SELECT setval('presentaciones_id_presentacion_seq', :max_id, true)")
                    conn.execute(query_reset_seq, {"max_id": next_id - 1})
                except Exception as seq_error:
                    print(f"⚠️  No se pudo resetear la secuencia: {seq_error}")
                    # Continuar aunque falle el reset de secuencia
                
                conn.commit()
                
            QMessageBox.information(self, "Éxito", "Presentaciones actualizadas correctamente.")
            self._populate_grids()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron guardar las presentaciones: {str(e)}")


    def _guardar_presentaciones_simple(self, producto_id, nuevas_presentaciones, product_name):
        """Guarda presentaciones usando el método simple: eliminar todo e insertar nuevo"""
        try:
            with self.engine.connect() as conn:
                # **TRANSACCIÓN SIMPLE**: Eliminar todas las presentaciones del producto
                conn.execute(
                    text("DELETE FROM presentaciones WHERE id_producto = :id_p"),
                    {"id_p": producto_id}
                )
                
                # Insertar todas las nuevas presentaciones
                for pres in nuevas_presentaciones:
                    conn.execute(
                        text("""
                            INSERT INTO presentaciones (id_producto, nombre_presentacion, factor, id_envase, costo_envase)
                            VALUES (:id_p, :nombre, :factor, :id_envase, :costo_envase)
                        """),
                        {
                            "id_p": producto_id,
                            "nombre": pres['nombre_presentacion'],
                            "factor": pres['factor'],
                            "id_envase": pres['id_envase'],
                            "costo_envase": pres['costo_envase']
                        }
                    )
                
                # Commit explícito
                conn.commit()
                
            QMessageBox.information(self, "Éxito", "Presentaciones actualizadas correctamente.")
            self._populate_grids()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron guardar las presentaciones: {e}")

    def _procesar_presentaciones_definitivo(self, producto_id, nuevas_presentaciones, presentaciones_actuales, product_name):
        """Procesa las presentaciones con manejo robusto de transacciones"""
        try:
            with self.engine.connect() as conn:
                # **SOLUCIÓN: Hacer una transacción simple y directa**
                # Primero eliminar todas las presentaciones existentes para este producto
                # Luego insertar todas las nuevas
                
                conn.execute(
                    text("DELETE FROM presentaciones WHERE id_producto = :id_p"),
                    {"id_p": producto_id}
                )
                
                # Insertar todas las nuevas presentaciones
                for pres in nuevas_presentaciones:
                    conn.execute(
                        text("""
                            INSERT INTO presentaciones (id_producto, nombre_presentacion, factor, id_envase, costo_envase)
                            VALUES (:id_p, :nombre, :factor, :id_envase, :costo_envase)
                        """),
                        {
                            "id_p": producto_id,
                            "nombre": pres['nombre_presentacion'],
                            "factor": pres['factor'],
                            "id_envase": pres['id_envase'],
                            "costo_envase": pres['costo_envase']
                        }
                    )
                
                # Hacer commit explícito
                conn.commit()
                
            QMessageBox.information(self, "Éxito", "Presentaciones actualizadas correctamente.")
            # Recargar los productos para reflejar cambios
            self._populate_grids()

        except Exception as e:
            # Si hay error, hacer rollback automáticamente (el context manager se encarga)
            QMessageBox.critical(self, "Error", f"No se pudieron guardar las presentaciones: {e}")

    def _calcular_precio_presentacion(self, nombre_presentacion, precio_base_por_unidad, costo_envase, factor):
        """Calcula el precio automático CORREGIDO - precio_base es por kg/L"""
        
        # PRIMERO: Calcular el costo del PRODUCTO en esta presentación
        # precio_base_por_unidad es el costo por kg o litro
        costo_producto_en_presentacion = precio_base_por_unidad * factor
        
        # LUEGO: Aplicar las fórmulas específicas de ENVASE
        formulas = {
            "BARRIL 120 KG": lambda: costo_producto_en_presentacion + (costo_envase / 130),
            "COSTAL CON ETIQUETA": lambda: costo_producto_en_presentacion + (costo_envase / 25),
            "ENVASE ALCOHOLERO 1 L": lambda: costo_producto_en_presentacion + costo_envase,
            "ENVASE PET 1 L": lambda: costo_producto_en_presentacion + costo_envase,
            "ENVASE BOSTON 1 L": lambda: costo_producto_en_presentacion + costo_envase,
            "ENVASE PET 5 L": lambda: costo_producto_en_presentacion + (costo_envase / 5),
            "ENVASE PET 20 L": lambda: costo_producto_en_presentacion + (0.98 / 20),
            "ENVASE MUESTRA 250 mL": lambda: (precio_base_por_unidad * 0.25) + costo_envase,  # 250 mL = 0.25 L
            "ENVASE MUESTRA 500 mL": lambda: (precio_base_por_unidad * 0.5) + costo_envase,   # 500 mL = 0.5 L
            "BOLSA BLANCA": lambda: costo_producto_en_presentacion + costo_envase,
            "BOLSA TRANSPARENTE": lambda: costo_producto_en_presentacion + costo_envase,
        }
        
        if nombre_presentacion in formulas:
            precio_calculado = formulas[nombre_presentacion]()
        else:
            precio_calculado = costo_producto_en_presentacion + costo_envase
        
        return round(precio_calculado, 2)

    def _establecer_precio_manual_presentacion(self, product_name, presentacion_nombre):
        """Establece un precio manual para una presentación específica - SIN ERROR DE AMBIGÜEDAD"""
        try:
            with self.engine.connect() as conn:
                # SOLUCIÓN INGENIOSA: Primero obtener el ID del producto, luego buscar en presentaciones
                # Esto evita el JOIN problemático
                
                # 1. Obtener el ID del producto
                query_producto_id = text("SELECT id_producto FROM productos WHERE nombre_producto = :producto")
                producto_id = conn.execute(query_producto_id, {"producto": product_name}).scalar()
                
                if not producto_id:
                    QMessageBox.warning(self, "Error", f"No se encontró el producto '{product_name}'")
                    return
                
                # 2. Obtener precio actual usando solo el ID (sin JOIN ambiguo)
                query_precio_actual = text("""
                    SELECT precio_venta 
                    FROM presentaciones 
                    WHERE id_producto = :producto_id AND nombre_presentacion = :presentacion
                """)
                precio_actual = conn.execute(query_precio_actual, {
                    "producto_id": producto_id, 
                    "presentacion": presentacion_nombre
                }).scalar()
                
                # Pedir nuevo precio al usuario (MISMA FUNCIONALIDAD)
                nuevo_precio, ok = QInputDialog.getDouble(
                    self,
                    f"Precio Manual - {presentacion_nombre}",
                    f"Establecer precio manual para:\n{product_name} - {presentacion_nombre}\n\nPrecio actual: ${precio_actual if precio_actual else 'Automático'}",
                    value=precio_actual if precio_actual else 0,
                    min=0.01,
                    max=10000,
                    decimals=2
                )
                
                if ok:
                    # Actualizar en base de datos (MISMA FUNCIONALIDAD)
                    query_update = text("""
                        UPDATE presentaciones 
                        SET precio_venta = :precio
                        WHERE id_producto = :producto_id AND nombre_presentacion = :presentacion
                    """)
                    conn.execute(query_update, {
                        "precio": nuevo_precio,
                        "producto_id": producto_id,
                        "presentacion": presentacion_nombre
                    })
                    conn.commit()
                    
                    QMessageBox.information(
                        self, 
                        "Precio Manual Establecido", 
                        f"✅ Precio manual establecido:\n\n{product_name} - {presentacion_nombre}\n💵 ${nuevo_precio:.2f}"
                    )
                    
                    # Recargar presentaciones si están visibles (MISMA FUNCIONALIDAD)
                    if self.current_product_with_presentaciones == product_name:
                        self._ocultar_presentaciones()
                        self._mostrar_presentaciones("productos", product_name)
                            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo establecer el precio manual: {e}")

    def _volver_a_calculo_automatico_presentacion(self, product_name, presentacion_nombre):
        """Vuelve al cálculo automático para una presentación - SIN ERROR DE AMBIGÜEDAD"""
        try:
            with self.engine.connect() as conn:
                # SOLUCIÓN INGENIOSA: Primero obtener el ID del producto
                query_producto_id = text("SELECT id_producto FROM productos WHERE nombre_producto = :producto")
                producto_id = conn.execute(query_producto_id, {"producto": product_name}).scalar()
                
                if not producto_id:
                    QMessageBox.warning(self, "Error", f"No se encontró el producto '{product_name}'")
                    return
                
                # Establecer precio_venta como NULL (sin JOIN ambiguo)
                query_update = text("""
                    UPDATE presentaciones 
                    SET precio_venta = NULL
                    WHERE id_producto = :producto_id AND nombre_presentacion = :presentacion
                """)
                conn.execute(query_update, {
                    "producto_id": producto_id,
                    "presentacion": presentacion_nombre
                })
                conn.commit()
                
                QMessageBox.information(
                    self, 
                    "Cálculo Automático Activado", 
                    f"Cálculo automático activado:\n\n{product_name} - {presentacion_nombre}\n\nEl precio se calculará automáticamente según la fórmula."
                )
                
                # Recargar presentaciones si están visibles (MISMA FUNCIONALIDAD)
                if self.current_product_with_presentaciones == product_name:
                    self._ocultar_presentaciones()
                    self._mostrar_presentaciones("productos", product_name)
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo activar el cálculo automático: {e}")



    def verificar_y_corregir_precios(self):
        """Verifica que todos los productos tengan fórmulas y precios calculados correctamente"""
        try:
            with self.engine.connect() as conn:
                # Obtener todos los productos
                query_productos = text("SELECT nombre_producto, id_producto FROM productos")
                productos = conn.execute(query_productos).fetchall()
                
                productos_sin_formula = []
                productos_sin_precio = []
                productos_corregidos = []
                
                for producto_nombre, producto_id in productos:
                    print(f"Verificando: {producto_nombre}")
                    
                    # Verificar si tiene fórmula
                    query_formula = text("SELECT COUNT(*) FROM formulas WHERE id_producto = :id_p")
                    tiene_formula = conn.execute(query_formula, {"id_p": producto_id}).scalar()
                    
                    if not tiene_formula:
                        productos_sin_formula.append(producto_nombre)
                        print(f"Sin fórmula")
                        continue
                    
                    # Recalcular precio
                    nuevo_precio = self._recalcular_precio_producto(conn, producto_nombre)
                    
                    if nuevo_precio == 0:
                        productos_sin_precio.append(producto_nombre)
                        print(f"Precio $0 después del cálculo")
                    else:
                        productos_corregidos.append((producto_nombre, nuevo_precio))
                        print(f"Precio calculado: ${nuevo_precio:.2f}")
                
                # Mostrar resumen
                mensaje = ""
                if productos_corregidos:
                    mensaje += "Productos con precios calculados:\n"
                    for nombre, precio in productos_corregidos:
                        mensaje += f"   - {nombre}: ${precio:.2f}\n"
                    mensaje += "\n"
                
                if productos_sin_formula:
                    mensaje += "Productos sin fórmula definida:\n" + "\n".join([f"   - {p}" for p in productos_sin_formula]) + "\n\n"
                
                if productos_sin_precio:
                    mensaje += "Productos con precio $0 (verificar costos de materias primas):\n" + "\n".join([f"   - {p}" for p in productos_sin_precio])
                
                if not productos_sin_formula and not productos_sin_precio:
                    mensaje = "Todos los productos tienen fórmulas y precios calculados correctamente."
                
                QMessageBox.information(self, "Verificación de Precios", mensaje)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error en verificación de precios: {e}")
    # -------------------------
    # Event Filter para resize
    # -------------------------
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize and obj in self.viewport_map:
            table_name, grid_layout = self.viewport_map[obj]
            self._relayout_table(table_name, grid_layout, viewport=obj)
        return super().eventFilter(obj, event)

    # -------------------------
    # Población de grids
    # -------------------------
    def _populate_grids(self):
        """Poblar los grids con productos - MANTENER ESTA FUNCIÓN"""
        categories = [
            ("productos", "nombre_producto", "estatus_producto", self.grid_layout_productos),
            ("productosreventa", "nombre_prev", "estatus_prev", self.grid_layout_reventa),
            ("materiasprimas", "nombre_mp", "estatus_mp", self.grid_layout_materias_primas)
        ]
        for table_name, name_col, status_col, grid_layout in categories:
            self._create_buttons_for_category(table_name, name_col, status_col, grid_layout)

    # -------------------------
    # Crear botones, eliminar duplicados
    # -------------------------
    def _create_buttons_for_category(self, table_name, name_col, status_col, grid_layout):
        """Crear botones para categoría - VERSIÓN COMPLETAMENTE CORREGIDA"""
        try:
            stock_col_map = {
                "productos": "cantidad_producto",
                "productosreventa": "cantidad_prev", 
                "materiasprimas": "cantidad_comprada_mp"
            }
            stock_col = stock_col_map.get(table_name, None)

            with self.engine.connect() as conn:
                if stock_col:
                    query = text(f"""
                        SELECT {name_col}, {stock_col}
                        FROM {table_name}
                        WHERE {status_col} = 1
                        ORDER BY {name_col};
                    """)
                else:
                    query = text(f"""
                        SELECT {name_col}, NULL
                        FROM {table_name}
                        WHERE {status_col} = 1
                        ORDER BY {name_col};
                    """)
                
                # EJECUTAR CONEXIÓN CORRECTAMENTE
                result = conn.execute(query)
                rows = result.fetchall()
                
                productos = []
                for row in rows:
                    # ACCEDER POR ÍNDICE NUMÉRICO - CORRECCIÓN DEFINITIVA
                    nombre = row[0] if row[0] is not None else ""
                    stock = row[1] if len(row) > 1 and row[1] is not None else 0
                    
                    if nombre and str(nombre).strip() != "":
                        productos.append((str(nombre).strip(), stock))
                        
                print(f"✅ Cargados {len(productos)} productos de {table_name}")
                
        except Exception as e:
            print(f"[ui_pos] Error al leer '{table_name}': {e}")
            productos = []

        # Guardar en cache
        self.products_cache[table_name] = productos

        # Forzar relayout
        for viewport, (tn, gl) in self.viewport_map.items():
            if tn == table_name:
                self._relayout_table(table_name, gl, viewport)
                break

    # -------------------------
    # Layout tipo object-fit, eliminar duplicados
    # -------------------------
    def _relayout_table(self, table_name, grid_layout, viewport):
        """
        Dibuja los botones en el grid usando la lista (nombre, stock) almacenada en products_cache.
        """
        productos = self.products_cache.get(table_name, [])
        if not productos:
            return

        available_width = max(10, viewport.width())
        columnas = max(1, available_width // (self.min_button_width + grid_layout.spacing()))

        # Limpiar layout y eliminar botones duplicados existentes
        nombres_vistos = set()
        widgets_a_eliminar = []
        for i in range(grid_layout.count()):
            item = grid_layout.itemAt(i)
            w = item.widget()
            if w and isinstance(w, QPushButton):
                pname = w.property('product_name')
                if pname is None:
                    text = w.text()
                    pname = text.split(" (")[0] if " (" in text else text
                if pname in nombres_vistos:
                    widgets_a_eliminar.append(w)
                else:
                    nombres_vistos.add(pname)

        for w in widgets_a_eliminar:
            grid_layout.removeWidget(w)
            w.deleteLater()

        # Agregar botones nuevos
        idx_real = 0
        for nombre, stock in productos:
            if nombre in nombres_vistos or not str(nombre).strip():
                continue

            fila = idx_real // columnas
            col = idx_real % columnas

            try:
                if isinstance(stock, float) and stock.is_integer():
                    stock_display = int(stock)
                else:
                    stock_display = stock
            except Exception:
                stock_display = stock

            btn = QPushButton(f"{nombre} ({stock_display})")
            btn.setProperty('product_name', nombre)

            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setMinimumSize(self.min_button_width, self.min_button_height)
            btn.setToolTip(nombre)

            # MODIFICACIÓN: Solo productos normales usan presentaciones
            if table_name == "productos":
                btn.clicked.connect(functools.partial(self._mostrar_presentaciones, table_name, nombre))
            else:
                btn.clicked.connect(functools.partial(self._add_product_to_ticket, table_name, nombre))
                

            # Menú contextual en POS
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                functools.partial(self._mostrar_menu_contextual_pos, table_name, nombre, btn))

            grid_layout.addWidget(btn, fila, col)
            nombres_vistos.add(nombre)
            idx_real += 1



    # -------------------------
    # Refrescar todos los layouts
    # -------------------------
    def _refresh_all_layouts(self):
        """Refrescar todos los layouts - MANTENER ESTA FUNCIÓN"""
        for viewport, (table_name, grid_layout) in self.viewport_map.items():
            self._relayout_table(table_name, grid_layout, viewport)

    # -------------------------
    # Funciones de Clientes
    # -------------------------
    def _load_clients(self):
        """Carga los clientes de la base de datos en el QComboBox - VERSIÓN CORREGIDA"""
        self.cliente_combobox.clear()
        try:
            with self.engine.connect() as conn:
                # CORRECCIÓN: Usar nombre_cliente en lugar de nombre - YA ESTÁ CORRECTO
                query = text("SELECT id_cliente, nombre_cliente FROM clientes ORDER BY nombre_cliente")
                result = conn.execute(query)
                rows = result.fetchall()
                
                for row in rows:
                    # Acceder por índice numérico
                    id_cliente = row[0]
                    nombre_cliente = row[1]
                    self.cliente_combobox.addItem(nombre_cliente, id_cliente)
                        
                print(f"✅ Cargados {len(rows)} clientes")
                        
        except Exception as e:
            print(f"❌ Error al cargar clientes: {e}")
            QMessageBox.critical(self, "Error de Base de Datos", f"No se pudo cargar la lista de clientes:\n{e}")
            # Fallback
            self.cliente_combobox.addItem("Cliente General", 1)

        
    def _get_selected_client_id(self):
        """Obtiene el ID del cliente seleccionado en el QComboBox."""
        current_text = self.cliente_combobox.currentText().strip()
        
        # Si el usuario escribió algo que no está en la lista, buscar en la BD
        if self.cliente_combobox.findText(current_text) == -1:
            try:
                with self.engine.connect() as conn:
                    # CORRECCIÓN: Usar nombre_cliente
                    query = text("SELECT id_cliente FROM clientes WHERE nombre_cliente = :nombre")
                    result = conn.execute(query, {"nombre": current_text})
                    row = result.fetchone()
                    if row:
                        return row[0]  # Acceder por índice
            except Exception as e:
                print(f"Error al buscar cliente por nombre: {e}")
                
        # Si está en la lista o es "Cliente General"
        index = self.cliente_combobox.currentIndex()
        if index != -1:
            return self.cliente_combobox.itemData(index)
            
        # Fallback al cliente general
        return 1
        
    # -------------------------
    # Ticket methods
    # -------------------------
    def _add_product_to_ticket(self, table_name, product_name):
        """
        Añade un producto al ticket - VERSIÓN CORREGIDA PARA EVITAR DOBLE CÁLCULO
        """
        self.actualizar_area_producto(product_name, table_name)

        # Para productos normales, NO calcular precio aquí - ya se calculó en presentaciones
        product_price = 0.0
        
        try:
            with self.engine.connect() as conn:
                if table_name == "productos":
                    # Para productos normales, obtener el precio actual de la BD
                    # pero NO recalcular (ya debería estar calculado)
                    query = text("SELECT precio_venta FROM productos WHERE nombre_producto = :nombre")
                    resultado = conn.execute(query, {"nombre": product_name}).scalar()
                    if resultado is not None:
                        product_price = float(resultado)
                    
                    # Si el precio es 0, mostrar advertencia pero permitir continuar
                    if product_price == 0.0:
                        respuesta = QMessageBox.question(self, "Precio Cero", 
                                                        f"El precio de '{product_name}' es $0.00. ¿Desea continuar?",
                                                        QMessageBox.Yes | QMessageBox.No)
                        if respuesta == QMessageBox.No:
                            return
                        
                elif table_name == "materiasprimas":
                    query_id = text("SELECT id_mp FROM materiasprimas WHERE nombre_mp = :nombre")
                    product_id = conn.execute(query_id, {"nombre": product_name}).scalar()
                    if product_id:
                        query = text("SELECT costo_unitario_mp FROM materiasprimas WHERE id_mp = :id")
                        resultado = conn.execute(query, {"id": product_id}).scalar()
                        if resultado:
                            product_price = float(resultado)
                elif table_name == "productosreventa":
                    query = text("SELECT id_prev, precio_venta, unidad_medida_prev FROM productosreventa WHERE nombre_prev = :nombre")
                    resultado = conn.execute(query, {"nombre": product_name}).fetchone()
                    
                    if resultado:
                        id_prev, product_price, unidad_medida = resultado
                        product_price = float(product_price)
                            
        except Exception as e:
            QMessageBox.critical(self, "Error de Base de Datos", f"No se pudo obtener el precio del producto:\n{e}")
            return

        # Añadir el producto al ticket (solo la interfaz)
        if product_name in self.current_ticket:
            self.current_ticket[product_name]['qty'] += 1
            qty = self.current_ticket[product_name]['qty']
            price = self.current_ticket[product_name]['price']
            self.current_ticket[product_name]['label'].setText(f"{product_name} x{qty}  ${price*qty:.2f}")
        else:
            # Crear fila del ticket
            item_widget = QWidget()
            layout = QHBoxLayout(item_widget)
            layout.setContentsMargins(5, 2, 5, 2)

            label = QLabel(f"{product_name} x1  ${product_price:.2f}")
            layout.addWidget(label)

            delete_btn = QPushButton("–")
            delete_btn.setFixedSize(24, 24)
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff4d4d;
                    color: white;
                    border-radius: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #e60000;
                }
            """)
            delete_btn.hide()
            layout.addWidget(delete_btn)

            item_widget.enterEvent = lambda e: delete_btn.show()
            item_widget.leaveEvent = lambda e: delete_btn.hide()

            delete_btn.clicked.connect(lambda _, name=product_name: self._decrement_ticket_product(name))

            self.ticket_items_area.addWidget(item_widget)

            self.current_ticket[product_name] = {
                'qty': 1,
                'price': product_price,
                'widget': item_widget,
                'label': label,
                'product_name_base': product_name,
                'table_name': table_name
            }

        # Actualizar total
        self.current_total += product_price
        self._update_ticket_display()


    def _decrement_ticket_product(self, product_name):
        """Reduce la cantidad y elimina la fila si llega a 0 - VERSIÓN MEJORADA"""
        if product_name in self.current_ticket:
            product_data = self.current_ticket[product_name]
            product_data['qty'] -= 1
            qty = product_data['qty']
            price = product_data['price']
            label = product_data['label']

            if qty > 0:
                label.setText(f"{product_name} x{qty}  ${price*qty:.2f}")
            else:
                # Elimina el widget del layout
                widget = product_data['widget']
                self.ticket_items_area.removeWidget(widget)
                widget.deleteLater()
                del self.current_ticket[product_name]

            # Actualiza total - usar precio_calculado si existe
            precio_a_restar = product_data.get('precio_calculado', price)
            self.current_total -= precio_a_restar
            self._update_ticket_display()


    def _update_ticket_display(self):
        """Actualiza cantidades y total, sin eliminar los botones del ticket."""
        for name, data in self.current_ticket.items():
            qty = data['qty']
            price = data['price']
            label = data['label']
            label.setText(f"{name} x{qty}  ${price*qty:.2f}")

        self.total_label.setText(f"<b>Total: ${self.current_total:,.2f}</b>")



    def _clear_ticket(self):
        # Eliminar widgets del ticket
        for product_data in self.current_ticket.values():
            widget = product_data.get("widget")
            if widget:
                self.ticket_items_area.removeWidget(widget)
                widget.deleteLater()

        # Limpiar diccionario y total
        self.current_ticket.clear()
        self.current_total = 0.0
        self._update_ticket_display()


    # En ui_pos.py, reemplaza el método _process_sale con este código:

# En ui_pos.py, reemplaza el método _process_sale con esta versión corregida:

    def _process_sale(self):
        """Procesa la venta - VERSIÓN CORREGIDA CON ACCESO POR ÍNDICES"""
        if not self.current_ticket:
            QMessageBox.warning(self, "Ticket Vacío", "No hay productos en el ticket para cobrar.")
            return

        try:
            with self.engine.connect() as conn:
                with conn.begin() as trans:
                    cliente_id = self._get_selected_client_id()
                    total_venta = self.current_total

                    if not cliente_id:
                        query_cliente_general = text("SELECT id_cliente FROM clientes WHERE nombre_cliente = 'Cliente General'")
                        cliente_result = conn.execute(query_cliente_general).fetchone()
                        if cliente_result:
                            cliente_id = cliente_result[0]  # Acceder por índice
                        else:
                            QMessageBox.warning(self, "Error de Cliente", "No se pudo identificar al cliente ni al cliente general por defecto.")
                            return

                    # PRIMERO: VERIFICAR STOCK PARA TODOS LOS PRODUCTOS
                    productos_sin_stock = []
                    for product_name_display, data in self.current_ticket.items():
                        cantidad = data["qty"]
                        
                        # Usar el nombre base para productos con presentaciones
                        product_name_base = data.get('product_name_base', product_name_display)
                        
                        # Verificar producto normal - CORREGIDO: acceder por índice
                        producto = conn.execute(
                            text("SELECT id_producto, cantidad_producto FROM productos WHERE nombre_producto = :nombre"),
                            {"nombre": product_name_base}
                        ).fetchone()

                        if producto:
                            producto_id, stock_actual = producto[0], producto[1]  # Acceder por índice
                            if stock_actual < cantidad:
                                productos_sin_stock.append(f"'{product_name_base}': Stock {stock_actual}, Necesario {cantidad}")
                            continue

                        # Verificar producto reventa - CORREGIDO: acceder por índice
                        reventa = conn.execute(
                            text("SELECT id_prev, cantidad_prev, unidad_medida_prev FROM productosreventa WHERE nombre_prev = :nombre"),
                            {"nombre": product_name_base}
                        ).fetchone()

                        if reventa:
                            id_prev, stock_actual, unidad_medida = reventa[0], reventa[1], reventa[2]  # Acceder por índice
                            if stock_actual < cantidad:
                                productos_sin_stock.append(f"'{product_name_base}': Stock {stock_actual}, Necesario {cantidad}")
                            continue

                        # Verificar materia prima - CORREGIDO: acceder por índice
                        mp = conn.execute(
                            text("SELECT id_mp, cantidad_comprada_mp FROM materiasprimas WHERE nombre_mp = :nombre"),
                            {"nombre": product_name_base}
                        ).fetchone()

                        if mp:
                            id_mp, stock_actual = mp[0], mp[1]  # Acceder por índice
                            if stock_actual < cantidad:
                                productos_sin_stock.append(f"'{product_name_base}': Stock {stock_actual}, Necesario {cantidad}")
                            continue

                        productos_sin_stock.append(f"'{product_name_base}': No encontrado")

                    if productos_sin_stock:
                        mensaje_error = "Stock insuficiente:\n" + "\n".join(productos_sin_stock)
                        QMessageBox.warning(self, "Stock Insuficiente", mensaje_error)
                        return

                    # SEGUNDO: PROCESAR VENTA COMPLETA
                    for product_name_display, data in self.current_ticket.items():
                        cantidad = data["qty"]
                        precio_unitario = data["price"]
                        total_linea = cantidad * precio_unitario
                        
                        # Usar el nombre base para productos con presentaciones
                        product_name_base = data.get('product_name_base', product_name_display)

                        # ---------- PRODUCTO NORMAL ----------
                        producto = conn.execute(
                            text("SELECT id_producto, cantidad_producto FROM productos WHERE nombre_producto = :nombre"),
                            {"nombre": product_name_base}
                        ).fetchone()

                        if producto:
                            producto_id, stock_actual = producto[0], producto[1]  # Acceder por índice

                            # Actualizar stock
                            conn.execute(
                                text("UPDATE productos SET cantidad_producto = cantidad_producto - :cantidad WHERE id_producto = :id"),
                                {"cantidad": cantidad, "id": producto_id}
                            )

                            # Registrar venta
                            conn.execute(text("""
                                INSERT INTO ventas (id_cliente, nombre_producto, tipo_tabla, cantidad, total, fecha_venta)
                                VALUES (:cliente, :nombre, 'productos', :cantidad, :total, DATE('now'))
                            """), {
                                "cliente": cliente_id,
                                "nombre": product_name_display,
                                "cantidad": cantidad,
                                "total": total_linea
                            })

                        # ---------- PRODUCTO REVENTA ----------
                        reventa = conn.execute(
                            text("SELECT id_prev, cantidad_prev, unidad_medida_prev FROM productosreventa WHERE nombre_prev = :nombre"),
                            {"nombre": product_name_base}
                        ).fetchone()

                        if reventa:
                            id_prev, stock_actual, unidad_medida = reventa[0], reventa[1], reventa[2]  # Acceder por índice

                            # Actualizar stock
                            conn.execute(
                                text("UPDATE productosreventa SET cantidad_prev = cantidad_prev - :cantidad WHERE id_prev = :id"),
                                {"cantidad": cantidad, "id": id_prev}
                            )

                            # Registrar venta en venta_reventa
                            conn.execute(text("""
                                INSERT INTO venta_reventa (id_prev, nombre_producto, cantidad, precio_unitario, total, fecha_venta, unidad_medida)
                                VALUES (:id_prev, :nombre_producto, :cantidad, :precio_unitario, :total, DATE('now'), :unidad_medida)
                            """), {
                                "id_prev": id_prev,
                                "nombre_producto": product_name_display,
                                "cantidad": cantidad,
                                "precio_unitario": precio_unitario,
                                "total": total_linea,
                                "unidad_medida": unidad_medida or "PIEZA"
                            })

                        # ---------- MATERIA PRIMA ----------
                        mp = conn.execute(
                            text("SELECT id_mp, cantidad_comprada_mp FROM materiasprimas WHERE nombre_mp = :nombre"),
                            {"nombre": product_name_base}
                        ).fetchone()

                        if mp:
                            id_mp, stock_actual = mp[0], mp[1]  # Acceder por índice

                            # Actualizar stock
                            conn.execute(
                                text("UPDATE materiasprimas SET cantidad_comprada_mp = cantidad_comprada_mp - :cantidad WHERE id_mp = :id"),
                                {"cantidad": cantidad, "id": id_mp}
                            )

                            # Registrar venta
                            conn.execute(text("""
                                INSERT INTO ventas (id_cliente, nombre_producto, tipo_tabla, cantidad, total, fecha_venta)
                                VALUES (:cliente, :nombre, 'materiasprimas', :cantidad, :total, DATE('now'))
                            """), {
                                "cliente": cliente_id,
                                "nombre": product_name_display,
                                "cantidad": cantidad,
                                "total": total_linea
                            })

                    # TERCERO: ACTUALIZAR FONDO
                    query_ultimo_saldo = text("SELECT saldo FROM fondo ORDER BY id_movimiento DESC LIMIT 1")
                    ultimo_saldo_result = conn.execute(query_ultimo_saldo).fetchone()
                    ultimo_saldo = ultimo_saldo_result[0] if ultimo_saldo_result else 0  # Acceder por índice
                    
                    nuevo_saldo = ultimo_saldo + total_venta
                    
                    query_fondo = text("""
                        INSERT INTO fondo (fecha, tipo, concepto, monto, saldo)
                        VALUES (DATE('now'), 'INGRESO', 'Venta POS', :monto, :saldo)
                    """)
                    conn.execute(query_fondo, {
                        "monto": total_venta,
                        "saldo": nuevo_saldo
                    })

            # ACTUALIZAR VISTA
            self._force_immediate_refresh()

            QMessageBox.information(self, "Venta Registrada", 
                                f"Venta realizada con éxito.\n\nTotal: ${self.current_total:,.2f}")
            
            self._clear_ticket()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo registrar la venta: {str(e)}")
            import traceback
            traceback.print_exc()

    def _force_immediate_refresh(self):
        """Actualización que MANTIENE el layout pero actualiza stocks"""
        try:
            print("🔄 Actualización MANTENIENDO layout...")
            
            # 1. Leer datos FRESCOS desde BD
            stocks_actualizados = {}
            with self.engine.connect() as fresh_conn:
                # Leer todos los productos actualizados
                query_productos = text("SELECT nombre_producto, cantidad_producto FROM productos WHERE estatus_producto = 1")
                for nombre, stock in fresh_conn.execute(query_productos).fetchall():
                    stocks_actualizados[nombre] = stock
                
                query_reventa = text("SELECT nombre_prev, cantidad_prev FROM productosreventa WHERE estatus_prev = 1")  
                for nombre, stock in fresh_conn.execute(query_reventa).fetchall():
                    stocks_actualizados[nombre] = stock
                    
                query_mp = text("SELECT nombre_mp, cantidad_comprada_mp FROM materiasprimas WHERE estatus_mp = 1")
                for nombre, stock in fresh_conn.execute(query_mp).fetchall():
                    stocks_actualizados[nombre] = stock
            
            # 2. Actualizar stocks en la cache
            for table_name in ["productos", "productosreventa", "materiasprimas"]:
                if table_name in self.products_cache:
                    productos_actualizados = []
                    for nombre, stock_viejo in self.products_cache[table_name]:
                        stock_actual = stocks_actualizados.get(nombre, stock_viejo)
                        productos_actualizados.append((nombre, stock_actual))
                    self.products_cache[table_name] = productos_actualizados
            
            # 3. ACTUALIZAR BOTONES EXISTENTES sin recrear el layout
            self._update_existing_buttons_stocks(stocks_actualizados)
            
            print("✅ Stocks actualizados manteniendo layout")
            
        except Exception as e:
            print(f"❌ Error actualizando stocks: {e}")

    def _force_immediate_refresh(self):
        """Actualización que MANTIENE el layout pero actualiza stocks"""
        try:
            print("🔄 Actualización MANTENIENDO layout...")
            
            # 1. Leer datos FRESCOS desde BD
            stocks_actualizados = {}
            with self.engine.connect() as fresh_conn:
                # Leer todos los productos actualizados
                query_productos = text("SELECT nombre_producto, cantidad_producto FROM productos WHERE estatus_producto = 1")
                for nombre, stock in fresh_conn.execute(query_productos).fetchall():
                    stocks_actualizados[nombre] = stock
                
                query_reventa = text("SELECT nombre_prev, cantidad_prev FROM productosreventa WHERE estatus_prev = 1")  
                for nombre, stock in fresh_conn.execute(query_reventa).fetchall():
                    stocks_actualizados[nombre] = stock
                    
                query_mp = text("SELECT nombre_mp, cantidad_comprada_mp FROM materiasprimas WHERE estatus_mp = 1")
                for nombre, stock in fresh_conn.execute(query_mp).fetchall():
                    stocks_actualizados[nombre] = stock
            
            # 2. Actualizar stocks en la cache
            for table_name in ["productos", "productosreventa", "materiasprimas"]:
                if table_name in self.products_cache:
                    productos_actualizados = []
                    for nombre, stock_viejo in self.products_cache[table_name]:
                        stock_actual = stocks_actualizados.get(nombre, stock_viejo)
                        productos_actualizados.append((nombre, stock_actual))
                    self.products_cache[table_name] = productos_actualizados
            
            # 3. ACTUALIZAR BOTONES EXISTENTES sin recrear el layout
            self._update_existing_buttons_stocks(stocks_actualizados)
            
            print("Stocks actualizados manteniendo layout")
            
        except Exception as e:
            print(f"Error actualizando stocks: {e}")

    def _update_existing_buttons_stocks(self, stocks_actualizados):
        """Actualiza SOLO los textos de los botones existentes"""
        try:
            # Para cada grid layout
            for grid_layout in [self.grid_layout_productos, self.grid_layout_reventa, self.grid_layout_materias_primas]:
                for i in range(grid_layout.count()):
                    item = grid_layout.itemAt(i)
                    if item and item.widget():
                        btn = item.widget()
                        if isinstance(btn, QPushButton):
                            current_text = btn.text()
                            if " (" in current_text:
                                product_name = current_text.split(" (")[0]
                                
                                # Buscar stock actualizado
                                nuevo_stock = stocks_actualizados.get(product_name)
                                if nuevo_stock is not None:
                                    # Formatear stock
                                    try:
                                        if isinstance(nuevo_stock, float) and nuevo_stock.is_integer():
                                            stock_display = int(nuevo_stock)
                                        else:
                                            stock_display = nuevo_stock
                                    except Exception:
                                        stock_display = nuevo_stock
                                    
                                    # Actualizar texto
                                    nuevo_texto = f"{product_name} ({stock_display})"
                                    if btn.text() != nuevo_texto:
                                        btn.setText(nuevo_texto)
                                        print(f"✅ Actualizado: {product_name} -> {stock_display}")
                            
        except Exception as e:
            print(f"Error actualizando botones: {e}")

    def _update_tab_counts(self):
        """Actualiza los contadores en los nombres de las pestañas"""
        try:
            for i in range(self.tabs_productos.count()):
                scroll_area = self.tabs_productos.widget(i)
                viewport = scroll_area.viewport()
                table_name, _ = self.viewport_map.get(viewport, (None, None))
                
                if table_name:
                    with self.engine.connect() as conn:
                        result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                        count = result.scalar() or 0
                    
                    # Actualizar nombre de pestaña con contador
                    old_text = self.tabs_productos.tabText(i)
                    # Remover contador anterior si existe
                    base_text = old_text.split(' (')[0] if ' (' in old_text else old_text
                    self.tabs_productos.setTabText(i, f"{base_text} ({count})")
                    
        except Exception as e:
            print(f"Error actualizando contadores: {e}")

    def _refresh_tab_layout(self, table_name):
        """Refresca solo la pestaña específica"""
        try:
            # Encontrar el grid layout correspondiente a esta tabla
            grid_layout_map = {
                "productos": self.grid_layout_productos,
                "productosreventa": self.grid_layout_reventa, 
                "materiasprimas": self.grid_layout_materias_primas
            }
            
            grid_layout = grid_layout_map.get(table_name)
            if not grid_layout:
                return
                
            # Encontrar el viewport correspondiente
            for viewport, (tn, gl) in self.viewport_map.items():
                if tn == table_name and gl == grid_layout:
                    self._relayout_table(table_name, grid_layout, viewport)
                    break
                    
        except Exception as e:
            print(f"Error al refrescar pestaña {table_name}: {e}")

    def _aumentar_stock_existente(self):
        """Permite aumentar stock de una materia prima existente"""
        dialog = AumentarStockDialog(self, engine=self.engine)
        if dialog.exec_() == QDialog.Accepted:
            try:
                # Refrescar solo la sección de materias primas
                self._create_buttons_for_category(
                    "materiasprimas", 
                    "nombre_mp", 
                    "estatus_mp", 
                    self.grid_layout_materias_primas
                )
                QMessageBox.information(self, "Éxito", "Stock de materia prima actualizado correctamente.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo actualizar la vista: {e}")

    
    #-----Funciones para el menu contextual-----
    def _modificar_precio_compra(self, product_name):
        precio, ok = QInputDialog.getDouble(
            self, "Modificar Precio de Compra",
            f"Ingrese el nuevo precio de compra para '{product_name}':", decimals=2
        )

        if ok:
            try:
                with self.engine.connect() as conn:
                    query = text("""
                        UPDATE productosreventa 
                        SET precio_compra = :precio_compra 
                        WHERE nombre_prev = :nombre
                    """)
                    conn.execute(query, {"precio_compra": precio, "nombre": product_name})
                    conn.commit()
                QMessageBox.information(self, "Éxito", f"Precio de compra actualizado: {precio}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo actualizar el precio:\n{e}")

    def _agregar_producto_reventa(self):
        nombre, ok = QInputDialog.getText(self, "Agregar Producto Reventa", "Nombre del producto:")
        if not ok or not nombre.strip():
            return

        unidad, ok = QInputDialog.getText(self, "Agregar Producto Reventa", "Unidad de medida:")
        if not ok or not unidad.strip():
            return

        precio_venta, ok = QInputDialog.getDouble(
            self, "Agregar Producto Reventa", "Precio de venta:", decimals=2
        )
        if not ok:
            return

        precio_compra, ok = QInputDialog.getDouble(
            self, "Agregar Producto Reventa", "Precio de compra:", decimals=2
        )
        if not ok:
            return

        try:
            with self.engine.connect() as conn:
                query = text("""
                    INSERT INTO productosreventa 
                    (nombre_prev, unidad_medida_prev, estatus_prev, proveedor, area_prev, cantidad_prev, precio_venta, precio_compra)
                    VALUES (:nombre, :unidad, 1, :proveedor, 'QUIMO CLEAN', 0, :precio_venta, :precio_compra)
                """)
                conn.execute(query, {
                    "nombre": nombre,
                    "unidad": unidad,
                    "proveedor": "DESCONOCIDO",
                    "precio_venta": precio_venta,
                    "precio_compra": precio_compra
                })
                conn.commit()

            QMessageBox.information(self, "Éxito", f"Producto reventa '{nombre}' agregado correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo agregar el producto:\n{e}")

    def _agregar_producto(self):
        nombre, ok = QInputDialog.getText(self, "Agregar Existencias", "Nombre del producto:")
        if not ok or not nombre.strip():
            return

        cantidad, ok = QInputDialog.getDouble(
            self, "Agregar Existencias", "Cantidad a añadir:", decimals=2
        )
        if not ok:
            return

        try:
            with self.engine.connect() as conn:
                # Revisar si existe fórmula
                query_formula = text("""
                    SELECT id_producto, cantidad FROM formulas WHERE nombre_producto = :nombre
                """)
                formula_result = conn.execute(query_formula, {"nombre": nombre}).fetchall()

                if not formula_result:
                    QMessageBox.warning(self, "Error", f"No existe fórmula definida para '{nombre}'")
                    return

                # Recorrer fórmula para aumentar existencias de materia prima
                for id_producto, cantidad_formula in formula_result:
                    incremento = cantidad_formula * cantidad
                    query_update = text("""
                        UPDATE materiasprimas
                        SET existencia = existencia + :incremento
                        WHERE id_mp = :id_mp
                    """)
                    conn.execute(query_update, {"incremento": incremento, "id_mp": id_producto})

                conn.commit()
            QMessageBox.information(self, "Éxito", f"Existencias de '{nombre}' actualizadas.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo agregar existencias:\n{e}")

    def abrir_agregar_producto_reventa(self):
        dialog = AgregarProductosReventaDialog(self)
        dialog.exec_()

    # --- Funciones para el menú contextual ---
    # En ui_pos.py, en el método _mostrar_menu_contextual_pos
    def _mostrar_menu_contextual_pos(self, table_name, product_name, btn, position):
        """Menú contextual para los botones de productos en el POS - VERSIÓN COMPLETA CON GESTIÓN DE PRECIOS"""
        menu = QMenu()

        # --- MENÚ DE CANTIDAD ---
        menu_cantidad = menu.addMenu(" Agregar cantidad...")
        
        # Para productos normales, todas las opciones mostrarán presentaciones primero
        if table_name == "productos":
            # Opciones rápidas que mostrarán presentaciones
            cantidades = [1, 5, 10, 25, 50, 100]
            for cantidad in cantidades:
                accion = QAction(f"{cantidad} unidades", self)
                # Guardar la cantidad en una variable temporal
                accion.triggered.connect(
                    lambda checked, tn=table_name, pn=product_name, cant=cantidad: 
                    self._mostrar_presentaciones_con_cantidad(tn, pn, cant)
                )
                menu_cantidad.addAction(accion)
            
            # Opción personalizada
            accion_personalizada = QAction("Cantidad personalizada...", self)
            accion_personalizada.triggered.connect(
                lambda: self._pedir_cantidad_y_mostrar_presentaciones(table_name, product_name)
            )
            menu_cantidad.addAction(accion_personalizada)
        
        else:
            # Para productos reventa y materias primas, agregar directamente
            cantidades = [1, 5, 10, 25, 50, 100]
            for cantidad in cantidades:
                accion = QAction(f"{cantidad} unidades", self)
                accion.triggered.connect(
                    lambda checked, tn=table_name, pn=product_name, cant=cantidad: 
                    self._agregar_multiples_unidades(tn, pn, cant)
                )
                menu_cantidad.addAction(accion)
            
            # Opción personalizada para no-productos
            accion_personalizada = QAction("Cantidad personalizada...", self)
            accion_personalizada.triggered.connect(
                lambda: self._agregar_producto_con_cantidad(table_name, product_name)
            )
            menu_cantidad.addAction(accion_personalizada)
        
        # --- NUEVO: GESTIÓN DE PRECIOS POR PRESENTACIÓN (SOLO PARA PRODUCTOS NORMALES) ---
        if table_name == "productos":
            menu_precios = menu.addMenu(" Gestión de Precios por Presentación")
            
            try:
                with self.engine.connect() as conn:
                    # Obtener todas las presentaciones del producto
                    query_presentaciones = text("""
                        SELECT p.nombre_presentacion, p.precio_venta, p.factor, p.costo_envase
                        FROM presentaciones p
                        JOIN productos pr ON p.id_producto = pr.id_producto
                        WHERE pr.nombre_producto = :nombre
                        ORDER BY p.nombre_presentacion
                    """)
                    presentaciones = conn.execute(query_presentaciones, {"nombre": product_name}).fetchall()
                    
                    if presentaciones:
                        for nombre_pres, precio_actual, factor, costo_envase in presentaciones:
                            # Crear submenú para cada presentación
                            texto_presentacion = f" {nombre_pres}"
                            if precio_actual is not None:
                                texto_presentacion += f" -  ${precio_actual:.2f} (Manual)"
                            else:
                                texto_presentacion += f" -  (Automático)"
                            
                            submenu_pres = menu_precios.addMenu(texto_presentacion)
                            
                            # Opción: Establecer precio manual
                            accion_manual = QAction(" Establecer Precio Manual...", self)
                            accion_manual.triggered.connect(
                                lambda checked, pn=product_name, pres=nombre_pres: 
                                self._establecer_precio_manual_presentacion(pn, pres)
                            )
                            submenu_pres.addAction(accion_manual)
                            
                            
                            # Opción: Volver a automático (solo si tiene precio manual)
                            if precio_actual is not None:
                                accion_auto = QAction("Volver a Cálculo Automático", self)
                                accion_auto.triggered.connect(
                                    lambda checked, pn=product_name, pres=nombre_pres: 
                                    self._volver_a_calculo_automatico_presentacion(pn, pres)
                                )
                                submenu_pres.addAction(accion_auto)
                                
                            # Separador
                            submenu_pres.addSeparator()
                            
                            # Información de la presentación
                            info_texto = f"Factor: {factor}"
                            if costo_envase and costo_envase > 0:
                                info_texto += f" | Envase: ${costo_envase:.2f}"
                            accion_info = QAction(info_texto, self)
                            accion_info.setEnabled(False)  # Solo informativa, no clickeable
                            submenu_pres.addAction(accion_info)
                    
                    else:
                        # Si no tiene presentaciones, mostrar opción para gestionarlas
                        accion_sin_presentaciones = QAction("Gestionar Presentaciones...", self)
                        accion_sin_presentaciones.triggered.connect(
                            lambda: self._gestionar_presentaciones(product_name)
                        )
                        menu_precios.addAction(accion_sin_presentaciones)
                            
            except Exception as e:
                print(f"Error al cargar presentaciones para menú: {e}")
                accion_error = QAction(" Error al cargar presentaciones", self)
                accion_error.setEnabled(False)
                menu_precios.addAction(accion_error)

        # --- OPCIONES ESPECÍFICAS POR TIPO DE TABLA ---
        if table_name == "materiasprimas":
            accion_modificar = QAction(" Modificar Costo", self)
            accion_modificar.triggered.connect(functools.partial(self._modificar_costo, table_name, product_name))
            menu.addAction(accion_modificar)

            accion_agregar_mp = QAction("Agregar Materia Prima", self)
            accion_agregar_mp.triggered.connect(self._agregar_materia_prima)
            menu.addAction(accion_agregar_mp)

            accion_agregar_stock = QAction(" Aumentar stock existente", self)
            accion_agregar_stock.triggered.connect(self._aumentar_stock_existente)
            menu.addAction(accion_agregar_stock)

            # OPCIÓN: Eliminar Materia Prima
            accion_eliminar_mp = QAction(" Eliminar Materia Prima", self)
            accion_eliminar_mp.triggered.connect(functools.partial(self._eliminar_materia_prima, product_name))
            menu.addAction(accion_eliminar_mp)

        elif table_name == "productosreventa":
            accion_modificar_precio = QAction(" Modificar Precio Venta", self)
            accion_modificar_precio.triggered.connect(functools.partial(self._modificar_precio, table_name, product_name))
            menu.addAction(accion_modificar_precio)

            # NUEVA OPCIÓN: Comprar/Agregar Stock
            accion_comprar_stock = QAction(" Comprar/Agregar Stock", self)
            accion_comprar_stock.triggered.connect(functools.partial(self._comprar_producto_reventa, product_name))
            menu.addAction(accion_comprar_stock)

            accion_agregar_reventa = QAction(" Agregar producto de reventa", self)
            accion_agregar_reventa.triggered.connect(self.abrir_agregar_producto_reventa)
            menu.addAction(accion_agregar_reventa)

            # OPCIÓN: Eliminar Producto Reventa
            accion_eliminar_reventa = QAction(" Eliminar Producto Reventa", self)
            accion_eliminar_reventa.triggered.connect(functools.partial(self._eliminar_producto_reventa, product_name))
            menu.addAction(accion_eliminar_reventa)

        elif table_name == "productos":
            # Para productos normales, ofrecer opciones de fórmula y presentaciones
            accion_formula = QAction("Modificar Fórmula", self)
            accion_formula.triggered.connect(functools.partial(self._modificar_formula, product_name))
            menu.addAction(accion_formula)

            accion_comprar_stock = QAction(" Comprar/Producir Stock", self)
            accion_comprar_stock.triggered.connect(functools.partial(self._comprar_producto_normal, product_name))
            menu.addAction(accion_comprar_stock)

            # OPCIÓN: Gestionar Presentaciones
            accion_presentaciones = QAction(" Gestionar Presentaciones", self)
            accion_presentaciones.triggered.connect(functools.partial(self._gestionar_presentaciones, product_name))
            menu.addAction(accion_presentaciones)


            # Agregar opción cambiar área
            accion_cambiar_area = QAction(" Cambiar Área", self)
            accion_cambiar_area.triggered.connect(
                functools.partial(self._cambiar_area_producto, table_name, product_name)
            )
            menu.addAction(accion_cambiar_area)

            # OPCIÓN: Modificar Lote
            accion_modificar_lote = QAction(" Modificar Lote", self)
            accion_modificar_lote.triggered.connect(
                functools.partial(self._modificar_lote, product_name)
            )   
            menu.addAction(accion_modificar_lote)


            # OPCIÓN: Eliminar Producto
            accion_eliminar = QAction(" Eliminar Producto", self)
            accion_eliminar.triggered.connect(
                functools.partial(self._eliminar_producto, table_name, product_name)
            )
            menu.addAction(accion_eliminar)

        # --- OPCIÓN UNIVERSAL: ACTUALIZAR STOCK/VISTA ---
        menu.addSeparator()
        accion_actualizar = QAction(" Actualizar Vista", self)
        accion_actualizar.triggered.connect(self._populate_grids)
        menu.addAction(accion_actualizar)

        # Mostrar el menú
        menu.exec_(btn.mapToGlobal(position))

# AÑADE estos nuevos métodos para comprar productos de reventa
    def _comprar_producto_reventa(self, product_name):
        """Abre diálogo para comprar/agregar stock a un producto de reventa"""
        try:
            with self.engine.connect() as conn:
                # Obtener información actual del producto
                query = text("""
                    SELECT id_prev, cantidad_prev, precio_compra, precio_venta, unidad_medida_prev 
                    FROM productosreventa 
                    WHERE nombre_prev = :nombre
                """)
                resultado = conn.execute(query, {"nombre": product_name}).fetchone()
                
                if not resultado:
                    QMessageBox.warning(self, "Error", f"No se encontró el producto '{product_name}'")
                    return
                    
                id_prev, stock_actual, precio_compra_actual, precio_venta, unidad_medida = resultado
                
                # Crear y mostrar diálogo de compra
                dialogo = DialogoComprarProductoReventa(
                    product_name, 
                    stock_actual, 
                    precio_compra_actual or 0.0,
                    precio_venta or 0.0,
                    unidad_medida or "PIEZA",
                    self
                )
                
                if dialogo.exec_() == QDialog.Accepted:
                    cantidad_comprada, precio_compra, precio_venta_nuevo = dialogo.get_datos_compra()
                    
                    if cantidad_comprada <= 0:
                        QMessageBox.warning(self, "Error", "La cantidad debe ser mayor a 0")
                        return
                        
                    if precio_compra <= 0:
                        QMessageBox.warning(self, "Error", "El precio de compra debe ser mayor a 0")
                        return
                        
                    # Calcular total de la compra
                    total_compra = cantidad_comprada * precio_compra
                    
                    # Verificar que hay suficiente fondo
                    query_fondo = text("SELECT saldo FROM fondo ORDER BY id_movimiento DESC LIMIT 1")
                    saldo_actual = conn.execute(query_fondo).scalar() or 0
                    
                    if saldo_actual < total_compra:
                        QMessageBox.warning(
                            self, 
                            "Fondo Insuficiente", 
                            f"Fondo disponible: ${saldo_actual:,.2f}\n"
                            f"Total compra: ${total_compra:,.2f}\n\n"
                            f"No hay suficiente dinero en el fondo para realizar esta compra."
                        )
                        return
                    
                    # Confirmar la compra
                    confirmacion = QMessageBox.question(
                        self,
                        "Confirmar Compra",
                        f"¿Confirmar compra de {product_name}?\n\n"
                        f"Cantidad: {cantidad_comprada} {unidad_medida}\n"
                        f"Precio compra: ${precio_compra:.2f} c/u\n"
                        f"Total: ${total_compra:,.2f}\n\n"
                        f"Esta cantidad se descontará del fondo.",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    
                    if confirmacion == QMessageBox.Yes:
                        self._procesar_compra_reventa(
                            id_prev, product_name, cantidad_comprada, 
                            precio_compra, precio_venta_nuevo, total_compra, unidad_medida
                        )
                        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo procesar la compra: {e}")

    def _comprar_producto_normal(self, product_name):
        """Abre diálogo para comprar/producir más unidades de un producto normal según su fórmula"""
        try:
            with self.engine.connect() as conn:
                # Obtener información actual del producto y su fórmula
                query = text("""
                    SELECT 
                        p.id_producto, 
                        p.cantidad_producto,
                        p.precio_venta,
                        p.unidad_medida_producto,
                        COUNT(f.id_mp) as num_ingredientes
                    FROM productos p
                    LEFT JOIN formulas f ON p.id_producto = f.id_producto
                    WHERE p.nombre_producto = :nombre
                    GROUP BY p.id_producto
                """)
                resultado = conn.execute(query, {"nombre": product_name}).fetchone()
                
                if not resultado:
                    QMessageBox.warning(self, "Error", f"No se encontró el producto '{product_name}'")
                    return
                    
                id_producto, stock_actual, precio_venta, unidad_medida, num_ingredientes = resultado
                
                if num_ingredientes == 0:
                    QMessageBox.warning(
                        self, 
                        "Error", 
                        f"El producto '{product_name}' no tiene fórmula definida.\n\n"
                        f"Primero debe definir la fórmula antes de poder producirlo."
                    )
                    return
                
                # Obtener la fórmula completa con costos
                query_formula = text("""
                    SELECT 
                        mp.nombre_mp,
                        mp.costo_unitario_mp,
                        mp.unidad_medida_mp,
                        f.porcentaje,
                        mp.cantidad_comprada_mp as stock_mp
                    FROM formulas f
                    JOIN materiasprimas mp ON f.id_mp = mp.id_mp
                    WHERE f.id_producto = :id_producto
                """)
                ingredientes = conn.execute(query_formula, {"id_producto": id_producto}).fetchall()
                
                # Calcular costo actual por unidad del producto
                costo_por_unidad = 0.0
                for nombre_mp, costo_mp, unidad_mp, porcentaje, stock_mp in ingredientes:
                    if costo_mp is None:
                        QMessageBox.warning(
                            self,
                            "Error en Costos",
                            f"La materia prima '{nombre_mp}' no tiene costo definido.\n\n"
                            f"Debe establecer un costo para todas las materias primas antes de producir."
                        )
                        return
                    costo_por_unidad += float(costo_mp) * (float(porcentaje) / 100.0)
                
                # Crear y mostrar diálogo de producción
                dialogo = DialogoProducirProducto(
                    product_name, 
                    stock_actual, 
                    costo_por_unidad,
                    precio_venta or 0.0,
                    unidad_medida or "UNIDAD",
                    ingredientes,
                    self
                )
                
                if dialogo.exec_() == QDialog.Accepted:
                    cantidad_a_producir, precio_venta_nuevo = dialogo.get_datos_produccion()
                    
                    if cantidad_a_producir <= 0:
                        QMessageBox.warning(self, "Error", "La cantidad debe ser mayor a 0")
                        return
                    
                    # VERIFICAR STOCK DE MATERIAS PRIMAS
                    materias_primas_insuficientes = []
                    for nombre_mp, costo_mp, unidad_mp, porcentaje, stock_mp in ingredientes:
                        cantidad_necesaria = (float(porcentaje) / 100.0) * cantidad_a_producir
                        if stock_mp < cantidad_necesaria:
                            faltante = cantidad_necesaria - stock_mp
                            materias_primas_insuficientes.append(
                                f"  - {nombre_mp}: Necesario {cantidad_necesaria:.2f} {unidad_mp}, Disponible {stock_mp:.2f} {unidad_mp} (Faltan {faltante:.2f} {unidad_mp})"
                            )
                    
                    if materias_primas_insuficientes:
                        mensaje_error = f"Stock insuficiente de materias primas para producir {cantidad_a_producir} unidades de '{product_name}':\n\n" + "\n".join(materias_primas_insuficientes)
                        QMessageBox.warning(self, "Stock Insuficiente", mensaje_error)
                        return
                    
                    # Calcular costo total de producción (solo informativo, no se descuenta)
                    costo_total_produccion = costo_por_unidad * cantidad_a_producir
                    
                    # Confirmar la producción (SIN DESCONTAR DEL FONDO)
                    confirmacion = QMessageBox.question(
                        self,
                        "Confirmar Producción",
                        f"¿Confirmar producción de {product_name}?\n\n"
                        f"Cantidad a producir: {cantidad_a_producir} {unidad_medida}\n"
                        f"Costo por unidad: ${costo_por_unidad:.2f}\n"
                        f"Costo total: ${costo_total_produccion:,.2f}\n"
                        f"Precio venta: ${precio_venta_nuevo:.2f} c/u\n\n"
                        f"Se consumirán las materias primas necesarias del inventario.",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    
                    if confirmacion == QMessageBox.Yes:
                        self._procesar_produccion_producto(
                            id_producto, product_name, cantidad_a_producir, 
                            costo_por_unidad, costo_total_produccion, precio_venta_nuevo, 
                            unidad_medida, ingredientes
                        )
                            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo procesar la producción: {e}")


    # CORRECCIÓN para ui_pos.py
# Reemplaza el método _procesar_produccion_producto con esta versión corregida:

    def _procesar_produccion_producto(self, id_producto, product_name, cantidad, costo_unitario, costo_total, precio_venta, unidad_medida, ingredientes):
        """
        Procesa la producción de un producto normal.
        CORREGIDO: No descuenta del fondo, solo consume materias primas
        """
        try:
            with self.engine.begin() as conn:
                # 1. ACTUALIZAR STOCK DEL PRODUCTO
                conn.execute(
                    text("UPDATE productos SET cantidad_producto = cantidad_producto + :cantidad, precio_venta = :precio WHERE id_producto = :id"),
                    {
                        "cantidad": cantidad,
                        "precio": precio_venta,
                        "id": id_producto
                    }
                )
                
                # 2. CONSUMIR MATERIAS PRIMAS SEGÚN FÓRMULA
                for nombre_mp, costo_mp, unidad_mp, porcentaje, stock_mp in ingredientes:
                    cantidad_necesaria = (float(porcentaje) / 100.0) * cantidad
                    
                    conn.execute(
                        text("UPDATE materiasprimas SET cantidad_comprada_mp = cantidad_comprada_mp - :cantidad WHERE nombre_mp = :nombre"),
                        {
                            "cantidad": cantidad_necesaria,
                            "nombre": nombre_mp
                        }
                    )
                
                # 3. REGISTRAR EN PRODUCCIÓN - CORRECCIÓN PARA MANEJAR RESTRICCIÓN UNIQUE
                # Primero verificar si ya existe un registro para hoy
                query_existe = text("""
                    SELECT COUNT(*) FROM produccion 
                    WHERE fecha = DATE('now') AND producto_id = :producto_id
                """)
                existe = conn.execute(query_existe, {"producto_id": id_producto}).scalar()
                
                if existe:
                    # Actualizar registro existente
                    conn.execute(
                        text("""
                            UPDATE produccion 
                            SET cantidad = cantidad + :cantidad, 
                                costo = costo + :costo,
                                dia = DATE('now')
                            WHERE fecha = DATE('now') AND producto_id = :producto_id
                        """),
                        {
                            "producto_id": id_producto,
                            "cantidad": cantidad,
                            "costo": costo_total
                        }
                    )
                else:
                    # Insertar nuevo registro
                    conn.execute(
                        text("""
                            INSERT INTO produccion (fecha, producto_id, cantidad, costo, area, dia)
                            VALUES (DATE('now'), :producto_id, :cantidad, :costo, :area, DATE('now'))
                        """),
                        {
                            "producto_id": id_producto,
                            "cantidad": cantidad,
                            "costo": costo_total,
                            "area": "Producción"
                        }
                    )
                
            # 4. ACTUALIZAR INTERFAZ
            QMessageBox.information(
                self, 
                "Producción Exitosa", 
                f"Producción realizada con éxito:\n\n"
                f"Producto: {product_name}\n"
                f"Cantidad producida: +{cantidad} {unidad_medida}\n"
                f"Costo unitario: ${costo_unitario:.2f}\n"
                f"Costo total: ${costo_total:,.2f}\n"
                f"Precio venta: ${precio_venta:.2f} c/u\n\n"
                f"✅ Se consumieron las materias primas necesarias del inventario."
            )
            
            # 5. REFRESCAR LA VISTA
            self._populate_grids()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"❌ No se pudo completar la producción: {e}")

    def _eliminar_materia_prima(self, product_name):
        """Elimina COMPLETAMENTE una materia prima de la BD"""
        confirm = QMessageBox.question(
            self, 
            "Eliminar Materia Prima", 
            f"¿Está seguro de eliminar COMPLETAMENTE la materia prima '{product_name}'?\n\n"
            f"ADVERTENCIA: Esta acción no se puede deshacer y borrará permanentemente el registro.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            try:
                with self.engine.connect() as conn:
                    # 1. Verificar si la materia prima está siendo usada en alguna fórmula
                    query_verificar_uso = text("""
                        SELECT COUNT(*) FROM formulas f
                        JOIN materiasprimas mp ON f.id_mp = mp.id_mp
                        WHERE mp.nombre_mp = :nombre
                    """)
                    uso_count = conn.execute(query_verificar_uso, {"nombre": product_name}).scalar()
                    
                    if uso_count > 0:
                        QMessageBox.warning(
                            self, 
                            "No se puede eliminar", 
                            f"No se puede eliminar '{product_name}' porque está siendo usada en {uso_count} fórmula(s).\n\n"
                            f"Primero debe removerla de todas las fórmulas antes de eliminarla."
                        )
                        return
                    
                    # 2. Obtener el ID de la materia prima para borrar referencias
                    query_id = text("SELECT id_mp FROM materiasprimas WHERE nombre_mp = :nombre")
                    id_mp = conn.execute(query_id, {"nombre": product_name}).scalar()
                    
                    if not id_mp:
                        QMessageBox.warning(self, "Error", f"No se encontró la materia prima '{product_name}'")
                        return
                    
                    # 3. ELIMINACIÓN FÍSICA - Borrar completamente el registro
                    conn.execute(
                        text("DELETE FROM materiasprimas WHERE nombre_mp = :nombre"),
                        {"nombre": product_name}
                    )
                    
                    # 4. También eliminar cualquier referencia en fórmulas (por si acaso)
                    conn.execute(
                        text("DELETE FROM formulas WHERE id_mp = :id_mp"),
                        {"id_mp": id_mp}
                    )
                    
                    conn.commit()
                    
                QMessageBox.information(self, "Éxito", f"Materia prima '{product_name}' eliminada COMPLETAMENTE.")
                
                # 5. Refrescar la vista INMEDIATAMENTE
                self._create_buttons_for_category(
                    "materiasprimas", 
                    "nombre_mp", 
                    "estatus_mp", 
                    self.grid_layout_materias_primas
                )
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar la materia prima: {e}")

    def _eliminar_producto_reventa(self, product_name):
        """Elimina un producto de reventa de la BD (eliminación lógica)"""
        confirm = QMessageBox.question(
            self, 
            "Eliminar Producto Reventa", 
            f"¿Está seguro de eliminar el producto de reventa '{product_name}'?\n\n"
            f"Esta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            try:
                with self.engine.connect() as conn:
                    # Verificar si hay ventas registradas para este producto
                    query_verificar_ventas = text("""
                        SELECT COUNT(*) FROM venta_reventa 
                        WHERE nombre_producto = :nombre
                    """)
                    ventas_count = conn.execute(query_verificar_ventas, {"nombre": product_name}).scalar()
                    
                    if ventas_count > 0:
                        respuesta = QMessageBox.warning(
                            self, 
                            "Advertencia", 
                            f"El producto '{product_name}' tiene {ventas_count} venta(s) registrada(s).\n\n"
                            f"¿Está seguro de que desea eliminarlo? Las ventas permanecerán en el historial pero el producto ya no estará disponible.",
                            QMessageBox.Yes | QMessageBox.No
                        )
                        if respuesta == QMessageBox.No:
                            return
                    
                    # Eliminar (desactivar) el producto de reventa
                    conn.execute(
                        text("UPDATE productosreventa SET estatus_prev = 0 WHERE nombre_prev = :nombre"),
                        {"nombre": product_name}
                    )
                    conn.commit()
                    
                QMessageBox.information(self, "Éxito", f"Producto de reventa '{product_name}' eliminado correctamente.")
                self._populate_grids()  # Refrescar la vista
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar el producto de reventa: {e}")

    def verificar_precio_individual(self, product_name):
        """Verifica y corrige el precio de un producto individual"""
        try:
            with self.engine.connect() as conn:
                precio = self._recalcular_precio_producto(conn, product_name)
                if precio > 0:
                    QMessageBox.information(self, "Precio Corregido", 
                                        f"El precio de '{product_name}' ha sido calculado:\n\n${precio:.2f}")
                else:
                    QMessageBox.warning(self, "Problema con el Precio", 
                                    f"No se pudo calcular el precio para '{product_name}'. Verifique:\n\n"
                                    f"1. Que tenga fórmula definida\n"
                                    f"2. Que las materias primas tengan costos")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo verificar el precio: {e}")


    def _procesar_compra_reventa(self, id_prev, product_name, cantidad, precio_compra, precio_venta, total_compra, unidad_medida):
        """Procesa la compra de producto de reventa y actualiza fondos"""
        try:
            with self.engine.begin() as conn:
                # 1. Actualizar 
                # 
                # stock y precios del producto
                query_update = text("""
                    UPDATE productosreventa 
                    SET cantidad_prev = cantidad_prev + :cantidad,
                        precio_compra = :precio_compra,
                        precio_venta = :precio_venta
                    WHERE id_prev = :id_prev
                """)
                conn.execute(query_update, {
                    "cantidad": cantidad,
                    "precio_compra": precio_compra,
                    "precio_venta": precio_venta,
                    "id_prev": id_prev
                })
                
                # 2. Restar del fondo
                query_ultimo_saldo = text("SELECT saldo FROM fondo ORDER BY id_movimiento DESC LIMIT 1")
                ultimo_saldo_result = conn.execute(query_ultimo_saldo).fetchone()
                ultimo_saldo = ultimo_saldo_result[0] if ultimo_saldo_result else 0
                
                nuevo_saldo = ultimo_saldo - total_compra
                
                query_fondo = text("""
                    INSERT INTO fondo (fecha, tipo, concepto, monto, saldo)
                    VALUES (DATE('now'), 'EGRESO', :concepto, :monto, :saldo)
                """)
                conn.execute(query_fondo, {
                    "concepto": f"Compra {product_name}",
                    "monto": total_compra,
                    "saldo": nuevo_saldo
                })
            
            # 3. Actualizar interfaz
            QMessageBox.information(
                self, 
                "Compra Exitosa", 
                f"Compra realizada con éxito:\n\n"
                f"Producto: {product_name}\n"
                f"Cantidad: +{cantidad} {unidad_medida}\n"
                f"Precio compra: ${precio_compra:.2f} c/u\n"
                f"Precio venta: ${precio_venta:.2f} c/u\n"
                f"Total: ${total_compra:,.2f}\n\n"
                f"Fondo actualizado: -${total_compra:,.2f}"
            )
            
            # 4. Refrescar la vista
            self._populate_grids()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo completar la compra: {e}")


    def _agregar_materia_prima(self):
        """Permite agregar una o más materias primas desde un diálogo y resta del fondo"""
        dialog = AgregarMultiplesMPDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            materias_primas = dialog.get_materias_primas()
            if not materias_primas:
                QMessageBox.warning(self, "Error", "No se ingresaron materias primas válidas.")
                return

            # Obtener la tasa de cambio de la ventana principal
            ventana_principal = self.window()
            if hasattr(ventana_principal, 'tasa_cambio_actual'):
                tasa_cambio = ventana_principal.tasa_cambio_actual
            else:
                # Fallback si no se encuentra la tasa
                tasa_cambio = 20.0
                QMessageBox.warning(
                    self, 
                    "Tasa de Cambio No Encontrada",
                    "No se encontró la tasa de cambio actual. Se usará tasa por defecto: 1 USD = $20.00 MXN"
                )

            # Verificar si hay materias primas en USD
            tiene_usd = any(mp['moneda'] == 'USD' for mp in materias_primas)

            try:
                with self.engine.begin() as conn:
                    total_gasto = 0
                    
                    for mp in materias_primas:
                        # Convertir a MXN si es necesario
                        costo_mxn = mp["costo"]
                        if mp["moneda"] == "USD":
                            costo_mxn = mp["costo"] * tasa_cambio
                            print(f"💰 Conversión: ${mp['costo']:.2f} USD × {tasa_cambio} = ${costo_mxn:.2f} MXN")

                        # CORRECCIÓN: total_mp es la CANTIDAD de artículos en stock
                        # Para una nueva materia prima, el stock inicial es igual a la cantidad comprada
                        cantidad = mp["cantidad"]
                        
                        # Calcular el gasto para esta compra
                        gasto_mp = costo_mxn * cantidad

                        # CORRECCIÓN: Incluir todos los campos necesarios
                        conn.execute(
                            text("""
                                INSERT INTO materiasprimas (
                                    nombre_mp, costo_unitario_mp, proveedor, 
                                    unidad_medida_mp, cantidad_comprada_mp, tipo_moneda, total_mp,
                                    estatus_mp, fecha_mp
                                )
                                VALUES (:nombre, :costo, :proveedor, :unidad_medida, :cantidad, :moneda, :total_mp,
                                        1, DATE('now'))
                            """),
                            {
                                "nombre": mp["nombre"], 
                                "costo": costo_mxn,
                                "proveedor": mp["proveedor"],
                                "unidad_medida": mp["unidad"],
                                "cantidad": cantidad,  # cantidad_comprada_mp
                                "moneda": "MXN",
                                "total_mp": cantidad   # CORRECCIÓN: total_mp = cantidad_comprada_mp (mismo valor)
                            }
                        )
                        total_gasto += gasto_mp
                    
                    # RESTAR DEL FONDO (siempre en MXN)
                    if total_gasto > 0:
                        query_ultimo_saldo = text("SELECT saldo FROM fondo ORDER BY id_movimiento DESC LIMIT 1")
                        ultimo_saldo_result = conn.execute(query_ultimo_saldo).fetchone()
                        ultimo_saldo = ultimo_saldo_result[0] if ultimo_saldo_result else 0
                        
                        nuevo_saldo = ultimo_saldo - total_gasto
                        
                        query_fondo = text("""
                            INSERT INTO fondo (fecha, tipo, concepto, monto, saldo)
                            VALUES (DATE('now'), 'EGRESO', 'Compra Materia Prima', :monto, :saldo)
                        """)
                        conn.execute(query_fondo, {
                            "monto": total_gasto,
                            "saldo": nuevo_saldo
                        })
                    
                mensaje = f"Se agregaron {len(materias_primas)} materias primas.\nGasto del fondo: ${total_gasto:,.2f} MXN"
                if tiene_usd:
                    mensaje += f"\n(Tasa de cambio utilizada: 1 USD = {tasa_cambio:.2f} MXN)"
                    
                QMessageBox.information(self, "Éxito", mensaje)
                self._populate_grids()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo agregar las materias primas: {e}")


    def _modificar_costo(self, table_name, product_name):
        """Modifica el costo de una materia prima con selección de moneda"""
        try:
            with self.engine.connect() as conn:
                # Obtener el costo actual
                query = text("SELECT costo_unitario_mp, tipo_moneda FROM materiasprimas WHERE nombre_mp = :nombre")
                result = conn.execute(query, {"nombre": product_name}).fetchone()
                
                if not result:
                    QMessageBox.warning(self, "Error", f"No se encontró la materia prima '{product_name}'")
                    return
                    
                costo_actual = result[0] or 0.0
                moneda_actual = result[1] or "MXN"
                
                # Crear diálogo personalizado para costo y moneda
                dialog = QDialog(self)
                dialog.setWindowTitle(f"Modificar Costo - {product_name}")
                dialog.setMinimumWidth(300)
                
                layout = QVBoxLayout(dialog)
                
                # Información del producto
                info_label = QLabel(f"<b>Producto:</b> {product_name}")
                layout.addWidget(info_label)
                
                # Campo para el costo
                layout.addWidget(QLabel("Nuevo costo:"))
                spin_costo = QDoubleSpinBox()
                spin_costo.setMinimum(0.0)
                spin_costo.setMaximum(100000.0)
                spin_costo.setDecimals(2)
                spin_costo.setValue(costo_actual)
                spin_costo.setPrefix("$ ")
                layout.addWidget(spin_costo)
                
                # Selector de moneda
                layout.addWidget(QLabel("Moneda:"))
                combo_moneda = QComboBox()
                combo_moneda.addItems(["MXN", "USD"])
                combo_moneda.setCurrentText(moneda_actual)
                layout.addWidget(combo_moneda)
                
                # Etiqueta informativa
                info_label = QLabel("💡 El costo se almacenará en la moneda seleccionada.")
                info_label.setStyleSheet("color: #666; font-size: 10px;")
                layout.addWidget(info_label)
                
                # Botones
                btn_layout = QHBoxLayout()
                btn_aceptar = QPushButton("Aceptar")
                btn_cancelar = QPushButton("Cancelar")
                
                btn_aceptar.clicked.connect(dialog.accept)
                btn_cancelar.clicked.connect(dialog.reject)
                
                btn_layout.addWidget(btn_aceptar)
                btn_layout.addWidget(btn_cancelar)
                layout.addLayout(btn_layout)
                
                if dialog.exec_() == QDialog.Accepted:
                    nuevo_costo = spin_costo.value()
                    moneda_seleccionada = combo_moneda.currentText()
                    
                    # Si la moneda es USD, preguntar tasa de cambio
                    if moneda_seleccionada == "USD":
                        # Obtener tasa de cambio de la ventana principal
                        ventana_principal = self.window()
                        if hasattr(ventana_principal, 'tasa_cambio_actual'):
                            tasa_cambio = ventana_principal.tasa_cambio_actual
                        else:
                            # Fallback si no se encuentra la tasa
                            tasa_cambio = 20.0
                        
                        # Preguntar si quiere usar la tasa actual o una diferente
                        usar_tasa_actual = QMessageBox.question(
                            self,
                            "Tasa de Cambio",
                            f"¿Usar la tasa de cambio actual?\n1 USD = ${tasa_cambio:.2f} MXN\n\n"
                            f"Si selecciona 'No', puede ingresar una tasa diferente.",
                            QMessageBox.Yes | QMessageBox.No
                        )
                        
                        if usar_tasa_actual == QMessageBox.No:
                            # Pedir tasa personalizada
                            tasa_personalizada, ok = QInputDialog.getDouble(
                                self,
                                "Tasa de Cambio Personalizada",
                                "Ingrese la tasa de cambio (USD a MXN):",
                                value=tasa_cambio,
                                min=1.0,
                                max=100.0,
                                decimals=2
                            )
                            if ok:
                                tasa_cambio = tasa_personalizada
                            else:
                                return  # Usuario canceló
                    
                    # Actualizar en la base de datos
                    query_update = text("""
                        UPDATE materiasprimas 
                        SET costo_unitario_mp = :costo, tipo_moneda = :moneda 
                        WHERE nombre_mp = :nombre
                    """)
                    conn.execute(query_update, {
                        "costo": nuevo_costo, 
                        "moneda": moneda_seleccionada, 
                        "nombre": product_name
                    })
                    conn.commit()
                    
                    mensaje = f"Costo de '{product_name}' actualizado:\n${nuevo_costo:.2f} {moneda_seleccionada}"
                    if moneda_seleccionada == "USD":
                        costo_mxn = nuevo_costo * tasa_cambio
                        mensaje += f"\n(Equivale a ${costo_mxn:.2f} MXN al cambio de {tasa_cambio:.2f})"
                    
                    QMessageBox.information(self, "Éxito", mensaje)
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo modificar el costo: {str(e)}")

    def _modificar_precio(self, table_name, product_name):
        """Modifica el precio de un producto de reventa o producto normal"""
        try:
            with self.engine.connect() as conn:
                # Determinar la tabla y columna correctas
                if table_name == "productosreventa":
                    # Para productos de reventa, necesitamos agregar la columna precio_venta si no existe
                    # Primero verificamos si existe la columna
                    try:
                        query_check = text("SELECT precio_venta FROM productosreventa WHERE nombre_prev = :nombre")
                        precio_actual = conn.execute(query_check, {"nombre": product_name}).scalar() or 0.0
                    except:
                        # Si la columna no existe, la creamos
                        query_alter = text("ALTER TABLE productosreventa ADD COLUMN precio_venta REAL DEFAULT 0")
                        conn.execute(query_alter)
                        precio_actual = 0.0
                        
                    columna = "precio_venta"
                    tabla = "productosreventa"
                    columna_nombre = "nombre_prev"
                    
                elif table_name == "productos":
                    query = text("SELECT precio_venta FROM productos WHERE nombre_producto = :nombre")
                    precio_actual = conn.execute(query, {"nombre": product_name}).scalar() or 0.0
                    columna = "precio_venta"
                    tabla = "productos"
                    columna_nombre = "nombre_producto"
                else:
                    return
                
                # Pedir nuevo precio
                nuevo_precio, ok = QInputDialog.getDouble(
                    self, 
                    "Modificar Precio", 
                    f"Nuevo precio para '{product_name}':", 
                    value=precio_actual,
                    min=0.0,
                    decimals=2
                )
                
                if ok:
                    # Actualizar en la base de datos
                    query_update = text(f"UPDATE {tabla} SET {columna} = :precio WHERE {columna_nombre} = :nombre")
                    conn.execute(query_update, {"precio": nuevo_precio, "nombre": product_name})
                    conn.commit()
                    
                    QMessageBox.information(self, "Éxito", f"Precio de '{product_name}' actualizado a ${nuevo_precio:.2f}")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo modificar el precio: {str(e)}")

    


    def _modificar_formula(self, product_name):
        """Abre el diálogo para modificar la fórmula de un producto"""
        try:
            with self.engine.connect() as conn:
                # 1. Obtener todas las materias primas disponibles
                query_mps = text("SELECT nombre_mp FROM materiasprimas ORDER BY nombre_mp")
                materias_primas_disponibles = [row[0] for row in conn.execute(query_mps).fetchall()]

                # 2. Obtener el ID del producto actual
                query_id = text("SELECT id_producto FROM productos WHERE nombre_producto = :nombre")
                producto_id = conn.execute(query_id, {"nombre": product_name}).scalar()
                if not producto_id:
                    QMessageBox.warning(self, "Error", "No se encontró el producto.")
                    return

                # 3. Obtener la fórmula actual de ese producto
                query_formula_actual = text("""
                    SELECT mp.nombre_mp, f.porcentaje
                    FROM formulas f
                    JOIN materiasprimas mp ON f.id_mp = mp.id_mp
                    WHERE f.id_producto = :id_p
                """)
                formula_actual_raw = conn.execute(query_formula_actual, {"id_p": producto_id}).fetchall()
                formula_actual = [{"nombre_mp": nombre, "porcentaje": porc} for nombre, porc in formula_actual_raw]
                
                # 4. Crear y mostrar el diálogo
                dialogo = FormulaDialog(product_name, materias_primas_disponibles, formula_actual, self)
                
                if dialogo.exec_() == QDialog.Accepted:
                    nueva_formula = dialogo.get_formula()
                    
                    if nueva_formula is None: # Ocurrió un error de validación (ej: >100%)
                        return

                    # 5. Guardar la nueva fórmula en la base de datos
                    with conn.begin() as trans:
                        # Borrar la fórmula anterior
                        conn.execute(text("DELETE FROM formulas WHERE id_producto = :id_p"), {"id_p": producto_id})

                        # Insertar los nuevos ingredientes
                        for ingrediente in nueva_formula:
                            # Obtener el ID de la materia prima por su nombre
                            query_id_mp = text("SELECT id_mp FROM materiasprimas WHERE nombre_mp = :nombre")
                            id_mp = conn.execute(query_id_mp, {"nombre": ingrediente["nombre_mp"]}).scalar()
                            
                            if id_mp:
                                query_insert = text("""
                                    INSERT INTO formulas (id_producto, id_mp, porcentaje)
                                    VALUES (:id_p, :id_m, :porc)
                                """)
                                conn.execute(query_insert, {
                                    "id_p": producto_id,
                                    "id_m": id_mp,
                                    "porc": ingrediente["porcentaje"]
                                })
                    
                    QMessageBox.information(self, "Éxito", "Fórmula actualizada correctamente.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cambiar la fórmula: {e}")

    

    def _recalcular_precio_producto(self, conn, product_name):
        """Recalcula el precio de un producto basado en su fórmula y costos de materias primas."""
        try:
            print(f"Iniciando cálculo de precio para: {product_name}")
            
            # 1. Obtener el ID del producto - CORRECCIÓN: Acceder por índice
            query_id = text("SELECT id_producto FROM productos WHERE nombre_producto = :nombre")
            result = conn.execute(query_id, {"nombre": product_name})
            row = result.fetchone()
            if not row:
                print(f"Producto '{product_name}' no encontrado")
                return 0.0
            producto_id = row[0]  # Acceder por índice


            # 2. Verificar si el producto tiene fórmula
            query_verificar_formula = text("SELECT COUNT(*) FROM formulas WHERE id_producto = :id_p")
            count_formula = conn.execute(query_verificar_formula, {"id_p": producto_id}).scalar()
            
            if count_formula == 0:
                print(f"Producto '{product_name}' no tiene fórmula definida")
                # Si no tiene fórmula, usar precio_venta actual o 0
                query_precio_actual = text("SELECT precio_venta FROM productos WHERE id_producto = :id_p")
                precio_actual = conn.execute(query_precio_actual, {"id_p": producto_id}).scalar()
                return precio_actual or 0.0

            # 3. Obtener la fórmula y costos de las materias primas
            query_formula = text("""
                SELECT m.nombre_mp, m.costo_unitario_mp, f.porcentaje
                FROM formulas f
                JOIN materiasprimas m ON f.id_mp = m.id_mp
                WHERE f.id_producto = :id_p
            """)
            ingredientes = conn.execute(query_formula, {"id_p": producto_id}).fetchall()

            if not ingredientes:
                print(f"Producto '{product_name}' no tiene ingredientes en la fórmula")
                return 0.0

            # 4. Calcular el costo base por unidad de producto
            costo_base = 0.0
            print(f"Calculando precio para '{product_name}':")
            
            ingredientes_con_costo = 0
            for nombre_mp, costo_mp, porcentaje in ingredientes:
                if costo_mp is None:
                    print(f" Materia prima '{nombre_mp}' no tiene costo")
                    continue
                if porcentaje is None:
                    print(f" Materia prima '{nombre_mp}' no tiene porcentaje")
                    continue
                    
                costo_contribucion = float(costo_mp) * (float(porcentaje) / 100.0)
                costo_base += costo_contribucion
                ingredientes_con_costo += 1
                print(f"   - {nombre_mp}: ${costo_mp:.2f} × {porcentaje}% = ${costo_contribucion:.2f}")

            if ingredientes_con_costo == 0:
                print(f" Ninguna materia prima tiene costo asignado para '{product_name}'")
                return 0.0

            print(f"Costo base total: ${costo_base:.2f}")

            # 5. Calcular el precio final (costo + 30% margen)
            precio_final = costo_base * 1.30
            print(f"Precio final (costo + 30%): ${precio_final:.2f}")

            # 6. Actualizar el precio en la base de datos
            query_update = text("UPDATE productos SET precio_venta = :precio WHERE id_producto = :id_p")
            result = conn.execute(query_update, {"precio": precio_final, "id_p": producto_id})
            conn.commit()
            
            print(f"Precio actualizado en BD para '{product_name}': ${precio_final:.2f}")
            return precio_final

        except Exception as e:
            print(f"Error al recalcular precio para '{product_name}': {e}")
            import traceback
            traceback.print_exc()
            return 0.0
        
    
    def actualizar_area_producto(self, producto_nombre, tipo_tabla):
        with self.engine.connect() as conn:
            if tipo_tabla == "productos":
                query = text("SELECT area_producto FROM productos WHERE nombre_producto = :nombre")
            elif tipo_tabla == "productosreventa":
                query = text("SELECT area_prev FROM productosreventa WHERE nombre_prev = :nombre")
            elif tipo_tabla == "materiasprimas":
                query = text("SELECT 'Almacén' as area")  # Las materias primas normalmente están en almacén
            else:
                self.area_combobox.clear()
                self.area_combobox.addItem("Almacén")
                return

            result = conn.execute(query, {"nombre": producto_nombre}).fetchall()
            self.area_combobox.clear()
            if result:
                # Si hay varias áreas (aunque normalmente habrá 1)
                for r in result:
                    self.area_combobox.addItem(r[0])
            else:
                self.area_combobox.addItem("Desconocido")

    def _remove_ticket_product(self, product_name, widget):
        """Elimina un producto del ticket y actualiza total."""
        if product_name in self.current_ticket:
            qty = self.current_ticket[product_name]['qty']
            price = self.current_ticket[product_name]['price']
            self.current_total -= price * qty

            # Eliminar widget de la UI
            self.ticket_items_area.removeWidget(widget)
            widget.deleteLater()

            # Quitar del diccionario
            del self.current_ticket[product_name]

            self._update_ticket_display()

    def _cambiar_area_producto(self, table_name, product_name):
        """Permite seleccionar una nueva área para el producto."""
        areas = ["Quimo", "Quimo Clean"]  # puedes traer de BD si las tienes
        area, ok = QInputDialog.getItem(self, "Cambiar Área", f"Selecciona el área para '{product_name}':", areas, 0, False)
        if ok and area:
            try:
                with self.engine.connect() as conn:
                    if table_name == "productos":
                        conn.execute(text("UPDATE productos SET area_producto = :area WHERE nombre_producto = :nombre"),
                                    {"area": area, "nombre": product_name})
                        conn.commit()
                    elif table_name == "productosreventa":
                        conn.execute(text("UPDATE productosreventa SET area_prev = :area WHERE nombre_prev = :nombre"),
                                    {"area": area, "nombre": product_name})
                        conn.commit()
                QMessageBox.information(self, "Éxito", f"Área de '{product_name}' actualizada a '{area}'")
                self.actualizar_area_producto(product_name, table_name)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo actualizar el área: {e}")

    def _eliminar_producto(self, table_name, product_name):
        """Elimina COMPLETAMENTE un producto de la BD"""
        confirm = QMessageBox.question(
            self, 
            "Eliminar Producto", 
            f"¿Está seguro de eliminar COMPLETAMENTE el producto '{product_name}'?\n\n"
            f"⚠️ ADVERTENCIA: Esta acción no se puede deshacer y borrará permanentemente el registro.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            try:
                with self.engine.connect() as conn:
                    # 1. Verificar si hay ventas registradas para este producto
                    query_verificar_ventas = text("""
                        SELECT COUNT(*) FROM ventas 
                        WHERE nombre_producto = :nombre
                    """)
                    ventas_count = conn.execute(query_verificar_ventas, {"nombre": product_name}).scalar()
                    
                    if ventas_count > 0:
                        respuesta = QMessageBox.warning(
                            self, 
                            "Advertencia", 
                            f"El producto '{product_name}' tiene {ventas_count} venta(s) registrada(s).\n\n"
                            f"¿Está seguro de que desea eliminarlo COMPLETAMENTE? Las ventas permanecerán en el historial pero el producto ya no estará disponible.",
                            QMessageBox.Yes | QMessageBox.No
                        )
                        if respuesta == QMessageBox.No:
                            return
                    
                    # 2. Obtener el ID del producto para borrar referencias
                    query_id = text("SELECT id_producto FROM productos WHERE nombre_producto = :nombre")
                    producto_id = conn.execute(query_id, {"nombre": product_name}).scalar()
                    
                    if not producto_id:
                        QMessageBox.warning(self, "Error", f"No se encontró el producto '{product_name}'")
                        return
                    
                    # 3. ELIMINACIÓN FÍSICA - Borrar completamente el registro y sus dependencias
                    
                    # Primero eliminar presentaciones
                    conn.execute(
                        text("DELETE FROM presentaciones WHERE id_producto = :id"),
                        {"id": producto_id}
                    )
                    
                    # Eliminar fórmulas
                    conn.execute(
                        text("DELETE FROM formulas WHERE id_producto = :id"),
                        {"id": producto_id}
                    )
                    
                    # Eliminar lotes
                    conn.execute(
                        text("DELETE FROM lotes WHERE id_producto = :id"),
                        {"id": producto_id}
                    )
                    
                    # Finalmente eliminar el producto
                    conn.execute(
                        text("DELETE FROM productos WHERE nombre_producto = :nombre"),
                        {"nombre": product_name}
                    )
                    
                    conn.commit()
                    
                QMessageBox.information(self, "Éxito", f"Producto '{product_name}' eliminado COMPLETAMENTE.")
                
                # 4. Refrescar la vista INMEDIATAMENTE
                self._create_buttons_for_category(
                    "productos", 
                    "nombre_producto", 
                    "estatus_producto", 
                    self.grid_layout_productos
                )
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar el producto: {e}")

    def _modificar_lote(self, product_name, es_admin=False):
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT codigo_lote 
                    FROM lotes 
                    WHERE id_producto = (
                        SELECT id_producto FROM productos WHERE nombre_producto = :nombre
                    )
                """),
                {"nombre": product_name}
            )
            lote_actual = result.scalar()

        # Si no hay lote, poner un mensaje y dejar campo vacío para crearlo
        if lote_actual is None:
            lote_actual = ""  # El diálogo empieza vacío
            QMessageBox.information(
                self, 
                "Nuevo Lote", 
                f"No se encontró lote actual para {product_name}.\n\n"
                "Ingrese un nuevo lote para este producto."
            )

        dialog = ModificarLoteDialog(product_name, lote_actual, self.engine, self, es_admin)
        dialog.exec_()

    #No pierdas esto 
    #ESto es muy importante para el programa 
    def mostrar_presentaciones(self, nombre, table_name):
        """Muestra las presentaciones disponibles para un producto o materia prima."""
        try:
            with self.engine.connect() as conn:
                # Determinar columnas por tabla
                id_col_map = {
                    "productos": ("id_producto", "nombre_producto"),
                    "productosreventa": ("id_prev", "nombre_prev"),
                    "materiasprimas": ("id_mp", "nombre_mp")
                }
                id_col, name_col = id_col_map.get(table_name, (None, None))
                if not id_col or not name_col:
                    QMessageBox.warning(self, "Error", f"No se encontró mapeo para {table_name}.")
                    return

                # Buscar el ID del producto según el nombre
                result = conn.execute(
                    text(f"SELECT {id_col} FROM {table_name} WHERE {name_col} = :nombre"),
                    {"nombre": nombre}
                ).fetchone()

                if not result:
                    QMessageBox.warning(self, "Error", f"No se encontró el registro '{nombre}'.")
                    return

                producto_id = result[0]

                # Buscar presentaciones asociadas
                pres = conn.execute(text("""
                    SELECT nombre_presentacion, factor, precio_venta
                    FROM presentaciones
                    WHERE id_producto = :pid
                    ORDER BY nombre_presentacion
                """), {"pid": producto_id}).fetchall()

            if not pres:
                QMessageBox.information(self, "Sin presentaciones", f"El producto '{nombre}' no tiene presentaciones registradas.")
                return

            # Crear un diálogo emergente
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Presentaciones de {nombre}")
            layout = QVBoxLayout(dialog)

            for p_nombre, p_factor, p_precio in pres:
                btn = QPushButton(f"{p_nombre} — {p_factor}x  |  ${p_precio}")
                btn.clicked.connect(lambda _, n=p_nombre, f=p_factor, pr=p_precio: self._seleccionar_presentacion(nombre, n, f, pr))
                layout.addWidget(btn)

            dialog.setLayout(layout)
            dialog.exec_()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar las presentaciones: {e}")


    def _agregar_producto_con_cantidad(self, table_name, product_name):
        """Abre un diálogo para especificar la cantidad a agregar"""
        # Obtener stock disponible
        stock_disponible = 0
        try:
            with self.engine.connect() as conn:
                if table_name == "productos":
                    query = text("SELECT cantidad_producto FROM productos WHERE nombre_producto = :nombre")
                    resultado = conn.execute(query, {"nombre": product_name}).scalar()
                    stock_disponible = resultado or 0
                elif table_name == "productosreventa":
                    query = text("SELECT cantidad_prev FROM productosreventa WHERE nombre_prev = :nombre")
                    resultado = conn.execute(query, {"nombre": product_name}).scalar()
                    stock_disponible = resultado or 0
                elif table_name == "materiasprimas":
                    query = text("SELECT cantidad_comprada_mp FROM materiasprimas WHERE nombre_mp = :nombre")
                    resultado = conn.execute(query, {"nombre": product_name}).scalar()
                    stock_disponible = resultado or 0
        except Exception as e:
            print(f"Error al obtener stock: {e}")

        # Diálogo para cantidad
        cantidad, ok = QInputDialog.getDouble(
            self, 
            f"Agregar {product_name}",
            f"Ingrese la cantidad a agregar:\n(Stock disponible: {stock_disponible})",
            min=0.1,
            max=stock_disponible if stock_disponible > 0 else 10000,
            value=1.0,
            decimals=2
        )
        
        if ok and cantidad > 0:
            # Agregar múltiples unidades
            self._agregar_multiples_unidades(table_name, product_name, cantidad)

    def _agregar_multiples_unidades(self, table_name, product_name, cantidad):
        """Agrega múltiples unidades de un producto al ticket"""
        self.actualizar_area_producto(product_name, table_name)

        # Obtener precio unitario
        precio_unitario = 0.0
        try:
            with self.engine.connect() as conn:
                if table_name == "productos":
                    query = text("SELECT precio_venta FROM productos WHERE nombre_producto = :nombre")
                    resultado = conn.execute(query, {"nombre": product_name}).scalar()
                    if resultado is not None:
                        precio_unitario = float(resultado)
                        
                    if precio_unitario == 0.0:
                        respuesta = QMessageBox.question(self, "Precio Cero", 
                                                    f"El precio de '{product_name}' es $0.00. ¿Desea continuar?",
                                                    QMessageBox.Yes | QMessageBox.No)
                        if respuesta == QMessageBox.No:
                            return
                        
                elif table_name == "materiasprimas":
                    query_id = text("SELECT id_mp FROM materiasprimas WHERE nombre_mp = :nombre")
                    product_id = conn.execute(query_id, {"nombre": product_name}).scalar()
                    if product_id:
                        query = text("SELECT costo_unitario_mp FROM materiasprimas WHERE id_mp = :id")
                        resultado = conn.execute(query, {"id": product_id}).scalar()
                        if resultado:
                            precio_unitario = float(resultado)
                elif table_name == "productosreventa":
                    query = text("SELECT precio_venta FROM productosreventa WHERE nombre_prev = :nombre")
                    resultado = conn.execute(query, {"nombre": product_name}).scalar()
                    if resultado:
                        precio_unitario = float(resultado)
                            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo obtener el precio: {e}")
            return

        # Calcular total
        total_linea = precio_unitario * cantidad
        nombre_display = product_name

        # Verificar si ya existe en el ticket
        if nombre_display in self.current_ticket:
            # Actualizar cantidad existente
            self.current_ticket[nombre_display]['qty'] += cantidad
            qty = self.current_ticket[nombre_display]['qty']
            price = self.current_ticket[nombre_display]['price']
            self.current_ticket[nombre_display]['label'].setText(f"{nombre_display} x{qty:.2f}  ${price*qty:.2f}")
        else:
            # Crear nueva entrada
            item_widget = QWidget()
            layout = QHBoxLayout(item_widget)
            layout.setContentsMargins(5, 2, 5, 2)

            label = QLabel(f"{nombre_display} x{cantidad:.2f}  ${total_linea:.2f}")
            layout.addWidget(label)

            delete_btn = QPushButton("–")
            delete_btn.setFixedSize(24, 24)
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff4d4d;
                    color: white;
                    border-radius: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #e60000;
                }
            """)
            delete_btn.hide()
            layout.addWidget(delete_btn)

            item_widget.enterEvent = lambda e: delete_btn.show()
            item_widget.leaveEvent = lambda e: delete_btn.hide()

            delete_btn.clicked.connect(lambda _, name=nombre_display: self._decrement_ticket_product(name))

            self.ticket_items_area.addWidget(item_widget)

            self.current_ticket[nombre_display] = {
                'qty': cantidad,
                'price': precio_unitario,
                'widget': item_widget,
                'label': label,
                'product_name_base': product_name,
                'table_name': table_name
            }

        # Actualizar total
        self.current_total += total_linea
        self._update_ticket_display()

    def _mostrar_presentaciones_con_cantidad(self, table_name, product_name, cantidad):
        """Muestra presentaciones con una cantidad específica ya definida"""
        # Para productos normales, mostrar presentaciones
        if table_name == "productos":
            self._cantidad_pendiente = cantidad  # Guardar la cantidad temporalmente
            self._mostrar_presentaciones(table_name, product_name)
        else:
            # Para otros productos, agregar directamente
            self._agregar_multiples_unidades(table_name, product_name, cantidad)

    def _pedir_cantidad_y_mostrar_presentaciones(self, table_name, product_name):
        """Pide cantidad y luego muestra presentaciones para productos normales"""
        if table_name == "productos":
            # Pedir cantidad primero
            cantidad, ok = QInputDialog.getDouble(
                self, 
                f"Agregar {product_name}",
                "Ingrese la cantidad:",
                min=0.1,
                value=1.0,
                decimals=2
            )
            
            if ok and cantidad > 0:
                self._cantidad_pendiente = cantidad
                self._mostrar_presentaciones(table_name, product_name)
        else:
            # Para otros productos, usar el método normal
            self._agregar_producto_con_cantidad(table_name, product_name)





class ModificarLoteDialog(QDialog):
    def __init__(self, product_name, lote_actual, engine, parent=None, es_admin=False):
        super().__init__(parent)
        self.product_name = product_name
        self.lote_actual = lote_actual
        self.engine = engine
        self.es_admin = es_admin   

        self.setWindowTitle(f"Modificar Lote - {product_name}")

        self.layout = QVBoxLayout()

        self.label_actual = QLabel(f"Lote actual de {product_name}: {lote_actual}")
        self.layout.addWidget(self.label_actual)

        self.input_numero = QLineEdit()
        self.input_numero.setPlaceholderText("Ingrese nuevo número de lote")
        self.layout.addWidget(self.input_numero)

        self.btn_modificar = QPushButton("Modificar lote")
        self.btn_modificar.clicked.connect(self.modificar_numero)
        self.layout.addWidget(self.btn_modificar)

        self.btn_admin = QPushButton("Administrador")
        self.btn_admin.clicked.connect(self.admin_modificar)
        self.layout.addWidget(self.btn_admin)

        self.setLayout(self.layout)

    def modificar_numero(self):
        nuevo_numero = self.input_numero.text().strip()
        if not nuevo_numero:
            QMessageBox.warning(self, "Error", "Debes ingresar un número")
            return

        partes = self.lote_actual.split("-")
        if len(partes) >= 2:
            partes[-1] = nuevo_numero
            nuevo_lote = "-".join(partes)
        else:
            nuevo_lote = self.lote_actual + "-" + nuevo_numero

        self.guardar_lote(nuevo_lote)

    def admin_modificar(self):
        from PyQt5.QtWidgets import QInputDialog
        password, ok = QInputDialog.getText(self, "Contraseña Administrador",
                                            "Ingrese contraseña:",
                                            QLineEdit.Password)
        if not ok or password != "1234":  # Aquí tu contraseña
            QMessageBox.warning(self, "Error", "Contraseña incorrecta")
            return

        nuevo_lote, ok = QInputDialog.getText(self, "Modificar Lote Completo",
                                               f"Lote actual de {self.product_name}: {self.lote_actual}\nIngrese nuevo lote completo:")
        if ok and nuevo_lote.strip():
            self.guardar_lote(nuevo_lote.strip())

    def guardar_lote(self, nuevo_lote):
        with self.engine.begin() as conn:
            result = conn.execute(
                text("""
                    SELECT id_lote FROM lotes 
                    WHERE id_producto = (
                        SELECT id_producto FROM productos WHERE nombre_producto = :nombre
                    )
                """),
                {"nombre": self.product_name}
            ).fetchone()

            if result:
                conn.execute(
                    text("""
                        UPDATE lotes SET codigo_lote = :nuevo 
                        WHERE id_producto = (
                            SELECT id_producto FROM productos WHERE nombre_producto = :nombre
                        )
                    """),
                    {"nuevo": nuevo_lote, "nombre": self.product_name}
                )
            else:
                conn.execute(
                    text("""
                        INSERT INTO lotes (id_producto, codigo_lote, cantidad) 
                        VALUES (
                            (SELECT id_producto FROM productos WHERE nombre_producto = :nombre), 
                            :nuevo, 0
                        )
                    """),
                    {"nuevo": nuevo_lote, "nombre": self.product_name}
                )

        QMessageBox.information(self, "Éxito", f"Lote actualizado a:\n{nuevo_lote}")
        self.accept()


    def diagnosticar_carga_productos(self):
        """Función temporal para diagnosticar problemas de carga"""
        try:
            with self.engine.connect() as conn:
                # Probar cada tabla por separado
                tablas = ["productos", "productosreventa", "materiasprimas"]
                
                for tabla in tablas:
                    print(f"\n=== DIAGNÓSTICO TABLA: {tabla} ===")
                    
                    if tabla == "productos":
                        query = text("SELECT nombre_producto, cantidad_producto FROM productos WHERE estatus_producto = 1 LIMIT 3")
                    elif tabla == "productosreventa":
                        query = text("SELECT nombre_prev, cantidad_prev FROM productosreventa WHERE estatus_prev = 1 LIMIT 3")
                    else:  # materiasprimas
                        query = text("SELECT nombre_mp, cantidad_comprada_mp FROM materiasprimas WHERE estatus_mp = 1 LIMIT 3")
                    
                    result = conn.execute(query)
                    rows = result.fetchall()
                    
                    print(f"Encontrados {len(rows)} registros")
                    for i, row in enumerate(rows):
                        print(f"Fila {i}: {row} - Tipo: {type(row)}")
                        if hasattr(row, '_asdict'):
                            print(f"  Como diccionario: {row._asdict()}")
                        print(f"  Como tupla: {tuple(row)}")
                        
        except Exception as e:
            print(f"Error en diagnóstico: {e}")



class AgregarMultiplesMPDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Agregar Materias Primas")
        self.resize(900, 400)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Añadir información sobre moneda
        info_label = QLabel(
            "💡 <b>Nota:</b> Todos los costos se convertirán automáticamente a Pesos Mexicanos (MXN).<br>"
            "Si selecciona USD, se le pedirá la tasa de cambio al guardar."
        )
        info_label.setStyleSheet("background-color: #e3f2fd; padding: 8px; border-radius: 4px;")
        info_label.setWordWrap(True)
        self.layout.addWidget(info_label)

        self.tabla = QTableWidget(0, 6)
        self.tabla.setHorizontalHeaderLabels(["Materia Prima", "Costo Unitario", "Moneda", "Unidad Medida", "Proveedor", "Cantidad"])
        
        # Configurar el resize mode para mejor visualización
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)  # Materia Prima se expande
        for i in range(1, 6):
            self.tabla.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        self.layout.addWidget(self.tabla)

        btn_agregar_fila = QPushButton("Agregar Fila")
        btn_agregar_fila.clicked.connect(self.agregar_fila)
        self.layout.addWidget(btn_agregar_fila)

        btn_guardar = QPushButton("Guardar")
        btn_guardar.clicked.connect(self.accept)
        self.layout.addWidget(btn_guardar)

        self.proveedores = self.obtener_proveedores()
        self.unidades_comunes = ["KG", "L", "ML", "G", "PIEZA", "BOLSA", "LITRO", "GALON", "BARRIL", "COSTAL"]
        self.monedas = ["MXN", "USD"]

        # Agregar una fila inicial
        self.agregar_fila()

    def obtener_proveedores(self):
        try:
            with self.parent.engine.connect() as conn:
                query = text("SELECT nombre_proveedor FROM proveedor ORDER BY nombre_proveedor")
                return [row[0] for row in conn.execute(query).fetchall()]
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudieron cargar proveedores: {e}")
            return []

    def agregar_fila(self):
        """CORREGIDO: Agrega una fila con los ComboBox en las columnas correctas"""
        fila = self.tabla.rowCount()
        self.tabla.insertRow(fila)

        # DEBUG: Mostrar información de columnas
        print(f"DEBUG: Agregando fila {fila} con {self.tabla.columnCount()} columnas")

        # Columna 0: Materia Prima (Text)
        self.tabla.setItem(fila, 0, QTableWidgetItem(""))
        print(f"DEBUG: Columna 0 - Materia Prima (texto)")
        
        # Columna 1: Costo Unitario (Text)
        item_costo = QTableWidgetItem("0.0")
        item_costo.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.tabla.setItem(fila, 1, item_costo)
        print(f"DEBUG: Columna 1 - Costo Unitario (texto)")
        
        # Columna 2: Moneda (ComboBox)
        combo_moneda = QComboBox()
        combo_moneda.addItems(self.monedas)
        combo_moneda.setCurrentText("MXN")
        self.tabla.setCellWidget(fila, 2, combo_moneda)
        print(f"DEBUG: Columna 2 - Moneda (ComboBox)")
        
        # Columna 3: Unidad de Medida (ComboBox)
        combo_unidad = QComboBox()
        combo_unidad.setEditable(True)
        combo_unidad.addItems(self.unidades_comunes)
        combo_unidad.setCurrentText("KG")
        self.tabla.setCellWidget(fila, 3, combo_unidad)
        print(f"DEBUG: Columna 3 - Unidad Medida (ComboBox)")
        
        # Columna 4: Proveedor (ComboBox)
        combo_proveedor = QComboBox()
        combo_proveedor.addItems(self.proveedores + ["Agregar proveedor..."])
        combo_proveedor.currentIndexChanged.connect(lambda index, f=fila: self.proveedor_seleccionado(index, f))
        self.tabla.setCellWidget(fila, 4, combo_proveedor)
        print(f"DEBUG: Columna 4 - Proveedor (ComboBox)")
        
        # Columna 5: Cantidad (Text)
        item_cantidad = QTableWidgetItem("1.0")
        item_cantidad.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.tabla.setItem(fila, 5, item_cantidad)
        print(f"DEBUG: Columna 5 - Cantidad (texto)")

    def proveedor_seleccionado(self, index, fila):
        combo = self.tabla.cellWidget(fila, 4)  # Columna 4 es Proveedor
        if combo.itemText(index) == "Agregar proveedor...":
            self.agregar_nuevo_proveedor(combo)

    def agregar_nuevo_proveedor(self, combo):
        nombre, ok = QInputDialog.getText(self, "Nuevo Proveedor", "Ingrese el nombre del proveedor:")
        if not ok or not nombre.strip():
            return

        telefono, _ = QInputDialog.getText(self, "Nuevo Proveedor", "Ingrese teléfono (opcional):")
        email, _ = QInputDialog.getText(self, "Nuevo Proveedor", "Ingrese email (opcional):")

        try:
            with self.parent.engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO proveedor (nombre_proveedor, telefono_proveedor, email_proveedor) VALUES (:nombre, :telefono, :email)"),
                    {"nombre": nombre.strip(), "telefono": telefono.strip(), "email": email.strip()}
                )
            self.proveedores.append(nombre.strip())
            combo.insertItem(combo.count() - 1, nombre.strip())
            combo.setCurrentText(nombre.strip())
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo agregar proveedor: {e}")

    def get_materias_primas(self):
        """Obtiene las materias primas ingresadas en la tabla"""
        materias_primas = []
        for fila in range(self.tabla.rowCount()):
            print(f"DEBUG: Procesando fila {fila}")
            
            # Columna 0: Materia Prima
            nombre_item = self.tabla.item(fila, 0)
            print(f"DEBUG: Columna 0 - nombre_item: {nombre_item.text() if nombre_item else 'None'}")
            
            # Columna 1: Costo Unitario
            costo_item = self.tabla.item(fila, 1)
            print(f"DEBUG: Columna 1 - costo_item: {costo_item.text() if costo_item else 'None'}")
            
            # Columna 2: Moneda (ComboBox)
            moneda_combo = self.tabla.cellWidget(fila, 2)
            print(f"DEBUG: Columna 2 - moneda_combo: {moneda_combo.currentText() if moneda_combo else 'None'}")
            
            # Columna 3: Unidad de Medida (ComboBox)
            unidad_combo = self.tabla.cellWidget(fila, 3)
            print(f"DEBUG: Columna 3 - unidad_combo: {unidad_combo.currentText() if unidad_combo else 'None'}")
            
            # Columna 4: Proveedor (ComboBox)
            proveedor_combo = self.tabla.cellWidget(fila, 4)
            print(f"DEBUG: Columna 4 - proveedor_combo: {proveedor_combo.currentText() if proveedor_combo else 'None'}")
            
            # Columna 5: Cantidad
            cantidad_item = self.tabla.item(fila, 5)
            print(f"DEBUG: Columna 5 - cantidad_item: {cantidad_item.text() if cantidad_item else 'None'}")
            
            if not nombre_item or not nombre_item.text().strip():
                continue  # Saltar filas vacías

            nombre = nombre_item.text().strip()
            
            try:
                costo = float(costo_item.text().strip()) if costo_item and costo_item.text().strip() else 0.0
            except ValueError:
                costo = 0.0
                
            try:
                cantidad = float(cantidad_item.text().strip()) if cantidad_item and cantidad_item.text().strip() else 1.0
            except ValueError:
                cantidad = 1.0
                
            moneda = moneda_combo.currentText() if moneda_combo else "MXN"
            unidad = unidad_combo.currentText() if unidad_combo else "KG"
            proveedor = proveedor_combo.currentText() if proveedor_combo else "Desconocido"

            print(f"DEBUG: Datos extraídos - nombre: {nombre}, costo: {costo}, moneda: {moneda}, unidad: {unidad}, proveedor: {proveedor}, cantidad: {cantidad}")

            materias_primas.append({
                "nombre": nombre,
                "costo": costo,
                "moneda": moneda,
                "unidad": unidad,
                "proveedor": proveedor,
                "cantidad": cantidad
            })
        
        return materias_primas




class AumentarStockDialog(QDialog):
    def __init__(self, parent=None, engine=None):
        super().__init__(parent)
        self.engine = engine
        self.setWindowTitle("Aumentar stock existente")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Selecciona materia prima:"))
        self.combo_mp = QComboBox()
        layout.addWidget(self.combo_mp)

        layout.addWidget(QLabel("Cantidad a agregar:"))
        self.txt_cantidad = QLineEdit()
        layout.addWidget(self.txt_cantidad)

        btn_guardar = QPushButton("Actualizar stock")
        layout.addWidget(btn_guardar)
        btn_guardar.clicked.connect(self.actualizar_stock)

        # Cargar nombres de materias primas
        self.cargar_materias_primas()

    def cargar_materias_primas(self):
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT nombre_mp FROM materiasprimas ORDER BY nombre_mp"))
            for row in result:
                self.combo_mp.addItem(row[0])

    def actualizar_stock(self):
        nombre = self.combo_mp.currentText()
        try:
            cantidad = float(self.txt_cantidad.text())
        except ValueError:
            QMessageBox.warning(self, "Error", "La cantidad debe ser numérica.")
            return

        if cantidad <= 0:
            QMessageBox.warning(self, "Error", "La cantidad debe ser mayor a 0.")
            return

        with self.engine.connect() as conn:
            conn.execute(text("""
                UPDATE materias_primas
                SET stock = stock + :cantidad
                WHERE nombre_mp = :nombre
            """), {"cantidad": cantidad, "nombre": nombre})
            conn.commit()

        QMessageBox.information(self, "Éxito", f"Se agregaron {cantidad} unidades a '{nombre}'.")
        self.accept()

    def _aumentar_stock_existente(self):
        """Permite aumentar stock de una materia prima existente"""
        dialog = AumentarStockDialog(self, engine=self.engine)
        if dialog.exec_() == QDialog.Accepted:
            try:
                # Refrescar solo la sección de materias primas
                self._create_buttons_for_category(
                    "materiasprimas", 
                    "nombre_mp", 
                    "estatus_mp", 
                    self.grid_layout_materias_primas
                )
                QMessageBox.information(self, "Éxito", "Stock de materia prima actualizado correctamente.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo actualizar la vista: {e}")




class AgregarProductosReventaDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Agregar Productos de Reventa")
        self.resize(800, 400)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Tabla
        self.tabla = QTableWidget(0, 6)
        self.tabla.setHorizontalHeaderLabels([
            "Producto", "Unidad de Medida", "Proveedor", 
            "Precio Compra", "Precio Venta", "Cantidad"
        ])
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.tabla)

        # Botones
        btn_agregar_fila = QPushButton("Agregar Fila")
        btn_agregar_fila.clicked.connect(self.agregar_fila)
        self.layout.addWidget(btn_agregar_fila)

        btn_guardar = QPushButton("Guardar Productos")
        btn_guardar.clicked.connect(self.guardar)
        self.layout.addWidget(btn_guardar)

        # Cargar proveedores
        self.proveedores = self.obtener_proveedores()

    def obtener_proveedores(self):
        """Carga los nombres de proveedores disponibles."""
        try:
            with self.parent.engine.connect() as conn:
                query = text("SELECT nombre_proveedor FROM proveedor ORDER BY nombre_proveedor")
                return [row[0] for row in conn.execute(query).fetchall()]
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudieron cargar proveedores: {e}")
            return []

    def agregar_fila(self):
        """Agrega una nueva fila editable en la tabla."""
        fila = self.tabla.rowCount()
        self.tabla.insertRow(fila)

        # Producto y unidad de medida
        self.tabla.setItem(fila, 0, QTableWidgetItem(""))
        self.tabla.setItem(fila, 1, QTableWidgetItem("PIEZA"))

        # Combo de proveedor
        combo_proveedor = QComboBox()
        combo_proveedor.addItems(self.proveedores + ["Agregar proveedor..."])
        combo_proveedor.currentIndexChanged.connect(lambda index, f=fila: self.proveedor_seleccionado(index, f))
        self.tabla.setCellWidget(fila, 2, combo_proveedor)

        # Precios y cantidad
        self.tabla.setItem(fila, 3, QTableWidgetItem("0.0"))  # precio compra
        self.tabla.setItem(fila, 4, QTableWidgetItem("0.0"))  # precio venta
        self.tabla.setItem(fila, 5, QTableWidgetItem("0"))    # cantidad

    def proveedor_seleccionado(self, index, fila):
        combo = self.tabla.cellWidget(fila, 2)
        if combo.itemText(index) == "Agregar proveedor...":
            self.agregar_nuevo_proveedor(combo)

    def agregar_nuevo_proveedor(self, combo):
        """Permite agregar un nuevo proveedor directamente desde el diálogo."""
        nombre, ok = QInputDialog.getText(self, "Nuevo Proveedor", "Ingrese el nombre del proveedor:")
        if not ok or not nombre.strip():
            return

        telefono, _ = QInputDialog.getText(self, "Nuevo Proveedor", "Ingrese teléfono (opcional):")
        email, _ = QInputDialog.getText(self, "Nuevo Proveedor", "Ingrese email (opcional):")

        try:
            with self.parent.engine.begin() as conn:
                conn.execute(
                    text("""
                        INSERT INTO proveedor (nombre_proveedor, telefono_proveedor, email_proveedor)
                        VALUES (:nombre, :telefono, :email)
                    """),
                    {"nombre": nombre.strip(), "telefono": telefono.strip(), "email": email.strip()}
                )
            self.proveedores.append(nombre.strip())
            combo.insertItem(combo.count() - 1, nombre.strip())
            combo.setCurrentText(nombre.strip())
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo agregar proveedor: {e}")

    def guardar(self):
        """Guarda todos los productos ingresados en la tabla productosreventa."""
        try:
            with self.parent.engine.begin() as conn:
                for fila in range(self.tabla.rowCount()):
                    nombre = self.tabla.item(fila, 0).text().strip()
                    unidad = self.tabla.item(fila, 1).text().strip()
                    proveedor = self.tabla.cellWidget(fila, 2).currentText()
                    precio_compra = float(self.tabla.item(fila, 3).text().strip())
                    precio_venta = float(self.tabla.item(fila, 4).text().strip())
                    cantidad = float(self.tabla.item(fila, 5).text().strip())

                    if not nombre:
                        continue  # ignorar filas vacías

                    # Insertar el producto de reventa
                    conn.execute(
                        text("""
                            INSERT INTO productosreventa (
                                nombre_prev, unidad_medida_prev, proveedor, 
                                precio_compra, precio_venta, cantidad_prev, area_prev, estatus_prev
                            )
                            VALUES (:nombre, :unidad, :proveedor, :precio_compra, :precio_venta, :cantidad, 'QUIMO CLEAN', 1)
                        """),
                        {
                            "nombre": nombre,
                            "unidad": unidad,
                            "proveedor": proveedor,
                            "precio_compra": precio_compra,
                            "precio_venta": precio_venta,
                            "cantidad": cantidad
                        }
                    )
            QMessageBox.information(self, "Éxito", "Productos de reventa agregados correctamente.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron guardar los productos: {e}")



    

class DialogoComprarProductoReventa(QDialog):
    def __init__(self, product_name, stock_actual, precio_compra_actual, precio_venta_actual, unidad_medida, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Comprar Stock - {product_name}")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Información del producto
        info_group = QGroupBox("Información del Producto")
        info_layout = QVBoxLayout(info_group)
        
        info_layout.addWidget(QLabel(f"<b>Producto:</b> {product_name}"))
        info_layout.addWidget(QLabel(f"<b>Stock actual:</b> {stock_actual} {unidad_medida}"))
        info_layout.addWidget(QLabel(f"<b>Unidad:</b> {unidad_medida}"))
        
        layout.addWidget(info_group)
        
        # Datos de la compra
        compra_group = QGroupBox("Datos de la Compra")
        compra_layout = QVBoxLayout(compra_group)
        
        # Cantidad
        cantidad_layout = QHBoxLayout()
        cantidad_layout.addWidget(QLabel("Cantidad a comprar:"))
        self.spin_cantidad = QDoubleSpinBox()
        self.spin_cantidad.setMinimum(0.1)
        self.spin_cantidad.setMaximum(10000)
        self.spin_cantidad.setDecimals(2)
        self.spin_cantidad.setValue(1.0)
        cantidad_layout.addWidget(self.spin_cantidad)
        cantidad_layout.addWidget(QLabel(unidad_medida))
        compra_layout.addLayout(cantidad_layout)
        
        # Precio de compra
        precio_compra_layout = QHBoxLayout()
        precio_compra_layout.addWidget(QLabel("Precio de compra:"))
        self.spin_precio_compra = QDoubleSpinBox()
        self.spin_precio_compra.setMinimum(0.01)
        self.spin_precio_compra.setMaximum(100000)
        self.spin_precio_compra.setDecimals(2)
        self.spin_precio_compra.setValue(precio_compra_actual or 0.0)
        self.spin_precio_compra.setPrefix("$ ")
        precio_compra_layout.addWidget(self.spin_precio_compra)
        precio_compra_layout.addWidget(QLabel(f"c/u ({unidad_medida})"))
        compra_layout.addLayout(precio_compra_layout)
        
        # Precio de venta
        precio_venta_layout = QHBoxLayout()
        precio_venta_layout.addWidget(QLabel("Precio de venta:"))
        self.spin_precio_venta = QDoubleSpinBox()
        self.spin_precio_venta.setMinimum(0.01)
        self.spin_precio_venta.setMaximum(100000)
        self.spin_precio_venta.setDecimals(2)
        self.spin_precio_venta.setValue(precio_venta_actual or 0.0)
        self.spin_precio_venta.setPrefix("$ ")
        precio_venta_layout.addWidget(self.spin_precio_venta)
        precio_venta_layout.addWidget(QLabel(f"c/u ({unidad_medida})"))
        compra_layout.addLayout(precio_venta_layout)
        
        # Total calculado
        self.label_total = QLabel("Total: $0.00")
        self.label_total.setStyleSheet("font-weight: bold; color: #e74c3c;")
        compra_layout.addWidget(self.label_total)
        
        layout.addWidget(compra_group)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_comprar = QPushButton("Comprar")
        btn_comprar.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        
        btn_cancelar.clicked.connect(self.reject)
        btn_comprar.clicked.connect(self.accept)
        
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_comprar)
        layout.addLayout(btn_layout)
        
        # Conectar señales para calcular total en tiempo real
        self.spin_cantidad.valueChanged.connect(self._calcular_total)
        self.spin_precio_compra.valueChanged.connect(self._calcular_total)
        
        # Calcular total inicial
        self._calcular_total()
    
    def _calcular_total(self):
        """Calcula el total de la compra en tiempo real"""
        cantidad = self.spin_cantidad.value()
        precio = self.spin_precio_compra.value()
        total = cantidad * precio
        self.label_total.setText(f"Total: ${total:,.2f}")
    
    def get_datos_compra(self):
        """Devuelve los datos de la compra"""
        return (
            self.spin_cantidad.value(),
            self.spin_precio_compra.value(),
            self.spin_precio_venta.value()
        )





class DialogoProducirProducto(QDialog):
    def __init__(self, product_name, stock_actual, costo_unitario, precio_venta_actual, unidad_medida, ingredientes, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Producir - {product_name}")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        # Información del producto
        info_group = QGroupBox("Información del Producto")
        info_layout = QVBoxLayout(info_group)
        
        info_layout.addWidget(QLabel(f"<b>Producto:</b> {product_name}"))
        info_layout.addWidget(QLabel(f"<b>Stock actual:</b> {stock_actual} {unidad_medida}"))
        info_layout.addWidget(QLabel(f"<b>Unidad:</b> {unidad_medida}"))
        info_layout.addWidget(QLabel(f"<b>Costo unitario actual:</b> ${costo_unitario:.2f} MXN"))
        
        layout.addWidget(info_group)
        
        # Datos de la producción
        produccion_group = QGroupBox("Datos de Producción")
        produccion_layout = QVBoxLayout(produccion_group)
        
        # Cantidad
        cantidad_layout = QHBoxLayout()
        cantidad_layout.addWidget(QLabel("Cantidad a producir:"))
        self.spin_cantidad = QDoubleSpinBox()
        self.spin_cantidad.setMinimum(0.1)
        self.spin_cantidad.setMaximum(10000)
        self.spin_cantidad.setDecimals(2)
        self.spin_cantidad.setValue(1.0)
        cantidad_layout.addWidget(self.spin_cantidad)
        cantidad_layout.addWidget(QLabel(unidad_medida))
        produccion_layout.addLayout(cantidad_layout)
        
        # Precio de venta
        precio_layout = QHBoxLayout()
        precio_layout.addWidget(QLabel("Precio de venta:"))
        self.spin_precio_venta = QDoubleSpinBox()
        self.spin_precio_venta.setMinimum(0.01)
        self.spin_precio_venta.setMaximum(100000)
        self.spin_precio_venta.setDecimals(2)
        self.spin_precio_venta.setValue(precio_venta_actual or 0.0)
        self.spin_precio_venta.setPrefix("$ ")
        precio_layout.addWidget(self.spin_precio_venta)
        precio_layout.addWidget(QLabel(f"c/u ({unidad_medida})"))
        produccion_layout.addLayout(precio_layout)
        
        # Información de costos
        self.label_costo_total = QLabel("Costo total: $0.00")
        self.label_costo_total.setStyleSheet("font-weight: bold; color: #e74c3c;")
        produccion_layout.addWidget(self.label_costo_total)
        
        layout.addWidget(produccion_group)
        
        # Información de la fórmula
        if ingredientes:
            formula_group = QGroupBox("Fórmula del Producto")
            formula_layout = QVBoxLayout(formula_group)
            
            for nombre_mp, costo_mp, unidad_mp, porcentaje, stock_mp in ingredientes:
                ingrediente_text = f"  - {nombre_mp}: {porcentaje}% ({costo_mp:.2f} MXN/{unidad_mp}) - Stock: {stock_mp} {unidad_mp}"
                formula_layout.addWidget(QLabel(ingrediente_text))
            
            layout.addWidget(formula_group)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_producir = QPushButton("Producir")
        btn_producir.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        
        btn_cancelar.clicked.connect(self.reject)
        btn_producir.clicked.connect(self.accept)
        
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_producir)
        layout.addLayout(btn_layout)
        
        # Conectar señales para calcular costo total en tiempo real
        self.spin_cantidad.valueChanged.connect(self._calcular_costo_total)
        self.costo_unitario = costo_unitario
        
        # Calcular costo total inicial
        self._calcular_costo_total()
    
    def _calcular_costo_total(self):
        """Calcula el costo total de producción en tiempo real"""
        cantidad = self.spin_cantidad.value()
        costo_total = cantidad * self.costo_unitario
        self.label_costo_total.setText(f"Costo total: ${costo_total:,.2f} MXN")
    
    def get_datos_produccion(self):
        """Devuelve los datos de la producción"""
        return (
            self.spin_cantidad.value(),
            self.spin_precio_venta.value()
        )