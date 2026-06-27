from app import create_app
from app.extensions import db, bcrypt
from app.models import Usuario, Rol

app = create_app()

with app.app_context():
    try:
        # 1. Roles
        roles_necesarios = ['Auxiliar', 'Estudiante', 'Docente']
        for nombre_rol in roles_necesarios:
            if not Rol.query.filter_by(nombre=nombre_rol).first():
                db.session.add(Rol(nombre=nombre_rol))
        db.session.commit()

        # 2. Inyección segura de Administrador
        # Verificamos si existe por username O por CI para evitar el conflicto
        if not Usuario.query.filter_by(username='admin').first() and \
           not Usuario.query.filter_by(ci='13828757').first():
            
            rol_auxiliar = Rol.query.filter_by(nombre='Auxiliar').first()
            password_encriptada = bcrypt.generate_password_hash('tu_contraseña_123').decode('utf-8')
            
            nuevo_admin = Usuario(
                nombres='José David', 
                apellidos='Lecoña Huayhua', 
                ci='13828757', 
                username='admin', 
                password_hash=password_encriptada, 
                rol_id=rol_auxiliar.id, 
                estado=True
            )
            db.session.add(nuevo_admin)
            db.session.commit()
            print("Administrador creado.")
            
    except Exception as e:
        db.session.rollback()
        print(f"La base de datos ya está inicializada o hubo un error: {e}")

if __name__ == '__main__':
    app.run()