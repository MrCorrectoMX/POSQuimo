# ui/ui_panel_derecho.py (modificado)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QMessageBox, QTabWidget, QGroupBox,
    QSpinBox, QDoubleSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from sqlalchemy import text


class PanelDerecho(QWidget):
    # Señal para notificar cuando se actualizan los datos
    datos_actualizados = pyqtSignal()
    
    def __init__(self, engine,modo="POS", callback_registro_produccion=None, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.callback_registro_produccion = callback_registro_produccion
        self.current_product_id = None
        self.current_table_type = "productos"
        self.modo = modo 
        
        self.setLayout(QVBoxLayout())
        
        self.tabs = QTabWidget()
        self.layout().addWidget(self.tabs)
        
        # Pestaña de Gestión (simplificada)
        self.tab_gestion = QWidget()
        self.tabs.addTab(self.tab_gestion, "Gestión de Inventario")
        self._setup_tab_gestion()
        
        # Pestaña de Producción
        self.tab_produccion = QWidget()
        self.tabs.addTab(self.tab_produccion, "Registro de Producción")
        self._setup_tab_produccion()
        
        # Pestaña de Ventas
        self.tab_ventas = QWidget()
        self.tabs.addTab(self.tab_ventas, "Registro de Ventas")
        self._setup_tab_ventas()

    def _setup_tab_gestion(self):
        layout = QVBoxLayout(self.tab_gestion)
        
        # Grupo para añadir nuevo producto
        grupo_nuevo = QGroupBox("Añadir Nuevo Producto")
        grupo_layout = QVBoxLayout(grupo_nuevo)
        
        self.input_nombre = QLineEdit(placeholderText="Nombre del producto")
        self.input_unidad = QLineEdit(placeholderText="Unidad de medida")
        
        # Siempre ComboBox para Área
        self.input_area = QComboBox()
        self.input_area.addItems(["Quimo", "Quimo Clean"])  # O tus áreas reales
        
        self.input_cantidad = QSpinBox()
        self.input_cantidad.setMinimum(0)
        self.input_cantidad.setMaximum(10000)
        
        grupo_layout.addWidget(QLabel("Nombre:"))
        grupo_layout.addWidget(self.input_nombre)
        grupo_layout.addWidget(QLabel("Unidad:"))
        grupo_layout.addWidget(self.input_unidad)
        grupo_layout.addWidget(QLabel("Área:"))
        grupo_layout.addWidget(self.input_area)
        grupo_layout.addWidget(QLabel("Cantidad inicial:"))
        grupo_layout.addWidget(self.input_cantidad)
        
        btn_guardar = QPushButton("Guardar Producto")
        btn_guardar.clicked.connect(self.guardar_producto)
        grupo_layout.addWidget(btn_guardar)
        
        layout.addWidget(grupo_nuevo)
        layout.addStretch()

    def _setup_tab_produccion(self):
        layout = QVBoxLayout(self.tab_produccion)
        
        # Grupo para registro de producción
        grupo_produccion = QGroupBox("Registrar Producción")
        grupo_layout = QVBoxLayout(grupo_produccion)
        
        self.combo_producto_produccion = QComboBox()
        self.cargar_productos_combo(self.combo_producto_produccion)
        
        self.input_cantidad_produccion = QSpinBox()
        self.input_cantidad_produccion.setMinimum(1)
        self.input_cantidad_produccion.setMaximum(1000)
        
        grupo_layout.addWidget(QLabel("Producto:"))
        grupo_layout.addWidget(self.combo_producto_produccion)
        grupo_layout.addWidget(QLabel("Cantidad producida:"))
        grupo_layout.addWidget(self.input_cantidad_produccion)
        
        btn_registrar_produccion = QPushButton("Registrar Producción")
        btn_registrar_produccion.clicked.connect(self.registrar_produccion)
        grupo_layout.addWidget(btn_registrar_produccion)
        
        layout.addWidget(grupo_produccion)
        layout.addStretch()

    def _setup_tab_ventas(self):
        layout = QVBoxLayout(self.tab_ventas)
        
        # Grupo para registro de ventas
        grupo_ventas = QGroupBox("Registrar Venta")
        grupo_layout = QVBoxLayout(grupo_ventas)
        
        self.combo_producto_venta = QComboBox()
        self.cargar_productos_combo(self.combo_producto_venta)
        
        self.input_cantidad_venta = QSpinBox()
        self.input_cantidad_venta.setMinimum(1)
        self.input_cantidad_venta.setMaximum(1000)
        
        self.combo_cliente = QComboBox()
        self.cargar_clientes_combo()
        
        grupo_layout.addWidget(QLabel("Producto:"))
        grupo_layout.addWidget(self.combo_producto_venta)
        grupo_layout.addWidget(QLabel("Cantidad vendida:"))
        grupo_layout.addWidget(self.input_cantidad_venta)
        grupo_layout.addWidget(QLabel("Cliente:"))
        grupo_layout.addWidget(self.combo_cliente)
        
        btn_registrar_venta = QPushButton("Registrar Venta")
        btn_registrar_venta.clicked.connect(self.registrar_venta)
        grupo_layout.addWidget(btn_registrar_venta)
        
        layout.addWidget(grupo_ventas)
        layout.addStretch()

    def cargar_productos_combo(self, combo):
        try:
            with self.engine.connect() as conn:
                query = text("SELECT id_producto, nombre_producto FROM productos WHERE estatus_producto = 1 ORDER BY nombre_producto")
                result = conn.execute(query)
                
                combo.clear()
                for row in result:
                    combo.addItem(row['nombre_producto'], row['id_producto'])
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los productos: {e}")

    def cargar_clientes_combo(self):
        try:
            with self.engine.connect() as conn:
                query = text("SELECT id_cliente, nombre FROM clientes ORDER BY nombre")
                result = conn.execute(query)
                
                self.combo_cliente.clear()
                for row in result:
                    self.combo_cliente.addItem(row['nombre'], row['id_cliente'])
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los clientes: {e}")

    def guardar_producto(self):
        nombre = self.input_nombre.text().strip()
        unidad = self.input_unidad.text().strip()
        if isinstance(self.input_area, QComboBox):
            area = self.input_area.currentText()
        else:
            area = self.input_area.text().strip()
        cantidad = self.input_cantidad.value()
        
        if not nombre or not unidad:
            QMessageBox.warning(self, "Error", "El nombre y la unidad son obligatorios.")
            return
            
        try:
            with self.engine.connect() as conn:
                with conn.begin() as trans:
                    query = text("""
                        INSERT INTO productos (nombre_producto, unidad_medida_producto, area_producto, cantidad_producto, estatus_producto)
                        VALUES (:nombre, :unidad, :area, :cantidad, 1)
                    """)
                    conn.execute(query, {
                        "nombre": nombre,
                        "unidad": unidad,
                        "area": area,
                        "cantidad": cantidad
                    })
            
            QMessageBox.information(self, "Éxito", "Producto guardado correctamente.")
            self.limpiar_formulario_gestion()
            self.datos_actualizados.emit()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el producto: {e}")

    def limpiar_formulario_gestion(self):
        self.input_nombre.clear()
        self.input_unidad.clear()
        if isinstance(self.input_area, QComboBox):
            self.input_area.setCurrentIndex(0)
        else:
            self.input_area.clear()
        self.input_cantidad.setValue(0)

    def registrar_produccion(self):
        producto_id = self.combo_producto_produccion.currentData()
        cantidad = self.input_cantidad_produccion.value()

        if not producto_id or cantidad <= 0:
            QMessageBox.warning(self, "Error", "Seleccione un producto y una cantidad válida.")
            return

        try:
            # Determinar tipo de producto (productos, productosreventa, materiasprimas)
            tipo_tabla = self.current_table_type  # Debes actualizar este valor según selección en tu UI
            tabla_nombre = {
                "productos": "productos",
                "productosreventa": "productosreventa",
                "materiasprimas": "materiasprimas"
            }.get(tipo_tabla, "productos")

            campo_nombre = {
                "productos": "nombre_producto",
                "productosreventa": "nombre_prev",
                "materiasprimas": "nombre_mp"
            }.get(tipo_tabla, "nombre_producto")

            campo_cantidad = {
                "productos": "cantidad_producto",
                "productosreventa": "cantidad_prev",
                "materiasprimas": "cantidad_mp"
            }.get(tipo_tabla, "cantidad_producto")

            campo_area = {
                "productos": "area_producto",
                "productosreventa": "area_prev",
                "materiasprimas": "area_mp"
            }.get(tipo_tabla, "area_producto")

            with self.engine.connect() as conn:
                # Obtener información del producto
                query = text(f"SELECT {campo_nombre}, {campo_area} FROM {tabla_nombre} WHERE id_{tabla_nombre[:-1]} = :id")
                result = conn.execute(query, {"id": producto_id}).fetchone()

                if not result:
                    QMessageBox.warning(self, "Error", "Producto no encontrado.")
                    return

                nombre_producto = result[campo_nombre]
                area = result[campo_area]

                # Calcular costo (puedes implementar tu lógica aquí)
                costo = 0

                # Callback opcional
                if self.callback_registro_produccion:
                    self.callback_registro_produccion(nombre_producto, cantidad, area, costo)

                # Actualizar cantidad en inventario
                query_update = text(f"UPDATE {tabla_nombre} SET {campo_cantidad} = {campo_cantidad} + :cantidad WHERE id_{tabla_nombre[:-1]} = :id")
                conn.execute(query_update, {"cantidad": cantidad, "id": producto_id})
                conn.commit()

            QMessageBox.information(self, "Éxito", f"Producción de {cantidad} unidades de {nombre_producto} registrada.")
            self.input_cantidad_produccion.setValue(1)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo registrar la producción: {e}")


    def registrar_venta(self):
        producto_id = self.combo_producto_venta.currentData()
        cantidad = self.input_cantidad_venta.value()
        cliente_id = self.combo_cliente.currentData()
        
        if not producto_id or cantidad <= 0 or not cliente_id:
            QMessageBox.warning(self, "Error", "Complete todos los campos correctamente.")
            return
            
        try:
            # Verificar stock disponible
            with self.engine.connect() as conn:
                query_stock = text("SELECT cantidad_producto, nombre_producto FROM productos WHERE id_producto = :id")
                result = conn.execute(query_stock, {"id": producto_id}).fetchone()
                
                if not result:
                    QMessageBox.warning(self, "Error", "Producto no encontrado.")
                    return
                    
                stock_actual = result['cantidad_producto']
                nombre_producto = result['nombre_producto']
                
                if stock_actual < cantidad:
                    QMessageBox.warning(self, "Error", f"Stock insuficiente. Solo hay {stock_actual} unidades disponibles.")
                    return
                
                # Registrar la venta
                query_venta = text("""
                    INSERT INTO ventas (producto_id, cliente_id, cantidad, fecha_venta)
                    VALUES (:producto_id, :cliente_id, :cantidad, DATE('now'))
                """)
                conn.execute(query_venta, {
                    "producto_id": producto_id,
                    "cliente_id": cliente_id,
                    "cantidad": cantidad
                })
                
                # Actualizar el stock
                query_update = text("UPDATE productos SET cantidad_producto = cantidad_producto - :cantidad WHERE id_producto = :id")
                conn.execute(query_update, {"cantidad": cantidad, "id": producto_id})
                
                conn.commit()
                
            QMessageBox.information(self, "Éxito", f"Venta de {cantidad} unidades de {nombre_producto} registrada.")
            self.input_cantidad_venta.setValue(1)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo registrar la venta: {e}")

    
    