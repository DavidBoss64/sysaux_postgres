import os

# Obtiene la ruta absoluta del proyecto
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Llave secreta para proteger las sesiones y contraseñas
    # Intentará buscarla en la nube, y si no está, usará esta por defecto para desarrollo local
    SECRET_KEY = os.environ.get('SECRET_KEY') or "clave-secreta-super-segura-byte-soft"
    
    # 1. Buscamos la URL de la base de datos en la nube (Variables de Entorno de Render)
    database_url = os.environ.get('DATABASE_URL')

    # 2. Parche de compatibilidad: SQLAlchemy exige 'postgresql://' pero Render a veces entrega 'postgres://'
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    # 3. Si existe la URL de la nube, usa PostgreSQL. Si está vacío (en tu PC), usa SQLite local.
    SQLALCHEMY_DATABASE_URI = database_url or "sqlite:///" + os.path.join(BASE_DIR, "instance", "sysaux.db")
    
    # Apagamos esto para ahorrar memoria en el servidor
    SQLALCHEMY_TRACK_MODIFICATIONS = False