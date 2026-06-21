from flask import render_template, redirect, url_for
from flask_login import current_user
from . import main_bp
from ..models import Paralelo, ParametroEvaluacion # Mis modelos para calcular las estadísticas

@main_bp.route('/')
def index():
    # Control de seguridad inicial: si no hay sesión, al login universal
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))

    # Bifurcación de Dashboards según el rol
    if current_user.rol.nombre.lower() in ['administrador', 'auxiliar']:
        
        # --- CÁLCULO DE MÉTRICAS EN TIEMPO REAL PARA EL DASHBOARD ---
        # 1. Obtengo todos los paralelos activos que me pertenecen
        mis_paralelos = Paralelo.query.filter_by(auxiliar_id=current_user.id, estado=True).all()
        total_paralelos = len(mis_paralelos)
        
        total_estudiantes = 0
        total_actividades = 0
        
        # 2. Recorro mis paralelos para sumar estudiantes y actividades
        for paralelo in mis_paralelos:
            # Sumo las inscripciones que estén activas (estado=True)
            total_estudiantes += len([inscripcion for inscripcion in paralelo.inscripciones if inscripcion.estado])
            
            # Obtengo los parámetros de evaluación de este paralelo
            parametros = ParametroEvaluacion.query.filter_by(paralelo_id=paralelo.id, estado=True).all()
            for param in parametros:
                # Sumo las actividades activas dentro de cada parámetro
                total_actividades += len([act for act in param.actividades if act.estado])
                
        # Inyecto las variables al renderizar el template
        return render_template('index.html', 
                               total_paralelos=total_paralelos,
                               total_estudiantes=total_estudiantes,
                               total_actividades=total_actividades)
        
    elif current_user.rol.nombre.lower() == 'estudiante':
        # Redirección al entorno aislado de los alumnos (próximo a desarrollar)
        return redirect(url_for('estudiante.dashboard'))