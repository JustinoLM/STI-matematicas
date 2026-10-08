#!/bin/bash

# Script de testing local para frontend

echo "======================================"
echo "🧪 TESTING FRONTEND - STI"
echo "======================================"
echo ""

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar que estamos en el directorio correcto
if [ ! -f "package.json" ]; then
    echo -e "${RED}❌ Error: Ejecuta este script desde el directorio frontend/${NC}"
    exit 1
fi

# 1. Linting
echo -e "${YELLOW}📋 Paso 1/3: Linting con ESLint...${NC}"
npm run lint || {
    echo -e "${RED}❌ Linting falló${NC}"
    exit 1
}
echo -e "${GREEN}✅ Linting exitoso${NC}"
echo ""

# 2. Tests
echo -e "${YELLOW}📋 Paso 2/3: Ejecutando tests con Vitest...${NC}"
npm test -- --run || {
    echo -e "${RED}❌ Tests fallaron${NC}"
    exit 1
}
echo -e "${GREEN}✅ Tests exitosos${NC}"
echo ""

# 3. Build
echo -e "${YELLOW}📋 Paso 3/3: Build de producción...${NC}"
npm run build || {
    echo -e "${RED}❌ Build falló${NC}"
    exit 1
}
echo -e "${GREEN}✅ Build exitoso${NC}"
echo ""

echo "======================================"
echo -e "${GREEN}✅ TODOS LOS TESTS PASARON${NC}"
echo "======================================"
