from app import create_app
from app.extensions import db, bcrypt
from app.models import Usuario, Rol

app = create_app()

# INYECCIÓN AUTOMÁTICA DE ROLES Y ADMINISTRADOR
with app.app_context():
    
    # 1. Verificamos y creamos TODOS los roles base del sistema
    roles_necesarios = ['Auxiliar', 'Estudiante', 'Docente']
    
    for nombre_rol in roles_necesarios:
        rol_existente = Rol.query.filter_by(nombre=nombre_rol).first()
        if not rol_existente:
            nuevo_rol = Rol(nombre=nombre_rol)
            db.session.add(nuevo_rol)
            print(f"Rol '{nombre_rol}' creado exitosamente.")
            
    # Guardamos todos los roles en la base de datos para que existan
    db.session.commit()

    # 2. Obtenemos el ID del rol Auxiliar para asignártelo
    rol_auxiliar = Rol.query.filter_by(nombre='Auxiliar').first()

    # 3. Verificamos si tu usuario ya existe
    admin_existente = Usuario.query.filter_by(username='admin').first()
    
    if not admin_existente and rol_auxiliar:
        # AQUÍ PON LA CONTRASEÑA REAL QUE QUIERAS USAR
        password_encriptada = bcrypt.generate_password_hash('tu_contraseña_123').decode('utf-8')
        
        nuevo_admin = Usuario(
            nombres='José David', 
            apellidos='Lecoña Huayhua', 
            ci='1234567', # Cambia a tu C.I. real
            username='admin', 
            password_hash=password_encriptada, 
            rol_id=rol_auxiliar.id, 
            estado=True
        )
        db.session.add(nuevo_admin)
        db.session.commit()
        print("¡Cuenta maestra inyectada exitosamente en PostgreSQL!")

if __name__ == '__main__':
    app.run()