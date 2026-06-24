from app import create_app
from app.extensions import db, bcrypt
from app.models import Rol, Usuario


app = create_app()

with app.app_context():
    #Crear los roles
    if not Rol.query.first():
        rol_auxiliar = Rol(nombre='Auxiliar')
        rol_docente = Rol(nombre='Docente')
        rol_estudiante = Rol(nombre='Estudiante')
        
        db.session.add_all([rol_auxiliar, rol_docente, rol_estudiante])
        db.session.commit()
        print("Roles creados exitosamente (Auxiliar, Docente, Estudiante).")

    # 2. Crear tu cuenta maestra (Solo si no existe)
    if not Usuario.query.filter_by(username='admin_aux').first():
        rol_admin = Rol.query.filter_by(nombre='Auxiliar').first()
        
        # Encriptamos la contraseña por seguridad
        hashed_pw = bcrypt.generate_password_hash('discreta123').decode('utf-8')
        
        admin_user = Usuario(
            nombres='Jose David',
            apellidos='Lecoña Huayhua',
            ci='0000000',
            ru=None,  # Como definimos, el RU no es obligatorio
            username='admin_aux',
            password_hash=hashed_pw,
            rol_id=rol_admin.id
        )
        db.session.add(admin_user)
        db.session.commit()
        print("Cuenta maestra creada exitosamente.")
        print("--> Usuario: admin_aux")
        print("--> Clave: discreta123")
    else:
        print("La cuenta administradora ya existe en la base de datos.")