-- Ejecuta esto en el SQL Editor de Supabase antes de usar la app rediseñada.
-- Añade a la tabla "jugadores" los campos de perfil que la nueva interfaz utiliza.
-- Si alguna columna ya existe, Postgres la ignorará gracias a "IF NOT EXISTS".

ALTER TABLE jugadores
    ADD COLUMN IF NOT EXISTS fecha_nacimiento DATE,
    ADD COLUMN IF NOT EXISTS nacionalidad TEXT,
    ADD COLUMN IF NOT EXISTS pie_dominante TEXT,
    ADD COLUMN IF NOT EXISTS altura_cm INTEGER;

-- (dorsal, nombre, posicion y url_foto ya existían según tu código original)
