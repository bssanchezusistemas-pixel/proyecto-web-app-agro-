// CU-06 a CU-08: iniciar ciclo, ver dias restantes y cerrar

import { CheckCircle2, Plus } from "lucide-react"
import { useEffect, useState } from "react"
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
import { api } from "@/lib/api"

const HOY = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10)

export default function Ciclos() {
  const [ciclos, setCiclos] = useState([])
  const [lotes, setLotes] = useState([])
  const [abierto, setAbierto] = useState(false)
  const [form, setForm] = useState({ lote_id: "", fecha_inicio: HOY, observaciones: "" })

  useEffect(() => {
    cargar()
  }, [])

  function cargar() {
    api.get("/ciclos").then(setCiclos).catch((e) => toast.error(e.message))
    api.get("/lotes").then(setLotes).catch((e) => toast.error(e.message))
  }

  async function iniciar() {
    try {
      await api.post("/ciclos", {
        lote_id: form.lote_id,
        fecha_inicio: form.fecha_inicio,
        observaciones: form.observaciones || null,
      })
      toast.success("Ciclo iniciado")
      setAbierto(false)
      setForm({ lote_id: "", fecha_inicio: HOY, observaciones: "" })
      cargar()
    } catch (e) {
      toast.error(e.message)
    }
  }

  async function cerrar(ciclo) {
    if (!confirm(`Cerrar el ciclo del ${ciclo.lote?.nombre}?`)) return
    try {
      await api.post(`/ciclos/${ciclo.id}/cerrar`, {})
      toast.success("Ciclo cerrado")
      cargar()
    } catch (e) {
      toast.error(e.message)
    }
  }

  function diasRestantes(ciclo) {
    const dias = Math.ceil((new Date(ciclo.fecha_fin_estimada) - new Date()) / 86400000)
    if (ciclo.estado === "cerrado") return "-"
    return dias < 0 ? `${Math.abs(dias)} de retraso` : `${dias} dias`
  }

  return (
    <>
      <Encabezado titulo="Ciclo productivo" descripcion="Desde la siembra hasta la cosecha">
        <Button onClick={() => setAbierto(true)}>
          <Plus className="size-4" /> Iniciar ciclo
        </Button>
      </Encabezado>

      <Card className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Lote</TableHead>
              <TableHead>Cultivo</TableHead>
              <TableHead>Inicio</TableHead>
              <TableHead>Cosecha estimada</TableHead>
              <TableHead>Faltan</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead className="text-right">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {ciclos.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="py-8 text-center text-muted-foreground">
                  Todavia no hay ciclos registrados.
                </TableCell>
              </TableRow>
            )}
            {ciclos.map((c) => (
              <TableRow key={c.id}>
                <TableCell className="font-medium">{c.lote?.nombre}</TableCell>
                <TableCell>{c.lote?.cultivo?.nombre}</TableCell>
                <TableCell>{c.fecha_inicio}</TableCell>
                <TableCell>{c.fecha_fin_estimada}</TableCell>
                <TableCell>{diasRestantes(c)}</TableCell>
                <TableCell>
                  <Badge variant={c.estado === "activo" ? "secondary" : "outline"}>
                    {c.estado}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  {c.estado === "activo" && (
                    <Button variant="ghost" size="sm" onClick={() => cerrar(c)}>
                      <CheckCircle2 className="size-4" /> Cerrar
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
        titulo="Iniciar ciclo productivo"
        descripcion="La fecha de cosecha se calcula con los dias de ciclo del cultivo."
        alGuardar={iniciar}
      >
        <Campo etiqueta="Lote">
          <Select value={form.lote_id} onValueChange={(v) => setForm({ ...form, lote_id: v })}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Selecciona un lote" />
            </SelectTrigger>
            <SelectContent>
              {lotes.filter((l) => l.activo).map((l) => (
                <SelectItem key={l.id} value={String(l.id)}>
                  {l.nombre} - {l.cultivo?.nombre}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Campo>
        <Campo
          etiqueta="Fecha de inicio" id="inicio" type="date" value={form.fecha_inicio}
          onChange={(e) => setForm({ ...form, fecha_inicio: e.target.value })} required
        />
        <Campo
          etiqueta="Observaciones" id="obs" value={form.observaciones}
          onChange={(e) => setForm({ ...form, observaciones: e.target.value })}
        />
      </Modal>
    </>
  )
}
