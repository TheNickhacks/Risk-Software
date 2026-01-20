-- =====================================================
-- MIGRACIÓN: DATOS PERSONALES
-- Agregar campos: nombre, apellido, edad, ciudad
-- Fecha: 2026-01-19
-- =====================================================

-- Agregar columnas de datos personales
ALTER TABLE users
ADD COLUMN IF NOT EXISTS first_name VARCHAR(100),
ADD COLUMN IF NOT EXISTS last_name VARCHAR(100),
ADD COLUMN IF NOT EXISTS age INTEGER,
ADD COLUMN IF NOT EXISTS city VARCHAR(100);

-- Actualizar usuarios existentes con datos por defecto
UPDATE users 
SET 
    first_name = COALESCE(first_name, 'Sin especificar'),
    last_name = COALESCE(last_name, 'Sin especificar'),
    age = COALESCE(age, 25),
    city = COALESCE(city, 'Chile')
WHERE first_name IS NULL OR last_name IS NULL OR age IS NULL OR city IS NULL;

-- Hacer campos obligatorios después de actualizar datos
ALTER TABLE users
ALTER COLUMN first_name SET NOT NULL,
ALTER COLUMN last_name SET NOT NULL,
ALTER COLUMN age SET NOT NULL,
ALTER COLUMN city SET NOT NULL;

-- Agregar constraint de edad válida (18-120)
ALTER TABLE users
ADD CONSTRAINT check_age_range CHECK (age >= 18 AND age <= 120);

-- Verificar columnas creadas
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'users'
  AND column_name IN ('first_name', 'last_name', 'age', 'city')
ORDER BY column_name;

-- Ver datos actualizados
SELECT id, email, first_name, last_name, age, city
FROM users
LIMIT 5;
