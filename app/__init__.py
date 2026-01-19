from flask import Flask
from flask_login import LoginManager
from config import config
import logging
from logging.handlers import RotatingFileHandler
import os
from dotenv import load_dotenv

# Cargar variables de entorno al iniciar
load_dotenv()

from app.models import db, User


def create_app(config_name: str = None) -> Flask:
    """
    Application Factory - Inicializar aplicación Flask
    Conecta automáticamente a Neon DB
    """
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    # Ajustar engine options según el tipo de base de datos
    db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    engine_opts = dict(app.config.get("SQLALCHEMY_ENGINE_OPTIONS", {}))
    if db_uri.startswith("postgresql") or db_uri.startswith("postgres"):
        # Mantener configuración para Neon (serverless Postgres)
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_opts
    else:
        # Remover opciones no compatibles con SQLite
        engine_opts.pop("poolclass", None)
        engine_opts.pop("connect_args", None)
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_opts
    
    # Log de configuración de base de datos
    app.logger.info(f"🔌 Conectando a base de datos: {os.getenv('DB_HOST', 'localhost')}")
    
    # Inicializar extensiones
    db.init_app(app)
    
    # Configurar Login Manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Por favor, inicia sesión para acceder a esta página."
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)
    
    # Crear contexto de aplicación y base de datos
    with app.app_context():
        # Importar modelos para que SQLAlchemy los registre
        from app import models
        
        # Crear tablas
        db.create_all()
        
        # Registrar blueprints (rutas)
        from app.routes import auth_bp, dashboard_bp, project_bp, chat_bp
        
        app.register_blueprint(auth_bp)
        app.register_blueprint(dashboard_bp)
        app.register_blueprint(project_bp)
        app.register_blueprint(chat_bp)
    
    # Configurar logging
    setup_logging(app)
    
    @app.shell_context_processor
    def make_shell_context():
        return {"db": db, "User": User}
    
    return app


def setup_logging(app: Flask) -> None:
    """Configurar sistema de logs con rotación"""
    if not os.path.exists("logs"):
        os.mkdir("logs")
    
    file_handler = RotatingFileHandler(
        "logs/preincubadora.log",
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
    ))
    file_handler.setLevel(logging.INFO)
    
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info("=== PreIncubadora AI - Iniciando ===")
