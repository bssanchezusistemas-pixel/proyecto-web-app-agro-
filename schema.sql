-- ==============================================================================
-- SISTEMA DE GESTIÓN DE CULTIVOS AGRÍCOLAS
-- Esquema Relacional Inicial - PostgreSQL / Supabase
-- Módulo: Personas, Empleados, Cultivos y Lotes
-- ==============================================================================

-- 1. EXTENSIONES
-- Requerida para la función genérica gen_random_uuid() en versiones previas a PG 13
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. FUNCIONES Y DISPARADORES GENÉRICOS (TRIGGERS)
-- Función para actualizar automáticamente el campo updated_at al modificar registros
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ==============================================================================
-- 3. TABLA: personas
-- Representa a cualquier individuo en el sistema (empleados, clientes, contratistas).
-- ==============================================================================
CREATE TABLE IF NOT EXISTS personas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre VARCHAR(150) NOT NULL,
    documento VARCHAR(50) NOT NULL,
    telefono VARCHAR(20),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Restricciones de integridad
    CONSTRAINT uq_personas_documento UNIQUE (documento),
    CONSTRAINT chk_personas_nombre_no_vacio CHECK (char_length(trim(nombre)) > 0),
    CONSTRAINT chk_personas_documento_no_vacio CHECK (char_length(trim(documento)) > 0)
);

COMMENT ON TABLE personas IS 'Entidad base abstracta para individuos registrados en el sistema agropecuario.';
COMMENT ON COLUMN personas.id IS 'Identificador único UUID.';
COMMENT ON COLUMN personas.nombre IS 'Nombre completo de la persona.';
COMMENT ON COLUMN personas.documento IS 'Documento de identidad oficial (único).';
COMMENT ON COLUMN personas.telefono IS 'Teléfono de contacto o WhatsApp.';
COMMENT ON COLUMN personas.created_at IS 'Fecha y hora de creación del registro.';

-- ==============================================================================
-- 4. TABLA: empleados
-- Especialización 1 a 1 con personas. Contiene datos laborales de la finca.
-- ==============================================================================
CREATE TABLE IF NOT EXISTS empleados (
    id UUID PRIMARY KEY REFERENCES personas(id) ON DELETE CASCADE,
    cargo VARCHAR(100) NOT NULL,
    fecha_ingreso DATE NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Restricciones de negocio
    CONSTRAINT chk_empleados_cargo_no_vacio CHECK (char_length(trim(cargo)) > 0),
    CONSTRAINT chk_empleados_fecha_ingreso_valida CHECK (fecha_ingreso <= CURRENT_DATE)
);

COMMENT ON TABLE empleados IS 'Especialización laboral de personas vinculadas operativamente a la finca.';
COMMENT ON COLUMN empleados.id IS 'Clave foránea y primaria hacia personas(id). Relación 1:1 estricta.';
COMMENT ON COLUMN empleados.cargo IS 'Cargo operativo (ej. Agrónomo, Fumigador, Recolector).';
COMMENT ON COLUMN empleados.fecha_ingreso IS 'Fecha de inicio de labores (no puede ser fecha futura).';
COMMENT ON COLUMN empleados.activo IS 'Estado del trabajador. Permite desactivar sin perder trazabilidad histórica.';

-- Trigger para mantener actualizado 'updated_at' en empleados
DROP TRIGGER IF EXISTS trg_empleados_updated_at ON empleados;
CREATE TRIGGER trg_empleados_updated_at
BEFORE UPDATE ON empleados
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ==============================================================================
-- 5. TABLA: cultivos
-- Catálogo de especies y variedades de frutas/productos agrícolas sembrados.
-- ==============================================================================
CREATE TABLE IF NOT EXISTS cultivos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre VARCHAR(100) NOT NULL,
    variedad VARCHAR(100),
    dias_a_cosecha INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Restricciones de negocio
    CONSTRAINT chk_cultivos_nombre_no_vacio CHECK (char_length(trim(nombre)) > 0),
    CONSTRAINT chk_cultivos_dias_a_cosecha_positivo CHECK (dias_a_cosecha > 0)
);

