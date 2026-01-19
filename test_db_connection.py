#!/usr/bin/env python
"""
Script para verificar conexión a Neon DB
Uso: python test_db_connection.py
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2 import sql
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()


def test_direct_connection():
    """Test de conexión directa con psycopg2"""
    logger.info("=" * 60)
    logger.info("PROBANDO CONEXIÓN DIRECTA A NEON DB")
    logger.info("=" * 60)
    
    try:
        # Leer variables de conexión
        db_config = {
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'sslmode': os.getenv('DB_SSL_MODE', 'require'),
        }
        
        logger.info(f"🔍 Intentando conectar a: {db_config['host']}")
        
        # Conectar
        conn = psycopg2.connect(**db_config)
        logger.info("✅ Conexión establecida exitosamente")
        
        # Obtener información de la conexión
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        logger.info(f"📊 PostgreSQL version: {version[0]}")
        
        # Listar tablas existentes
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        
        if tables:
            logger.info(f"📋 Tablas existentes ({len(tables)}):")
            for table in tables:
                logger.info(f"   - {table[0]}")
        else:
            logger.warning("⚠️  No hay tablas en la base de datos")
        
        # Cerrar conexión
        cursor.close()
        conn.close()
        
        logger.info("✅ Test de conexión directa: EXITOSO")
        return True
    
    except Exception as e:
        logger.error(f"❌ Error en conexión directa: {str(e)}")
        return False


def test_sqlalchemy_connection():
    """Test de conexión con SQLAlchemy"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("PROBANDO CONEXIÓN CON SQLALCHEMY")
    logger.info("=" * 60)
    
    try:
        from app.database import create_db_engine
        
        logger.info("🔍 Creando motor SQLAlchemy...")
        engine = create_db_engine()
        
        logger.info("✅ Motor SQLAlchemy creado exitosamente")
        
        # Test con inspect
        from sqlalchemy import inspect, text
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if tables:
            logger.info(f"📋 Tablas accesibles ({len(tables)}):")
            for table in tables:
                logger.info(f"   - {table}")
        else:
            logger.warning("⚠️  No hay tablas accesibles")
        
        logger.info("✅ Test de SQLAlchemy: EXITOSO")
        return True
    
    except Exception as e:
        logger.error(f"❌ Error en SQLAlchemy: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_flask_app_connection():
    """Test de conexión con Flask App"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("PROBANDO CONEXIÓN CON FLASK APP")
    logger.info("=" * 60)
    
    try:
        from app import create_app
        
        logger.info("🔍 Creando aplicación Flask...")
        app = create_app()
        
        logger.info("✅ Aplicación Flask creada exitosamente")
        
        with app.app_context():
            from app.models import db
            
            logger.info("🔍 Verificando conexión DB...")
            conn = db.engine.connect()
            result = conn.execute(db.text("SELECT 1"))
            conn.close()
            
            logger.info("✅ Test de Flask App: EXITOSO")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Error en Flask App: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ejecutar todos los tests"""
    logger.info("\n" + "=" * 60)
    logger.info("INICIANDO TESTS DE CONEXIÓN A NEON DB")
    logger.info("=" * 60)
    
    results = {
        "Conexión Directa": test_direct_connection(),
        "SQLAlchemy": test_sqlalchemy_connection(),
        "Flask App": test_flask_app_connection(),
    }
    
    logger.info("\n" + "=" * 60)
    logger.info("RESUMEN DE RESULTADOS")
    logger.info("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ EXITOSO" if result else "❌ FALLÓ"
        logger.info(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        logger.info("\n🎉 TODOS LOS TESTS PASARON - Base de datos configurada correctamente")
        return 0
    else:
        logger.error("\n⚠️  ALGUNOS TESTS FALLARON - Revisa la configuración")
        return 1


if __name__ == "__main__":
    sys.exit(main())
