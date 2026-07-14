import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { ProtectedRoute } from '@/components/routing/ProtectedRoute'

function renderRuta(
  isAuthenticated: boolean,
  userRole?: 'estudiante' | 'profesor',
  requiredRole?: 'estudiante' | 'profesor',
) {
  return render(
    <MemoryRouter initialEntries={['/ruta-protegida']}>
      <Routes>
        <Route
          path="/ruta-protegida"
          element={
            <ProtectedRoute
              isAuthenticated={isAuthenticated}
              userRole={userRole}
              requiredRole={requiredRole}
            >
              <div data-testid="contenido-protegido">Contenido privado</div>
            </ProtectedRoute>
          }
        />
        <Route path="/login" element={<div data-testid="pagina-login">Login</div>} />
        <Route path="/student/dashboard" element={<div data-testid="dashboard-estudiante">Dashboard estudiante</div>} />
        <Route path="/teacher/dashboard" element={<div data-testid="dashboard-profesor">Dashboard profesor</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ProtectedRoute', () => {
  it('sin autenticación redirige a /login y no muestra el contenido', () => {
    renderRuta(false)
    expect(screen.getByTestId('pagina-login')).toBeInTheDocument()
    expect(screen.queryByTestId('contenido-protegido')).not.toBeInTheDocument()
  })

  it('profesor intenta acceder a ruta de estudiante → redirige a /teacher/dashboard', () => {
    renderRuta(true, 'profesor', 'estudiante')
    expect(screen.getByTestId('dashboard-profesor')).toBeInTheDocument()
    expect(screen.queryByTestId('contenido-protegido')).not.toBeInTheDocument()
  })

  it('estudiante intenta acceder a ruta de profesor → redirige a /student/dashboard', () => {
    renderRuta(true, 'estudiante', 'profesor')
    expect(screen.getByTestId('dashboard-estudiante')).toBeInTheDocument()
    expect(screen.queryByTestId('contenido-protegido')).not.toBeInTheDocument()
  })

  it('rol correcto → muestra el contenido protegido', () => {
    renderRuta(true, 'estudiante', 'estudiante')
    expect(screen.getByTestId('contenido-protegido')).toBeInTheDocument()
  })

  it('autenticado sin requiredRole → acceso permitido sin importar el rol', () => {
    renderRuta(true, 'profesor', undefined)
    expect(screen.getByTestId('contenido-protegido')).toBeInTheDocument()
  })
})
