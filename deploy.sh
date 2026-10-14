#!/bin/bash

# Script maestro de deployment manual.
# NOTA: es el script de la validación. Usa las CLI de Railway y Vercel; esa infraestructura se dio
# de baja, por lo que solo funciona si se vuelven a configurar esas cuentas.

echo "=========================================="
echo "🚀 DEPLOYMENT MANUAL - STI"
echo "=========================================="
echo ""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Función para preguntar confirmación
confirm() {
    read -p "$1 (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}❌ Cancelado${NC}"
        exit 1
    fi
}

# 1. Tests Backend
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}📋 Paso 1/5: Testing Backend${NC}"
echo -e "${BLUE}========================================${NC}"
cd backend
./test.sh || {
    echo -e "${RED}❌ Tests de backend fallaron. Fix y vuelve a intentar.${NC}"
    exit 1
}
cd ..
echo ""

# 2. Tests Frontend
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}📋 Paso 2/5: Testing Frontend${NC}"
echo -e "${BLUE}========================================${NC}"
cd frontend
./test.sh || {
    echo -e "${RED}❌ Tests de frontend fallaron. Fix y vuelve a intentar.${NC}"
    exit 1
}
cd ..
echo ""

# 3. Confirmación
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}📋 Paso 3/5: Confirmación${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}⚠️  Vas a desplegar a PRODUCCIÓN${NC}"
confirm "¿Estás seguro de continuar?"
echo ""

# 4. Deploy Backend
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}📋 Paso 4/5: Deploy Backend a Railway${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}Ejecutando: railway up${NC}"
cd backend
railway up || {
    echo -e "${RED}❌ Deploy de backend falló${NC}"
    exit 1
}
cd ..
echo -e "${GREEN}✅ Backend desplegado${NC}"
echo ""

# 5. Deploy Frontend
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}📋 Paso 5/5: Deploy Frontend a Vercel${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}Ejecutando: vercel --prod${NC}"
cd frontend
vercel --prod || {
    echo -e "${RED}❌ Deploy de frontend falló${NC}"
    exit 1
}
cd ..
echo -e "${GREEN}✅ Frontend desplegado${NC}"
echo ""

# Resumen
echo "=========================================="
echo -e "${GREEN}✅ DEPLOYMENT COMPLETO${NC}"
echo "=========================================="
echo ""
echo "🔗 URLs: las que muestren Railway y Vercel al terminar el despliegue."
echo ""
echo "📝 Próximos pasos:"
echo "  1. Verificar health check: curl <URL del backend>/health"
echo "  2. Probar frontend en navegador"
echo "  3. Verificar logs: railway logs (backend) y vercel logs (frontend)"
echo ""
