# ui/ui_inventario.py (COMPLETO Y ACTUALIZADO)

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox,
    QHeaderView, QComboBox, QPushButton, QLabel, QMenu, QAction,
    QStackedWidget, QInputDialog, QTabWidget, QSplitter
)
from PyQt5.QtCore import Qt
import pandas as pd
from PyQt5.QtCore import QTimer
import traceback

from sqlalchemy import text

from ui.ui_panel_derecho import PanelDerecho
from ui.ui_panel_inferior import PanelInferiorRedisenado
from .ui_pos import POSWindow
from .ui_panel_ventas import PanelVentas
from .ui_panel_fondo import PanelFondo

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
        
        # --- Pestaña 4: Gestión de Inventario y Ventas (Original) ---
        self.tab_inventario_ventas = QWidget()
        self.tabs.addTab(self.tab_inventario_ventas, "Inventario")
        
        # Usar un splitter horizontal para dividir esta pestaña
        splitter = QSplitter(Qt.Horizontal)
        tab_inventario_layout = QHBoxLayout(self.tab_inventario_ventas)
        tab_inventario_layout.addWidget(splitter)
        
        # Panel izquierdo: Registro de clientes
        #self.registro_clientes = RegistroClientesWidget(self.engine)
        #splitter.addWidget(self.registro_clientes)
        
        # Panel derecho: Gestión de inventario, producción y ventas
        self.panel_derecho = PanelDerecho(self.engine, self.panel_inferior.registrar_produccion_con_costo)
        splitter.addWidget(self.panel_derecho)
        
        # Configurar proporciones del splitter
        splitter.setSizes([300, 700])


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
        
        # 1. Crear el QStackedWidget PRIMERO
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # 2. Crear las instancias de los modos
        self.pos_widget = POSWindow(self.engine)
        self.admin_widget = AdminWidget(self.engine)
        
        # 3. Añadir los widgets al stack AHORA que ya existe
        self.stacked_widget.addWidget(self.pos_widget)
        self.stacked_widget.addWidget(self.admin_widget)
        
        self._crear_menu_principal()
        
        # Iniciar en el modo de ventas (POS)
        self._cambiar_modo(0)

        
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
            except Exception as e:
                print(f"Error al cargar datos iniciales: {e}")