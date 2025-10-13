from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QTableWidget,
    QPushButton, QDialogButtonBox, QAbstractItemView, QTableWidgetItem,
    QInputDialog, QMessageBox, QHeaderView
)

class FormulaDialog(QDialog):
    def __init__(self, producto_nombre, materias_primas_disponibles, formula_actual, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Fórmula para: {producto_nombre}")
        self.setMinimumSize(600, 400)

        # --- Layout Principal ---
        main_layout = QVBoxLayout(self)
        
        # --- Layout de Contenido (Listas y Botones) ---
        content_layout = QHBoxLayout()
        main_layout.addLayout(content_layout)

        # Columna Izquierda: Todas las materias primas
        disponibles_layout = QVBoxLayout()
        disponibles_layout.addWidget(QLabel("<b>Materias Primas Disponibles</b>"))
        self.lista_materias_primas = QListWidget()
        self.lista_materias_primas.addItems(materias_primas_disponibles)
        self.lista_materias_primas.setSelectionMode(QAbstractItemView.ExtendedSelection)
        disponibles_layout.addWidget(self.lista_materias_primas)
        
        # Columna Central: Botones para agregar/quitar
        botones_centrales_layout = QVBoxLayout()
        self.btn_agregar = QPushButton("Añadir →")
        self.btn_quitar = QPushButton("← Quitar")
        botones_centrales_layout.addStretch()
        botones_centrales_layout.addWidget(self.btn_agregar)
        botones_centrales_layout.addWidget(self.btn_quitar)
        botones_centrales_layout.addStretch()

        # Columna Derecha: Tabla con la fórmula actual
        formula_layout = QVBoxLayout()
        formula_layout.addWidget(QLabel("<b>Fórmula Actual del Producto</b>"))
        self.tabla_formula = QTableWidget()
        self.tabla_formula.setColumnCount(2)
        self.tabla_formula.setHorizontalHeaderLabels(["Materia Prima", "Porcentaje (%)"])
        self.tabla_formula.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        formula_layout.addWidget(self.tabla_formula)
        
        content_layout.addLayout(disponibles_layout, 2)
        content_layout.addLayout(botones_centrales_layout, 1)
        content_layout.addLayout(formula_layout, 3)

        # --- Botones OK y Cancelar ---
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        main_layout.addWidget(button_box)
        
        # --- Conexiones ---
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.btn_agregar.clicked.connect(self.agregar_ingrediente)
        self.btn_quitar.clicked.connect(self.quitar_ingrediente)

        # --- Cargar datos iniciales ---
        self.cargar_formula_actual(formula_actual)

    def cargar_formula_actual(self, formula_actual):
        """Llena la tabla con la fórmula existente del producto."""
        for ingrediente in formula_actual:
            row_position = self.tabla_formula.rowCount()
            self.tabla_formula.insertRow(row_position)
            self.tabla_formula.setItem(row_position, 0, QTableWidgetItem(ingrediente['nombre_mp']))
            self.tabla_formula.setItem(row_position, 1, QTableWidgetItem(str(ingrediente['porcentaje'])))
    
    def agregar_ingrediente(self):
        """Agrega los ítems seleccionados de la lista a la tabla de fórmula."""
        items_seleccionados = self.lista_materias_primas.selectedItems()
        if not items_seleccionados:
            return

        # Verificar si el ingrediente ya está en la fórmula
        nombres_en_formula = {self.tabla_formula.item(row, 0).text() for row in range(self.tabla_formula.rowCount())}

        for item in items_seleccionados:
            if item.text() in nombres_en_formula:
                continue # Saltar si ya existe

            # Pedir el porcentaje al usuario
            porcentaje, ok = QInputDialog.getDouble(self, "Asignar Porcentaje", f"Porcentaje para '{item.text()}':", 0, 0, 100, 2)
            
            if ok:
                row_position = self.tabla_formula.rowCount()
                self.tabla_formula.insertRow(row_position)
                self.tabla_formula.setItem(row_position, 0, QTableWidgetItem(item.text()))
                self.tabla_formula.setItem(row_position, 1, QTableWidgetItem(str(porcentaje)))

    def quitar_ingrediente(self):
        """Quita la fila seleccionada de la tabla de fórmula."""
        fila_seleccionada = self.tabla_formula.currentRow()
        if fila_seleccionada >= 0:
            self.tabla_formula.removeRow(fila_seleccionada)

    def get_formula(self):
        """Recopila y devuelve la fórmula final de la tabla."""
        formula = []
        total_porcentaje = 0
        for row in range(self.tabla_formula.rowCount()):
            nombre_mp = self.tabla_formula.item(row, 0).text()
            try:
                porcentaje = float(self.tabla_formula.item(row, 1).text())
                total_porcentaje += porcentaje
                formula.append({"nombre_mp": nombre_mp, "porcentaje": porcentaje})
            except (ValueError, TypeError):
                # Ignorar filas con porcentaje inválido
                continue
        
        # Validar que la suma no exceda 100
        if total_porcentaje > 100.1: # Usamos un pequeño margen por errores de flotantes
            QMessageBox.warning(self, "Porcentaje Excedido", f"La suma de los porcentajes ({total_porcentaje}%) no puede exceder 100%.")
            return None # Devolver None indica un error

        return formula