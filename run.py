from app import create_app
from app.extensions import db, bcrypt
from app.models import Usuario, Rol

app = create_app()

# INYECCIÓN AUTOMÁTICA DE ROLES Y ADMINISTRADOR CON PROTECCIÓN
with app.app_context():
    try:
        # 1. Creamos los roles base de manera segura
        roles_necesarios = ['Auxiliar', 'Estudiante', 'Docente']
        
        for nombre_rol in roles_necesarios:
            rol_existente = Rol.query.filter_by(nombre=nombre_rol).first()
            if not rol_existente:
                nuevo_rol = Rol(nombre=nombre_rol)
                db.session.add(nuevo_rol)
                print(f"Rol '{nombre_rol}' preparado para creación.")
                
        db.session.commit()

        # 2. Obtenemos el ID del rol Auxiliar para el administrador
        rol_auxiliar = Rol.query.filter_by(nombre='Auxiliar').first()

        # 3. Verificamos e inyectamos el usuario administrador
        admin_existente = Usuario.query.filter_by(username='admin').first()
        
        if not admin_existente and rol_auxiliar:
            # 
            password_encriptada = bcrypt.generate_password_hash('password123').decode('utf-8')
            
            nuevo_admin = Usuario(
                nombres='José David', 
                apellidos='Lecoña Huayhua', 
                ci='1234567', 
                username='admin', 
                password_hash=password_encriptada, 
                rol_id=rol_auxiliar.id, 
                estado=True
            )
            db.session.add(nuevo_admin)
            db.session.commit()
            print("¡Cuenta maestra inyectada exitosamente!")
            
    except Exception as e:
        # Si la base de datos está ocupada o las tablas se están creando,
        # hacemos un rollback para evitar bloquear la base de datos y dejamos que el sistema encienda.
        db.session.rollback()
        print(f"Aviso de inicialización: {e}")

if __name__ == '__main__':
    app.run()