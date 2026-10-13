// Ventana reutilizable para los formularios

import { Button } from "@/components/ui/button"
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"

export default function Modal({ abierto, alCerrar, titulo, descripcion, alGuardar, children }) {
  return (
    <Dialog open={abierto} onOpenChange={alCerrar}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{titulo}</DialogTitle>
          {descripcion && <DialogDescription>{descripcion}</DialogDescription>}
        </DialogHeader>

        <form
          onSubmit={(e) => {
            e.preventDefault()
            alGuardar()
          }}
          className="space-y-4"
        >
          {children}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => alCerrar(false)}>
              Cancelar
            </Button>
            <Button type="submit">Guardar</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
