from flask import render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from . import auth_bp
from ..models import Usuario
from ..extensions import bcrypt

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Si intento entrar al login ya estando logueado, me auto-redirijo al Dashboard
    if current_user.is_authenticated:
        if current_user.rol.nombre.lower() in ['administrador', 'auxiliar']:
            return redirect(url_for('main.index'))
        return redirect(url_for('estudiante.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')

        # Busco mis credenciales en la tabla unificada de Usuarios
        usuario = Usuario.query.filter_by(username=username).first()

        # Valido la existencia y la contraseña encriptada
        if usuario and bcrypt.check_password_hash(usuario.password_hash, password):
            if not usuario.estado:
                flash('Esta cuenta se encuentra inactiva. Comunícate con el administrador.', 'danger')
                return redirect(url_for('auth.login'))

            # Levanto la sesión segura en Flask
            login_user(usuario)
            
            # --- CORRECCIÓN DE FLUJO ---
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
