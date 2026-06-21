import os
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError  
from sqlalchemy import or_
from openpyxl import load_workbook         
from datetime import datetime
from . import gestion_bp
from ..models import Paralelo, Usuario, Inscripcion, Rol
from ..extensions import db, bcrypt

@gestion_bp.route('/paralelo/<int:id>/estudiantes', methods=['GET', 'POST'])
@login_required
def estudiantes(id):
    paralelo = Paralelo.query.get_or_404(id)
    if paralelo.auxiliar_id != current_user.id:
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('gestion.paralelos'))

    if request.method == 'POST':
        nombres = request.form.get('nombres')
        apellidos = request.form.get('apellidos')
        ci = request.form.get('ci')
        ru = request.form.get('ru')

        estudiante = Usuario.query.filter_by(ci=ci).first()
        
        if not estudiante:
            rol_estudiante = Rol.query.filter_by(nombre='Estudiante').first()
            hashed_pw = bcrypt.generate_password_hash(ci).decode('utf-8')
            estudiante = Usuario(
                nombres=nombres.upper(), 
                apellidos=apellidos.upper(), 
                ci=ci, 
                ru=ru if ru else None, 
                username=ci, 
                password_hash=hashed_pw, 
                rol_id=rol_estudiante.id,
                estado=True
            )
            db.session.add(estudiante)
            
            # Control de duplicados en el registro manual unificado
            try:
                db.session.flush()
            except IntegrityError:
                db.session.rollback()
                flash('Error: El C.I. o el R.U. ingresado ya le pertenece a otra cuenta en el sistema.', 'danger')
                return redirect(url_for('gestion.estudiantes', id=id))

    # Control de la inscripción manual garantizando el estado activo
        inscripcion_previa = Inscripcion.query.filter_by(estudiante_id=estudiante.id, paralelo_id=id).first()
        
        if sig_insc := inscripcion_previa:
            if not sig_insc.estado:
                sig_insc.estado = True # Lo restauro si fue dado de baja previamente
                flash('Inscripción del estudiante reactivada.', 'success')
            else:
                flash('El estudiante ya está inscrito en este paralelo.', 'warning')
        else:
            nueva_inscripcion = Alignment = Inscripcion(estudiante_id=estudiante.id, paralelo_id=id, estado=True)
            db.session.add(nueva_inscripcion)
            flash('Estudiante inscrito exitosamente.', 'success')
            
        db.session.commit()
        return redirect(url_for('gestion.estudiantes', id=id))

    # Consulto las inscripciones activas y las ordeno alfabéticamente por el apellido del estudiante
    inscripciones_bd = Inscripcion.query.filter_by(paralelo_id=id, estado=True).all()
    inscripciones = sorted(inscripciones_bd, key=lambda i: (i.estudiante.apellidos, i.estudiante.nombres))
    return render_template('gestion/estudiantes.html', paralelo=paralelo, inscripciones=inscripciones)

@gestion_bp.route('/estudiante/<int:id>/editar', methods=['POST'])
@login_required
def editar_estudiante(id):
    estudiante = Usuario.query.get_or_404(id)
    paralelo_id = request.form.get('paralelo_id')
    
    estudiante.nombres = request.form.get('nombres').upper()
    estudiante.apellidos = request.form.get('apellidos').upper()
    estudiante.ci = request.form.get('ci')
    estudiante.ru = request.form.get('ru') or None
    
    try:
        db.session.commit()
        flash('Datos del estudiante actualizados correctamente.', 'success')
    except IntegrityError:
        db.session.rollback() 
        flash('Error de duplicidad: El C.I. o el R.U. que intentas asignar ya le pertenece a otro estudiante.', 'danger')
        
    return redirect(url_for('gestion.estudiantes', id=paralelo_id))

