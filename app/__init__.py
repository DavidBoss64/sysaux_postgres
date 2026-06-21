import os
from flask import Flask
from config import Config
from .extensions import db, login_manager, bcrypt, migrate # Importamos las nuevas extensiones

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    if not os.path.exists(app.instance_path):
        os.makedirs(app.instance_path)

    # Inicializamos todas las extensiones
    db.init_app(app)
    migrate.init_app(app,db)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    # Dentro de mi función de configuración de extensiones o en create_app():
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, inicia sesión para acceder a esta sección del sistema.'
    login_manager.login_message_category = 'warning'
        
    with app.app_context():
        from . import models
        db.create_all()
        
        # Registramos los Blueprints
        from .main import main_bp
        app.register_blueprint(main_bp)
        
        from .auth import auth_bp
        app.register_blueprint(auth_bp, url_prefix='/auth') # Todas las rutas de login empezarán con /auth
        
        from .gestion import gestion_bp
        app.register_blueprint(gestion_bp, url_prefix='/gestion')

            # -Registramos el módulo de reportes ---
        from app.reportes import reportes_bp
        app.register_blueprint(reportes_bp)

        from app.configuracion import configuracion_bp
        app.register_blueprint(configuracion_bp, url_prefix='/configuracion')

    return app