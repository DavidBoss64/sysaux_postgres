from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from . import gestion_bp
from ..models import Paralelo, ParametroEvaluacion
from ..extensions import db

@gestion_bp.route('/paralelo/<int:id>/parametros', methods=['GET', 'POST'])
@login_required
def parametros(id):
    paralelo = Paralelo.query.get_or_404(id)
    if paralelo.auxiliar_id != current_user.id:
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('gestion.paralelos'))

    parametros_bd = ParametroEvaluacion.query.filter_by(paralelo_id=paralelo.id, estado=True).all()
    
    # NUEVA LÓGICA: Solo sumamos los parámetros regulares (normal y asistencia)
    total_puntos = sum(p.ponderacion for p in parametros_bd if p.tipo in ['normal', 'asistencia'])
    tiene_liberacion = any(p.tipo == 'liberacion' for p in parametros_bd)

    if request.method == 'POST':
        nombre = request.form.get('nombre_parametro')
        tipo = request.form.get('tipo')
        ponderacion = float(request.form.get('ponderacion'))
        modo_liberacion = request.form.get('modo_liberacion') if tipo == 'liberacion' else None

        # Validación: Solo los regulares están sujetos al tope de la nota máxima
        if tipo in ['normal', 'asistencia']:
            if total_puntos + ponderacion > paralelo.nota_maxima:
                flash(f'Error: La ponderación excede los {paralelo.nota_maxima} puntos máximos.', 'danger')
                return redirect(url_for('gestion.parametros', id=paralelo.id))
                
        nuevo_parametro = ParametroEvaluacion(
            paralelo_id=paralelo.id,
            nombre_parametro=nombre,
            tipo=tipo,
            ponderacion=ponderacion,
            modo_liberacion=modo_liberacion
        )
        db.session.add(nuevo_parametro)
        db.session.commit()
        flash('Parámetro agregado con éxito.', 'success')
        return redirect(url_for('gestion.parametros', id=paralelo.id))

    return render_template('gestion/parametros.html', 
                        paralelo=paralelo, 
                        parametros=parametros_bd, 
                        total_puntos=total_puntos,
                        tiene_liberacion=tiene_liberacion)

@gestion_bp.route('/parametro/<int:id>/editar', methods=['POST'])
@login_required
def editar_parametro(id):
    parametro = ParametroEvaluacion.query.get_or_404(id)
    paralelo = parametro.paralelo
    
    if paralelo.auxiliar_id != current_user.id:
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('gestion.paralelos'))

    nuevo_nombre = request.form.get('nombre_parametro')
    nueva_ponderacion = float(request.form.get('ponderacion'))

    if parametro.tipo in ['normal', 'asistencia']:
        # Calculamos los puntos de los DEMÁS parámetros regulares
        otros_parametros = ParametroEvaluacion.query.filter(
            ParametroEvaluacion.paralelo_id == paralelo.id,
            ParametroEvaluacion.id != parametro.id,
            ParametroEvaluacion.tipo.in_(['normal', 'asistencia']),
            ParametroEvaluacion.estado == True
        ).all()
        
        puntos_otros = sum(p.ponderacion for p in otros_parametros)
        
        if puntos_otros + nueva_ponderacion > paralelo.nota_maxima:
            flash(f'Error: La nueva ponderación haría que el total exceda los {paralelo.nota_maxima} puntos.', 'danger')
            return redirect(url_for('gestion.parametros', id=paralelo.id))

    parametro.nombre_parametro = nuevo_nombre
    parametro.ponderacion = nueva_ponderacion
    db.session.commit()
    
    flash('Parámetro actualizado con éxito. Las notas se recalcularán automáticamente.', 'success')
    return redirect(url_for('gestion.parametros', id=paralelo.id))

from ..models import Calificacion, Actividad # Asegúrate de tener estas importaciones arriba

@gestion_bp.route('/parametro/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_parametro(id):
    parametro = ParametroEvaluacion.query.get_or_404(id)
    paralelo_id = parametro.paralelo_id
    
    if parametro.paralelo.auxiliar_id != current_user.id:
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('gestion.paralelos'))

    try:
        # ELIMINACIÓN LÓGICA DIRECTA (Soft Delete)
        parametro.estado = False
        
        # También damos de baja (ocultamos) sus actividades asociadas
        for act in parametro.actividades:
            act.estado = False
            
        db.session.commit()
        flash('Categoría enviada a la Papelera. Puedes restaurarla en cualquier momento.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error al enviar a la papelera.', 'danger')
        print(f"Error: {e}")

    return redirect(url_for('gestion.parametros', id=paralelo_id))


@gestion_bp.route('/paralelo/<int:id>/reajustar_parametros', methods=['POST'])
@login_required
def reajustar_parametros(id):
    paralelo = Paralelo.query.get_or_404(id)
    if paralelo.auxiliar_id != current_user.id:
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('gestion.paralelos'))

    nuevas_ponderaciones = {}
    for key, value in request.form.items():
        if key.startswith('param_'):
            param_id = int(key.split('_')[1])
            # Convertimos a float manejando posibles inputs vacíos
            nuevas_ponderaciones[param_id] = float(value) if value else 0.0

    # Validamos matemáticamente que no te pases de la nota máxima
    suma_total = sum(nuevas_ponderaciones.values())
    if suma_total > paralelo.nota_maxima:
        flash(f'Error crítico: La suma ({suma_total}) excede la nota máxima del paralelo ({paralelo.nota_maxima}). No se guardaron los cambios.', 'danger')
        return redirect(url_for('gestion.parametros', id=paralelo.id))

    # Si la validación pasa, actualizamos la base de datos
    for param_id, nueva_pond in nuevas_ponderaciones.items():
        parametro = ParametroEvaluacion.query.get(param_id)
        # Aseguramos de que solo cambie los normales y asistencias que pertenecen a este paralelo
        if parametro and parametro.paralelo_id == paralelo.id and parametro.tipo in ['normal', 'asistencia']:
            parametro.ponderacion = nueva_pond
    
    db.session.commit()
    flash('¡Ponderaciones reajustadas con éxito! Las notas de los estudiantes se han recalculado automáticamente a la nueva escala.', 'success')
    return redirect(url_for('gestion.parametros', id=paralelo.id))