from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from . import estudiante_bp
from ..models import Inscripcion, Paralelo, ParametroEvaluacion, Actividad, Calificacion
from ..extensions import db


@estudiante_bp.route('/dashboard')
@login_required
def dashboard():
    # Seguridad: Si un administrador intenta entrar aquí, lo devolvemos a su panel
    if current_user.rol.nombre.lower() != 'estudiante':
        return redirect(url_for('main.index'))

    # Buscamos todas las materias/paralelos donde el estudiante está inscrito y activo
    mis_inscripciones = Inscripcion.query.filter_by(estudiante_id=current_user.id, estado=True).all()

    return render_template('estudiante/dashboard.html', inscripciones=mis_inscripciones)

@estudiante_bp.route('/rendimiento/<int:paralelo_id>')
@login_required
def rendimiento(paralelo_id):
    if current_user.rol.nombre.lower() != 'estudiante':
        return redirect(url_for('main.index'))

    inscripcion = Inscripcion.query.filter_by(estudiante_id=current_user.id, paralelo_id=paralelo_id, estado=True).first_or_404()
    paralelo = inscripcion.paralelo
    parametros = ParametroEvaluacion.query.filter_by(paralelo_id=paralelo.id, estado=True).all()
    
    # 1. Cargamos TODAS las notas del estudiante en un diccionario de acceso rápido
    calificaciones = Calificacion.query.filter_by(estudiante_id=current_user.id).all()
    mis_notas = {c.actividad_id: c.puntaje for c in calificaciones}
    
    subtotales = {}
    nota_acumulada = 0.0
    
    # 2. CÁLCULO IDENTICO AL CENTRALIZADOR
    for param in parametros:
        # Buscamos todas las actividades que el AUXILIAR creó en este parámetro
        actividades = Actividad.query.filter_by(parametro_id=param.id, estado=True).all()
        
        if param.tipo != 'liberacion':
            suma_puntajes = 0.0
            
            for act in actividades:
                # Si el alumno tiene nota, la tomamos. Si no entregó (no existe), le asignamos 0.0
                puntaje = mis_notas.get(act.id, 0.0)
                suma_puntajes += puntaje
            
            # El divisor es el total de actividades creadas (len(actividades)), no las entregadas
            if len(actividades) > 0:
                promedio = suma_puntajes / len(actividades)
            else:
                promedio = 0.0
                
            subtotales[param.id] = round(promedio, 2)
            nota_acumulada += subtotales[param.id]
            
    nota_acumulada = round(nota_acumulada, 2)

    # 3. Lógica de Asistencia en Vivo (sin cambios)
    actividad_abierta = Actividad.query.join(ParametroEvaluacion).filter(
        ParametroEvaluacion.paralelo_id == paralelo.id,
        Actividad.esta_abierta == True,
        Actividad.estado == True
    ).first()

    asistencia_marcada = False
    if actividad_abierta:
        # Buscamos rápidamente en el diccionario que ya creamos
        puntaje_asistencia = mis_notas.get(actividad_abierta.id, 0.0)
        if puntaje_asistencia > 0:
            asistencia_marcada = True

    return render_template('estudiante/rendimiento.html', 
                        paralelo=paralelo, 
                        parametros=parametros, 
                        mis_notas=mis_notas,
                        subtotales=subtotales, 
                        nota_acumulada=nota_acumulada,
                        actividad_abierta=actividad_abierta,
                        asistencia_marcada=asistencia_marcada)


@estudiante_bp.route('/marcar_asistencia/<int:paralelo_id>', methods=['POST'])
@login_required
def marcar_asistencia(paralelo_id):
    # Convertimos a MAYÚSCULAS lo que el alumno escriba para evitar errores
    codigo_ingresado = request.form.get('codigo_asistencia', '').strip().upper()
    
    actividad = Actividad.query.join(ParametroEvaluacion).filter(
        ParametroEvaluacion.paralelo_id == paralelo_id,
        Actividad.esta_abierta == True,
        Actividad.estado == True
    ).first()

    if not actividad:
        flash('No hay ninguna actividad abierta en este momento.', 'warning')
        return redirect(url_for('estudiante.rendimiento', paralelo_id=paralelo_id))

    # Comparamos ignorando si el auxiliar o el alumno usaron minúsculas
    if actividad.codigo_asistencia.strip().upper() != codigo_ingresado:
        flash('El código ingresado es incorrecto. Verifica la pizarra.', 'danger')
        return redirect(url_for('estudiante.rendimiento', paralelo_id=paralelo_id))

    calificacion_previa = Calificacion.query.filter_by(actividad_id=actividad.id, estudiante_id=current_user.id).first()
    
    if calificacion_previa:
        # Si la nota estaba en 0 (por error previo), la restauramos
        calificacion_previa.puntaje = actividad.parametro.ponderacion
        db.session.commit()
    else:
        nueva_asistencia = Calificacion(
            puntaje=actividad.parametro.ponderacion,
            estudiante_id=current_user.id,
            actividad_id=actividad.id
        )
        db.session.add(nueva_asistencia)
        db.session.commit()

    flash('¡Asistencia registrada exitosamente!', 'success')
    return redirect(url_for('estudiante.rendimiento', paralelo_id=paralelo_id))