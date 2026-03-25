#!/bin/bash
# Genera el paquete .deb de Nivelador de volumen by tuxor

APP_NAME="niveladordevolumen"
VERSION="1.0"
REVISION="1"
PKG_NAME="${APP_NAME}_${VERSION}-${REVISION}"
BUILD_DIR="/tmp/${PKG_NAME}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=================================="
echo " Generando .deb: ${PKG_NAME}"
echo "=================================="

# Limpiar build anterior
rm -rf "$BUILD_DIR"

# Crear estructura de directorios
mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/usr/bin"
mkdir -p "$BUILD_DIR/usr/lib/${APP_NAME}"
mkdir -p "$BUILD_DIR/usr/share/applications"
mkdir -p "$BUILD_DIR/usr/share/icons/hicolor/scalable/apps"

# Copiar archivo de control
cp "$SCRIPT_DIR/debian/DEBIAN/control" "$BUILD_DIR/DEBIAN/control"

# Copiar aplicacion
cp "$SCRIPT_DIR/nivelador.py" "$BUILD_DIR/usr/lib/${APP_NAME}/nivelador.py"
chmod 755 "$BUILD_DIR/usr/lib/${APP_NAME}/nivelador.py"

# Crear launcher
cat > "$BUILD_DIR/usr/bin/${APP_NAME}" << 'EOF'
#!/bin/bash
exec python3 /usr/lib/niveladordevolumen/nivelador.py "$@"
EOF
chmod 755 "$BUILD_DIR/usr/bin/${APP_NAME}"

# Copiar .desktop e icono
cp "$SCRIPT_DIR/assets/${APP_NAME}.desktop" "$BUILD_DIR/usr/share/applications/"
cp "$SCRIPT_DIR/assets/${APP_NAME}.svg" "$BUILD_DIR/usr/share/icons/hicolor/scalable/apps/"

# Permisos
find "$BUILD_DIR" -type d -exec chmod 755 {} \;
find "$BUILD_DIR/DEBIAN" -type f -exec chmod 644 {} \;

# Generar .deb
dpkg-deb --build "$BUILD_DIR" "$SCRIPT_DIR/${PKG_NAME}.deb"

if [ $? -eq 0 ]; then
    echo ""
    echo "=================================="
    echo " .deb generado exitosamente:"
    echo " ${SCRIPT_DIR}/${PKG_NAME}.deb"
    echo ""
    echo " Para instalar:"
    echo "   sudo dpkg -i ${PKG_NAME}.deb"
    echo "   sudo apt install -f"
    echo "=================================="
else
    echo ""
    echo "ERROR: No se pudo generar el .deb"
    exit 1
fi

# Limpiar
rm -rf "$BUILD_DIR"
