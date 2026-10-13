// CU-17 a CU-19: registrar cosecha y calcular kilaje

import { Plus, Trash2 } from "lucide-react"
import { useEffect, useState } from "react"
import { toast } from "sonner"

import Campo from "@/components/Campo"
import Encabezado from "@/components/Encabezado"
import Modal from "@/components/Modal"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { useAuth } from "@/context/AuthContext"
import { api } from "@/lib/api"

const HOY = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10)
const VACIO = { ciclo_id: "", empleado_id: "", fecha: HOY, kilos: "", calidad: "", observaciones: "" }

export default function Cosechas() {
  const { esAdmin } = useAuth()
  const [cosechas, setCosechas] = useState([])
  const [ciclos, setCiclos] = useState([])
  const [empleados, setEmpleados] = useState([])
  const [abierto, setAbierto] = useState(false)
  const [form, setForm] = useState(VACIO)

  useEffect(() => {
    cargar()
  }, [])

  function cargar() {
    api.get("/cosechas").then(setCosechas).catch((e) => toast.error(e.message))
    if (esAdmin) {
      api.get("/ciclos?estado=activo").then(setCiclos).catch(() => {})
      api.get("/empleados?solo_activos=true").then(setEmpleados).catch(() => {})
    }
  }

  async function guardar() {
    try {
      await api.post("/cosechas", {
        ciclo_id: form.ciclo_id,
        empleado_id: form.empleado_id,
        fecha: form.fecha,
        kilos: Number(form.kilos),
        calidad: form.calidad || null,
        observaciones: form.observaciones || null,
      })
      toast.success("Cosecha registrada")
      setAbierto(false)
      setForm(VACIO)
      cargar()
    } catch (e) {
      toast.error(e.message)
    }
  }

  async function eliminar(cosecha) {
    if (!confirm("Eliminar este registro de cosecha?")) return
    try {
      await api.del(`/cosechas/${cosecha.id}`)
      toast.success("Cosecha eliminada")
      cargar()
    } catch (e) {
      toast.error(e.message)
    }
  }

  const total = cosechas.reduce((suma, c) => suma + Number(c.kilos), 0)

  return (
    <>
      <Encabezado titulo="Cosechas" descripcion={`Kilaje acumulado: ${total.toLocaleString("es-CO")} kg`}>
        {esAdmin && (
          <Button onClick={() => setAbierto(true)}>
            <Plus className="size-4" /> Registrar cosecha
          </Button>
        )}
      </Encabezado>

      <Card className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Fecha</TableHead>
              <TableHead>Kilos</TableHead>
              <TableHead>Calidad</TableHead>
              <TableHead>Recolector</TableHead>
              <TableHead>Observaciones</TableHead>
              {esAdmin && <TableHead className="text-right">Acciones</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {cosechas.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-8 text-center text-muted-foreground">
                  No hay cosechas registradas.
                </TableCell>
              </TableRow>
            )}
            {cosechas.map((c) => (
              <TableRow key={c.id}>
                <TableCell>{c.fecha}</TableCell>
                <TableCell className="font-medium">
                  {Number(c.kilos).toLocaleString("es-CO")} kg
                </TableCell>
                <TableCell>{c.calidad || "-"}</TableCell>
                <TableCell>{c.empleado?.nombre}</TableCell>
                <TableCell className="text-muted-foreground">{c.observaciones || "-"}</TableCell>
                {esAdmin && (
                  <TableCell className="text-right">
                    <Button variant="ghost" size="icon" onClick={() => eliminar(c)}>
                      <Trash2 className="size-4 text-destructive" />
                    </Button>
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      <Modal
        abierto={abierto}
        alCerrar={setAbierto}
        titulo="Registrar cosecha"
        descripcion="El sistema verifica el periodo de carencia antes de guardar."
        alGuardar={guardar}
      >
        <Campo etiqueta="Ciclo">
          <Select value={form.ciclo_id} onValueChange={(v) => setForm({ ...form, ciclo_id: v })}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Selecciona un ciclo activo" />
            </SelectTrigger>
            <SelectContent>
              {ciclos.map((c) => (
                <SelectItem key={c.id} value={String(c.id)}>
                  {c.lote?.nombre} - {c.lote?.cultivo?.nombre}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Campo>

        <Campo etiqueta="Recolector">
          <Select value={form.empleado_id} onValueChange={(v) => setForm({ ...form, empleado_id: v })}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Selecciona un empleado" />
            </SelectTrigger>
            <SelectContent>
              {empleados.map((e) => (
                <SelectItem key={e.id} value={String(e.id)}>
                  {e.nombre} - {e.cargo}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Campo>

        <div className="grid grid-cols-2 gap-4">
          <Campo
            etiqueta="Fecha" id="fecha" type="date" value={form.fecha}
            onChange={(e) => setForm({ ...form, fecha: e.target.value })} required
          />
          <Campo
            etiqueta="Kilos" id="kilos" type="number" step="0.01" min="0.01" value={form.kilos}
            onChange={(e) => setForm({ ...form, kilos: e.target.value })} required
          />
        </div>

        <Campo
          etiqueta="Calidad" id="calidad" value={form.calidad} placeholder="Primera, segunda..."
          onChange={(e) => setForm({ ...form, calidad: e.target.value })}
        />
        <Campo
          etiqueta="Observaciones" id="obs" value={form.observaciones}
          onChange={(e) => setForm({ ...form, observaciones: e.target.value })}
        />
      </Modal>
    </>
  )
}
