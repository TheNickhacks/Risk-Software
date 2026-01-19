"""
Módulo de conexión a base de datos con Neon DB (PostgreSQL 17)
"""
import os
import logging
from sqlalchemy import create_engine, event, pool
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Configuración de base de datos Neon DB"""
    
    def __init__(self):
        self.host = os.getenv("DB_HOST")
        self.port = os.getenv("DB_PORT", "5432")
        self.database = os.getenv("DB_NAME")
        self.user = os.getenv("DB_USER")
        self.password = os.getenv("DB_PASSWORD")
        self.ssl_mode = os.getenv("DB_SSL_MODE", "require")
        
        # URL de conexión desde .env (prioridad)
        self.database_url = os.getenv("DATABASE_URL")
        
        if not self.database_url:
            # Construir URL si no existe DATABASE_URL
            self.database_url = self._build_connection_string()
        
        logger.info(f"Database configured for: {self.host}")
    
    def _build_connection_string(self) -> str:
        """Construye la connection string de PostgreSQL"""
        if not all([self.host, self.database, self.user, self.password]):
            raise ValueError("Missing required database configuration in .env")
        
        return (
            f"postgresql://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
            f"?sslmode={self.ssl_mode}&channel_binding=require"
        )


def create_db_engine():
    """
    Crea el engine de SQLAlchemy para Neon DB
    
    Returns:
        Engine: Motor de SQLAlchemy configurado
    """
    config = DatabaseConfig()
    
    try:
        # Usar NullPool para Neon DB (recomienda para serverless)
        engine = create_engine(
            config.database_url,
            poolclass=pool.NullPool,
            echo=os.getenv("FLASK_DEBUG", "False").lower() == "true",
            connect_args={
                "connect_timeout": 10,
            }
        )
        
        # Test de conexión
        with engine.connect() as conn:
            logger.info("✓ Conexión a Neon DB establecida correctamente")
        
        return engine
    
    except Exception as e:
        logger.error(f"✗ Error al conectar a Neon DB: {str(e)}")
        raise


def init_db(app):
    """
    Inicializa la base de datos con la aplicación Flask
    
    Args:
        app: Instancia de Flask
    """
    try:
        from app.models import db
        
        # Actualizar configuración
        app.config["SQLALCHEMY_DATABASE_URI"] = DatabaseConfig().database_url
        
        # Inicializar db con app
        db.init_app(app)
        
        # Context para operaciones fuera de request
        with app.app_context():
            db.create_all()
            logger.info("✓ Base de datos inicializada")
        
        return True
    
    except Exception as e:
        logger.error(f"✗ Error inicializando base de datos: {str(e)}")
        raise


# Exportar para uso en aplicación
__all__ = ["DatabaseConfig", "create_db_engine", "init_db"]
