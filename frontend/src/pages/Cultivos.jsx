// CU-03 a CU-05: registrar, consultar y modificar cultivos y lotes

import { Pencil, Plus, Trash2 } from "lucide-react"
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { api } from "@/lib/api"

const CULTIVO_VACIO = { nombre: "", variedad: "", dias_ciclo: 180, periodo_carencia_dias: 0, activo: true }
const LOTE_VACIO = { nombre: "", ubicacion: "", area_hectareas: "", cultivo_id: "", activo: true }

export default function Cultivos() {
  const [cultivos, setCultivos] = useState([])
  const [lotes, setLotes] = useState([])
  const [modal, setModal] = useState(null)
  const [editando, setEditando] = useState(null)
  const [form, setForm] = useState({})

  useEffect(() => {
    cargar()
  }, [])

  function cargar() {
    api.get("/cultivos").then(setCultivos).catch((e) => toast.error(e.message))
    api.get("/lotes").then(setLotes).catch((e) => toast.error(e.message))
  }

  function abrir(tipo, registro = null) {
    setModal(tipo)
    setEditando(registro)
    if (registro) setForm({ ...registro, cultivo_id: String(registro.cultivo_id ?? "") })
    else setForm(tipo === "cultivo" ? CULTIVO_VACIO : LOTE_VACIO)
  }

  async function guardar() {
    try {
      if (modal === "cultivo") {
        const datos = {
          ...form,
          variedad: form.variedad || null,
          dias_ciclo: Number(form.dias_ciclo),
          periodo_carencia_dias: Number(form.periodo_carencia_dias),
        }
        if (editando) await api.put(`/cultivos/${editando.id}`, datos)
        else await api.post("/cultivos", datos)
      } else {
        const datos = {
          ...form,
          ubicacion: form.ubicacion || null,
          area_hectareas: Number(form.area_hectareas),
          cultivo_id: form.cultivo_id || null,
        }
        if (editando) await api.put(`/lotes/${editando.id}`, datos)
        else await api.post("/lotes", datos)
      }
      toast.success("Guardado correctamente")
      setModal(null)
      cargar()
    } catch (e) {
      toast.error(e.message)
    }
  }

  async function eliminar(tipo, registro) {
    if (!confirm(`Desactivar ${registro.nombre}?`)) return
    try {
      await api.del(`/${tipo}s/${registro.id}`)
      toast.success("Desactivado")
      cargar()
    } catch (e) {
      toast.error(e.message)
    }
  }

  return (
    <>
      <Encabezado titulo="Cultivos y lotes" descripcion="Que se siembra y donde se siembra" />

      <Tabs defaultValue="cultivos">
        <TabsList>
          <TabsTrigger value="cultivos">Cultivos</TabsTrigger>
          <TabsTrigger value="lotes">Lotes</TabsTrigger>
        </TabsList>

        <TabsContent value="cultivos" className="mt-4 space-y-4">
          <Button onClick={() => abrir("cultivo")}>
            <Plus className="size-4" /> Nuevo cultivo
          </Button>

          <Card className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre</TableHead>
                  <TableHead>Variedad</TableHead>
                  <TableHead>Dias de ciclo</TableHead>
                  <TableHead>Carencia</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {cultivos.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell className="font-medium">{c.nombre}</TableCell>
                    <TableCell>{c.variedad || "-"}</TableCell>
                    <TableCell>{c.dias_ciclo} dias</TableCell>
                    <TableCell>{c.periodo_carencia_dias} dias</TableCell>
                    <TableCell>
                      <Badge variant={c.activo ? "secondary" : "outline"}>
                        {c.activo ? "Activo" : "Inactivo"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon" onClick={() => abrir("cultivo", c)}>
                        <Pencil className="size-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => eliminar("cultivo", c)}>
                        <Trash2 className="size-4 text-destructive" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>

        <TabsContent value="lotes" className="mt-4 space-y-4">
          <Button onClick={() => abrir("lote")}>
            <Plus className="size-4" /> Nuevo lote
          </Button>

          <Card className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Lote</TableHead>
                  <TableHead>Cultivo</TableHead>
                  <TableHead>Ubicacion</TableHead>
                  <TableHead>Area</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {lotes.map((l) => (
                  <TableRow key={l.id}>
                    <TableCell className="font-medium">{l.nombre}</TableCell>
                    <TableCell>{l.cultivo?.nombre}</TableCell>
                    <TableCell>{l.ubicacion || "-"}</TableCell>
                    <TableCell>{Number(l.area_hectareas)} ha</TableCell>
                    <TableCell>
                      <Badge variant={l.activo ? "secondary" : "outline"}>
                        {l.activo ? "Activo" : "Inactivo"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon" onClick={() => abrir("lote", l)}>
                        <Pencil className="size-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => eliminar("lote", l)}>
                        <Trash2 className="size-4 text-destructive" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>
      </Tabs>

      <Modal
        abierto={modal === "cultivo"}
        alCerrar={() => setModal(null)}
        titulo={editando ? "Editar cultivo" : "Nuevo cultivo"}
        alGuardar={guardar}
      >
        <Campo
          etiqueta="Nombre" id="nombre" value={form.nombre || ""}
          onChange={(e) => setForm({ ...form, nombre: e.target.value })} required
        />
        <Campo
          etiqueta="Variedad" id="variedad" value={form.variedad || ""}
          onChange={(e) => setForm({ ...form, variedad: e.target.value })}
        />
        <Campo
          etiqueta="Dias del ciclo" id="dias" type="number" min="1" value={form.dias_ciclo || ""}
          onChange={(e) => setForm({ ...form, dias_ciclo: e.target.value })} required
        />
        <Campo
          etiqueta="Periodo de carencia (dias)" id="carencia" type="number" min="0"
          value={form.periodo_carencia_dias ?? 0}
          onChange={(e) => setForm({ ...form, periodo_carencia_dias: e.target.value })} required
        />
      </Modal>

      <Modal
        abierto={modal === "lote"}
        alCerrar={() => setModal(null)}
        titulo={editando ? "Editar lote" : "Nuevo lote"}
        alGuardar={guardar}
      >
        <Campo
          etiqueta="Nombre" id="lote-nombre" value={form.nombre || ""}
          onChange={(e) => setForm({ ...form, nombre: e.target.value })} required
        />
        <Campo etiqueta="Cultivo">
          <Select
            value={form.cultivo_id || ""}
            onValueChange={(v) => setForm({ ...form, cultivo_id: v })}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Selecciona un cultivo" />
            </SelectTrigger>
            <SelectContent>
              {cultivos.filter((c) => c.activo).map((c) => (
                <SelectItem key={c.id} value={String(c.id)}>
                  {c.nombre} {c.variedad ? `(${c.variedad})` : ""}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Campo>
        <Campo
          etiqueta="Ubicacion" id="ubicacion" value={form.ubicacion || ""}
          onChange={(e) => setForm({ ...form, ubicacion: e.target.value })}
        />
        <Campo
          etiqueta="Area (hectareas)" id="area" type="number" step="0.01" min="0.01"
          value={form.area_hectareas || ""}
          onChange={(e) => setForm({ ...form, area_hectareas: e.target.value })} required
        />
      </Modal>
    </>
  )
}
