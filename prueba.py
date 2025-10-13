from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QApplication, QFrame
import sys

class POSDemo(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("POS Demo - Presentaciones horizontales")
        self.layout = QVBoxLayout(self)

        # Botón principal (producto)
        self.producto_boton = QPushButton("Leche")
        self.layout.addWidget(self.producto_boton)

        # Contenedor de presentaciones (oculto al inicio)
        self.presentaciones_frame = QFrame()
        self.presentaciones_layout = QHBoxLayout(self.presentaciones_frame)  # Horizontal aquí
        self.presentaciones_frame.setVisible(False)
        self.layout.addWidget(self.presentaciones_frame)

        # Crear botones de presentaciones
        presentaciones = ["500 ml", "1 L", "5 L"]
        for p in presentaciones:
            btn = QPushButton(p)
            btn.setStyleSheet("""
                background-color: #f0f0f0;
                margin: 5px;
                padding: 8px 15px;
                border-radius: 6px;
            """)
            btn.clicked.connect(lambda checked, pres=p: self.seleccionar_presentacion("Leche", pres))
            self.presentaciones_layout.addWidget(btn)

        # Conectar botón producto
        self.producto_boton.clicked.connect(self.toggle_presentaciones)

    def toggle_presentaciones(self):
        estado = not self.presentaciones_frame.isVisible()
        self.presentaciones_frame.setVisible(estado)

    def seleccionar_presentacion(self, producto, presentacion):
        print(f"✅ Seleccionaste {presentacion} de {producto}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = POSDemo()
    window.show()
    sys.exit(app.exec_())
