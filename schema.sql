-- ============================================
-- SCHEMA RELACIONAL: PRE-INCUBADORA AI
-- Database: preincubadora_db
-- PostgreSQL 16
-- ============================================

-- ============================================
-- 1. TABLA: user (Usuarios del Sistema)
-- ============================================
CREATE TABLE IF NOT EXISTS "user" (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    rut VARCHAR(12) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('user', 'admin', 'seller')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Password Recovery Fields
    reset_token VARCHAR(255) UNIQUE,
    reset_token_expiry TIMESTAMP,
    last_project_creation TIMESTAMP,
    -- GDPR/LPD Compliance Fields
    consent_given BOOLEAN DEFAULT FALSE NOT NULL,
    consent_timestamp TIMESTAMP,
    consent_ip VARCHAR(45),
    consent_version VARCHAR(20),
    scheduled_deletion TIMESTAMP
);

CREATE INDEX idx_user_rut ON "user"(rut);
CREATE INDEX idx_user_email ON "user"(email);
CREATE INDEX idx_user_reset_token ON "user"(reset_token);
CREATE INDEX idx_user_scheduled_deletion ON "user"(scheduled_deletion);

COMMENT ON TABLE "user" IS 'Usuarios del sistema con validación RUT única (1 cuenta/RUT)';
COMMENT ON COLUMN "user".rut IS 'RUT único de Chile (sin puntos ni guión)';
COMMENT ON COLUMN "user".role IS 'Rol del usuario: user (emprendedor), admin, seller';
COMMENT ON COLUMN "user".reset_token IS 'Token UUID para recuperación de contraseña (único, temporal)';
COMMENT ON COLUMN "user".reset_token_expiry IS 'Fecha/hora de expiración del token de recuperación (1 hora)';
COMMENT ON COLUMN "user".last_project_creation IS 'Timestamp del último proyecto creado (para rate limiting)';
COMMENT ON COLUMN "user".consent_given IS 'GDPR: Consentimiento explícito otorgado por el usuario';
COMMENT ON COLUMN "user".consent_timestamp IS 'GDPR: Fecha/hora exacta del consentimiento (trazabilidad)';
COMMENT ON COLUMN "user".consent_ip IS 'GDPR: IP desde donde se otorgó el consentimiento';
COMMENT ON COLUMN "user".consent_version IS 'GDPR: Versión de los Términos y Condiciones aceptada';
COMMENT ON COLUMN "user".scheduled_deletion IS 'GDPR: Fecha programada para hard delete (30 días tras soft delete)';


