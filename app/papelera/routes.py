from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from . import papelera_bp
# Añadimos Calificacion a las importaciones
from ..models import Paralelo, Inscripcion, Actividad, ParametroEvaluacion, Calificacion, Materia
from ..extensions import db

# --- ACTUALIZAR EL INDEX ---
@papelera_bp.route('/')
@login_required
def index():
    paralelos_archivados = Paralelo.query.filter_by(auxiliar_id=current_user.id, estado=False).all()
    
    inscripciones_archivadas = Inscripcion.query.join(Paralelo).filter(
        Paralelo.auxiliar_id == current_user.id, 
        Inscripcion.estado == False
    ).all()

    actividades_archivadas = Actividad.query.join(ParametroEvaluacion).join(Paralelo).filter(
        Paralelo.auxiliar_id == current_user.id,
        Actividad.estado == False
    ).all()

    # NUEVO: Consultamos las materias dadas de baja
    materias_archivadas = Materia.query.filter_by(estado=False).all()

    return render_template('papelera/index.html', 
                        paralelos=paralelos_archivados, 
                        inscripciones=inscripciones_archivadas,
                        actividades=actividades_archivadas,
                        materias=materias_archivadas) # Pasamos las materias a la vista


# ==========================================
# NUEVAS RUTAS PARA MATERIAS (Añadir al final del archivo)
# ==========================================
@papelera_bp.route('/materia/<int:id>/restaurar', methods=['POST'])
@login_required
def restaurar_materia(id):
    materia = Materia.query.get_or_404(id)
    materia.estado = True
    db.session.commit()
    flash(f'Materia "{materia.nombre}" restaurada con éxito.', 'success')
    return redirect(url_for('papelera.index'))

@papelera_bp.route('/materia/<int:id>/eliminar_definitivo', methods=['POST'])
@login_required
def eliminar_materia_definitiva(id):
    materia = Materia.query.get_or_404(id)
    
    # CASCADA MANUAL EXTREMA: Si destruimos la materia, destruimos sus paralelos y todo lo que contienen
    paralelos = Paralelo.query.filter_by(materia_id=materia.id).all()
    for paralelo in paralelos:
        Inscripcion.query.filter_by(paralelo_id=paralelo.id).delete()
        
        parametros = ParametroEvaluacion.query.filter_by(paralelo_id=paralelo.id).all()
        for param in parametros:
            actividades = Actividad.query.filter_by(parametro_id=param.id).all()
            for act in actividades:
                Calificacion.query.filter_by(actividad_id=act.id).delete()
                db.session.delete(act)
            db.session.delete(param)
        db.session.delete(paralelo)
        
    db.session.delete(materia) # Finalmente destruimos la materia
    db.session.commit()
    
    flash(f'La materia "{materia.nombre}" y TODO su contenido histórico fueron destruidos.', 'success')
    return redirect(url_for('papelera.index'))

# ==========================================
# RESTAURACIONES
# ==========================================
@papelera_bp.route('/paralelo/<int:id>/restaurar', methods=['POST'])
@login_required
def restaurar_paralelo(id):
    paralelo = Paralelo.query.get_or_404(id)
    if paralelo.auxiliar_id == current_user.id:
        paralelo.estado = True
        db.session.commit()
        flash(f'Paralelo {paralelo.nombre} restaurado.', 'success')
    return redirect(url_for('papelera.index'))

@papelera_bp.route('/inscripcion/<int:id>/restaurar', methods=['POST'])
@login_required
def restaurar_inscripcion(id):
    inscripcion = Inscripcion.query.get_or_404(id)
    if inscripcion.paralelo.auxiliar_id == current_user.id:
        inscripcion.estado = True
        db.session.commit()
        flash('Inscripción restaurada.', 'success')
    return redirect(url_for('papelera.index'))

@papelera_bp.route('/actividad/<int:id>/restaurar', methods=['POST'])
@login_required
def restaurar_actividad(id):
    actividad = Actividad.query.get_or_404(id)
    if actividad.parametro.paralelo.auxiliar_id != current_user.id:
        return redirect(url_for('papelera.index'))
    actividad.estado = True 
    db.session.commit()
    flash(f'Actividad restaurada.', 'success')
    return redirect(url_for('papelera.index'))


# ==========================================
# DESTRUCCIÓN DEFINITIVA (Cascada Manual)
# ==========================================
@papelera_bp.route('/paralelo/<int:id>/eliminar_definitivo', methods=['POST'])
@login_required
def eliminar_paralelo_definitivo(id):
    paralelo = Paralelo.query.get_or_404(id)
    if paralelo.auxiliar_id == current_user.id:
        # 1. Limpiamos todas las inscripciones
        Inscripcion.query.filter_by(paralelo_id=paralelo.id).delete()
        
        # 2. Limpiamos Calificaciones, Actividades y Parámetros
        parametros = ParametroEvaluacion.query.filter_by(paralelo_id=paralelo.id).all()
        for param in parametros:
            actividades = Actividad.query.filter_by(parametro_id=param.id).all()
            for act in actividades:
                Calificacion.query.filter_by(actividad_id=act.id).delete() # Notas fuera
                db.session.delete(act) # Actividad fuera
            db.session.delete(param) # Parámetro fuera
            
        # 3. Finalmente destruimos el Paralelo (Libre de ataduras)
        db.session.delete(paralelo) 
        db.session.commit()
        flash(f'El paralelo {paralelo.nombre} y todos sus datos fueron destruidos.', 'success')
    return redirect(url_for('papelera.index'))

@papelera_bp.route('/inscripcion/<int:id>/eliminar_definitivo', methods=['POST'])
@login_required
def eliminar_inscripcion_definitiva(id):
    inscripcion = Inscripcion.query.get_or_404(id)
    if inscripcion.paralelo.auxiliar_id == current_user.id:
        db.session.delete(inscripcion)
        db.session.commit()
        flash('Registro de inscripción destruido definitivamente.', 'success')
    return redirect(url_for('papelera.index'))

@papelera_bp.route('/actividad/<int:id>/eliminar_definitivo', methods=['POST'])
@login_required
def eliminar_actividad_definitiva(id):
    actividad = Actividad.query.get_or_404(id)
    if actividad.parametro.paralelo.auxiliar_id == current_user.id:
        # Destruimos las calificaciones asociadas a esta actividad primero
        Calificacion.query.filter_by(actividad_id=actividad.id).delete()
        db.session.delete(actividad)
        db.session.commit()
        flash('Actividad y sus calificaciones destruidas.', 'success')
    return redirect(url_for('papelera.index'))