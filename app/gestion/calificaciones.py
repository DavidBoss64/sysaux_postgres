from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from . import gestion_bp
from ..models import Actividad, Inscripcion, Calificacion
from ..extensions import db
from flask import jsonify

@gestion_bp.route('/actividad/<int:id>/calificar', methods=['GET', 'POST'])
@login_required
def calificar_actividad(id):
    actividad = Actividad.query.get_or_404(id)
    paralelo = actividad.parametro.paralelo
    tipo_parametro = actividad.parametro.tipo  # 'normal' o 'asistencia'
    
    if paralelo.auxiliar_id != current_user.id:
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('gestion.paralelos'))

    # Consultamos las inscripciones activas y las ordenamos exactamente igual que en los reportes
    inscripciones_bd = Inscripcion.query.filter_by(paralelo_id=paralelo.id, estado=True).all()
    inscripciones = sorted(inscripciones_bd, key=lambda i: (i.estudiante.apellidos, i.estudiante.nombres))
    calificaciones_bd = Calificacion.query.filter_by(actividad_id=actividad.id).all()
    notas_actuales = {c.estudiante_id: c.puntaje for c in calificaciones_bd}

    if request.method == 'POST':
        for inscripcion in inscripciones:
            estudiante_id = inscripcion.estudiante_id
            calificacion_existente = Calificacion.query.filter_by(actividad_id=actividad.id, estudiante_id=estudiante_id).first()

            if tipo_parametro == 'asistencia':
                # Los checkbox en HTML solo se envían si están tiqueados
                asistio = request.form.get(f'asistencia_{estudiante_id}')
                # Si asistió, gana el puntaje total de la actividad (manejado de forma entera)
                puntaje = actividad.parametro.ponderacion if asistio else 0.0
                
                if calificacion_existente:
                    calificacion_existente.puntaje = puntaje
                else:
                    nueva_nota = Calificacion(actividad_id=actividad.id, estudiante_id=estudiante_id, puntaje=puntaje)
                    db.session.add(nueva_nota)
            else:
                # Lógica normal para prácticas o exámenes
                nota_input = request.form.get(f'nota_{estudiante_id}')
                if nota_input is not None and nota_input.strip() != '':
                    puntaje = float(nota_input)
                    max_pts = actividad.parametro.ponderacion
                    if puntaje > max_pts: puntaje = max_pts
                    if puntaje < 0: puntaje = 0

                    if calificacion_existente:
                        calificacion_existente.puntaje = puntaje
                    else:
                        nueva_nota = Calificacion(actividad_id=actividad.id, estudiante_id=estudiante_id, puntaje=puntaje)
                        db.session.add(nueva_nota)
                else:
                    if calificacion_existente:
                        db.session.delete(calificacion_existente)
                        
        db.session.commit()
        flash('Calificaciones actualizadas con éxito.', 'success')
        return redirect(url_for('gestion.calificar_actividad', id=actividad.id))

    return render_template('gestion/calificaciones.html', 
                        actividad=actividad, 
                        paralelo=paralelo, 
                        inscripciones=inscripciones, 
                        notas=notas_actuales,
                        tipo_parametro=tipo_parametro)

# --- RUTA PARA EL AUTOGUARDADO EN TIEMPO REAL (AJAX) ---
@gestion_bp.route('/actividad/<int:id>/calificar_ajax', methods=['POST'])
@login_required
def calificar_actividad_ajax(id):
    actividad = Actividad.query.get_or_404(id)
    
    # Seguridad básica
    if actividad.parametro.paralelo.auxiliar_id != current_user.id:
        return jsonify({'success': False, 'message': 'No autorizado'}), 403

    # Recibimos los datos enviados por Javascript
    data = request.get_json()
    estudiante_id = data.get('estudiante_id')
    valor_input = data.get('valor') # Puede ser un número o un booleano (para asistencia)

    # Buscamos si ya existe una calificación previa
    calificacion = Calificacion.query.filter_by(actividad_id=actividad.id, estudiante_id=estudiante_id).first()

    # Si el valor está vacío, eliminamos la nota (si existía)
    if valor_input == '' or valor_input is None:
        if calificacion:
            db.session.delete(calificacion)
            db.session.commit()
        return jsonify({'success': True, 'accion': 'eliminado'})

    # Lógica para guardar o actualizar
    try:
        puntaje = float(valor_input)
        # Validamos límites
        max_pts = actividad.parametro.ponderacion
        if puntaje > max_pts: puntaje = max_pts
        if puntaje < 0: puntaje = 0

        if calificacion:
            calificacion.puntaje = puntaje
        else:
            nueva_nota = Calificacion(actividad_id=actividad.id, estudiante_id=estudiante_id, puntaje=puntaje)
            db.session.add(nueva_nota)
            
        db.session.commit()
        return jsonify({'success': True, 'accion': 'guardado', 'puntaje_final': puntaje})

    except ValueError:
        return jsonify({'success': False, 'message': 'Valor inválido'}), 400 