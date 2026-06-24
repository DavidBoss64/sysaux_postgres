from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from . import reportes_bp
from ..models import Paralelo, ParametroEvaluacion, Actividad, Calificacion
from ..extensions import db

@reportes_bp.route('/')
@reportes_bp.route('/selector')
@login_required
def selector():
    mis_paralelos = Paralelo.query.filter_by(auxiliar_id=current_user.id, estado=True).all()
    info_paralelos = []
    for paralelo in mis_paralelos:
        parametros = ParametroEvaluacion.query.filter_by(paralelo_id=paralelo.id, estado=True).all()
        tiene_liberacion = any(p.tipo == 'liberacion' for p in parametros)
        info_paralelos.append({
            'paralelo': paralelo,
            'tiene_liberacion': tiene_liberacion
        })
    return render_template('reportes/selector.html', info_paralelos=info_paralelos)

@reportes_bp.route('/paralelo/<int:id>/matriz')
@login_required
def matriz_notas(id):
    paralelo = Paralelo.query.get_or_404(id)
    if paralelo.auxiliar_id != current_user.id:
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('reportes.selector'))

    parametros = ParametroEvaluacion.query.filter_by(paralelo_id=id, estado=True).order_by(ParametroEvaluacion.id).all()
    
    inscripciones_activas = [insc for insc in paralelo.inscripciones if insc.estado]
    estudiantes = sorted([insc.estudiante for insc in inscripciones_activas], key=lambda e: (e.apellidos, e.nombres))
    
    # Agrupamos todos los parámetros que se muestran en columnas antes de la nota final
    parametros_evaluacion = [p for p in parametros if p.tipo != 'liberacion']
    param_liberacion = next((p for p in parametros if p.tipo == 'liberacion'), None)

    matriz = []
    
    for estudiante in estudiantes:
        fila = {
            'estudiante': estudiante,
            'notas_regulares': {},    
            'detalle_actividades': {},
            'nota_semestre': 0.0,
            'nota_liberacion': None,
            'nota_final': 0.0
        }

        nota_base_acumulada = 0.0
        nota_extra_acumulada = 0.0

        # 1. Calcular notas convertidas de Base 100 a su Ponderación
        for param in parametros_evaluacion:
            actividades = Actividad.query.filter_by(parametro_id=param.id, estado=True).all()
            suma_puntajes_100 = 0.0
            
            for act in actividades:
                calif = Calificacion.query.filter_by(actividad_id=act.id, estudiante_id=estudiante.id, estado=True).first()
                puntaje_obtenido = calif.puntaje if calif else 0.0
                
                fila['detalle_actividades'][act.id] = puntaje_obtenido
                suma_puntajes_100 += puntaje_obtenido

            # NUEVA LÓGICA MATEMÁTICA: (Promedio sobre 100 / 100) * Ponderación real
            if len(actividades) > 0:
                promedio_100 = suma_puntajes_100 / len(actividades)
                nota_convertida = (promedio_100 / 100.0) * param.ponderacion
            else:
                nota_convertida = 0.0
                
            fila['notas_regulares'][param.id] = round(nota_convertida, 2)
            
            # Separamos las notas base de los puntos extra
            if param.tipo == 'extra':
                nota_extra_acumulada += nota_convertida
            else:
                nota_base_acumulada += nota_convertida

        # 2. Consolidar la Nota del Semestre con el TOPE (Regla del Extra)
        nota_semestre_bruta = nota_base_acumulada + nota_extra_acumulada
        fila['nota_semestre'] = round(min(nota_semestre_bruta, paralelo.nota_maxima), 2)

        # 3. Calcular Examen de Liberación (También en Base 100)
        if param_liberacion:
            actividades_lib = Actividad.query.filter_by(parametro_id=param_liberacion.id, estado=True).first()
            if actividades_lib:
                calif_lib = Calificacion.query.filter_by(actividad_id=actividades_lib.id, estudiante_id=estudiante.id, estado=True).first()
                puntaje_lib_100 = calif_lib.puntaje if calif_lib else 0.0
                
                fila['detalle_actividades'][actividades_lib.id] = puntaje_lib_100
                # Convertimos la nota de liberación a su ponderación
                nota_liberacion_convertida = (puntaje_lib_100 / 100.0) * param_liberacion.ponderacion
                fila['nota_liberacion'] = round(nota_liberacion_convertida, 2)
            else:
                fila['nota_liberacion'] = 0.0
        
        # 4. Aplicar Estrategia Final
        if param_liberacion and fila['nota_liberacion'] is not None and fila['nota_liberacion'] > 0:
            if param_liberacion.modo_liberacion == 'reemplazo':
                fila['nota_final'] = fila['nota_liberacion']
            else: 
                fila['nota_final'] = max(fila['nota_semestre'], fila['nota_liberacion'])
        else:
            fila['nota_final'] = fila['nota_semestre']
            
        # REDONDEO ACADÉMICO PARA LA NOTA FINAL (Ej: 50.5 -> 51)
        fila['nota_final'] = int(fila['nota_final'] + 0.5)
        
        matriz.append(fila)

    return render_template('reportes/matriz_notas.html', 
                        paralelo=paralelo, 
                        parametros_regulares=parametros_evaluacion,
                        param_liberacion=param_liberacion,
                        matriz=matriz)