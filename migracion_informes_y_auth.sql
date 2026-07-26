-- ============================================================
-- MIGRACIÓN 2: sistema de informes por partido + accesos + auth
-- Ejecuta esto en el SQL Editor de Supabase.
-- (La migración anterior, migracion_jugadores.sql, ya debiste ejecutarla)
-- ============================================================

-- 1) Enlazar los informes con un partido concreto (opcional: puede ser NULL
--    para informes de pretemporada o individuales que no dependen de un partido)
ALTER TABLE informes_pdf
    ADD COLUMN IF NOT EXISTS id_partido BIGINT REFERENCES partidos(id_partido);

-- 2) Ajustar los valores de "tipo" que vas a usar desde ahora (informativo,
--    Postgres no restringe el texto salvo que uses un CHECK o un ENUM):
--      'Pretemporada'
--      'Analisis Propio Pre'
--      'Analisis Propio Post'
--      'Analisis Rival Pre'
--      'Analisis Rival Post'
--      'Individual'

-- 3) Tabla de accesos individuales: qué jugadores pueden ver un informe
--    marcado como "Individual". Para el resto de tipos no hace falta fila
--    aquí, porque son visibles para toda la plantilla.
CREATE TABLE IF NOT EXISTS informes_acceso (
    id BIGSERIAL PRIMARY KEY,
    id_informe BIGINT NOT NULL REFERENCES informes_pdf(id) ON DELETE CASCADE,
    id_jugador BIGINT NOT NULL REFERENCES jugadores(id_jugador) ON DELETE CASCADE,
    UNIQUE (id_informe, id_jugador)
);

-- NOTA IMPORTANTE: esta migración asume que la clave primaria de
-- "informes_pdf" se llama "id". Si en tu tabla se llama distinto
-- (por ejemplo "id_informe"), avísame y ajusto el código en consecuencia.

-- 4) Vincular cada fila de usuarios_roles con su usuario real de Supabase Auth,
--    para poder resetear contraseñas desde la app sin tener que buscarlo a mano.
ALTER TABLE usuarios_roles
    ADD COLUMN IF NOT EXISTS auth_user_id UUID;
