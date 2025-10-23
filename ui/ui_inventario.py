# ui/ui_inventario.py (COMPLETO Y ACTUALIZADO)

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox,
    QHeaderView, QComboBox, QPushButton, QLabel, QMenu, QAction,
    QStackedWidget, QInputDialog, QTabWidget, QSplitter, QDialog
)
from PyQt5.QtCore import Qt, QTimer
import pandas as pd
import traceback

from sqlalchemy import text

from ui.ui_panel_derecho import PanelDerecho
from ui.ui_panel_inferior import PanelInferiorRedisenado
from .ui_pos import POSWindow
from .ui_panel_ventas import PanelVentas
from .ui_panel_fondo import PanelFondo
from .ui_registro_clientes import RegistroClientesWidget

import sys
import os

def get_project_root():
    """
    Obtiene la ruta raíz del proyecto de forma fiable, tanto en
    desarrollo como en la aplicación empaquetada (.exe).
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


class AdminWidget(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        
        # Usamos un splitter para dividir la interfaz
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Crear un tab widget para las secciones principales
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # --- Pestaña 1: Gestión de Producción ---
        self.tab_produccion = QWidget()
        self.tabs.addTab(self.tab_produccion, "Producción")
        
        # Solo el panel inferior en esta pestaña
        tab_produccion_layout = QVBoxLayout(self.tab_produccion)
        self.panel_inferior = PanelInferiorRedisenado(self.engine)
        tab_produccion_layout.addWidget(self.panel_inferior)
        
        # --- Pestaña 2: Panel de Ventas ---
        self.tab_ventas = QWidget()
        self.tabs.addTab(self.tab_ventas, "Ventas")
        
        tab_ventas_layout = QVBoxLayout(self.tab_ventas)
        self.panel_ventas = PanelVentas(self.engine)
        tab_ventas_layout.addWidget(self.panel_ventas)
        
        # --- Pestaña 3: Gestión de Fondos ---
        self.tab_fondos = QWidget()
        self.tabs.addTab(self.tab_fondos, "Fondos")
        
        tab_fondos_layout = QVBoxLayout(self.tab_fondos)
        self.panel_fondos = PanelFondo(self.engine)
        tab_fondos_layout.addWidget(self.panel_fondos)
        
        # --- Pestaña 4: Gestión de Clientes (NUEVA PESTAÑA) ---
        self.tab_clientes = QWidget()
        self.tabs.addTab(self.tab_clientes, "Clientes")
        
        tab_clientes_layout = QVBoxLayout(self.tab_clientes)
        self.registro_clientes = RegistroClientesWidget(self.engine)
        tab_clientes_layout.addWidget(self.registro_clientes)
        
        # --- Pestaña 5: Gestión de Inventario y Ventas (Original) ---
        self.tab_inventario_ventas = QWidget()
        self.tabs.addTab(self.tab_inventario_ventas, "Inventario")
        
        # Usar un splitter horizontal para dividir esta pestaña
        splitter = QSplitter(Qt.Horizontal)
        tab_inventario_layout = QHBoxLayout(self.tab_inventario_ventas)
        tab_inventario_layout.addWidget(splitter)
        
        # Panel derecho: Gestión de inventario, producción y ventas
        self.panel_derecho = PanelDerecho(self.engine, self.panel_inferior.registrar_produccion_con_costo)
        splitter.addWidget(self.panel_derecho)
        
        # Configurar proporciones del splitter
        splitter.setSizes([700])  # Solo un panel ahora


class InventarioApp(QMainWindow):
    def __init__(self):
        from sqlalchemy import create_engine
        
        super().__init__()
        self.setWindowTitle("Sistema de Inventario - QUIMO")
        self.setMinimumSize(1200, 800)
        
        # Conexión a la base de datos
        db_path = os.path.join(get_project_root(), 'quimo.db')
        print(f"DEBUG: Conectando a la base de datos en: {db_path}")
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        
        # Variable para almacenar la tasa de cambio actual
        self.tasa_cambio_actual = self.obtener_tasa_cambio_guardada()
        
        # 1. Crear el QStackedWidget PRIMERO
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # 2. Crear las instancias de los modos
        self.pos_widget = POSWindow(self.engine)
        self.admin_widget = AdminWidget(self.engine)  # Ahora AdminWidget está definido antes
        
        # 3. Añadir los widgets al stack AHORA que ya existe
        self.stacked_widget.addWidget(self.pos_widget)
        self.stacked_widget.addWidget(self.admin_widget)
        
        self._crear_menu_principal()
        
        # Iniciar en el modo de ventas (POS)
        self._cambiar_modo(0)
        
        # Mostrar popup de tasa de cambio después de que la ventana esté lista
        QTimer.singleShot(500, self.mostrar_popup_tasa_cambio)

    def obtener_tasa_cambio_guardada(self):
        """Intenta obtener la última tasa de cambio guardada en la base de datos"""
        try:
            with self.engine.connect() as conn:
                # Buscar en una tabla de configuración o en la última materia prima en USD
                query = text("""
                    SELECT tasa_cambio FROM configuracion 
                    WHERE clave = 'tasa_cambio_usd' 
                    ORDER BY fecha_actualizacion DESC 
                    LIMIT 1
                """)
                result = conn.execute(query).fetchone()
                if result:
                    return float(result[0])
        except:
            pass
        
        # Valor por defecto si no hay tasa guardada
        return 20.0

    def guardar_tasa_cambio(self, tasa):
        """Guarda la tasa de cambio en la base de datos para futuras sesiones"""
        try:
            with self.engine.begin() as conn:
                # Crear tabla de configuración si no existe
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS configuracion (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        clave TEXT UNIQUE,
                        valor TEXT,
                        fecha_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Insertar o actualizar la tasa
                conn.execute(text("""
                    INSERT OR REPLACE INTO configuracion (clave, valor)
                    VALUES ('tasa_cambio_usd', :tasa)
                """), {"tasa": str(tasa)})
        except Exception as e:
            print(f"Error al guardar tasa de cambio: {e}")

    def mostrar_popup_tasa_cambio(self):
        """Muestra el popup para confirmar la tasa de cambio del dólar"""
        from PyQt5.QtWidgets import QInputDialog
        
        tasa, ok = QInputDialog.getDouble(
            self,
            "Tasa de Cambio USD/MXN",
            "Por favor, ingrese la tasa de cambio actual del dólar:\n\n"
            "¿A cuántos pesos mexicanos equivale 1 dólar americano (USD)?",
            value=self.tasa_cambio_actual,
            min=1.0,
            max=100.0,
            decimals=2
        )
        
        if ok:
            self.tasa_cambio_actual = tasa
            self.guardar_tasa_cambio(tasa)
            
            QMessageBox.information(
                self,
                "Tasa de Cambio Actualizada",
                f"Tasa de cambio establecida:\n\n"
                f"1 USD = ${tasa:.2f} MXN\n\n"
                f"Esta tasa se usará para convertir automáticamente\n"
                f"todas las materias primas en dólares a pesos mexicanos."
            )
        else:
            # Si el usuario cancela, usar la tasa guardada o por defecto
            QMessageBox.information(
                self,
                "Tasa de Cambio",
                f"ℹSe usará la tasa de cambio guardada:\n\n"
                f"1 USD = ${self.tasa_cambio_actual:.2f} MXN\n\n"
                f"Puede actualizarla luego en el menú de Configuración."
            )

    def actualizar_tasa_cambio_desde_menu(self):
        """Permite actualizar la tasa de cambio desde el menú"""
        from PyQt5.QtWidgets import QInputDialog
        
        tasa, ok = QInputDialog.getDouble(
            self,
            "💰 Actualizar Tasa de Cambio USD/MXN",
            "Ingrese la nueva tasa de cambio actual:\n\n"
            "¿A cuántos pesos mexicanos equivale 1 dólar americano (USD)?",
            value=self.tasa_cambio_actual,
            min=1.0,
            max=100.0,
            decimals=2
        )
        
        if ok:
            self.tasa_cambio_actual = tasa
            self.guardar_tasa_cambio(tasa)
            
            QMessageBox.information(
                self,
                "Tasa de Cambio Actualizada",
                f" Tasa de cambio actualizada:\n\n"
                f"1 USD = ${tasa:.2f} MXN\n\n"
                f"Esta tasa se usará para todas las conversiones futuras."
            )

    def _crear_menu_principal(self):
        """Crea la barra de menú para cambiar entre modos."""
        menu_bar = self.menuBar()
        menu_ver = menu_bar.addMenu("&Ver")

        accion_modo_venta = QAction("Modo Venta (POS)", self)
        accion_modo_venta.triggered.connect(lambda: self._cambiar_modo(0))
        menu_ver.addAction(accion_modo_venta)

        accion_modo_admin = QAction("Modo Administración", self)
        accion_modo_admin.triggered.connect(lambda: self._cambiar_modo(1))
        menu_ver.addAction(accion_modo_admin)

        # Añadir menú de configuración
        menu_config = menu_bar.addMenu("&Configuración")
        
        accion_tasa_cambio = QAction("Actualizar Tasa de Cambio USD/MXN", self)
        accion_tasa_cambio.triggered.connect(self.actualizar_tasa_cambio_desde_menu)
        menu_config.addAction(accion_tasa_cambio)

    def _cambiar_modo(self, index):
        """Cambia la vista activa en el QStackedWidget."""
        self.stacked_widget.setCurrentIndex(index)
        if index == 1:  # Si cambiamos al modo admin
            # Cargar datos iniciales en todos los paneles
            try:
                self.admin_widget.panel_inferior.cargar_datos_desde_db()
                self.admin_widget.panel_ventas.cargar_ventas_desde_db()
                self.admin_widget.panel_fondos.actualizar_saldo()
                self.admin_widget.panel_fondos.cargar_movimientos()
                # AÑADIR: Cargar clientes cuando se cambie al modo admin
                self.admin_widget.registro_clientes.cargar_clientes()
            except Exception as e:
                print(f"Error al cargar datos iniciales: {e}")