-- ============================================
-- 2. TABLA: project (Proyectos/Ideas de Negocio)
-- ============================================
CREATE TABLE IF NOT EXISTS project (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    raw_idea TEXT NOT NULL,
    variability_score INTEGER CHECK (variability_score >= 0 AND variability_score <= 100),
    status VARCHAR(50) DEFAULT 'ambiguous' CHECK (status IN ('ambiguous', 'ready', 'approved', 'rejected')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_project_user_id ON project(user_id);
CREATE INDEX idx_project_status ON project(status);
CREATE INDEX idx_project_created_at ON project(created_at);

COMMENT ON TABLE project IS 'Proyectos/ideas de negocio generados por usuarios';
COMMENT ON COLUMN project.variability_score IS 'Score 0-100: qué tan vaga/ambigua es la idea (0=clara, 100=muy confusa)';
COMMENT ON COLUMN project.status IS 'Estado del proyecto: ambiguous (requiere clarificación), ready, approved, rejected';


-- ============================================
-- 3. TABLA: business_plan (Planes de Negocio - 9 Pilares)
-- ============================================
CREATE TABLE IF NOT EXISTS business_plan (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL UNIQUE REFERENCES project(id) ON DELETE CASCADE,
    value_proposition TEXT,
    target_market TEXT,
    revenue_model TEXT,
    operations_plan TEXT,
    roadmap TEXT,
    problem_real VARCHAR(10) DEFAULT 'pending' CHECK (problem_real IN ('yes', 'no', 'pending')),
    tech_viability VARCHAR(10) DEFAULT 'pending' CHECK (tech_viability IN ('yes', 'no', 'pending')),
    scalability VARCHAR(10) DEFAULT 'pending' CHECK (scalability IN ('yes', 'no', 'pending')),
    risk_analysis TEXT,
    validation_strategy TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_business_plan_project_id ON business_plan(project_id);
CREATE INDEX idx_business_plan_generated_at ON business_plan(generated_at);

COMMENT ON TABLE business_plan IS 'Plan de negocio generado por IA con análisis de 9 pilares de viabilidad';
COMMENT ON COLUMN business_plan.problem_real IS 'Validación: ¿Existe el problema en la realidad?';
COMMENT ON COLUMN business_plan.tech_viability IS 'Validación: ¿Es técnicamente viable?';
COMMENT ON COLUMN business_plan.scalability IS 'Validación: ¿Es escalable?';


-- ============================================
-- 4. TABLA: chat_session (Sesiones de Chat por Proyecto)
-- ============================================
CREATE TABLE IF NOT EXISTS chat_session (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    message_count INTEGER DEFAULT 0 CHECK (message_count >= 0 AND message_count <= 10),
    is_locked BOOLEAN DEFAULT FALSE,
    clarity_level INTEGER DEFAULT 0 CHECK (clarity_level >= 0 AND clarity_level <= 100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    CONSTRAINT lock_at_10_messages CHECK (
        (message_count < 10 AND is_locked = FALSE) OR 
        (message_count = 10 AND is_locked = TRUE)
    )
);

CREATE INDEX idx_chat_session_project_id ON chat_session(project_id);
CREATE INDEX idx_chat_session_is_locked ON chat_session(is_locked);
CREATE INDEX idx_chat_session_created_at ON chat_session(created_at);

COMMENT ON TABLE chat_session IS 'Sesiones independientes de chat para clarificación de ideas (hard cap: 10 mensajes)';
COMMENT ON COLUMN chat_session.message_count IS 'Contador de mensajes: se bloquea en 10';
COMMENT ON COLUMN chat_session.is_locked IS 'TRUE cuando se alcanza máximo de 10 mensajes';
COMMENT ON COLUMN chat_session.clarity_level IS 'Nivel de claridad después de la sesión (0-100)';


-- ============================================
-- 5. TABLA: chat_message (Mensajes Individuales)
-- ============================================
CREATE TABLE IF NOT EXISTS chat_message (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES chat_session(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    message_type VARCHAR(50) CHECK (message_type IN ('clarification', 'question', 'answer', 'analysis', 'system')),
    tokens_used INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chat_message_session_id ON chat_message(session_id);
CREATE INDEX idx_chat_message_role ON chat_message(role);
CREATE INDEX idx_chat_message_created_at ON chat_message(created_at);

COMMENT ON TABLE chat_message IS 'Historial de mensajes dentro de cada sesión de chat';
COMMENT ON COLUMN chat_message.role IS 'user (emprendedor), assistant (IA Gemini), system (automático)';
COMMENT ON COLUMN chat_message.message_type IS 'Tipo de mensaje: clarification, question, answer, analysis';
COMMENT ON COLUMN chat_message.tokens_used IS 'Tokens consumidos por este mensaje (para tracking de costo)';


-- ============================================
-- 6. TABLA: audit_log (Auditoría GDPR/LPD)
-- ============================================
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    details JSONB DEFAULT '{}',
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);
CREATE INDEX idx_audit_log_resource ON audit_log(resource_type, resource_id);

COMMENT ON TABLE audit_log IS 'Registro de auditoría para cumplimiento GDPR/LPD (protección de datos)';
COMMENT ON COLUMN audit_log.action IS 'Acción ejecutada: login, create_project, generate_report, delete_project, etc';
COMMENT ON COLUMN audit_log.resource_type IS 'Tipo de recurso afectado: user, project, business_plan, chat_session';
COMMENT ON COLUMN audit_log.details IS 'Detalles en JSON: {old_value, new_value, timestamp, reason}';


-- ============================================
-- RESTRICCIONES DE INTEGRIDAD REFERENCIAL
-- ============================================

-- Restricción: Un usuario no puede crear más de 2 proyectos en 24 horas
-- (Implementar en aplicación con validación en runtime)

-- Restricción: Una sesión de chat no puede tener más de 10 mensajes
-- (Implementada en chat_session.message_count con CHECK)

-- Restricción: Un proyecto solo puede tener 1 business_plan (opcional)
-- (Implementada con UNIQUE en business_plan.project_id)


-- ============================================
-- VISTAS ÚTILES
-- ============================================

-- Vista: Resumen de proyectos con últimos chats
CREATE OR REPLACE VIEW v_project_summary AS
SELECT 
    p.id,
    p.user_id,
    u.full_name,
    u.email,
    p.title,
    p.variability_score,
    p.status,
    COUNT(DISTINCT cs.id) AS chat_sessions_count,
    COUNT(DISTINCT cm.id) AS total_messages,
    MAX(cm.created_at) AS last_message_at,
    p.created_at,
    p.updated_at
FROM project p
LEFT JOIN "user" u ON p.user_id = u.id
LEFT JOIN chat_session cs ON p.id = cs.project_id
LEFT JOIN chat_message cm ON cs.id = cm.session_id
GROUP BY p.id, p.user_id, u.full_name, u.email, p.title, p.variability_score, p.status, p.created_at, p.updated_at;

COMMENT ON VIEW v_project_summary IS 'Vista que resume proyectos con estadísticas de chat';


-- Vista: Auditoría de cambios recientes
CREATE OR REPLACE VIEW v_audit_recent AS
SELECT 
    al.id,
    u.full_name,
    u.email,
    al.action,
    al.resource_type,
    al.resource_id,
    al.ip_address,
    al.created_at,
    al.details
FROM audit_log al
LEFT JOIN "user" u ON al.user_id = u.id
ORDER BY al.created_at DESC
LIMIT 100;

COMMENT ON VIEW v_audit_recent IS 'Vista con últimos 100 registros de auditoría';


-- ============================================
-- FUNCIONES ÚTILES
-- ============================================

-- Función: Verificar si usuario puede crear proyecto (max 2 en 24h)
CREATE OR REPLACE FUNCTION check_user_project_limit(p_user_id INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM project
    WHERE user_id = p_user_id
    AND created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours';
    
    RETURN v_count < 2;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION check_user_project_limit IS 'Verifica si usuario puede crear proyecto (límite 2/24h)';


-- Función: Lock automático de sesión al llegar a 10 mensajes
CREATE OR REPLACE FUNCTION lock_session_at_10_messages()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.message_count >= 10 THEN
        UPDATE chat_session
        SET is_locked = TRUE
        WHERE id = NEW.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para lock automático
DROP TRIGGER IF EXISTS trg_lock_session ON chat_session;
CREATE TRIGGER trg_lock_session
    AFTER UPDATE ON chat_session
    FOR EACH ROW
    EXECUTE FUNCTION lock_session_at_10_messages();

COMMENT ON FUNCTION lock_session_at_10_messages IS 'Bloquea sesión automáticamente al llegar a 10 mensajes';


-- Función: Registrar auditoría de cambios
CREATE OR REPLACE FUNCTION audit_user_changes()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (user_id, action, resource_type, resource_id, details, created_at)
    VALUES (
        NEW.id,
        'update_profile',
        'user',
        NEW.id,
        jsonb_build_object(
            'old_email', OLD.email,
            'new_email', NEW.email,
            'old_name', OLD.full_name,
            'new_name', NEW.full_name,
            'timestamp', CURRENT_TIMESTAMP
        ),
        CURRENT_TIMESTAMP
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para auditar cambios en usuario
DROP TRIGGER IF EXISTS trg_audit_user_changes ON "user";
CREATE TRIGGER trg_audit_user_changes
    AFTER UPDATE ON "user"
    FOR EACH ROW
    EXECUTE FUNCTION audit_user_changes();

COMMENT ON FUNCTION audit_user_changes IS 'Audita cambios realizados en perfiles de usuario';


-- ============================================
-- DATOS DE EJEMPLO (Opcional)
-- ============================================

-- INSERT INTO "user" (email, password_hash, rut, full_name, role) VALUES
-- ('admin@preincubadora.cl', 'hashed_password_here', '12345678-9', 'Admin Usuario', 'admin'),
-- ('emprendedor@preincubadora.cl', 'hashed_password_here', '98765432-1', 'Juan Pérez', 'user');

-- INSERT INTO project (user_id, title, raw_idea, variability_score, status) VALUES
-- (1, 'App de Delivery', 'Vender comida en línea', 35, 'ready');


-- ============================================
-- MIGRACIONES Y ACTUALIZACIONES
-- ============================================

-- MIGRACIÓN: Agregar campos de recuperación de contraseña (2026-01-19)
-- Ejecutar esta sección si la tabla "user" ya existe sin estos campos
/*
ALTER TABLE "user"
ADD COLUMN IF NOT EXISTS reset_token VARCHAR(255) UNIQUE,
ADD COLUMN IF NOT EXISTS reset_token_expiry TIMESTAMP,
ADD COLUMN IF NOT EXISTS last_project_creation TIMESTAMP;

-- Crear índice para el token de recuperación
CREATE INDEX IF NOT EXISTS idx_user_reset_token ON "user"(reset_token);

-- Actualizar comentarios
COMMENT ON COLUMN "user".reset_token IS 'Token UUID para recuperación de contraseña (único, temporal)';
COMMENT ON COLUMN "user".reset_token_expiry IS 'Fecha/hora de expiración del token de recuperación (1 hora)';
COMMENT ON COLUMN "user".last_project_creation IS 'Timestamp del último proyecto creado (para rate limiting)';
*/

-- MIGRACIÓN: Agregar campos GDPR/LPD (2026-01-19)
-- Ejecutar esta sección para agregar conformidad con GDPR/LPD
/*
ALTER TABLE "user"
ADD COLUMN IF NOT EXISTS consent_given BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN IF NOT EXISTS consent_timestamp TIMESTAMP,
ADD COLUMN IF NOT EXISTS consent_ip VARCHAR(45),
ADD COLUMN IF NOT EXISTS consent_version VARCHAR(20),
ADD COLUMN IF NOT EXISTS scheduled_deletion TIMESTAMP;

-- Crear índice para eliminaciones programadas
CREATE INDEX IF NOT EXISTS idx_user_scheduled_deletion ON "user"(scheduled_deletion);

-- Actualizar usuarios existentes (migración data)
UPDATE "user" SET consent_given = TRUE WHERE consent_given IS NULL OR consent_given = FALSE;
UPDATE "user" SET consent_timestamp = created_at WHERE consent_timestamp IS NULL;
UPDATE "user" SET consent_version = '1.0' WHERE consent_version IS NULL;

-- Actualizar comentarios
COMMENT ON COLUMN "user".consent_given IS 'GDPR: Consentimiento explícito otorgado por el usuario';
COMMENT ON COLUMN "user".consent_timestamp IS 'GDPR: Fecha/hora exacta del consentimiento (trazabilidad)';
COMMENT ON COLUMN "user".consent_ip IS 'GDPR: IP desde donde se otorgó el consentimiento';
COMMENT ON COLUMN "user".consent_version IS 'GDPR: Versión de los Términos y Condiciones aceptada';
COMMENT ON COLUMN "user".scheduled_deletion IS 'GDPR: Fecha programada para hard delete (30 días tras soft delete)';
*/
COMMENT ON COLUMN "user".reset_token_expiry IS 'Fecha/hora de expiración del token de recuperación (1 hora)';
COMMENT ON COLUMN "user".last_project_creation IS 'Timestamp del último proyecto creado (para rate limiting)';
*/

-- (2, 'Plataforma de Delivery Local', 'Una app para pedir comida de restaurantes cercanos', 45, 'ambiguous'),
-- (2, 'Software de Gestión de Riesgos', 'Sistema para analizar y mitigar riesgos empresariales', 72, 'ready');


-- ============================================
-- FIN DEL SCHEMA
-- ============================================
