// CU-09 a CU-16: fumigacion, fertilizacion, otras labores y programacion

import { Check, Plus, X } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { toast } from "sonner"

import Campo from "@/components/Campo"
import Encabezado from "@/components/Encabezado"
import Modal from "@/components/Modal"
import { Badge } from "@/components/ui/badge"
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

const TIPOS = ["fumigacion", "fertilizacion", "riego", "poda", "otra"]
const HOY = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10)
const PESOS = new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 })

const VACIO = {
  ciclo_id: "", empleado_id: "", tipo: "fumigacion", fecha_programada: HOY,
  fecha_ejecucion: "", producto: "", dosis: "", costo: "0", observaciones: "",
}

export default function Labores() {
  const { esAdmin } = useAuth()
  const [labores, setLabores] = useState([])
  const [ciclos, setCiclos] = useState([])
  const [empleados, setEmpleados] = useState([])
  const [filtro, setFiltro] = useState("todas")
  const [abierto, setAbierto] = useState(false)
  const [form, setForm] = useState(VACIO)

  const cargar = useCallback(() => {
    const ruta = filtro === "todas" ? "/labores" : `/labores?tipo=${filtro}`
    api.get(ruta).then(setLabores).catch((e) => toast.error(e.message))

    if (esAdmin) {
      api.get("/ciclos?estado=activo").then(setCiclos).catch(() => {})
      api.get("/empleados?solo_activos=true").then(setEmpleados).catch(() => {})
    }
  }, [filtro, esAdmin])

  useEffect(() => {
    cargar()
  }, [cargar])

  async function guardar() {
    try {
      await api.post("/labores", {
        ciclo_id: form.ciclo_id,
        empleado_id: form.empleado_id,
        tipo: form.tipo,
        fecha_programada: form.fecha_programada,
        fecha_ejecucion: form.fecha_ejecucion || null,
        producto: form.producto || null,
        dosis: form.dosis || null,
        costo: Number(form.costo || 0),
        observaciones: form.observaciones || null,
      })
      toast.success("Labor registrada")
      setAbierto(false)
      setForm(VACIO)
      cargar()
    } catch (e) {
      toast.error(e.message)
    }
  }

  async function ejecutar(labor) {
    try {
      await api.post(`/labores/${labor.id}/ejecutar`, { fecha_ejecucion: HOY })
      toast.success("Labor marcada como ejecutada")
      cargar()
    } catch (e) {
      toast.error(e.message)
    }
  }

  async function cancelar(labor) {
    if (!confirm("Cancelar esta labor?")) return
    try {
      await api.del(`/labores/${labor.id}`)
      toast.success("Labor cancelada")
      cargar()
    } catch (e) {
      toast.error(e.message)
    }
  }

  const colorEstado = { ejecutada: "secondary", programada: "default", cancelada: "outline" }

  return (
    <>
      <Encabezado titulo="Labores de campo" descripcion="Fumigaciones, abonadas, riego y podas">
        <Select value={filtro} onValueChange={setFiltro}>
          <SelectTrigger className="w-44" aria-label="Filtrar por tipo de labor">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todas">Todos los tipos</SelectItem>
            {TIPOS.map((t) => (
              <SelectItem key={t} value={t} className="capitalize">
                {t}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {esAdmin && (
          <Button onClick={() => setAbierto(true)}>
            <Plus className="size-4" /> Nueva labor
          </Button>
        )}
      </Encabezado>

      <Card className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Tipo</TableHead>
              <TableHead>Programada</TableHead>
              <TableHead>Ejecutada</TableHead>
              <TableHead>Responsable</TableHead>
              <TableHead>Producto</TableHead>
              <TableHead>Costo</TableHead>
              <TableHead>Estado</TableHead>
              {esAdmin && <TableHead className="text-right">Acciones</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {labores.length === 0 && (
              <TableRow>
                <TableCell colSpan={esAdmin ? 8 : 7} className="py-8 text-center text-muted-foreground">
                  No hay labores registradas.
                </TableCell>
              </TableRow>
            )}
            {labores.map((l) => (
              <TableRow key={l.id}>
                <TableCell className="font-medium capitalize">{l.tipo}</TableCell>
                <TableCell>{l.fecha_programada}</TableCell>
                <TableCell>{l.fecha_ejecucion || "-"}</TableCell>
                <TableCell>{l.empleado?.nombre}</TableCell>
                <TableCell>{l.producto || "-"}</TableCell>
                <TableCell>{PESOS.format(Number(l.costo))}</TableCell>
                <TableCell>
                  <Badge variant={colorEstado[l.estado]} className="capitalize">
                    {l.estado}
                  </Badge>
                </TableCell>
                {esAdmin && (
                  <TableCell className="text-right">
                    {l.estado === "programada" && (
                      <>
                        <Button
                          variant="ghost"
                          size="icon"
                          aria-label={`Marcar labor de ${l.tipo} como ejecutada`}
                          title="Marcar como ejecutada"
                          onClick={() => ejecutar(l)}
                        >
                          <Check className="size-4 text-primary" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          aria-label={`Cancelar labor de ${l.tipo}`}
                          title="Cancelar labor"
                          onClick={() => cancelar(l)}
                        >
                          <X className="size-4 text-destructive" />
                        </Button>
                      </>
                    )}
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
        titulo="Registrar labor"
        descripcion="Deja la fecha de ejecucion vacia para dejarla solo programada."
        alGuardar={guardar}
      >
        <Campo etiqueta="Ciclo" id="labor-ciclo">
          <Select value={form.ciclo_id} onValueChange={(v) => setForm({ ...form, ciclo_id: v })}>
            <SelectTrigger id="labor-ciclo" aria-label="Ciclo" className="w-full">
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

        <Campo etiqueta="Empleado responsable" id="labor-empleado">
          <Select value={form.empleado_id} onValueChange={(v) => setForm({ ...form, empleado_id: v })}>
            <SelectTrigger id="labor-empleado" aria-label="Empleado responsable" className="w-full">
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

        <Campo etiqueta="Tipo de labor" id="labor-tipo">
          <Select value={form.tipo} onValueChange={(v) => setForm({ ...form, tipo: v })}>
            <SelectTrigger id="labor-tipo" aria-label="Tipo de labor" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TIPOS.map((t) => (
                <SelectItem key={t} value={t} className="capitalize">
                  {t}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Campo>

        <div className="grid grid-cols-2 gap-4">
          <Campo
            etiqueta="Fecha programada" id="prog" type="date" value={form.fecha_programada}
            onChange={(e) => setForm({ ...form, fecha_programada: e.target.value })} required
          />
          <Campo
            etiqueta="Fecha de ejecucion" id="ejec" type="date" value={form.fecha_ejecucion}
            onChange={(e) => setForm({ ...form, fecha_ejecucion: e.target.value })}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Campo
            etiqueta="Producto" id="producto" value={form.producto}
            onChange={(e) => setForm({ ...form, producto: e.target.value })}
          />
          <Campo
            etiqueta="Dosis" id="dosis" value={form.dosis} placeholder="2 g/L"
            onChange={(e) => setForm({ ...form, dosis: e.target.value })}
          />
        </div>

        <Campo
          etiqueta="Costo" id="costo" type="number" min="0" step="1000" value={form.costo}
          onChange={(e) => setForm({ ...form, costo: e.target.value })}
        />
        <Campo
          etiqueta="Observaciones" id="obs" value={form.observaciones}
          onChange={(e) => setForm({ ...form, observaciones: e.target.value })}
        />
      </Modal>
    </>
  )
}
