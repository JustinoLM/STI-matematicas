#!/bin/bash

# Script de testing local para backend

echo "======================================"
echo "🧪 TESTING BACKEND - STI"
echo "======================================"
echo ""

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar que estamos en el directorio correcto
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}❌ Error: Ejecuta este script desde el directorio backend/${NC}"
    exit 1
fi

# 1. Linting
echo -e "${YELLOW}📋 Paso 1/2: Linting con Ruff...${NC}"
poetry run ruff check app/ || {
    echo -e "${RED}❌ Linting falló${NC}"
    exit 1
}
echo -e "${GREEN}✅ Linting exitoso${NC}"
echo ""

# 2. Tests
echo -e "${YELLOW}📋 Paso 2/2: Ejecutando tests con pytest...${NC}"
poetry run pytest tests/ -v --cov=app --cov-report=term-missing || {
    echo -e "${RED}❌ Tests fallaron${NC}"
    exit 1
}
echo ""

echo "======================================"
echo -e "${GREEN}✅ TODOS LOS TESTS PASARON${NC}"
echo "======================================"
