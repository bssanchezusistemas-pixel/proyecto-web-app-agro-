// Resumen general y estado de los ciclos activos

import { CalendarRange, CircleDollarSign, Clock, Users, Wheat } from "lucide-react"
import { useEffect, useState } from "react"

import Encabezado from "@/components/Encabezado"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { api } from "@/lib/api"

const PESOS = new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 })

export default function Panel() {
  const [resumen, setResumen] = useState(null)
  const [ciclos, setCiclos] = useState([])

  useEffect(() => {
    api.get("/reportes/resumen").then(setResumen).catch(() => {})
    api.get("/ciclos/estado").then(setCiclos).catch(() => {})
  }, [])

  const tarjetas = [
    { titulo: "Ciclos activos", valor: resumen?.ciclos_activos ?? 0, Icono: CalendarRange },
    { titulo: "Lotes", valor: resumen?.lotes ?? 0, Icono: Wheat },
    { titulo: "Empleados", valor: resumen?.empleados ?? 0, Icono: Users },
    { titulo: "Labores pendientes", valor: resumen?.labores_pendientes ?? 0, Icono: Clock },
    { titulo: "Kilos cosechados", valor: `${Number(resumen?.kilos_totales ?? 0).toLocaleString("es-CO")} kg`, Icono: Wheat },
    { titulo: "Costo acumulado", valor: PESOS.format(Number(resumen?.costo_total ?? 0)), Icono: CircleDollarSign },
  ]

  return (
    <>
      <Encabezado titulo="Panel" descripcion="Estado general del cultivo" />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {tarjetas.map(({ titulo, valor, Icono }) => (
          <Card key={titulo}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{titulo}</CardTitle>
              <Icono className="size-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold">{valor}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <h2 className="mb-3 mt-8 text-lg font-semibold">Ciclos en curso</h2>

      {ciclos.length === 0 ? (
        <p className="text-sm text-muted-foreground">No hay ciclos activos en este momento.</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {ciclos.map((ciclo) => (
            <Card key={ciclo.id}>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-base">
                  {ciclo.lote} · {ciclo.cultivo}
                </CardTitle>
                <Badge variant={ciclo.dias_restantes < 0 ? "destructive" : "secondary"}>
                  {ciclo.dias_restantes < 0
                    ? `${Math.abs(ciclo.dias_restantes)} dias de retraso`
                    : `Faltan ${ciclo.dias_restantes} dias`}
                </Badge>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="h-2 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary transition-all"
                    style={{ width: `${ciclo.porcentaje_avance}%` }}
                  />
                </div>
                <div className="flex justify-between text-sm text-muted-foreground">
                  <span>Dia {ciclo.dias_transcurridos}</span>
                  <span>{ciclo.porcentaje_avance}%</span>
                  <span>Cosecha: {ciclo.fecha_fin_estimada}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </>
  )
}
