// CU-01 y CU-02: registrar y gestionar empleados

import { Pencil, Plus, UserX } from "lucide-react"
import { useEffect, useState } from "react"
import { toast } from "sonner"

import Campo from "@/components/Campo"
import Encabezado from "@/components/Encabezado"
import Modal from "@/components/Modal"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { api } from "@/lib/api"

const VACIO = { nombre: "", documento: "", cargo: "", telefono: "", activo: true }

export default function Empleados() {
  const [empleados, setEmpleados] = useState([])
  const [abierto, setAbierto] = useState(false)
  const [editando, setEditando] = useState(null)
  const [form, setForm] = useState(VACIO)

  useEffect(() => {
    cargar()
  }, [])

  function cargar() {
    api.get("/empleados").then(setEmpleados).catch((e) => toast.error(e.message))
  }

  function abrirNuevo() {
    setEditando(null)
    setForm(VACIO)
    setAbierto(true)
  }

  function abrirEdicion(empleado) {
    setEditando(empleado)
    setForm({ ...empleado })
    setAbierto(true)
  }

  async function guardar() {
    try {
      const datos = { ...form, telefono: form.telefono || null }
      if (editando) {
        await api.put(`/empleados/${editando.id}`, datos)
        toast.success("Empleado actualizado")
      } else {
        await api.post("/empleados", datos)
        toast.success("Empleado registrado")
      }
      setAbierto(false)
      cargar()
    } catch (e) {
      toast.error(e.message)
    }
  }

  async function desactivar(empleado) {
    if (!confirm(`Desactivar a ${empleado.nombre}?`)) return
    try {
      await api.del(`/empleados/${empleado.id}`)
      toast.success("Empleado desactivado")
      cargar()
    } catch (e) {
      toast.error(e.message)
    }
  }

  return (
    <>
      <Encabezado titulo="Empleados" descripcion="Responsables de las labores de campo">
        <Button onClick={abrirNuevo}>
          <Plus className="size-4" /> Nuevo empleado
        </Button>
      </Encabezado>

      <Card className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nombre</TableHead>
              <TableHead>Documento</TableHead>
              <TableHead>Cargo</TableHead>
              <TableHead>Telefono</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead className="text-right">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {empleados.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-8 text-center text-muted-foreground">
                  Todavia no hay empleados registrados.
                </TableCell>
              </TableRow>
            )}
            {empleados.map((e) => (
              <TableRow key={e.id}>
                <TableCell className="font-medium">{e.nombre}</TableCell>
                <TableCell>{e.documento}</TableCell>
                <TableCell>{e.cargo}</TableCell>
                <TableCell>{e.telefono || "-"}</TableCell>
                <TableCell>
                  <Badge variant={e.activo ? "secondary" : "outline"}>
                    {e.activo ? "Activo" : "Inactivo"}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={`Editar ${e.nombre}`}
                    title="Editar empleado"
                    onClick={() => abrirEdicion(e)}
                  >
                    <Pencil className="size-4" />
                  </Button>
                  {e.activo && (
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Desactivar ${e.nombre}`}
                      title="Desactivar empleado"
                      onClick={() => desactivar(e)}
                    >
                      <UserX className="size-4 text-destructive" />
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      <Modal
        abierto={abierto}
        alCerrar={setAbierto}
        titulo={editando ? "Editar empleado" : "Nuevo empleado"}
        alGuardar={guardar}
      >
        <Campo
          etiqueta="Nombre completo"
          id="nombre"
          value={form.nombre}
          onChange={(e) => setForm({ ...form, nombre: e.target.value })}
          required
        />
        <Campo
          etiqueta="Documento"
          id="documento"
          value={form.documento}
          onChange={(e) => setForm({ ...form, documento: e.target.value })}
          required
        />
        <Campo
          etiqueta="Cargo"
          id="cargo"
          value={form.cargo}
          onChange={(e) => setForm({ ...form, cargo: e.target.value })}
          placeholder="Fumigador, recolector, agronomo..."
          required
        />
        <Campo
          etiqueta="Telefono"
          id="telefono"
          value={form.telefono || ""}
          onChange={(e) => setForm({ ...form, telefono: e.target.value })}
        />
      </Modal>
    </>
  )
}
