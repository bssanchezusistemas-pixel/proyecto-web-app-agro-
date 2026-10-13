// Barra lateral y estructura general

import {
  CalendarRange, LayoutDashboard, LogOut, Package, Sprout, Users, Wheat, FileBarChart,
} from "lucide-react"
import { NavLink, Outlet } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { useAuth } from "@/context/AuthContext"
import { cn } from "@/lib/utils"

const MENU = [
  { a: "/", texto: "Panel", Icono: LayoutDashboard, soloAdmin: false },
  { a: "/empleados", texto: "Empleados", Icono: Users, soloAdmin: true },
  { a: "/cultivos", texto: "Cultivos y lotes", Icono: Sprout, soloAdmin: true },
  { a: "/ciclos", texto: "Ciclo productivo", Icono: CalendarRange, soloAdmin: true },
  { a: "/labores", texto: "Labores de campo", Icono: Package, soloAdmin: false },
  { a: "/cosechas", texto: "Cosechas", Icono: Wheat, soloAdmin: false },
  { a: "/reportes", texto: "Reportes", Icono: FileBarChart, soloAdmin: false },
]

export default function Layout() {
  const { usuario, esAdmin, salir } = useAuth()
  const menu = MENU.filter((item) => !item.soloAdmin || esAdmin)

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="hidden w-64 shrink-0 flex-col border-r bg-card md:flex">
        <div className="flex items-center gap-2 border-b px-6 py-5">
          <Sprout className="size-6 text-primary" />
          <span className="font-semibold leading-tight">Gestion de Cultivos</span>
        </div>

        <nav className="flex-1 space-y-1 p-3">
          {menu.map(({ a, texto, Icono }) => (
            <NavLink
              key={a}
              to={a}
              end={a === "/"}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )
              }
            >
              <Icono className="size-4" />
              {texto}
            </NavLink>
          ))}
        </nav>

        <div className="border-t p-3">
          <p className="px-3 text-sm font-medium">{usuario?.nombre}</p>
          <p className="px-3 pb-2 text-xs capitalize text-muted-foreground">{usuario?.rol}</p>
          <Button variant="ghost" className="w-full justify-start gap-3" onClick={salir}>
            <LogOut className="size-4" />
            Cerrar sesion
          </Button>
        </div>
      </aside>

      <main className="flex-1 overflow-x-auto p-6 md:p-8">
        <Outlet />
      </main>
    </div>
  )
}
