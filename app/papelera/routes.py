from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from . import papelera_bp
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

    materias_archivadas = Materia.query.filter_by(estado=False).all()

    # NUEVO: Consultamos los Parámetros (Categorías) dados de baja
    parametros_archivados = ParametroEvaluacion.query.join(Paralelo).filter(
        Paralelo.auxiliar_id == current_user.id,
        ParametroEvaluacion.estado == False
    ).all()

    return render_template('papelera/index.html', 
                        paralelos=paralelos_archivados, 
                        inscripciones=inscripciones_archivadas,
                        actividades=actividades_archivadas,
                        materias=materias_archivadas,
                        parametros=parametros_archivados) # Pasamos a la vista


# ==========================================
# RUTAS PARA MATERIAS
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
    
    # CASCADA MANUAL EXTREMA
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
        
    db.session.delete(materia)
    db.session.commit()
    
    flash(f'La materia "{materia.nombre}" y TODO su contenido histórico fueron destruidos.', 'success')
    return redirect(url_for('papelera.index'))

# ==========================================
# RUTAS PARA PARALELOS
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

@papelera_bp.route('/paralelo/<int:id>/eliminar_definitivo', methods=['POST'])
@login_required
def eliminar_paralelo_definitivo(id):
    paralelo = Paralelo.query.get_or_404(id)
    if paralelo.auxiliar_id == current_user.id:
        Inscripcion.query.filter_by(paralelo_id=paralelo.id).delete()
        
        parametros = ParametroEvaluacion.query.filter_by(paralelo_id=paralelo.id).all()
        for param in parametros:
            actividades = Actividad.query.filter_by(parametro_id=param.id).all()
            for act in actividades:
                Calificacion.query.filter_by(actividad_id=act.id).delete()
                db.session.delete(act)
            db.session.delete(param)
            
        db.session.delete(paralelo) 
        db.session.commit()
        flash(f'El paralelo {paralelo.nombre} y todos sus datos fueron destruidos.', 'success')
    return redirect(url_for('papelera.index'))

# ==========================================
# RUTAS PARA PARÁMETROS (NUEVO)
# ==========================================
@papelera_bp.route('/parametro/<int:id>/restaurar', methods=['POST'])
@login_required
def restaurar_parametro(id):
    parametro = ParametroEvaluacion.query.get_or_404(id)
    if parametro.paralelo.auxiliar_id == current_user.id:
        parametro.estado = True
        # Restaurar las actividades ocultas que le pertenecen
        for act in parametro.actividades:
            act.estado = True
        db.session.commit()
        flash(f'La categoría "{parametro.nombre_parametro}" fue restaurada.', 'success')
    return redirect(url_for('papelera.index'))

@papelera_bp.route('/parametro/<int:id>/eliminar_definitivo', methods=['POST'])
@login_required
def eliminar_parametro_definitivo(id):
    parametro = ParametroEvaluacion.query.get_or_404(id)
    
    if parametro.paralelo.auxiliar_id == current_user.id:
        try:
            # Eliminamos las notas, luego las actividades y finalmente la categoría
            actividades = Actividad.query.filter_by(parametro_id=parametro.id).all()
            for act in actividades:
                Calificacion.query.filter_by(actividad_id=act.id).delete()
                db.session.delete(act)
                
            db.session.delete(parametro)
            db.session.commit()
            flash('Categoría y todas sus notas destruidas de forma irreversible.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Ocurrió un error al intentar destruir el parámetro.', 'danger')
            
    return redirect(url_for('papelera.index'))

# ==========================================
# RUTAS PARA ACTIVIDADES E INSCRIPCIONES
# ==========================================
@papelera_bp.route('/inscripcion/<int:id>/restaurar', methods=['POST'])
@login_required
def restaurar_inscripcion(id):
    inscripcion = Inscripcion.query.get_or_404(id)
    if inscripcion.paralelo.auxiliar_id == current_user.id:
        inscripcion.estado = True
        db.session.commit()
        flash('Inscripción restaurada.', 'success')
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

@papelera_bp.route('/actividad/<int:id>/restaurar', methods=['POST'])
@login_required
def restaurar_actividad(id):
    actividad = Actividad.query.get_or_404(id)
    if actividad.parametro.paralelo.auxiliar_id == current_user.id:
        actividad.estado = True 
        db.session.commit()
        flash('Actividad restaurada.', 'success')
    return redirect(url_for('papelera.index'))

@papelera_bp.route('/actividad/<int:id>/eliminar_definitivo', methods=['POST'])
@login_required
def eliminar_actividad_definitiva(id):
    actividad = Actividad.query.get_or_404(id)
    if actividad.parametro.paralelo.auxiliar_id == current_user.id:
        Calificacion.query.filter_by(actividad_id=actividad.id).delete()
        db.session.delete(actividad)
        db.session.commit()
        flash('Actividad y sus calificaciones destruidas.', 'success')
    return redirect(url_for('papelera.index'))