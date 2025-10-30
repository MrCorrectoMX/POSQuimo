#!/bin/bash
echo "==============================================="
echo "   QUIMO POS - EJECUTAR APLICACIÓN"
echo "==============================================="
echo ""
echo "¡Felicidades! Estás a punto de ejecutar QuimoPOS."
echo "Esta aplicación fue desarrollada después de 5 meses de trabajo."
echo ""
echo "Asegúrate de tener:"
echo "1. PostgreSQL instalado"
echo "2. Base de datos 'quimo_bd_new' creada"  
echo "3. Servidor PostgreSQL ejecutándose"
echo ""
echo "Iniciando QuimoPOS..."
chmod +x ./QuimoPOS
./QuimoPOS
