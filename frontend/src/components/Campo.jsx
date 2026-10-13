// Etiqueta mas control de formulario

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export default function Campo({ etiqueta, children, ...props }) {
  return (
    <div className="space-y-2">
      <Label htmlFor={props.id}>{etiqueta}</Label>
      {children ?? <Input {...props} />}
    </div>
  )
}
