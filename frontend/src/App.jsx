// Rutas de la aplicacion

import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"

import Layout from "@/components/Layout"
import { Toaster } from "@/components/ui/sonner"
import { AuthProvider, useAuth } from "@/context/AuthContext"
import Ciclos from "@/pages/Ciclos"
import Cosechas from "@/pages/Cosechas"
import Cultivos from "@/pages/Cultivos"
import Empleados from "@/pages/Empleados"
import Labores from "@/pages/Labores"
import Login from "@/pages/Login"
import Panel from "@/pages/Panel"
import Reportes from "@/pages/Reportes"

function SoloAdmin({ children }) {
  const { esAdmin } = useAuth()
  return esAdmin ? children : <Navigate to="/" replace />
}

function Rutas() {
  const { usuario, cargando } = useAuth()

  if (cargando) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted-foreground">
        Cargando...
      </div>
    )
  }

  if (!usuario) return <Login />

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Panel />} />
        <Route path="/empleados" element={<SoloAdmin><Empleados /></SoloAdmin>} />
        <Route path="/cultivos" element={<SoloAdmin><Cultivos /></SoloAdmin>} />
        <Route path="/ciclos" element={<SoloAdmin><Ciclos /></SoloAdmin>} />
        <Route path="/labores" element={<Labores />} />
        <Route path="/cosechas" element={<Cosechas />} />
        <Route path="/reportes" element={<Reportes />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Rutas />
        <Toaster richColors position="top-right" />
      </AuthProvider>
    </BrowserRouter>
  )
}
