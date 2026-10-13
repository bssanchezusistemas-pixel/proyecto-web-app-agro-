// CU-20 a CU-25: consultas, reportes y exportacion

import { FileDown, FileSpreadsheet } from "lucide-react"
import { useEffect, useState } from "react"
import { toast } from "sonner"

import Encabezado from "@/components/Encabezado"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useAuth } from "@/context/AuthContext"
import { api, descargarReporte } from "@/lib/api"

const PESOS = new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 })

export default function Reportes() {
  const { esAdmin } = useAuth()
  const [porCiclo, setPorCiclo] = useState([])
  const [costos, setCostos] = useState([])
  const [historial, setHistorial] = useState([])
  const [proximas, setProximas] = useState([])

  useEffect(() => {
    api.get("/reportes/ciclos").then(setPorCiclo).catch(() => {})
    api.get("/reportes/costos").then(setCostos).catch(() => {})
    api.get("/reportes/historial").then(setHistorial).catch(() => {})
    api.get("/labores/proximas").then(setProximas).catch(() => {})
  }, [])

  async function exportar(formato) {
    try {
      await descargarReporte(formato)
      toast.success("Reporte descargado")
    } catch (e) {
      toast.error(e.message)
    }
  }

  return (
    <>
      <Encabezado titulo="Reportes" descripcion="Historial, costos y proximas labores">
        {esAdmin && (
          <>
            <Button variant="outline" onClick={() => exportar("csv")}>
              <FileDown className="size-4" /> CSV
            </Button>
            <Button variant="outline" onClick={() => exportar("excel")}>
              <FileSpreadsheet className="size-4" /> Excel
            </Button>
          </>
        )}
      </Encabezado>

      <Tabs defaultValue="ciclos">
        <TabsList className="max-w-full overflow-x-auto">
          <TabsTrigger value="ciclos">Por ciclo</TabsTrigger>
          <TabsTrigger value="costos">Costos</TabsTrigger>
          <TabsTrigger value="proximas">Proximas labores</TabsTrigger>
          <TabsTrigger value="historial">Historial</TabsTrigger>
        </TabsList>

        <TabsContent value="ciclos" className="mt-4">
          <Card className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Lote</TableHead>
                  <TableHead>Cultivo</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Labores</TableHead>
                  <TableHead>Costo total</TableHead>
                  <TableHead>Kilos</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {porCiclo.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} className="py-8 text-center text-muted-foreground">
                      No hay ciclos registrados.
                    </TableCell>
                  </TableRow>
                )}
                {porCiclo.map((c) => (
                  <TableRow key={c.ciclo_id}>
                    <TableCell className="font-medium">{c.lote}</TableCell>
                    <TableCell>{c.cultivo}</TableCell>
                    <TableCell>
                      <Badge variant={c.estado === "activo" ? "secondary" : "outline"}>
                        {c.estado}
                      </Badge>
                    </TableCell>
                    <TableCell>{c.total_labores}</TableCell>
                    <TableCell>{PESOS.format(Number(c.costo_total))}</TableCell>
                    <TableCell>{Number(c.kilos_cosechados).toLocaleString("es-CO")} kg</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>

        <TabsContent value="costos" className="mt-4">
          {costos.length === 0 ? (
            <p className="text-sm text-muted-foreground">No hay costos registrados.</p>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {costos.map((c) => (
                <Card key={c.tipo}>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium capitalize text-muted-foreground">
                      {c.tipo}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-2xl font-semibold">{PESOS.format(Number(c.costo_total))}</p>
                    <p className="text-sm text-muted-foreground">{c.cantidad} labores</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="proximas" className="mt-4">
          <Card className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Responsable</TableHead>
                  <TableHead>Producto</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {proximas.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4} className="py-8 text-center text-muted-foreground">
                      No hay labores programadas.
                    </TableCell>
                  </TableRow>
                )}
                {proximas.map((l) => (
                  <TableRow key={l.id}>
                    <TableCell>{l.fecha_programada}</TableCell>
                    <TableCell className="capitalize">{l.tipo}</TableCell>
                    <TableCell>{l.empleado?.nombre}</TableCell>
                    <TableCell>{l.producto || "-"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>

        <TabsContent value="historial" className="mt-4">
          <Card className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Lote</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Empleado</TableHead>
                  <TableHead>Producto</TableHead>
                  <TableHead>Costo</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {historial.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="py-8 text-center text-muted-foreground">
                      No hay historial de labores registrado.
                    </TableCell>
                  </TableRow>
                )}
                {historial.map((h, i) => (
                  <TableRow key={i}>
                    <TableCell>{h.Fecha}</TableCell>
                    <TableCell>{h.Lote}</TableCell>
                    <TableCell className="capitalize">{h.Tipo}</TableCell>
                    <TableCell className="capitalize">{h.Estado}</TableCell>
                    <TableCell>{h.Empleado}</TableCell>
                    <TableCell>{h.Producto || "-"}</TableCell>
                    <TableCell>{PESOS.format(Number(h.Costo))}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>
      </Tabs>
    </>
  )
}