COMMENT ON TABLE cultivos IS 'Tipos de cultivo y variedades sembradas en la finca.';
COMMENT ON COLUMN cultivos.nombre IS 'Nombre del cultivo (ej. Mango, Aguacate, Fresa).';
COMMENT ON COLUMN cultivos.variedad IS 'Variedad de la fruta (ej. Tommy, Hass, Albión).';
COMMENT ON COLUMN cultivos.dias_a_cosecha IS 'Días estimados del ciclo vegetativo hasta la cosecha (> 0).';

-- ==============================================================================
-- 6. TABLA: lotes
-- Porciones de terreno físico donde se establecen los ciclos productivos.
-- ==============================================================================
CREATE TABLE IF NOT EXISTS lotes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre VARCHAR(100) NOT NULL,
    area_ha NUMERIC(8,2) NOT NULL,
    ubicacion VARCHAR(200),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Restricciones de negocio
    CONSTRAINT chk_lotes_nombre_no_vacio CHECK (char_length(trim(nombre)) > 0),
    CONSTRAINT chk_lotes_area_ha_positiva CHECK (area_ha > 0)
);

COMMENT ON TABLE lotes IS 'Lotes y áreas de cultivo de la propiedad.';
COMMENT ON COLUMN lotes.nombre IS 'Identificador o nombre del lote (ej. Lote A, Lote Norte).';
COMMENT ON COLUMN lotes.area_ha IS 'Extensión territorial del lote en hectáreas (> 0).';
COMMENT ON COLUMN lotes.ubicacion IS 'Descripción o coordenadas geográficas del lote.';

-- ==============================================================================
-- 7. ÍNDICES DE RENDIMIENTO
-- ==============================================================================
CREATE INDEX IF NOT EXISTS idx_personas_documento ON personas(documento);
CREATE INDEX IF NOT EXISTS idx_personas_nombre ON personas(nombre);
CREATE INDEX IF NOT EXISTS idx_empleados_cargo ON empleados(cargo);
CREATE INDEX IF NOT EXISTS idx_empleados_activo ON empleados(activo);
CREATE INDEX IF NOT EXISTS idx_cultivos_nombre ON cultivos(nombre);
CREATE INDEX IF NOT EXISTS idx_lotes_nombre ON lotes(nombre);

-- ==============================================================================
-- 8. SEGURIDAD: ROW LEVEL SECURITY (RLS)
-- ==============================================================================
ALTER TABLE personas ENABLE ROW LEVEL SECURITY;
ALTER TABLE empleados ENABLE ROW LEVEL SECURITY;
ALTER TABLE cultivos ENABLE ROW LEVEL SECURITY;
ALTER TABLE lotes ENABLE ROW LEVEL SECURITY;

-- Políticas de desarrollo inicial:
-- Permiten lectura y escritura a clientes con llaves anon o autenticados.
-- En fases posteriores con autenticación se restringirán por roles de Supabase Auth.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'personas' AND policyname = 'dev_personas_all_access') THEN
        CREATE POLICY "dev_personas_all_access" ON personas FOR ALL USING (true) WITH CHECK (true);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'empleados' AND policyname = 'dev_empleados_all_access') THEN
        CREATE POLICY "dev_empleados_all_access" ON empleados FOR ALL USING (true) WITH CHECK (true);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'cultivos' AND policyname = 'dev_cultivos_all_access') THEN
        CREATE POLICY "dev_cultivos_all_access" ON cultivos FOR ALL USING (true) WITH CHECK (true);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'lotes' AND policyname = 'dev_lotes_all_access') THEN
        CREATE POLICY "dev_lotes_all_access" ON lotes FOR ALL USING (true) WITH CHECK (true);
    END IF;
END $$;
