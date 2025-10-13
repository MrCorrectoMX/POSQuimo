# ui/ui_registro_clientes.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QGroupBox
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
        
        form_layout.addWidget(QLabel("Nombre:"))
        form_layout.addWidget(self.input_nombre)
        form_layout.addWidget(QLabel("Teléfono:"))
        form_layout.addWidget(self.input_telefono)
        
        btn_registrar = QPushButton("Registrar")
        btn_registrar.clicked.connect(self.registrar_cliente)
        form_layout.addWidget(btn_registrar)
        
        grupo_layout.addLayout(form_layout)
        layout.addWidget(grupo_registro)
        
        # Grupo de lista de clientes
        grupo_lista = QGroupBox("Clientes Registrados")
        grupo_lista_layout = QVBoxLayout(grupo_lista)
        
        self.tabla_clientes = QTableWidget()
        self.tabla_clientes.setColumnCount(3)
        self.tabla_clientes.setHorizontalHeaderLabels(["ID", "Nombre", "Teléfono"])
        self.tabla_clientes.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        grupo_lista_layout.addWidget(self.tabla_clientes)
        
        layout.addWidget(grupo_lista)
        
        # Cargar clientes existentes
        self.cargar_clientes()

    def registrar_cliente(self):
        nombre = self.input_nombre.text().strip()
        telefono = self.input_telefono.text().strip()
        
        if not nombre:
            QMessageBox.warning(self, "Error", "El nombre del cliente es obligatorio.")
            return
            
        try:
            with self.engine.connect() as conn:
                with conn.begin() as trans:
                    query = text("""
                        INSERT INTO clientes (nombre, telefono)
                        VALUES (:nombre, :telefono)
                    """)
                    conn.execute(query, {
                        "nombre": nombre,
                        "telefono": telefono
                    })
            
            QMessageBox.information(self, "Éxito", "Cliente registrado correctamente.")
            self.limpiar_formulario()
            self.cargar_clientes()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo registrar el cliente: {e}")

    def limpiar_formulario(self):
        self.input_nombre.clear()
        self.input_telefono.clear()

    def cargar_clientes(self):
        try:
            with self.engine.connect() as conn:
                query = text("SELECT id_cliente, nombre, telefono FROM clientes ORDER BY nombre")
                df = pd.read_sql_query(query, conn)
                
            self.tabla_clientes.setRowCount(len(df))
            
            for i, row in df.iterrows():
                self.tabla_clientes.setItem(i, 0, QTableWidgetItem(str(row['id_cliente'])))
                self.tabla_clientes.setItem(i, 1, QTableWidgetItem(row['nombre']))
                self.tabla_clientes.setItem(i, 2, QTableWidgetItem(row['telefono']))
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los clientes: {e}")