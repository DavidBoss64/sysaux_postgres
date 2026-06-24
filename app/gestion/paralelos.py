from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from . import gestion_bp
from ..models import Paralelo, Materia
from ..extensions import db

@gestion_bp.route('/paralelos', methods=['GET', 'POST'])
@login_required
def paralelos():
    if request.method == 'POST':
        nombre_paralelo = request.form.get('nombre')
        materia_id = request.form.get('materia_id')
        codigo_inscripcion = request.form.get('codigo_inscripcion')
        # Capturamos la nota máxima, si viene vacía por defecto es 10.0
        nota_maxima = request.form.get('nota_maxima')
        nota_maxima = float(nota_maxima) if nota_maxima else 10.0
        
        if not nombre_paralelo or not materia_id:
            flash('Por favor, completa los campos obligatorios.', 'warning')
            return redirect(url_for('gestion.paralelos'))
            
        nuevo_paralelo = Paralelo(
            nombre=nombre_paralelo.upper(),
            materia_id=int(materia_id),
            codigo_inscripcion=codigo_inscripcion if codigo_inscripcion else None,
            nota_maxima=nota_maxima,
            auxiliar_id=current_user.id
        )
        try:
            db.session.add(nuevo_paralelo)
            db.session.commit()
            flash(f'Paralelo {nombre_paralelo} registrado con éxito.', 'success')
        except Exception:
            db.session.rollback()
            flash('Hubo un error al registrar el paralelo.', 'danger')
        return redirect(url_for('gestion.paralelos'))

    mis_paralelos = Paralelo.query.filter_by(auxiliar_id=current_user.id, estado=True).all()
    todas_materias = Materia.query.filter_by(estado=True).all()
    return render_template('gestion/paralelos.html', paralelos=mis_paralelos, materias=todas_materias)

@gestion_bp.route('/paralelo/<int:id>/editar', methods=['POST'])
@login_required
def editar_paralelo(id):
    paralelo = Paralelo.query.get_or_404(id)
    if paralelo.auxiliar_id == current_user.id:
        paralelo.nombre = request.form.get('nombre').upper()
        paralelo.materia_id = request.form.get('materia_id')
        paralelo.codigo_inscripcion = request.form.get('codigo_inscripcion') or None
        
        nota_maxima = request.form.get('nota_maxima')
        paralelo.nota_maxima = float(nota_maxima) if nota_maxima else 10.0
        
        db.session.commit()
        flash('Paralelo actualizado correctamente.', 'success')
    return redirect(url_for('gestion.paralelos'))

@gestion_bp.route('/paralelo/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_paralelo(id):
    paralelo = Paralelo.query.get_or_404(id)
    if paralelo.auxiliar_id == current_user.id:
        paralelo.estado = False
        db.session.commit()
        flash('Paralelo archivado.', 'info')
    return redirect(url_for('gestion.paralelos'))


from ..models import Calificacion, Actividad, Inscripcion, ParametroEvaluacion

@gestion_bp.route('/paralelo/<int:id>/reiniciar', methods=['POST'])
@login_required
def reiniciar_paralelo(id):
    paralelo = Paralelo.query.get_or_404(id)
    
    if paralelo.auxiliar_id != current_user.id:
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('gestion.paralelos'))

    # 1. Validación de Seguridad Estricta
    confirmacion = request.form.get('confirmacion', '').strip()
    if confirmacion != paralelo.nombre:
        flash('El texto de confirmación no coincide. El reinicio fue cancelado por seguridad.', 'danger')
        return redirect(url_for('gestion.paralelos'))

    try:
        # 2. Identificar a los estudiantes afectados antes de borrar sus inscripciones
        inscripciones = Inscripcion.query.filter_by(paralelo_id=paralelo.id).all()
        estudiantes_afectados = [insc.estudiante for insc in inscripciones]

        # 3. Identificar actividades y borrar calificaciones en cascada
        parametros_ids = [p.id for p in ParametroEvaluacion.query.filter_by(paralelo_id=paralelo.id).all()]
        actividades = Actividad.query.filter(Actividad.parametro_id.in_(parametros_ids)).all()
        actividades_ids = [a.id for a in actividades]
        
        if actividades_ids:
            # Borrar Notas
            Calificacion.query.filter(Calificacion.actividad_id.in_(actividades_ids)).delete(synchronize_session=False)
            # Borrar Actividades
            Actividad.query.filter(Actividad.parametro_id.in_(parametros_ids)).delete(synchronize_session=False)

        # 4. Borrar las inscripciones de este paralelo
        Inscripcion.query.filter_by(paralelo_id=paralelo.id).delete(synchronize_session=False)
        
        # Le decimos a la BD que aplique estos borrados temporalmente para el siguiente cálculo
        db.session.flush()

        # 5. El Limpiador Inteligente de Estudiantes
        estudiantes_eliminados = 0
        for estudiante in estudiantes_afectados:
            # Si el estudiante ya no tiene NINGUNA inscripción activa en el sistema, lo borramos
            otras_inscripciones = Inscripcion.query.filter_by(estudiante_id=estudiante.id).count()
            if otras_inscripciones == 0:
                db.session.delete(estudiante)
                estudiantes_eliminados += 1

        db.session.commit()
        flash(f'¡Reinicio exitoso! El paralelo {paralelo.nombre} está limpio y listo para un nuevo semestre. Se eliminaron {estudiantes_eliminados} estudiantes inactivos de la base de datos.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Ocurrió un error crítico durante el reinicio.', 'danger')
        print(f"Error de Reinicio: {e}") # Para tu consola de desarrollo

    return redirect(url_for('gestion.paralelos'))