import os
from datetime import timedelta
from sqlalchemy.pool import NullPool

class Config:
    """Configuración base de la aplicación"""
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    # Opciones de engine para conexiones serverless (Neon)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,            # Verifica conexión antes de usarla (reconecta si está caída)
        "pool_recycle": 1800,            # Recicla conexiones cada 30 min para evitar timeouts
        "poolclass": NullPool,           # Evita mantener conexiones abiertas (recomendado para Neon serverless)
        "connect_args": {
            "sslmode": "require",
            # TCP keepalive para evitar cierres abruptos
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        },
    }
    
    # Límites de uso
    MAX_PROJECTS_PER_DAY = int(os.getenv("MAX_PROJECTS_PER_DAY", 2))
    MAX_CHAT_MESSAGES = int(os.getenv("MAX_CHAT_MESSAGES", 10))
    AI_AMBIGUITY_QUESTIONS = int(os.getenv("AI_AMBIGUITY_CLARIFICATION_QUESTIONS", 3))
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_REFRESH_EACH_REQUEST = True
    
    # API Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-change-in-production")


class DevelopmentConfig(Config):
    """Configuración de desarrollo"""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///dev.db"
    )
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    """Configuración de producción"""
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    # Validación opcional (omitida para evitar fallos en despliegues con variables tardías)


class TestingConfig(Config):
    """Configuración de testing"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig
}
