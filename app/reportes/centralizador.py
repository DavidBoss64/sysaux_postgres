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
    
    # -Ordenamos alfabéticamente por Apellidos y luego Nombres ---
    inscripciones_activas = [insc for insc in paralelo.inscripciones if insc.estado]
    estudiantes = sorted([insc.estudiante for insc in inscripciones_activas], key=lambda e: (e.apellidos, e.nombres))
    # ------------------------------------------------------------------------------------
    
    parametros_regulares = [p for p in parametros if p.tipo != 'liberacion']
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

        # 1. Calcular notas regulares (Promedio directo)
        for param in parametros_regulares:
            actividades = Actividad.query.filter_by(parametro_id=param.id, estado=True).all()
            suma_puntajes = 0.0
            
            for act in actividades:
                calif = Calificacion.query.filter_by(actividad_id=act.id, estudiante_id=estudiante.id, estado=True).first()
                puntaje_obtenido = calif.puntaje if calif else 0.0
                
                fila['detalle_actividades'][act.id] = puntaje_obtenido
                suma_puntajes += puntaje_obtenido

            # la nota final del parámetro es simplemente el promedio de sus actividades.
            if len(actividades) > 0:
                nota_parametro = suma_puntajes / len(actividades)
            else:
                nota_parametro = 0.0
                
            fila['notas_regulares'][param.id] = round(nota_parametro, 2)
            fila['nota_semestre'] += nota_parametro
            

        #if fila['nota_semestre']>10:
        #    fila['nota_semestre']==10

        fila['nota_semestre'] = round(fila['nota_semestre'], 2)

        # 2. Calcular Examen de Liberación
        if param_liberacion:
            actividades_lib = Actividad.query.filter_by(parametro_id=param_liberacion.id, estado=True).first()
            if actividades_lib:
                calif_lib = Calificacion.query.filter_by(actividad_id=actividades_lib.id, estudiante_id=estudiante.id, estado=True).first()
                # CORRECCIÓN: Se toma directo, ya está validado sobre el límite
                puntaje_lib = calif_lib.puntaje if calif_lib else 0.0
                
                fila['nota_liberacion'] = round(puntaje_lib, 2)
                fila['detalle_actividades'][actividades_lib.id] = puntaje_lib
            else:
                fila['nota_liberacion'] = 0.0
        
        # 3. Aplicar Estrategia Final
        if param_liberacion and fila['nota_liberacion'] is not None and fila['nota_liberacion'] > 0:
            if param_liberacion.modo_liberacion == 'reemplazo':
                fila['nota_final'] = fila['nota_liberacion']
            else: 
                fila['nota_final'] = max(fila['nota_semestre'], fila['nota_liberacion'])
        else:
            fila['nota_final'] = fila['nota_semestre']
            
        fila['nota_final'] = round(fila['nota_final'], 2)
        matriz.append(fila)

    return render_template('reportes/matriz_notas.html', 
                        paralelo=paralelo, 
                        parametros_regulares=parametros_regulares,
                        param_liberacion=param_liberacion,
                        matriz=matriz)