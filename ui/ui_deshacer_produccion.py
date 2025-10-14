# ui/ui_deshacer_produccion.py (VERSIÓN CON DESHACER PARCIAL)

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QMessageBox, QHeaderView, QDoubleSpinBox, QComboBox
)
from PyQt5.QtCore import Qt
from sqlalchemy import text
import traceback
from datetime import datetime, timedelta

class VentanaDeshacerProduccion(QDialog):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.setWindowTitle("Deshacer Registro de Producción")
        self.setMinimumSize(600, 400)
        self.id_produccion_seleccionado = None

        # --- Layout y Widgets ---
        layout = QVBoxLayout(self)
        filtro_layout = QHBoxLayout()
        filtro_layout.addWidget(QLabel("<b>Filtrar por Período:</b>"))
        self.combo_periodo = QComboBox()
        self.combo_periodo.addItems(["Esta Semana", "Últimos 15 Días", "Este Mes", "Meses Anteriores"])
        filtro_layout.addWidget(self.combo_periodo)
        filtro_layout.addStretch()
        layout.addLayout(filtro_layout)
        layout.addWidget(QLabel("<b>1. Seleccione el registro de producción que desea deshacer:</b>"))

        self.tabla_produccion = QTableWidget()
        self.tabla_produccion.setColumnCount(4)
        self.tabla_produccion.setHorizontalHeaderLabels(["ID Reg.", "Fecha", "Producto", "Cantidad Producida"])
        self.tabla_produccion.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_produccion.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tabla_produccion.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tabla_produccion.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tabla_produccion)

        # --- INICIO DE LA MODIFICACIÓN 1: AÑADIR CAMPO DE CANTIDAD ---
        cantidad_layout = QHBoxLayout()
        cantidad_layout.addWidget(QLabel("<b>2. Especifique la cantidad a deshacer:</b>"))
        self.cantidad_a_deshacer_input = QDoubleSpinBox()
        self.cantidad_a_deshacer_input.setDecimals(2)
        self.cantidad_a_deshacer_input.setRange(0, 999999)
        self.cantidad_a_deshacer_input.setEnabled(False) # Deshabilitado hasta que se seleccione una fila
        cantidad_layout.addWidget(self.cantidad_a_deshacer_input)
        layout.addLayout(cantidad_layout)
        # --- FIN DE LA MODIFICACIÓN 1 ---

        btn_layout = QHBoxLayout()
        btn_deshacer = QPushButton("Deshacer Producción Seleccionada")
        btn_deshacer.setStyleSheet("background-color: #e74c3c; color: white;")
        btn_cancelar = QPushButton("Cancelar")
        btn_layout.addWidget(btn_deshacer)
        btn_layout.addWidget(btn_cancelar)
        layout.addLayout(btn_layout)

        # --- Conexiones ---
        btn_deshacer.clicked.connect(self.confirmar_y_deshacer)
        btn_cancelar.clicked.connect(self.reject)
        # --- INICIO DE LA MODIFICACIÓN 2: CONECTAR SELECCIÓN DE TABLA ---
        self.tabla_produccion.itemSelectionChanged.connect(self.on_selection_changed)
        self.combo_periodo.currentIndexChanged.connect(self.cargar_produccion)

        # --- FIN DE LA MODIFICACIÓN 2 ---

        # --- Cargar datos ---
        self.cargar_produccion_reciente()
    
    def cargar_produccion(self):
        """Carga los registros de producción según el período seleccionado."""
        periodo = self.combo_periodo.currentText()
        hoy = datetime.now().date()
        
        if periodo == "Esta Semana":
            # Lunes de esta semana
            fecha_inicio = hoy - timedelta(days=hoy.weekday())
            fecha_fin = hoy
        elif periodo == "Últimos 15 Días":
            fecha_inicio = hoy - timedelta(days=15)
            fecha_fin = hoy
        elif periodo == "Este Mes":
            # Primer día del mes actual
            fecha_inicio = hoy.replace(day=1)
            fecha_fin = hoy
        else: # Meses Anteriores
            # Todo lo que sea anterior al primer día de este mes
            fecha_fin = hoy.replace(day=1) - timedelta(days=1)
            # Mostramos un rango amplio hacia atrás
            fecha_inicio = fecha_fin - relativedelta(years=5)

        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT pr.id_produccion, pr.fecha, p.nombre_producto, pr.cantidad
                    FROM produccion pr
                    JOIN productos p ON pr.producto_id = p.id_producto
                    WHERE pr.cantidad > 0 AND pr.fecha BETWEEN :start_date AND :end_date
                    ORDER BY pr.id_produccion DESC
                    LIMIT 100
                """)
                resultados = conn.execute(query, {"start_date": fecha_inicio, "end_date": fecha_fin}).fetchall()

                self.tabla_produccion.clearContents()
                self.tabla_produccion.setRowCount(len(resultados))
                for i, row in enumerate(resultados):
                    self.tabla_produccion.setItem(i, 0, QTableWidgetItem(str(row[0])))
                    self.tabla_produccion.setItem(i, 1, QTableWidgetItem(str(row[1])))
                    self.tabla_produccion.setItem(i, 2, QTableWidgetItem(str(row[2])))
                    self.tabla_produccion.setItem(i, 3, QTableWidgetItem(f"{row[3]:.2f}"))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar la producción del período:\n{e}")

    # --- INICIO DE LA MODIFICACIÓN 3: NUEVA FUNCIÓN PARA MANEJAR LA SELECCIÓN ---
    def on_selection_changed(self):
        """Se activa cuando el usuario selecciona una fila en la tabla."""
        selected_items = self.tabla_produccion.selectedItems()
        if not selected_items:
            self.cantidad_a_deshacer_input.setEnabled(False)
            self.cantidad_a_deshacer_input.setValue(0)
            return

        fila_seleccionada = self.tabla_produccion.currentRow()
        cantidad_producida = float(self.tabla_produccion.item(fila_seleccionada, 3).text())
        
        self.cantidad_a_deshacer_input.setEnabled(True)
        self.cantidad_a_deshacer_input.setMaximum(cantidad_producida)
        self.cantidad_a_deshacer_input.setValue(cantidad_producida) # Por defecto, deshacer todo
    # --- FIN DE LA MODIFICACIÓN 3 ---

    def cargar_produccion_reciente(self):
        """Carga los últimos 20 registros de producción para que el usuario elija."""
        try:
            with self.engine.connect() as conn:
                # CORREGIDO: Consulta compatible
                query = text("""
                    SELECT pr.id_produccion, pr.fecha, p.nombre_producto, pr.cantidad
                    FROM produccion pr
                    JOIN productos p ON pr.producto_id = p.id_producto
                    WHERE pr.cantidad > 0
                    ORDER BY pr.id_produccion DESC
                    LIMIT 20
                """)
                resultados = conn.execute(query).fetchall()

                self.tabla_produccion.setRowCount(len(resultados))
                for i, row in enumerate(resultados):
                    self.tabla_produccion.setItem(i, 0, QTableWidgetItem(str(row[0])))
                    self.tabla_produccion.setItem(i, 1, QTableWidgetItem(str(row[1])))
                    self.tabla_produccion.setItem(i, 2, QTableWidgetItem(str(row[2])))
                    self.tabla_produccion.setItem(i, 3, QTableWidgetItem(f"{row[3]:.2f}"))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar la producción reciente:\n{e}")
    # --- INICIO DE LA MODIFICACIÓN 4: ACTUALIZAR LÓGICA DE CONFIRMACIÓN ---
    def confirmar_y_deshacer(self):
        selected_items = self.tabla_produccion.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Sin Selección", "Por favor, seleccione una fila de la tabla.")
            return

        cantidad_a_deshacer = self.cantidad_a_deshacer_input.value()
        if cantidad_a_deshacer <= 0:
            QMessageBox.warning(self, "Cantidad Inválida", "La cantidad a deshacer debe ser mayor que cero.")
            return

        fila_seleccionada = self.tabla_produccion.currentRow()
        id_produccion = int(self.tabla_produccion.item(fila_seleccionada, 0).text())
        nombre_producto = self.tabla_produccion.item(fila_seleccionada, 2).text()

        confirm = QMessageBox.question(self, "Confirmar Acción",
                                       f"¿Está seguro de que desea deshacer <b>{cantidad_a_deshacer:.2f} unidades</b> de la producción de:\n\n"
                                       f"<b>{nombre_producto}</b> (Registro ID: {id_produccion})?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if confirm == QMessageBox.StandardButton.Yes:
            self.ejecutar_deshacer(id_produccion, cantidad_a_deshacer)
    # --- FIN DE LA MODIFICACIÓN 4 ---

    # --- INICIO DE LA MODIFICACIÓN 5: REESCRIBIR LÓGICA DE EJECUCIÓN ---
    def ejecutar_deshacer(self, id_produccion, cantidad_a_deshacer):
        """
        Ejecuta la lógica de deshacer (parcial o total) dentro de una transacción.
        """
        try:
            with self.engine.connect() as conn:
                with conn.begin() as trans:
                    # 1. Obtener detalles de la producción original
                    q_prod = text("SELECT producto_id, cantidad, costo FROM produccion WHERE id_produccion = :id_p")
                    res_prod = conn.execute(q_prod, {"id_p": id_produccion}).fetchone()
                    if not res_prod: raise Exception("El registro de producción ya no existe.")
                    
                    producto_id, cantidad_original, costo_original = res_prod

                    if cantidad_a_deshacer > cantidad_original:
                        raise Exception("No se puede deshacer más de lo que se produjo.")

                    # 2. Restar el producto terminado del inventario de productos
                    q_update_prod = text("UPDATE productos SET cantidad_producto = cantidad_producto - :cant WHERE id_producto = :id")
                    conn.execute(q_update_prod, {"cant": cantidad_a_deshacer, "id": producto_id})

                    # 3. Devolver materias primas al inventario
                    q_formula = text("SELECT id_mp, porcentaje FROM formulas WHERE id_producto = :id")
                    ingredientes = conn.execute(q_formula, {"id": producto_id}).fetchall()
                    for id_mp, porcentaje in ingredientes:
                        mp_a_devolver = (float(porcentaje) / 100) * float(cantidad_a_deshacer)
                        q_update_mp = text("UPDATE materiasprimas SET cantidad_comprada_mp = cantidad_comprada_mp + :cant WHERE id_mp = :id_mp")
                        conn.execute(q_update_mp, {"cant": mp_a_devolver, "id_mp": id_mp})

                    # 4. Decidir si actualizar o eliminar el registro de producción
                    if cantidad_a_deshacer >= cantidad_original:
                        # Si se deshace todo o más (por si acaso), se elimina el registro
                        q_delete_prod = text("DELETE FROM produccion WHERE id_produccion = :id_p")
                        conn.execute(q_delete_prod, {"id_p": id_produccion})
                    else:
                        # Si es parcial, se actualiza el registro restando la cantidad y el costo proporcional
                        costo_proporcional_deshecho = (costo_original / cantidad_original) * cantidad_a_deshacer
                        q_update_registro = text("""
                            UPDATE produccion 
                            SET cantidad = cantidad - :cant, costo = costo - :costo
                            WHERE id_produccion = :id_p
                        """)
                        conn.execute(q_update_registro, {"cant": cantidad_a_deshacer, "costo": costo_proporcional_deshecho, "id_p": id_produccion})

            QMessageBox.information(self, "Éxito", "La producción ha sido deshecha correctamente.")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error en la Transacción", f"No se pudo deshacer la producción:\n{e}")
            traceback.print_exc()
    # --- FIN DE LA MODIFICACIÓN 5 ---