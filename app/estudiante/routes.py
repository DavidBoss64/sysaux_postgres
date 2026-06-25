from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from . import estudiante_bp
from ..models import Inscripcion, Paralelo, ParametroEvaluacion, Actividad, Calificacion
from ..extensions import db


@estudiante_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.rol.nombre.lower() != 'estudiante':
        return redirect(url_for('main.index'))

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
    
    calificaciones = Calificacion.query.filter_by(estudiante_id=current_user.id).all()
    mis_notas = {c.actividad_id: c.puntaje for c in calificaciones}
    
    subtotales = {}
    nota_base = 0.0
    nota_extra = 0.0
    
    # 1. CÁLCULO DEL SEMESTRE (Regulares y Extra)
    parametros_evaluacion = [p for p in parametros if p.tipo != 'liberacion']
    param_liberacion = next((p for p in parametros if p.tipo == 'liberacion'), None)

    for param in parametros_evaluacion:
        actividades = Actividad.query.filter_by(parametro_id=param.id, estado=True).all()
        suma_puntajes_100 = 0.0
        
        for act in actividades:
            puntaje = mis_notas.get(act.id, 0.0)
            suma_puntajes_100 += puntaje
        
        if len(actividades) > 0:
            promedio_100 = suma_puntajes_100 / len(actividades)
            nota_convertida = (promedio_100 / 100.0) * param.ponderacion
        else:
            nota_convertida = 0.0
            
        subtotales[param.id] = round(nota_convertida, 2)
        
        if param.tipo == 'extra':
            nota_extra += nota_convertida
        else:
            nota_base += nota_convertida
            
    # Tope del Semestre
    nota_semestre_bruta = nota_base + nota_extra
    nota_semestre = round(min(nota_semestre_bruta, paralelo.nota_maxima), 2)

    # 2. CÁLCULO DE LA LIBERACIÓN
    nota_liberacion = None
    if param_liberacion:
        actividades_lib = Actividad.query.filter_by(parametro_id=param_liberacion.id, estado=True).first()
        if actividades_lib:
            puntaje_lib_100 = mis_notas.get(actividades_lib.id, 0.0)
            # Convertimos la liberación a su peso
            nota_liberacion = round((puntaje_lib_100 / 100.0) * param_liberacion.ponderacion, 2)
            subtotales[param_liberacion.id] = nota_liberacion
        else:
            nota_liberacion = 0.0

    # 3. ESTRATEGIA FINAL EXACTAMENTE COMO EL CENTRALIZADOR
    if param_liberacion and nota_liberacion is not None and nota_liberacion > 0:
        if param_liberacion.modo_liberacion == 'reemplazo':
            nota_final = nota_liberacion
        else:
            nota_final = max(nota_semestre, nota_liberacion)
    else:
        nota_final = nota_semestre

    # Aplicamos el Redondeo Académico final para la vista del estudiante
    nota_final_entera = int(nota_final + 0.5)

    # Lógica de Asistencia en Vivo
    actividad_abierta = Actividad.query.join(ParametroEvaluacion).filter(
        ParametroEvaluacion.paralelo_id == paralelo.id,
        Actividad.esta_abierta == True,
        Actividad.estado == True
    ).first()

    asistencia_marcada = False
    if actividad_abierta:
        puntaje_asistencia = mis_notas.get(actividad_abierta.id, 0.0)
        if puntaje_asistencia > 0:
            asistencia_marcada = True

    return render_template('estudiante/rendimiento.html', 
                        paralelo=paralelo, 
                        parametros=parametros, 
                        mis_notas=mis_notas,
                        subtotales=subtotales, 
                        nota_semestre=nota_semestre,
                        nota_liberacion=nota_liberacion,
                        param_liberacion=param_liberacion,
                        nota_final=nota_final_entera,
                        actividad_abierta=actividad_abierta,
                        asistencia_marcada=asistencia_marcada)


@estudiante_bp.route('/marcar_asistencia/<int:paralelo_id>', methods=['POST'])
@login_required
def marcar_asistencia(paralelo_id):
    codigo_ingresado = request.form.get('codigo_asistencia', '').strip().upper()
    
    actividad = Actividad.query.join(ParametroEvaluacion).filter(
        ParametroEvaluacion.paralelo_id == paralelo_id,
        Actividad.esta_abierta == True,
        Actividad.estado == True
    ).first()

    if not actividad:
        flash('No hay ninguna actividad abierta en este momento.', 'warning')
        return redirect(url_for('estudiante.rendimiento', paralelo_id=paralelo_id))

    if actividad.codigo_asistencia.strip().upper() != codigo_ingresado:
        flash('El código ingresado es incorrecto. Verifica la pizarra.', 'danger')
        return redirect(url_for('estudiante.rendimiento', paralelo_id=paralelo_id))

    calificacion_previa = Calificacion.query.filter_by(actividad_id=actividad.id, estudiante_id=current_user.id).first()
    
    if calificacion_previa:
        # BASE 100: Si asiste, gana 100 pts
        calificacion_previa.puntaje = 100.0
        db.session.commit()
    else:
        # BASE 100: Asistencia nueva = 100 pts
        nueva_asistencia = Calificacion(
            puntaje=100.0,
            estudiante_id=current_user.id,
            actividad_id=actividad.id
        )
        db.session.add(nueva_asistencia)
        db.session.commit()

    flash('¡Asistencia registrada exitosamente!', 'success')
    return redirect(url_for('estudiante.rendimiento', paralelo_id=paralelo_id))