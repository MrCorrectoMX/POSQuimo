# ui/ui_registro_clientes.py (MEJORADO)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QGroupBox, QInputDialog
)
from PyQt5.QtCore import Qt
from sqlalchemy import text
import pandas as pd


class RegistroClientesWidget(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        
        layout = QVBoxLayout(self)
        
        # Grupo de registro de clientes
        grupo_registro = QGroupBox("Registro de Clientes")
        grupo_layout = QVBoxLayout(grupo_registro)
        
        form_layout = QHBoxLayout()
        self.input_nombre = QLineEdit(placeholderText="Nombre del cliente")
        self.input_telefono = QLineEdit(placeholderText="Teléfono")
        self.input_email = QLineEdit(placeholderText="Email (opcional)")
        
        form_layout.addWidget(QLabel("Nombre:"))
        form_layout.addWidget(self.input_nombre)
        form_layout.addWidget(QLabel("Teléfono:"))
        form_layout.addWidget(self.input_telefono)
        form_layout.addWidget(QLabel("Email:"))
        form_layout.addWidget(self.input_email)
        
        btn_registrar = QPushButton("Registrar Cliente")
        btn_registrar.clicked.connect(self.registrar_cliente)
        form_layout.addWidget(btn_registrar)
        
        grupo_layout.addLayout(form_layout)
        layout.addWidget(grupo_registro)
        
        # Grupo de lista de clientes
        grupo_lista = QGroupBox("Clientes Registrados")
        grupo_lista_layout = QVBoxLayout(grupo_lista)
        
        # Botones de acción para la lista
        botones_layout = QHBoxLayout()
        btn_actualizar = QPushButton("Actualizar Lista")
        btn_actualizar.clicked.connect(self.cargar_clientes)
        btn_eliminar = QPushButton("Eliminar Cliente Seleccionado")
        btn_eliminar.clicked.connect(self.eliminar_cliente)
        btn_editar = QPushButton("Editar Cliente Seleccionado")
        btn_editar.clicked.connect(self.editar_cliente)
        
        botones_layout.addWidget(btn_actualizar)
        botones_layout.addWidget(btn_eliminar)
        botones_layout.addWidget(btn_editar)
        botones_layout.addStretch()
        
        grupo_lista_layout.addLayout(botones_layout)
        
        self.tabla_clientes = QTableWidget()
        self.tabla_clientes.setColumnCount(4)
        self.tabla_clientes.setHorizontalHeaderLabels(["ID", "Nombre", "Teléfono", "Email"])
        self.tabla_clientes.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla_clientes.setSelectionBehavior(QTableWidget.SelectRows)
        grupo_lista_layout.addWidget(self.tabla_clientes)
        
        layout.addWidget(grupo_lista)
        
        # Cargar clientes existentes
        self.cargar_clientes()

    def registrar_cliente(self):
        nombre = self.input_nombre.text().strip()
        telefono = self.input_telefono.text().strip()
        email = self.input_email.text().strip()
        
        if not nombre:
            QMessageBox.warning(self, "Error", "El nombre del cliente es obligatorio.")
            return
            
        try:
            with self.engine.connect() as conn:
                with conn.begin() as trans:
                    query = text("""
                        INSERT INTO clientes (nombre_cliente, telefono, email)
                        VALUES (:nombre, :telefono, :email)
                    """)
                    conn.execute(query, {
                        "nombre": nombre,
                        "telefono": telefono,
                        "email": email
                    })
            
            QMessageBox.information(self, "Éxito", "Cliente registrado correctamente.")
            self.limpiar_formulario()
            self.cargar_clientes()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo registrar el cliente: {e}")

    def cargar_clientes(self):
        try:
            with self.engine.connect() as conn:
                query = text("SELECT id_cliente, nombre_cliente, telefono, email FROM clientes ORDER BY nombre_cliente")
                result = conn.execute(query)
                df = pd.DataFrame(result.fetchall(), columns=['id_cliente', 'nombre_cliente', 'telefono', 'email'])
                
            self.tabla_clientes.setRowCount(len(df))
            
            for i, row in df.iterrows():
                self.tabla_clientes.setItem(i, 0, QTableWidgetItem(str(row['id_cliente'])))
                self.tabla_clientes.setItem(i, 1, QTableWidgetItem(row['nombre_cliente']))
                self.tabla_clientes.setItem(i, 2, QTableWidgetItem(row['telefono']))
                self.tabla_clientes.setItem(i, 3, QTableWidgetItem(row['email']))
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los clientes: {e}")

    def eliminar_cliente(self):
        fila_seleccionada = self.tabla_clientes.currentRow()
        if fila_seleccionada == -1:
            QMessageBox.warning(self, "Error", "Por favor, seleccione un cliente para eliminar.")
            return
        
        id_cliente = self.tabla_clientes.item(fila_seleccionada, 0).text()
        nombre_cliente = self.tabla_clientes.item(fila_seleccionada, 1).text()
        
        confirmacion = QMessageBox.question(
            self, 
            "Confirmar Eliminación", 
            f"¿Está seguro de eliminar al cliente '{nombre_cliente}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirmacion == QMessageBox.Yes:
            try:
                with self.engine.connect() as conn:
                    with conn.begin() as trans:
                        query = text("DELETE FROM clientes WHERE id_cliente = :id")
                        conn.execute(query, {"id": id_cliente})
                
                QMessageBox.information(self, "Éxito", "Cliente eliminado correctamente.")
                self.cargar_clientes()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar el cliente: {e}")

    def editar_cliente(self):
        fila_seleccionada = self.tabla_clientes.currentRow()
        if fila_seleccionada == -1:
            QMessageBox.warning(self, "Error", "Por favor, seleccione un cliente para editar.")
            return
        
        id_cliente = self.tabla_clientes.item(fila_seleccionada, 0).text()
        nombre_actual = self.tabla_clientes.item(fila_seleccionada, 1).text()
        telefono_actual = self.tabla_clientes.item(fila_seleccionada, 2).text()
        email_actual = self.tabla_clientes.item(fila_seleccionada, 3).text()
        
        # Diálogo para editar
        nuevo_nombre, ok1 = QInputDialog.getText(
            self, "Editar Cliente", "Nombre:", text=nombre_actual
        )
        
        if not ok1:
            return
            
        nuevo_telefono, ok2 = QInputDialog.getText(
            self, "Editar Cliente", "Teléfono:", text=telefono_actual
        )
        
        if not ok2:
            return
            
        nuevo_email, ok3 = QInputDialog.getText(
            self, "Editar Cliente", "Email:", text=email_actual
        )
        
        if not ok3:
            return
        
        try:
            with self.engine.connect() as conn:
                with conn.begin() as trans:
                    query = text("""
                        UPDATE clientes 
                        SET nombre_cliente = :nombre, telefono = :telefono, email = :email
                        WHERE id_cliente = :id
                    """)
                    conn.execute(query, {
                        "nombre": nuevo_nombre,
                        "telefono": nuevo_telefono,
                        "email": nuevo_email,
                        "id": id_cliente
                    })
            
            QMessageBox.information(self, "Éxito", "Cliente actualizado correctamente.")
            self.cargar_clientes()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo actualizar el cliente: {e}")

    def limpiar_formulario(self):
        self.input_nombre.clear()
        self.input_telefono.clear()
        self.input_email.clear()