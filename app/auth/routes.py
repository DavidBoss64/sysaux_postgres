from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError
from . import auth_bp
from ..models import Usuario, Rol, Paralelo, Inscripcion
from ..extensions import db, bcrypt
import re #Importamos el motor de expresiones regulares de Python

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Si intento entrar al login ya estando logueado, me auto-redirijo al Dashboard
    if current_user.is_authenticated:
        if current_user.rol.nombre.lower() in ['administrador', 'auxiliar']:
            return redirect(url_for('main.index'))
        return redirect(url_for('estudiante.dashboard'))

    if request.method == 'POST':
        # Capturamos el usuario tal cual lo escribe el estudiante, sin forzar mayúsculas
        username_input = request.form.get('username')
        password = request.form.get('password')

        # Buscamos al usuario de forma exacta (respetando mayúsculas/minúsculas)
        # Esto permite que el username sea "José" o "jose" y el sistema los diferencie
        usuario = Usuario.query.filter_by(username=username_input).first()

        # Valido la existencia y la contraseña encriptada
        if usuario and bcrypt.check_password_hash(usuario.password_hash, password):
            if not usuario.estado:
                flash('Esta cuenta se encuentra inactiva. Comunícate con el administrador.', 'danger')
                return redirect(url_for('auth.login'))

            # Levanto la sesión segura en Flask
            login_user(usuario)
            
            # Redirección inteligente al Dashboard Principal de mi rol
            if usuario.rol.nombre.lower() in ['administrador', 'auxiliar']:
                flash(f'Bienvenido al sistema, {usuario.nombres}.', 'success')
                return redirect(url_for('main.index'))
            else:
                flash(f'Hola {usuario.nombres}, has iniciado sesión correctamente.', 'success')
                return redirect(url_for('estudiante.dashboard'))
        else:
            flash('Credenciales incorrectas. Por favor, intenta de nuevo.', 'danger')
            return redirect(url_for('auth.login'))

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    if request.method == 'POST':
        password_actual = request.form.get('password_actual')
        password_nueva = request.form.get('password_nueva')
        password_confirmar = request.form.get('password_confirmar')

        # 1. Verificamos que la contraseña actual sea correcta
        if not bcrypt.check_password_hash(current_user.password_hash, password_actual):
            flash('La contraseña actual ingresada es incorrecta.', 'danger')
            return redirect(url_for('auth.perfil'))

        # 2. Verificamos que las contraseñas nuevas coincidan
        if password_nueva != password_confirmar:
            flash('Las contraseñas nuevas no coinciden.', 'warning')
            return redirect(url_for('auth.perfil'))

        # 3. Validamos longitud por seguridad
        if len(password_nueva) < 6:
            flash('La nueva contraseña debe tener al menos 6 caracteres.', 'warning')
            return redirect(url_for('auth.perfil'))

        # 4. Encriptamos y guardamos la nueva clave
        current_user.password_hash = bcrypt.generate_password_hash(password_nueva).decode('utf-8')
        db.session.commit()
        
        flash('¡Tu contraseña ha sido actualizada con éxito! Utilízala en tu próximo inicio de sesión.', 'success')
        return redirect(url_for('auth.perfil'))

    return render_template('auth/perfil.html')

@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        nombres = request.form.get('nombres', '').strip().upper()
        apellidos = request.form.get('apellidos', '').strip().upper()
        
        # --- NUEVO: Sanitización estricta de CI y RU ---
        ci_crudo = request.form.get('ci', '').strip()
        # \D significa "cualquier cosa que NO sea un número". Lo reemplazamos por nada ('').
        ci = re.sub(r'\D', '', ci_crudo) 
        
        ru_crudo = request.form.get('ru', '').strip()
        ru = re.sub(r'\D', '', ru_crudo) if ru_crudo else None
        
        codigo = request.form.get('codigo_inscripcion', '').strip().upper()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')

        # Creamos un diccionario con los datos ingresados para devolverlos si hay error
        form_data = {
            'nombres': nombres,
            'apellidos': apellidos,
            'ci': ci,
            'ru': ru if ru else '',
            'codigo_inscripcion': codigo
        }

        # Validación 1: Contraseñas coinciden
        if password != password_confirm:
            flash('Las contraseñas no coinciden. Por favor, verifícalas.', 'warning')
            return render_template('auth/registro.html', **form_data)

        # Validación 2: El código de inscripción secreto
        paralelo = Paralelo.query.filter_by(codigo_inscripcion=codigo, estado=True).first()
        if not paralelo:
            flash('El código de inscripción es inválido. Verifica mayúsculas o consúltalo con tu Auxiliar.', 'danger')
            return render_template('auth/registro.html', **form_data)

        # Validación 3: Verificar si el alumno ya existe en el sistema
        if Usuario.query.filter_by(ci=ci).first():
            flash('Este C.I. ya está registrado en el sistema. Si olvidaste tu contraseña, pide al Auxiliar que la restablezca.', 'warning')
            return render_template('auth/registro.html', **form_data)

        # Crear el Usuario y su Inscripción en un solo paso
        try:
            rol_estudiante = Rol.query.filter_by(nombre='Estudiante').first()
            hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
            
            nuevo_usuario = Usuario(
                nombres=nombres,
                apellidos=apellidos,
                ci=ci,
                ru=ru,
                username=ci,
                password_hash=hashed_pw,
                rol_id=rol_estudiante.id,
                estado=True
            )
            db.session.add(nuevo_usuario)
            db.session.flush() 

            nueva_inscripcion = Inscripcion(
                estudiante_id=nuevo_usuario.id,
                paralelo_id=paralelo.id,
                estado=True
            )
            db.session.add(nueva_inscripcion)
            
            db.session.commit()
            flash(f'¡Cuenta creada exitosamente! Has sido inscrito en {paralelo.materia.nombre} (Paralelo {paralelo.nombre}). Ya puedes iniciar sesión.', 'success')
            return redirect(url_for('auth.login'))

        except IntegrityError:
            db.session.rollback()
            flash('Ocurrió un error al crear la cuenta. Verifica que el C.I. o R.U. no estén duplicados.', 'danger')
            return render_template('auth/registro.html', **form_data)

    return render_template('auth/registro.html')