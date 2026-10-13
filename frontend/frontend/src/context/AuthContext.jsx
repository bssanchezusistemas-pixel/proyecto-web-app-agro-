// Estado de la sesion del usuario

import { createContext, useContext, useEffect, useState } from "react"

import { api, borrarToken, iniciarSesion, leerToken } from "@/lib/api"

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null)
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    if (!leerToken()) {
      setCargando(false)
      return
    }
    api
      .get("/auth/yo")
      .then(setUsuario)
      .catch(() => borrarToken())
      .finally(() => setCargando(false))
  }, [])

  async function entrar(email, password) {
    await iniciarSesion(email, password)
    setUsuario(await api.get("/auth/yo"))
  }

  function salir() {
    borrarToken()
    setUsuario(null)
  }

  const esAdmin = usuario?.rol === "administrador"

  return (
    <AuthContext.Provider value={{ usuario, cargando, esAdmin, entrar, salir }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
