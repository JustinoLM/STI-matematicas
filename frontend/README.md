# Frontend - STI (Sistema de Tutoría Inteligente)

![React](https://img.shields.io/badge/React-18.2-61DAFB.svg)
![TypeScript](https://img.shields.io/badge/TypeScript-5.2-3178C6.svg)
![Vite](https://img.shields.io/badge/Vite-5.0-646CFF.svg)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.3-38B2AC.svg)

Interfaz de usuario construida con React + TypeScript + TailwindCSS.

## Arquitectura por Componentes
```
src/
├── components/       # Componentes reutilizables
├── pages/            # Páginas/vistas
├── hooks/            # Custom React hooks
├── services/         # API clients
├── store/            # Estado global (Zustand)
├── types/            # TypeScript interfaces
└── utils/            # Funciones auxiliares
```

## Inicio Rápido

### 1. Instalar pnpm
```bash
npm install -g pnpm
```

### 2. Instalar dependencias
```bash
cd frontend
pnpm install
```

### 3. Configurar variables de entorno
```bash
cp .env.example .env
# Editar .env con la URL de tu backend
```

### 4. Iniciar servidor de desarrollo
```bash
pnpm dev
```

La aplicación estará disponible en: http://localhost:5173

## TailwindCSS y Narrativas

El proyecto usa TailwindCSS con colores personalizables por narrativa:
```css
:root {
  --color-primary: #3b82f6;
  --color-secondary: #8b5cf6;
  --color-accent: #f59e0b;
}
```

Las narrativas disponibles son:
- Piratas
- Astronautas
- Magos
- Caballeros
- Cowboys
- Princesas Inventoras

### Breakpoints Tablet-First
```
xs:  480px   (Móviles grandes)
sm:  768px   (Tablets pequeñas)  ← Base de diseño
md:  1024px  (Tablets grandes)
lg:  1280px  (Laptops)
xl:  1920px  (Desktops)
```

## Testing
```bash
# Ejecutar tests
pnpm test

# Con UI
pnpm test:ui
```

## Linting
```bash
# Lint
pnpm lint

# Auto-fix
pnpm lint --fix
```

## Build para Producción
```bash
# Build
pnpm build

# Preview del build
pnpm preview
```

## Path Aliases
```typescript
// Evitar
import Button from '../../../components/ui/Button'

// Usar
import Button from '@components/ui/Button'
```

Aliases disponibles:
- `@/*` → `src/*`
- `@components/*` → `src/components/*`
- `@pages/*` → `src/pages/*`
- `@services/*` → `src/services/*`
- `@types/*` → `src/types/*`

## Deployment

### Vercel
```bash
vercel --prod
```

Variables de entorno en Vercel:
- `VITE_API_BASE_URL`: URL del backend en producción

## Licencia

Proyecto académico - Tesis de grado
