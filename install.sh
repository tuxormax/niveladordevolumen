#!/bin/bash
# Instalador de Nivelador de volumen by tuxor
# Instala todas las dependencias necesarias

echo "=================================="
echo " Nivelador de volumen by tuxor"
echo " Instalador de dependencias"
echo "=================================="
echo ""

# Verificar que se ejecute con permisos de root
if [ "$EUID" -ne 0 ]; then
    echo "Este script necesita permisos de administrador."
    echo "Ejecutar con: sudo bash install.sh"
    exit 1
fi

echo "[1/3] Actualizando lista de paquetes..."
apt update -y

echo ""
echo "[2/3] Instalando dependencias del sistema..."
apt install -y mp3gain python3 python3-pyqt5

echo ""
echo "[3/3] Verificando instalacion..."

# Verificar mp3gain
if command -v mp3gain &> /dev/null; then
    MP3GAIN_VER=$(mp3gain -v 2>&1 | grep -oP '\d+\.\d+\.\d+' || echo "OK")
    echo "  mp3gain:      v$MP3GAIN_VER"
else
    echo "  mp3gain:      ERROR - no se instalo"
fi

# Verificar Python3
if command -v python3 &> /dev/null; then
    PY_VER=$(python3 --version 2>&1)
    echo "  python3:      $PY_VER"
else
    echo "  python3:      ERROR - no se instalo"
fi

# Verificar PyQt5
if python3 -c "import PyQt5" 2>/dev/null; then
    echo "  PyQt5:        OK"
else
    echo "  PyQt5:        ERROR - no se instalo"
fi

echo ""
echo "=================================="
echo " Instalacion completada"
echo ""
echo " Para ejecutar:"
echo "   python3 nivelador.py"
echo "=================================="
