/**
 * Sidebar de navegación.
 */

import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import {
  Home,
  BookOpen,
  ShoppingBag,
  Package,
  Trophy,
  TrendingUp,
  LayoutDashboard,
  Users,
  Target,
  Settings,
  AlertTriangle,
  GraduationCap,
  Clapperboard,
  BarChart2,
  Scale,
} from 'lucide-react';

interface NavItem {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

const studentNav: NavItem[] = [
  { title: 'Inicio', href: '/student/dashboard', icon: Home },
  { title: 'Practicar', href: '/student/practice', icon: BookOpen },
  { title: 'Desafíos', href: '/student/challenges', icon: Target },
  { title: 'Inventario', href: '/student/inventory', icon: Package },
  { title: 'Tienda', href: '/student/shop', icon: ShoppingBag },
  { title: 'Medallero', href: '/student/badges', icon: Trophy },
  { title: 'Progreso', href: '/student/progress', icon: TrendingUp },
  { title: 'Animaciones', href: '/student/animaciones', icon: Clapperboard },
  { title: 'Regla de Tres', href: '/student/regla-de-tres', icon: Scale },
  { title: 'Configuración', href: '/student/settings', icon: Settings },
];

const teacherNav: NavItem[] = [
  { title: 'Dashboard', href: '/teacher/dashboard', icon: LayoutDashboard },
  { title: 'Grupos', href: '/teacher/groups', icon: Users },
  { title: 'Estudiantes', href: '/teacher/students', icon: GraduationCap },
  { title: 'Estadísticas', href: '/teacher/stats', icon: BarChart2 },
  { title: 'Regla de Tres', href: '/teacher/regla-de-tres', icon: Scale },
  { title: 'Desafíos', href: '/teacher/challenges', icon: Target },
  { title: 'Alertas', href: '/teacher/alerts', icon: AlertTriangle },
  { title: 'Configuración', href: '/teacher/configuration', icon: Settings },
];

interface SidebarProps {
  userRole: 'estudiante' | 'profesor';
  isOpen?: boolean;
  onClose?: () => void;
}

export function Sidebar({ userRole, isOpen = true, onClose }: SidebarProps) {
  const location = useLocation();
  const navItems = userRole === 'estudiante' ? studentNav : teacherNav;

  return (
    <>
      {/* Overlay para móvil */}
      {isOpen && onClose && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-16 z-40 h-[calc(100vh-4rem)] w-64 border-r bg-background transition-transform md:sticky md:translate-x-0',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <nav className="space-y-2 p-4">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              location.pathname === item.href ||
              location.pathname.startsWith(item.href + '/');

            return (
              <Link
                key={item.href}
                to={item.href}
                onClick={onClose}
                className={cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                )}
              >
                <Icon className="h-5 w-5" />
                {item.title}
              </Link>
            );
          })}
        </nav>
      </aside>
    </>
  );
}
