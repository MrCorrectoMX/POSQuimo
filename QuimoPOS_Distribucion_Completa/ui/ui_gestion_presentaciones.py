# ui_gestion_presentaciones.py - VERSIÓN SIMPLE Y FUNCIONAL

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QDialogButtonBox, QMessageBox, QComboBox
)
from PyQt5.QtCore import Qt

class GestionPresentacionesDialog(QDialog):
    def __init__(self, producto_nombre, producto_id, presentaciones_actuales, envases_disponibles, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Presentaciones: {producto_nombre}")
        self.setMinimumSize(400, 450)
        
        self.producto_nombre = producto_nombre
        self.producto_id = producto_id
        self.presentaciones = presentaciones_actuales.copy()
        self.envases_disponibles = envases_disponibles

        layout = QVBoxLayout(self)
        
        # Información
        layout.addWidget(QLabel(f"<b>Producto:</b> {producto_nombre}"))
        layout.addWidget(QLabel("<b>Seleccionar envase:</b>"))
        
        # Combo de envases
        self.combo_envase = QComboBox()
        self.combo_envase.addItem("Seleccione un envase...", None)
        for envase in self.envases_disponibles:
            self.combo_envase.addItem(
                f"{envase['nombre_envase']} - ${envase['costo_envase']:.2f}", 
                envase
            )
        layout.addWidget(self.combo_envase)
        
        # Botón agregar
        btn_agregar = QPushButton("➕ Agregar Presentación")
        btn_agregar.clicked.connect(self.agregar_presentacion)
        layout.addWidget(btn_agregar)
        
        # Presentaciones actuales
        layout.addWidget(QLabel("<b>Presentaciones actuales:</b>"))
        self.lista_presentaciones = QListWidget()
        self.actualizar_lista()
        layout.addWidget(self.lista_presentaciones)
        
        # Botón eliminar
        btn_eliminar = QPushButton("❌ Eliminar Seleccionada")
        btn_eliminar.clicked.connect(self.eliminar_seleccionada)
        layout.addWidget(btn_eliminar)
        
        # Botones
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def agregar_presentacion(self):
        """Agrega una nueva presentación"""
        envase_data = self.combo_envase.currentData()
        
        if not envase_data:
            QMessageBox.warning(self, "Error", "Seleccione un envase.")
            return
        
        nombre_presentacion = envase_data['nombre_envase']
        
        # Verificar si ya existe
        for pres in self.presentaciones:
            if pres['nombre_presentacion'] == nombre_presentacion:
                QMessageBox.warning(self, "Error", "Esta presentación ya existe.")
                return
        
        # Agregar nueva presentación
        nueva_presentacion = {
            'nombre_presentacion': nombre_presentacion,
            'factor': 1.0,
            'id_envase': envase_data['id_envase'],
            'costo_envase': envase_data['costo_envase'],
            'es_nuevo': True
        }
        
        self.presentaciones.append(nueva_presentacion)
        self.actualizar_lista()
        self.combo_envase.setCurrentIndex(0)

    def eliminar_seleccionada(self):
        """Elimina la presentación seleccionada"""
        current_item = self.lista_presentaciones.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Seleccione una presentación para eliminar.")
            return
        
        nombre = current_item.data(Qt.UserRole)
        
        confirm = QMessageBox.question(
            self, "Confirmar",
            f"¿Eliminar la presentación '{nombre}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            # Buscar y eliminar
            self.presentaciones = [p for p in self.presentaciones if p['nombre_presentacion'] != nombre]
            self.actualizar_lista()

    def actualizar_lista(self):
        """Actualiza la lista de presentaciones"""
        self.lista_presentaciones.clear()
        for pres in self.presentaciones:
            item = QListWidgetItem(f"{pres['nombre_presentacion']} - ${pres['costo_envase']:.2f}")
            item.setData(Qt.UserRole, pres['nombre_presentacion'])
            self.lista_presentaciones.addItem(item)

    def get_presentaciones(self):
        """Devuelve las presentaciones"""
        return self.presentaciones