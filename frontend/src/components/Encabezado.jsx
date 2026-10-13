// Titulo reutilizable de cada pagina

export default function Encabezado({ titulo, descripcion, children }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{titulo}</h1>
        {descripcion && <p className="text-sm text-muted-foreground">{descripcion}</p>}
      </div>
      <div className="flex gap-2">{children}</div>
    </div>
  )
}
