/**
 * Header principal de la aplicación.
 */

import { User, LogOut, Menu, Users, GraduationCap, School } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { studentService } from '@/services/studentService';
import { teacherService } from '@/services/teacherService';
import { useThemeStore } from '@/store/themeStore';

/** Emoji de cada tema narrativo. */
const TEMA_EMOJI: Record<string, string> = {
  'tema-default':      '📐',
  'tema-piratas':      '🏴‍☠️',
  'tema-astronautas':  '🚀',
  'tema-magos':        '🧙',
  'tema-caballeros':   '⚔️',
  'tema-vaqueros':     '🤠',
  'tema-princesas':    '👑',
};

interface HeaderProps {
  userName: string;
  userRole: 'estudiante' | 'profesor';
  onLogout: () => void;
  onMenuToggle?: () => void;
}

export function Header({ userName, userRole, onLogout, onMenuToggle }: HeaderProps) {
  const temaActivoId = useThemeStore(s => s.temaActivoId);
  const emoji = userRole === 'estudiante'
    ? (TEMA_EMOJI[temaActivoId] ?? '📐')
    : '🎓';

  const { data: perfil } = useQuery({
    queryKey: ['perfil-estudiante'],
    queryFn: () => studentService.getPerfil(),
    enabled: userRole === 'estudiante',
    staleTime: 5 * 60 * 1000,
  });

  const { data: perfilProfesor } = useQuery({
    queryKey: ['perfil-profesor'],
    queryFn: () => teacherService.getPerfilProfesor(),
    enabled: userRole === 'profesor',
    staleTime: 10 * 60 * 1000,
  });

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between px-4">
        {/* Left: Logo + Menu Toggle */}
        <div className="flex items-center gap-4">
          {onMenuToggle && (
            <Button
              variant="ghost"
              size="icon"
              onClick={onMenuToggle}
              className="md:hidden"
            >
              <Menu className="h-5 w-5" />
            </Button>
          )}
          <div className="flex items-center gap-2">
            <span className="text-2xl leading-none select-none" role="img">{emoji}</span>
            <span className="font-bold text-lg">STI Matemáticas</span>
          </div>
        </div>

        {/* Right: Grupo/Profesor info + User Info + Logout */}
        <div className="flex items-center gap-4">
          {/* Grupo y Profesor (solo estudiantes) */}
          {userRole === 'estudiante' && (perfil?.grupo_nombre || perfil?.profesor_nombre) && (
            <div className="hidden md:flex items-center gap-3 text-sm text-muted-foreground border-r pr-4">
              {perfil.grupo_nombre && (
                <div className="flex items-center gap-1">
                  <Users className="h-4 w-4" />
                  <span>{perfil.grupo_nombre}</span>
                </div>
              )}
              {perfil.profesor_nombre && (
                <div className="flex items-center gap-1">
                  <GraduationCap className="h-4 w-4" />
                  <span>{perfil.profesor_nombre}</span>
                </div>
              )}
            </div>
          )}

          {/* Organización (solo profesores) */}
          {userRole === 'profesor' && perfilProfesor?.organizacion_nombre && (
            <div className="hidden md:flex items-center gap-1 text-sm text-muted-foreground border-r pr-4">
              <School className="h-4 w-4" />
              <span>{perfilProfesor.organizacion_nombre}</span>
            </div>
          )}

          <div className="flex items-center gap-2">
            <User className="h-5 w-5 text-muted-foreground" />
            <div className="hidden sm:block">
              <p className="text-sm font-medium">{userName}</p>
              <p className="text-xs text-muted-foreground capitalize">{userRole}</p>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={onLogout}>
            <LogOut className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </header>
  );
}