@gestion_bp.route('/inscripcion/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_inscripcion(id):
    inscripcion = Inscripcion.query.get_or_404(id)
    paralelo_id = inscripcion.paralelo_id
    if inscripcion.paralelo.auxiliar_id == current_user.id:
        inscripcion.estado = False
        db.session.commit()
        flash('Estudiante dado de baja del paralelo.', 'info')
    return redirect(url_for('gestion.estudiantes', id=paralelo_id))


# ==============================================================================
# MOTOR BLINDADO: SAVEPOINTS Y DOBLE VERIFICACIÓN ANTI-COLISIONES
# ==============================================================================
@gestion_bp.route('/paralelo/<int:id>/importar_estudiantes', methods=['POST'])
@login_required
def importar_estudiantes(id):
    paralelo = Paralelo.query.get_or_404(id)
    
    if paralelo.auxiliar_id != current_user.id:
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('gestion.paralelos'))

    if 'archivo_excel' not in request.files:
        flash('No se seleccionó ningún archivo.', 'danger')
        return redirect(url_for('gestion.estudiantes', id=id))

    file = request.files['archivo_excel']
    if file.filename == '':
        flash('El archivo no tiene un nombre válido.', 'danger')
        return redirect(url_for('gestion.estudiantes', id=id))

    if file and file.filename.endswith(('.xlsx', '.xlsm')):
        try:
            wb = load_workbook(file, data_only=True)
            ws = wb.active 

            alumnos_inscritos = 0
            alumnos_existentes_en_paralelo = 0
            errores_omitidos = 0 # Contador para saber cuántos chocaron
            rol_estudiante = Rol.query.filter_by(nombre='Estudiante').first()

            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row or row[0] is None:
                    continue

                nombre_completo_crudo = str(row[0]).strip()
                ci = str(row[1]).strip()
                ru = str(row[2]).strip() if len(row) > 2 and row[2] is not None else None

                if not nombre_completo_crudo or not ci:
                    continue

                # Parseo sintáctico de nombres
                if ',' in nombre_completo_crudo:
                    partes = nombre_completo_crudo.split(',')
                    apellidos = partes[0].strip().upper()
                    nombres = partes[1].strip().upper()
                else:
                    palabras = nombre_completo_crudo.split()
                    if len(palabras) >= 4:
                        apellidos = f"{palabras[0]} {palabras[1]}".upper()
                        nombres = " ".join(palabras[2:]).upper()
                    elif len(palabras) == 3:
                        apellidos = f"{palabras[0]} {palabras[1]}".upper()
                        nombres = palabras[2].upper()
                    elif len(palabras) == 2:
                        apellidos = palabras[0].upper()
                        nombres = palabras[1].upper()
                    else:
                        apellidos = "SIN APELLIDO"
                        nombres = palabras[0].upper()

                # PASO 1: Búsqueda expansiva. Verifico si el CI ya existe como 'ci' o como 'username'
                estudiante = Usuario.query.filter(or_(Usuario.ci == ci, Usuario.username == ci)).first()

                if not estudiante:
                    # Si es nuevo, uso un SAVEPOINT. Si algo explota aquí, no afecta al resto de la lista.
                    try:
                        with db.session.begin_nested():
                            hashed_pw = bcrypt.generate_password_hash(ci).decode('utf-8')
                            estudiante = Usuario(
                                nombres=nombres, 
                                apellidos=apellidos, 
                                ci=ci, 
                                ru=ru, 
                                username=ci, 
                                password_hash=hashed_pw, 
                                rol_id=rol_estudiante.id,
                                estado=True
                            )
                            db.session.add(estudiante)
                    except IntegrityError:
                        # Si chocó por un R.U. duplicado o algo similar, lo ignoramos y pasamos al siguiente
                        errores_omitidos += 1
                        continue 

                # PASO 2: Matriculación con Savepoint
                if estudiante: # Me aseguro de que el estudiante exista en este punto
                    inscripcion_existente = Inscripcion.query.filter_by(
                        paralelo_id=paralelo.id, 
                        estudiante_id=estudiante.id
                    ).first()

                    if not inscripcion_existente:
                        try:
                            with db.session.begin_nested():
                                nueva_inscripcion = Inscripcion(
                                    paralelo_id=paralelo.id,
                                    estudiante_id=estudiante.id,
                                    fecha_inscripcion=datetime.now(),
                                    estado=True
                                )
                                db.session.add(nueva_inscripcion)
                                alumnos_inscritos += 1
                        except IntegrityError:
                            errores_omitidos += 1
                            continue
                    else:
                        if not inscripcion_existente.estado:
                            try:
                                with db.session.begin_nested():
                                    inscripcion_existente.estado = True
                                    alumnos_inscritos += 1
                            except IntegrityError:
                                errores_omitidos += 1
                                continue
                        else:
                            alumnos_existentes_en_paralelo += 1

            # Aplico el COMMIT final que guardará a todos los alumnos exitosos de un solo golpe
            db.session.commit()
            
            # Reporte detallado al usuario
            if alumnos_inscritos > 0:
                flash(f'Éxito: Se matricularon {alumnos_inscritos} estudiantes correctamente.', 'success')
            if alumnos_existentes_en_paralelo > 0:
                flash(f'Aviso: {alumnos_existentes_en_paralelo} alumnos del Excel ya estaban inscritos.', 'info')
            if errores_omitidos > 0:
                flash(f'Advertencia: Se omitieron {errores_omitidos} filas por conflicto de datos (Ej: R.U. duplicado).', 'warning')
            if alumnos_inscritos == 0 and alumnos_existentes_en_paralelo == 0 and errores_omitidos == 0:
                flash('No se encontraron registros válidos para importar en el archivo.', 'danger')

        except Exception as e:
            db.session.rollback()
            flash(f'Error al procesar el archivo Excel: Asegúrate de usar el formato correcto.', 'danger')
            print(f"Error interno: {str(e)}") # Para que lo veas en la consola sin asustar al usuario web
    else:
        flash('Formato no permitido. Sube un archivo Excel válido (.xlsx).', 'danger')

    return redirect(url_for('gestion.estudiantes', id=id))