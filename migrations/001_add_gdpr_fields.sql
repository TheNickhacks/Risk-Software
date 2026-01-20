-- =====================================================
-- MIGRACIÓN GDPR/LPD - PreIncubadora AI
-- Ejecutar en Neon PostgreSQL Console
-- Fecha: 2026-01-19
-- =====================================================

-- Agregar columnas GDPR/LPD a la tabla users
ALTER TABLE users
ADD COLUMN IF NOT EXISTS consent_given BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN IF NOT EXISTS consent_timestamp TIMESTAMP,
ADD COLUMN IF NOT EXISTS consent_ip VARCHAR(45),
ADD COLUMN IF NOT EXISTS consent_version VARCHAR(20),
ADD COLUMN IF NOT EXISTS scheduled_deletion TIMESTAMP;

-- Crear índice para eliminaciones programadas
CREATE INDEX IF NOT EXISTS idx_users_scheduled_deletion ON users(scheduled_deletion);

-- Actualizar usuarios existentes (darles consentimiento retroactivo)
UPDATE users 
SET consent_given = TRUE,
    consent_timestamp = created_at,
    consent_version = '1.0'
WHERE consent_given = FALSE OR consent_timestamp IS NULL;

-- Verificar que las columnas se crearon correctamente
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'users'
  AND column_name IN ('consent_given', 'consent_timestamp', 'consent_ip', 'consent_version', 'scheduled_deletion')
ORDER BY column_name;

-- Verificar datos actualizados
SELECT id, email, consent_given, consent_timestamp, consent_version
FROM users
LIMIT 5;
