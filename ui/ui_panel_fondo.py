# ui/ui_panel_fondo.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QMessageBox, QGroupBox, QLineEdit, QComboBox,
    QDateEdit, QDoubleSpinBox
)
from PyQt5.QtCore import Qt, QDate
import pandas as pd
from sqlalchemy import text

class PanelFondo(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        
        layout = QVBoxLayout(self)
        
        # --- Saldo Actual ---
        saldo_group = QGroupBox("Saldo Actual")
        saldo_layout = QHBoxLayout(saldo_group)
        self.label_saldo = QLabel("Cargando...")
        self.label_saldo.setStyleSheet("font-size: 24px; font-weight: bold; color: #2ecc71;")
        saldo_layout.addWidget(QLabel("Saldo Disponible:"))
        saldo_layout.addWidget(self.label_saldo)
        saldo_layout.addStretch()
        
        btn_actualizar = QPushButton("🔄 Actualizar")
        btn_actualizar.clicked.connect(self.actualizar_saldo)
        saldo_layout.addWidget(btn_actualizar)
        layout.addWidget(saldo_group)
        
        # --- Movimientos ---
        movimientos_group = QGroupBox("Movimientos de Fondos")
        movimientos_layout = QVBoxLayout(movimientos_group)
        
        # Filtros
        filtros_layout = QHBoxLayout()
        filtros_layout.addWidget(QLabel("Desde:"))
        self.date_desde = QDateEdit()
        self.date_desde.setDate(QDate.currentDate().addDays(-30))
        filtros_layout.addWidget(self.date_desde)
        
        filtros_layout.addWidget(QLabel("Hasta:"))
        self.date_hasta = QDateEdit()
        self.date_hasta.setDate(QDate.currentDate())
        filtros_layout.addWidget(self.date_hasta)
        
        self.btn_filtrar = QPushButton("Filtrar")
        self.btn_filtrar.clicked.connect(self.cargar_movimientos)
        filtros_layout.addWidget(self.btn_filtrar)
        filtros_layout.addStretch()
        movimientos_layout.addLayout(filtros_layout)
        
        # Tabla de movimientos
        self.tabla_movimientos = QTableWidget()
        self.tabla_movimientos.setColumnCount(6)
        self.tabla_movimientos.setHorizontalHeaderLabels([
            "Fecha", "Tipo", "Concepto", "Monto", "Saldo", "Acciones"
        ])
        movimientos_layout.addWidget(self.tabla_movimientos)
        layout.addWidget(movimientos_group)
        
        # --- Agregar Movimiento Manual ---
        agregar_group = QGroupBox("Agregar Movimiento Manual")
        agregar_layout = QHBoxLayout(agregar_group)
        
        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(["INGRESO", "EGRESO"])
        
        self.input_concepto = QLineEdit(placeholderText="Concepto del movimiento")
        self.input_monto = QDoubleSpinBox()
        self.input_monto.setMaximum(1000000)
        self.input_monto.setPrefix("$ ")
        
        btn_agregar = QPushButton("Agregar Movimiento")
        btn_agregar.clicked.connect(self.agregar_movimiento_manual)
        
        agregar_layout.addWidget(QLabel("Tipo:"))
        agregar_layout.addWidget(self.combo_tipo)
        agregar_layout.addWidget(QLabel("Concepto:"))
        agregar_layout.addWidget(self.input_concepto)
        agregar_layout.addWidget(QLabel("Monto:"))
        agregar_layout.addWidget(self.input_monto)
        agregar_layout.addWidget(btn_agregar)
        layout.addWidget(agregar_group)
        
        # Cargar datos iniciales
        self.actualizar_saldo()
        self.cargar_movimientos()

    def actualizar_saldo(self):
        """Actualiza el saldo actual mostrado"""
        try:
            with self.engine.connect() as conn:
                query = text("SELECT saldo FROM fondo ORDER BY id_movimiento DESC LIMIT 1")
                result = conn.execute(query).scalar()
                saldo = result if result is not None else 0
                self.label_saldo.setText(f"${saldo:,.2f}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar el saldo: {e}")

    def cargar_movimientos(self):
        """Carga los movimientos del fondo"""
        try:
            fecha_desde = self.date_desde.date().toPyDate()
            fecha_hasta = self.date_hasta.date().toPyDate()
            
            with self.engine.connect() as conn:
                query = text("""
                    SELECT id_movimiento, fecha, tipo, concepto, monto, saldo
                    FROM fondo 
                    WHERE fecha BETWEEN :start_date AND :end_date
                    ORDER BY fecha DESC, id_movimiento DESC
                """)
                movimientos = conn.execute(query, {
                    "start_date": fecha_desde, "end_date": fecha_hasta
                }).fetchall()
                
                self.tabla_movimientos.setRowCount(len(movimientos))
                for i, row in enumerate(movimientos):
                    color = "#2ecc71" if row.tipo == "INGRESO" else "#e74c3c"
                    
                    self.tabla_movimientos.setItem(i, 0, QTableWidgetItem(str(row.fecha)))
                    self.tabla_movimientos.setItem(i, 1, QTableWidgetItem(row.tipo))
                    self.tabla_movimientos.setItem(i, 2, QTableWidgetItem(row.concepto))
                    
                    monto_item = QTableWidgetItem(f"${row.monto:,.2f}")
                    monto_item.setForeground(Qt.green if row.tipo == "INGRESO" else Qt.red)
                    self.tabla_movimientos.setItem(i, 3, monto_item)
                    
                    self.tabla_movimientos.setItem(i, 4, QTableWidgetItem(f"${row.saldo:,.2f}"))
                    
                    # Botón eliminar
                    btn_eliminar = QPushButton("Eliminar")
                    btn_eliminar.clicked.connect(lambda checked, id=row.id_movimiento: self.eliminar_movimiento(id))
                    self.tabla_movimientos.setCellWidget(i, 5, btn_eliminar)
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los movimientos: {e}")

    def agregar_movimiento_manual(self):
        """Agrega un movimiento manual al fondo"""
        tipo = self.combo_tipo.currentText()
        concepto = self.input_concepto.text().strip()
        monto = self.input_monto.value()
        
        if not concepto:
            QMessageBox.warning(self, "Error", "El concepto es obligatorio.")
            return
            
        if monto <= 0:
            QMessageBox.warning(self, "Error", "El monto debe ser mayor a 0.")
            return

        try:
            with self.engine.connect() as conn:
                with conn.begin() as trans:
                    # Calcular nuevo saldo
                    query_ultimo_saldo = text("SELECT saldo FROM fondo ORDER BY id_movimiento DESC LIMIT 1")
                    ultimo_saldo = conn.execute(query_ultimo_saldo).scalar() or 0
                    
                    nuevo_saldo = ultimo_saldo + monto if tipo == "INGRESO" else ultimo_saldo - monto
                    
                    # Insertar movimiento
                    query_insert = text("""
                        INSERT INTO fondo (fecha, tipo, concepto, monto, saldo)
                        VALUES (DATE('now'), :tipo, :concepto, :monto, :saldo)
                    """)
                    conn.execute(query_insert, {
                        "tipo": tipo, 
                        "concepto": concepto, 
                        "monto": monto, 
                        "saldo": nuevo_saldo
                    })
            
            QMessageBox.information(self, "Éxito", "Movimiento agregado correctamente.")
            self.limpiar_formulario()
            self.actualizar_saldo()
            self.cargar_movimientos()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo agregar el movimiento: {e}")

    def eliminar_movimiento(self, movimiento_id):
        """Elimina un movimiento del fondo (solo para admin)"""
        confirm = QMessageBox.question(self, "Confirmar", 
                                      "¿Está seguro de eliminar este movimiento?\nEsta acción no se puede deshacer.",
                                      QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.No:
            return
            
        try:
            with self.engine.connect() as conn:
                with conn.begin() as trans:
                    # Obtener el movimiento a eliminar
                    query_mov = text("SELECT tipo, monto FROM fondo WHERE id_movimiento = :id")
                    mov = conn.execute(query_mov, {"id": movimiento_id}).fetchone()
                    
                    # Eliminar movimiento
                    query_delete = text("DELETE FROM fondo WHERE id_movimiento = :id")
                    conn.execute(query_delete, {"id": movimiento_id})
                    
                    # Recalcular saldos de movimientos posteriores
                    query_recalcular = text("""
                        UPDATE fondo 
                        SET saldo = saldo - :ajuste 
                        WHERE id_movimiento > :id
                    """)
                    ajuste = -mov.monto if mov.tipo == "INGRESO" else mov.monto
                    conn.execute(query_recalcular, {"ajuste": ajuste, "id": movimiento_id})
            
            QMessageBox.information(self, "Éxito", "Movimiento eliminado correctamente.")
            self.actualizar_saldo()
            self.cargar_movimientos()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo eliminar el movimiento: {e}")

    def limpiar_formulario(self):
        """Limpia el formulario de movimiento manual"""
        self.input_concepto.clear()
        self.input_monto.setValue(0)