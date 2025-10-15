# ui/ui_pos.py (modificado presentaciones)

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QScrollArea, QFrame, QGridLayout, QSizePolicy, QMessageBox, QTabWidget, QMenu,
    QAction, QInputDialog, QDialog, QComboBox,QLineEdit,QTableWidget,QHeaderView,QTableWidgetItem
    ,QApplication
)
from PyQt5.QtCore import Qt, QEvent, QTimer
from sqlalchemy import text
import functools
from ui.ui_panel_inferior import PanelInferiorRedisenado
from .ui_formula import FormulaDialog


class POSWindow(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine

        # Ticket
        self.current_ticket = {}
        self.current_total = 0.0

        # Cache de productos por tabla (para re-layout sin volver a consultar la BD)
        self.products_cache = {}

        # Map: viewport widget -> (table_name, grid_layout)
        self.viewport_map = {}

        # Anchura mínima deseada por "celda"
        self.min_button_width = 160
        self.min_button_height = 90

        # Variables para presentaciones
        self.current_product_with_presentations = None
        self.presentations_frame = None
        self.presentations_layout = None

        self._init_ui()
        self._populate_grids()

        # Primer re-layout cuando el widget se muestre
        QTimer.singleShot(120, self._refresh_all_layouts)
        
        # Cargar clientes al inicio
        self._load_clients()

    # -------------------------
    # UI Init
    # -------------------------
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

        # Scroll areas con contador en el título
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

            # --- Contar artículos en la tabla ---
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = result.scalar() or 0

            # --- Agregar número al título ---
            self.tabs_productos.addTab(scroll_area, f"{title} ({count})")

            viewport = scroll_area.viewport()
            self.viewport_map[viewport] = (table_name, grid_layout)
            viewport.installEventFilter(self)

            self.tabs_productos.addTab(scroll_area, title)

        left_panel.addWidget(self.tabs_productos)
        
        # --- Frame para presentaciones (inicialmente oculto) ---
        self.presentations_frame = QFrame()
        self.presentations_frame.setVisible(False)
        self.presentations_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                margin: 5px;
            }
        """)
        
        presentations_main_layout = QVBoxLayout(self.presentations_frame)
        
        # Header con nombre del producto
        self.presentations_header = QLabel()
        self.presentations_header.setStyleSheet("font-weight: bold; font-size: 14px; color: #495057;")
        presentations_main_layout.addWidget(self.presentations_header)
        
        # Layout horizontal para los botones de presentaciones
        self.presentations_layout = QHBoxLayout()
        self.presentations_layout.setSpacing(8)
        self.presentations_layout.setContentsMargins(10, 5, 10, 10)
        presentations_main_layout.addLayout(self.presentations_layout)
        
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
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        btn_cerrar_presentaciones.clicked.connect(self._ocultar_presentaciones)
        presentations_main_layout.addWidget(btn_cerrar_presentaciones)
        
        left_panel.addWidget(self.presentations_frame)
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

    # -------------------------
    # Funciones para presentaciones
    # -------------------------
    def _mostrar_presentaciones(self, table_name, product_name):
        """Muestra las presentaciones disponibles para un producto"""
        if table_name != "productos":
            # Para productos reventa y materias primas, añadir directamente
            self._add_product_to_ticket(table_name, product_name)
            return
            
        try:
            with self.engine.connect() as conn:
                # Obtener el ID del producto
                query_id = text("SELECT id_producto FROM productos WHERE nombre_producto = :nombre")
                producto_id = conn.execute(query_id, {"nombre": product_name}).scalar()
                
                if not producto_id:
                    self._add_product_to_ticket(table_name, product_name)
                    return
                
                # Buscar presentaciones
                query_presentaciones = text("""
                    SELECT nombre_presentacion, factor, precio_venta 
                    FROM presentaciones 
                    WHERE id_producto = :id_producto
                    ORDER BY factor
                """)
                presentaciones = conn.execute(query_presentaciones, {"id_producto": producto_id}).fetchall()
                
                if not presentaciones:
                    # Si no hay presentaciones, añadir directamente
                    self._add_product_to_ticket(table_name, product_name)
                    return
                
                # Mostrar el frame de presentaciones
                self.current_product_with_presentations = product_name
                self.presentations_header.setText(f"Presentaciones de: {product_name}")
                
                # Limpiar layout anterior
                while self.presentations_layout.count():
                    child = self.presentations_layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                
                # Crear botones para cada presentación
                for pres in presentaciones:
                    nombre_pres, factor, precio = pres
                    btn_pres = QPushButton(f"{nombre_pres}\n${precio:.2f}")
                    btn_pres.setStyleSheet("""
                        QPushButton {
                            background-color: #e9ecef;
                            border: 1px solid #ced4da;
                            border-radius: 6px;
                            padding: 8px 12px;
                            font-size: 11px;
                            min-width: 80px;
                            min-height: 50px;
                        }
                        QPushButton:hover {
                            background-color: #007bff;
                            color: white;
                        }
                    """)
                    btn_pres.clicked.connect(
                        functools.partial(self._seleccionar_presentacion, product_name, nombre_pres, precio)
                    )
                    self.presentations_layout.addWidget(btn_pres)
                
                self.presentations_frame.setVisible(True)
                
        except Exception as e:
            print(f"Error al cargar presentaciones: {e}")
            self._add_product_to_ticket(table_name, product_name)

    def _ocultar_presentaciones(self):
        """Oculta el frame de presentaciones"""
        self.presentations_frame.setVisible(False)
        self.current_product_with_presentations = None

    def _seleccionar_presentacion(self, product_name, presentacion_nombre, precio):
        """Añade el producto con la presentación seleccionada al ticket"""
        nombre_completo = f"{product_name} ({presentacion_nombre})"
        
        # Actualizar el área del producto
        self.actualizar_area_producto(product_name, "productos")
        
        # Añadir al ticket con el precio de la presentación
        if nombre_completo in self.current_ticket:
            self.current_ticket[nombre_completo]['qty'] += 1
            qty = self.current_ticket[nombre_completo]['qty']
            price = self.current_ticket[nombre_completo]['price']
            self.current_ticket[nombre_completo]['label'].setText(f"{nombre_completo} x{qty}  ${price*qty:.2f}")
        else:
            # Crear fila directamente dentro del ticket
            item_widget = QWidget()
            layout = QHBoxLayout(item_widget)
            layout.setContentsMargins(5, 2, 5, 2)

            # Etiqueta del producto
            label = QLabel(f"{nombre_completo} x1  ${precio:.2f}")
            layout.addWidget(label)

            # Botón eliminar
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
            delete_btn.hide()  # Solo visible al pasar el mouse
            layout.addWidget(delete_btn)

            # Mostrar botón solo al pasar el mouse
            item_widget.enterEvent = lambda e: delete_btn.show()
            item_widget.leaveEvent = lambda e: delete_btn.hide()

            # Conectar botón a función para decrementar
            delete_btn.clicked.connect(lambda _, name=nombre_completo: self._decrement_ticket_product(name))

            # Añadir directamente al ticket
            self.ticket_items_area.addWidget(item_widget)

            # Guardar referencia en el diccionario
            self.current_ticket[nombre_completo] = {
                'qty': 1,
                'price': precio,
                'widget': item_widget,
                'label': label,
                'product_name_base': product_name  # Guardar nombre base para procesar venta
            }

        # Actualizar total
        self.current_total += precio
        self._update_ticket_display()
        
        # Ocultar presentaciones después de seleccionar
        self._ocultar_presentaciones()


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
        """
        Lee los productos (nombre y stock) y guarda la lista en self.products_cache[table_name]
        """
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
                        SELECT {name_col} AS nombre, {stock_col} AS stock
                        FROM {table_name}
                        WHERE {status_col} = 1
                        ORDER BY nombre;
                    """)
                else:
                    query = text(f"""
                        SELECT {name_col} AS nombre, NULL AS stock
                        FROM {table_name}
                        WHERE {status_col} = 1
                        ORDER BY nombre;
                    """)
                rows = conn.execute(query).fetchall()
                productos = [(r[0], (r[1] if r[1] is not None else 0)) for r in rows if r[0] and str(r[0]).strip() != ""]
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
        Evita duplicados basándose en una propiedad 'product_name' del QPushButton.
        """
        productos = self.products_cache.get(table_name, [])
        if not productos:
            return

        available_width = max(10, viewport.width())
        columnas = max(1, available_width // (self.min_button_width + grid_layout.spacing()))

        # 🔹 Limpiar layout y eliminar botones duplicados existentes (comparando por product_name)
        nombres_vistos = set()
        widgets_a_eliminar = []
        for i in range(grid_layout.count()):
            item = grid_layout.itemAt(i)
            w = item.widget()
            if w and isinstance(w, QPushButton):
                pname = w.property('product_name')
                if pname is None:
                    # fallback: extraer antes del " (" en el texto del botón
                    text = w.text()
                    pname = text.split(" (")[0] if " (" in text else text
                if pname in nombres_vistos:
                    widgets_a_eliminar.append(w)
                else:
                    nombres_vistos.add(pname)

        for w in widgets_a_eliminar:
            grid_layout.removeWidget(w)
            w.deleteLater()

        # 🔹 Agregar botones nuevos solo si no existen aún
        idx_real = 0
        for nombre, stock in productos:
            if nombre in nombres_vistos or not str(nombre).strip():
                continue  # ignorar duplicados exactos o vacíos

            fila = idx_real // columnas
            col = idx_real % columnas

            # Mostrar stock como entero si es número, si no mostrar tal cual
            try:
                if isinstance(stock, float) and stock.is_integer():
                    stock_display = int(stock)
                else:
                    stock_display = stock
            except Exception:
                stock_display = stock

            btn = QPushButton(f"{nombre} ({stock_display})")
            # Guardamos el nombre "puro" en una property para comparaciones futuras
            btn.setProperty('product_name', nombre)

            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setMinimumSize(self.min_button_width, self.min_button_height)
            btn.setToolTip(nombre)
            
            # MODIFICACIÓN: Para productos, usar presentaciones; para otros, añadir directamente
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
        for viewport, (table_name, grid_layout) in self.viewport_map.items():
            self._relayout_table(table_name, grid_layout, viewport)

    # -------------------------
    # Funciones de Clientes
    # -------------------------
    def _load_clients(self):
        """Carga los clientes de la base de datos en el QComboBox."""
        self.cliente_combobox.clear()
        try:
            with self.engine.connect() as conn:
                # CORREGIDO: Usar nombre_cliente consistentemente
                query = text("SELECT nombre_cliente, id_cliente FROM clientes ORDER BY nombre_cliente")
                rows = conn.execute(query).fetchall()
                for nombre_cliente, id_cliente in rows:
                    self.cliente_combobox.addItem(nombre_cliente, id_cliente)
                    
        except Exception as e:
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
                    # CAMBIO: Se usa 'nombre_cliente' en lugar de 'nombre'
                    query = text("SELECT id_cliente FROM clientes WHERE nombre_cliente = :nombre")
                    result = conn.execute(query, {"nombre": current_text}).scalar()
                    if result:
                        return result
            except Exception as e:
                print(f"Error al buscar cliente por nombre: {e}")
                
        # Si está en la lista o es "Cliente General"
        index = self.cliente_combobox.currentIndex()
        if index != -1:
            return self.cliente_combobox.itemData(index)
            
        # Fallback al cliente general
        return 1  # Asumimos que el ID 1 es el cliente general por defecto
        
    # -------------------------
    # Ticket methods
    # -------------------------
    def _add_product_to_ticket(self, table_name, product_name):
        """
        Añade un producto al ticket buscando su precio en la tabla correcta
        según su tipo (table_name), y actualiza automáticamente el combobox de área.
        """
        self.actualizar_area_producto(product_name, table_name)

        # 🔹 Obtener precio del producto
        product_price = 0.0
        try:
            with self.engine.connect() as conn:
                if table_name == "productos":
                    query = text("SELECT precio_venta FROM productos WHERE nombre_producto = :nombre")
                    resultado = conn.execute(query, {"nombre": product_name}).scalar()
                    if resultado is not None:
                        product_price = float(resultado)
                    if product_price == 0.0:
                        product_price = self._recalcular_precio_producto(conn, product_name)
                elif table_name == "materiasprimas":
                    query_id = text("SELECT id_mp FROM materiasprimas WHERE nombre_mp = :nombre")
                    product_id = conn.execute(query_id, {"nombre": product_name}).scalar()
                    if product_id:
                        query = text("SELECT costo_unitario_mp FROM materiasprimas WHERE id_mp = :id")
                        resultado = conn.execute(query, {"id": product_id}).scalar()
                        if resultado:
                            product_price = float(resultado)
                elif table_name == "productosreventa":
                    # 🔸 1. Obtener precio del producto
                    query = text("SELECT id_prev, precio_venta FROM productosreventa WHERE nombre_prev = :nombre")
                    resultado = conn.execute(query, {"nombre": product_name}).fetchone()
                    
                    if resultado:
                        id_prev, product_price = resultado
                        product_price = float(product_price)
                        
                        # 🔸 2. Registrar venta en la tabla venta_reventa
                        try:
                            insert_query = text("""
                                INSERT INTO venta_reventa (id_prev, cantidad, total_venta, fecha_venta)
                                VALUES (:id_prev, :cantidad, :total_venta, DATE('now'))
                            """)
                            conn.execute(insert_query, {
                                "id_prev": id_prev,
                                "cantidad": 1,
                                "total_venta": product_price
                            })
                            conn.commit()
                        except Exception as e:
                            print(f"⚠️ Error al registrar venta_reventa: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error de Base de Datos", f"No se pudo obtener el precio del producto:\n{e}")
            return

        # 🔹 Crear fila del ticket
        if product_name in self.current_ticket:
            self.current_ticket[product_name]['qty'] += 1
            qty = self.current_ticket[product_name]['qty']
            price = self.current_ticket[product_name]['price']
            self.current_ticket[product_name]['label'].setText(f"{product_name} x{qty}  ${price*qty:.2f}")
        else:
            # Crear fila directamente dentro del ticket
            item_widget = QWidget()
            layout = QHBoxLayout(item_widget)
            layout.setContentsMargins(5, 2, 5, 2)

            # Etiqueta del producto
            label = QLabel(f"{product_name} x1  ${product_price:.2f}")
            layout.addWidget(label)

            # Botón eliminar
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
            delete_btn.hide()  # Solo visible al pasar el mouse
            layout.addWidget(delete_btn)

            # Mostrar botón solo al pasar el mouse
            item_widget.enterEvent = lambda e: delete_btn.show()
            item_widget.leaveEvent = lambda e: delete_btn.hide()

            # Conectar botón a función para decrementar
            delete_btn.clicked.connect(lambda _, name=product_name: self._decrement_ticket_product(name))

            # Añadir directamente al ticket
            self.ticket_items_area.addWidget(item_widget)

            # Guardar referencia en el diccionario
            self.current_ticket[product_name] = {
                'qty': 1,
                'price': product_price,
                'widget': item_widget,
                'label': label
            }

        # Actualizar total
        self.current_total += product_price
        self._update_ticket_display()


    def _decrement_ticket_product(self, product_name):
        """Reduce la cantidad y elimina la fila si llega a 0."""
        if product_name in self.current_ticket:
            self.current_ticket[product_name]['qty'] -= 1
            qty = self.current_ticket[product_name]['qty']
            price = self.current_ticket[product_name]['price']
            label = self.current_ticket[product_name]['label']

            if qty > 0:
                label.setText(f"{product_name} x{qty}  ${price*qty:.2f}")
            else:
                # Elimina el widget del layout
                widget = self.current_ticket[product_name]['widget']
                self.ticket_items_area.removeWidget(widget)
                widget.deleteLater()
                del self.current_ticket[product_name]

            # Actualiza total
            self.current_total -= price
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
                            cliente_id = cliente_result[0]
                        else:
                            QMessageBox.warning(self, "Error de Cliente", "No se pudo identificar al cliente ni al cliente general por defecto.")
                            return

                    # PRIMERO: VERIFICAR STOCK PARA TODOS LOS PRODUCTOS
                    productos_sin_stock = []
                    for product_name_display, data in self.current_ticket.items():
                        cantidad = data["qty"]
                        
                        # Usar el nombre base para productos con presentaciones
                        product_name_base = data.get('product_name_base', product_name_display)
                        
                        # Verificar producto normal
                        producto = conn.execute(
                            text("SELECT id_producto, cantidad_producto FROM productos WHERE nombre_producto = :nombre"),
                            {"nombre": product_name_base}
                        ).fetchone()

                        if producto:
                            producto_id, stock_actual = producto
                            if stock_actual < cantidad:
                                productos_sin_stock.append(f"'{product_name_base}': Stock {stock_actual}, Necesario {cantidad}")
                            continue

                        # Verificar producto reventa
                        reventa = conn.execute(
                            text("SELECT id_prev, cantidad_prev FROM productosreventa WHERE nombre_prev = :nombre"),
                            {"nombre": product_name_base}
                        ).fetchone()

                        if reventa:
                            id_prev, stock_actual = reventa
                            if stock_actual < cantidad:
                                productos_sin_stock.append(f"'{product_name_base}': Stock {stock_actual}, Necesario {cantidad}")
                            continue

                        # Verificar materia prima
                        mp = conn.execute(
                            text("SELECT id_mp, cantidad_comprada_mp FROM materiasprimas WHERE nombre_mp = :nombre"),
                            {"nombre": product_name_base}
                        ).fetchone()

                        if mp:
                            id_mp, stock_actual = mp
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
                            producto_id, stock_actual = producto

                            # Actualizar stock
                            conn.execute(
                                text("UPDATE productos SET cantidad_producto = cantidad_producto - :cantidad WHERE id_producto = :id"),
                                {"cantidad": cantidad, "id": producto_id}
                            )

                            # Registrar venta - usar el nombre display (con presentación) para el ticket
                            conn.execute(text("""
                                INSERT INTO ventas (id_cliente, nombre_producto, tipo_tabla, cantidad, total, fecha_venta)
                                VALUES (:cliente, :nombre, 'productos', :cantidad, :total, DATE('now'))
                            """), {
                                "cliente": cliente_id,
                                "nombre": product_name_display,  # Usar el nombre con presentación
                                "cantidad": cantidad,
                                "total": total_linea
                            })

                        # ... (el resto del código de _process_sale permanece igual)

                    # TERCERO: ACTUALIZAR FONDO - INGRESO POR VENTA
                    query_ultimo_saldo = text("SELECT saldo FROM fondo ORDER BY id_movimiento DESC LIMIT 1")
                    ultimo_saldo_result = conn.execute(query_ultimo_saldo).fetchone()
                    ultimo_saldo = ultimo_saldo_result[0] if ultimo_saldo_result else 0
                    
                    nuevo_saldo = ultimo_saldo + total_venta
                    
                    query_fondo = text("""
                        INSERT INTO fondo (fecha, tipo, concepto, monto, saldo)
                        VALUES (DATE('now'), 'INGRESO', 'Venta POS', :monto, :saldo)
                    """)
                    conn.execute(query_fondo, {
                        "monto": total_venta,
                        "saldo": nuevo_saldo
                    })

                    print("✅ Transacción commitada a la BD")

            # ACTUALIZAR VISTA DESPUÉS DEL COMMIT
            self._force_immediate_refresh()

            # Si todo sale bien
            total_str = f"${self.current_total:,.2f}"
            QMessageBox.information(self, "Venta Registrada", 
                                f"Venta realizada con éxito.\n\nTotal: {total_str}\nFondo actualizado: +${total_venta:,.2f}")
            
            self._clear_ticket()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo registrar la venta: {str(e)}")

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
            
            print("✅ Stocks actualizados manteniendo layout")
            
        except Exception as e:
            print(f"❌ Error actualizando stocks: {e}")

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
            print(f"❌ Error actualizando botones: {e}")

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
    def _mostrar_menu_contextual_pos(self, table_name, product_name, btn, position):
        """Menú contextual para los botones de productos en el POS"""
        menu = QMenu()
        
        # Opción para modificar precio/costo según el tipo de tabla
        if table_name == "materiasprimas":
            accion_modificar = QAction("Modificar Costo", self)
            accion_modificar.triggered.connect(functools.partial(self._modificar_costo, table_name, product_name))
            menu.addAction(accion_modificar)

            accion_agregar_mp = QAction("Agregar Materia Prima", self)
            accion_agregar_mp.triggered.connect(self._agregar_materia_prima)
            menu.addAction(accion_agregar_mp)

            accion_agregar_stock = QAction("Aumentar stock existente", self)
            accion_agregar_stock.triggered.connect(self._aumentar_stock_existente)
            menu.addAction(accion_agregar_stock)


        elif table_name == "productosreventa":
            accion_modificar_precio = QAction("Modificar Precio Venta", self)
            accion_modificar_precio.triggered.connect(functools.partial(self._modificar_precio, table_name, product_name))
            menu.addAction(accion_modificar_precio)

            accion_modificar_precio_compra = QAction("Modificar Precio Compra", self)
            accion_modificar_precio_compra.triggered.connect(functools.partial(self._modificar_precio_compra, product_name))
            menu.addAction(accion_modificar_precio_compra)

            accion_agregar_reventa = QAction("Agregar producto de reventa", self)
            accion_agregar_reventa.triggered.connect(self.abrir_agregar_producto_reventa)
            menu.addAction(accion_agregar_reventa)


        elif table_name == "productos":
            # Para productos normales, ofrecer opciones de fórmula y precio
            accion_formula = QAction("Modificar Fórmula", self)
            accion_formula.triggered.connect(functools.partial(self._modificar_formula, product_name))
            menu.addAction(accion_formula)
            # Agregar opción cambiar área
            accion_cambiar_area = QAction("Cambiar Área", self)
            accion_cambiar_area.triggered.connect(
                functools.partial(self._cambiar_area_producto, table_name, product_name)
            )
            menu.addAction(accion_cambiar_area)

            accion_eliminar = QAction("Eliminar Producto", self)
            accion_eliminar.triggered.connect(
                functools.partial(self._eliminar_producto, table_name, product_name)
            )
            menu.addAction(accion_eliminar)

            accion_modificar_lote = QAction("Modificar Lote", self)
            accion_modificar_lote.triggered.connect(
                functools.partial(self._modificar_lote, product_name)
            )   
            menu.addAction(accion_modificar_lote)

            
            accion_precio = QAction("Modificar Precio", self)
            accion_precio.triggered.connect(functools.partial(self._modificar_precio, table_name, product_name))
            menu.addAction(accion_precio)
        
        menu.exec_(btn.mapToGlobal(position))

    def _agregar_materia_prima(self):
        """Permite agregar una o más materias primas desde un diálogo y resta del fondo"""
        dialog = AgregarMultiplesMPDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            materias_primas = dialog.get_materias_primas()
            if not materias_primas:
                QMessageBox.warning(self, "Error", "No se ingresaron materias primas válidas.")
                return

            try:
                with self.engine.begin() as conn:
                    total_gasto = 0
                    
                    for mp in materias_primas:
                        # Insertar materia prima
                        conn.execute(
                            text("""
                                INSERT INTO materiasprimas (nombre_mp, costo_unitario_mp, proveedor, cantidad_comprada_mp)
                                VALUES (:nombre, :costo, :proveedor, 0)
                            """),
                            {"nombre": mp["nombre"], "costo": mp["costo"], "proveedor": mp["proveedor"]}
                        )
                        total_gasto += mp["costo"] * mp.get("cantidad", 1)
                    
                    # RESTAR DEL FONDO
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
                    
                QMessageBox.information(self, "Éxito", 
                                    f"Se agregaron {len(materias_primas)} materias primas.\n"
                                    f"Gasto del fondo: ${total_gasto:,.2f}")
                self._populate_grids()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo agregar las materias primas: {e}")


    def _modificar_costo(self, table_name, product_name):
        """Modifica el costo de una materia prima"""
        try:
            with self.engine.connect() as conn:
                # Obtener el costo actual
                query = text("SELECT costo_unitario_mp FROM materiasprimas WHERE nombre_mp = :nombre")
                costo_actual = conn.execute(query, {"nombre": product_name}).scalar() or 0.0
                
                # Pedir nuevo costo
                nuevo_costo, ok = QInputDialog.getDouble(
                    self, 
                    "Modificar Costo", 
                    f"Nuevo costo para '{product_name}':", 
                    value=costo_actual,
                    min=0.0,
                    decimals=2
                )
                
                if ok:
                    # Actualizar en la base de datos
                    query_update = text("UPDATE materiasprimas SET costo_unitario_mp = :costo WHERE nombre_mp = :nombre")
                    conn.execute(query_update, {"costo": nuevo_costo, "nombre": product_name})
                    conn.commit()
                    
                    QMessageBox.information(self, "Éxito", f"Costo de '{product_name}' actualizado a ${nuevo_costo:.2f}")
                    
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
            # 1. Obtener el ID del producto
            query_id = text("SELECT id_producto FROM productos WHERE nombre_producto = :nombre")
            producto_id = conn.execute(query_id, {"nombre": product_name}).scalar()
            if not producto_id:
                return 0.0

            # 2. Obtener la fórmula y costos de las materias primas
            query_formula = text("""
                SELECT m.costo_unitario_mp, f.porcentaje
                FROM formulas f
                JOIN materiasprimas m ON f.id_mp = m.id_mp
                WHERE f.id_producto = :id_p
            """)
            ingredientes = conn.execute(query_formula, {"id_p": producto_id}).fetchall()

            if not ingredientes:
                return 0.0

            # 3. Calcular el costo base por unidad de producto
            costo_base = 0.0
            for costo_mp, porcentaje in ingredientes:
                if costo_mp is not None and porcentaje is not None:
                    costo_base += float(costo_mp) * (float(porcentaje) / 100.0)

            # 4. Calcular el precio final (costo + 30%)
            precio_final = costo_base * 1.30

            # 5. Actualizar el precio en la base de datos para futuras consultas
            query_update = text("UPDATE productos SET precio_venta = :precio WHERE id_producto = :id_p")
            conn.execute(query_update, {"precio": precio_final, "id_p": producto_id})
            conn.commit()

            return precio_final

        except Exception as e:
            print(f"Error al recalcular precio: {e}")
            return 0.0
        
    
    def actualizar_area_producto(self, producto_nombre, tipo_tabla):
        with self.engine.connect() as conn:
            if tipo_tabla == "productos":
                query = text("SELECT area_producto FROM productos WHERE nombre_producto = :nombre")
            elif tipo_tabla == "productosreventa":
                query = text("SELECT area_prev FROM productosreventa WHERE nombre_prev = :nombre")
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
        """Elimina un producto de la BD y refresca la UI."""
        confirm = QMessageBox.question(self, "Eliminar Producto", f"¿Seguro que quieres eliminar '{product_name}'?", 
                                    QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            try:
                with self.engine.connect() as conn:
                    if table_name == "productos":
                        conn.execute(text("UPDATE productos SET estatus_producto = 0 WHERE nombre_producto = :nombre"),
                                    {"nombre": product_name})
                    elif table_name == "productosreventa":
                        conn.execute(text("UPDATE productosreventa SET estatus_prev = 0 WHERE nombre_prev = :nombre"),
                                    {"nombre": product_name})
                    conn.commit()
                QMessageBox.information(self, "Éxito", f"Producto '{product_name}' eliminado.")
                self._populate_grids()  # refrescar botones
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



class AgregarMultiplesMPDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Agregar Materias Primas")
        self.resize(600, 400)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.tabla = QTableWidget(0, 3)
        self.tabla.setHorizontalHeaderLabels(["Materia Prima", "Costo Unitario", "Proveedor"])
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.tabla)

        btn_agregar_fila = QPushButton("Agregar Fila")
        btn_agregar_fila.clicked.connect(self.agregar_fila)
        self.layout.addWidget(btn_agregar_fila)

        btn_guardar = QPushButton("Guardar")
        btn_guardar.clicked.connect(self.guardar)
        self.layout.addWidget(btn_guardar)

        self.proveedores = self.obtener_proveedores()

    def obtener_proveedores(self):
        try:
            with self.parent.engine.connect() as conn:
                query = text("SELECT nombre_proveedor FROM proveedor ORDER BY nombre_proveedor")
                return [row[0] for row in conn.execute(query).fetchall()]
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudieron cargar proveedores: {e}")
            return []

    def agregar_fila(self):
        fila = self.tabla.rowCount()
        self.tabla.insertRow(fila)

        self.tabla.setItem(fila, 0, QTableWidgetItem(""))
        self.tabla.setItem(fila, 1, QTableWidgetItem("0.0"))

        combo_proveedor = QComboBox()
        combo_proveedor.addItems(self.proveedores + ["Agregar proveedor..."])
        combo_proveedor.currentIndexChanged.connect(lambda index, f=fila: self.proveedor_seleccionado(index, f))
        self.tabla.setCellWidget(fila, 2, combo_proveedor)

    def proveedor_seleccionado(self, index, fila):
        combo = self.tabla.cellWidget(fila, 2)
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

    def guardar(self):
        try:
            with self.parent.engine.begin() as conn:
                for fila in range(self.tabla.rowCount()):
                    nombre_mp = self.tabla.item(fila, 0).text().strip()
                    costo_unitario = float(self.tabla.item(fila, 1).text().strip())
                    proveedor = self.tabla.cellWidget(fila, 2).currentText()

                    if not nombre_mp:
                        continue

                    conn.execute(
                        text("""
                            INSERT INTO materiasprimas (nombre_mp, costo_unitario_mp, proveedor)
                            VALUES (:nombre, :costo, :proveedor)
                        """),
                        {"nombre": nombre_mp, "costo": costo_unitario, "proveedor": proveedor}
                    )
            QMessageBox.information(self, "Éxito", "Materias primas agregadas correctamente.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron agregar las materias primas: {e}")




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