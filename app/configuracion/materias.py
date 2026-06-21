from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required
from . import configuracion_bp
from ..models import Materia
from ..extensions import db

@configuracion_bp.route('/materias', methods=['GET', 'POST'])
@login_required
def lista_materias():
    # Mi lógica para registrar una nueva materia por POST
    if request.method == 'POST':
        sigla = request.form.get('sigla').strip().upper()
        nombre = request.form.get('nombre').strip()
        
        # Compruebo si ya existe una materia activa con la misma sigla para mantener la integridad de los datos
        materia_existente = Materia.query.filter_by(sigla=sigla, estado=True).first()
        if materia_existente:
            flash(f'La sigla {sigla} ya está registrada en otra materia activa.', 'danger')
            return redirect(url_for('configuracion.lista_materias'))
            
        # Inserto la materia en la base de datos como activa
        nueva_materia = Materia(sigla=sigla, nombre=nombre, estado=True)
        db.session.add(nueva_materia)
        db.session.commit()
        flash('Materia registrada exitosamente.', 'success')
        return redirect(url_for('configuracion.lista_materias'))

    # Si es GET, listo todas las asignaturas vigentes ordenadas alfabéticamente por su sigla
    materias = Materia.query.filter_by(estado=True).order_by(Materia.sigla).all()
    return render_template('configuracion/materias.html', materias=materias)

@configuracion_bp.route('/materias/editar/<int:id>', methods=['POST'])
@login_required
def editar_materia(id):
    materia = Materia.query.get_or_404(id)
    sigla_nueva = request.form.get('sigla').strip().upper()
    nombre_nuevo = request.form.get('nombre').strip()
    
    # Valido que la nueva sigla editada no entre en conflicto con otra materia que ya exista
    choque_sigla = Materia.query.filter(Materia.sigla == sigla_nueva, Materia.id != id, Materia.estado == True).first()
    if choque_sigla:
        flash(f'No se pudo actualizar. La sigla {sigla_nueva} ya le pertenece a otra materia.', 'danger')
        return redirect(url_for('configuracion.lista_materias'))
        
    # Aplico los cambios confirmados en el modal de edición
    materia.sigla = sigla_nueva
    materia.nombre = nombre_nuevo
    db.session.commit()
    flash('Materia actualizada correctamente.', 'success')
    return redirect(url_for('configuracion.lista_materias'))

@configuracion_bp.route('/materias/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_materia(id):
    materia = Materia.query.get_or_404(id)
    
    # Ejecuto un borrado lógico para no romper las relaciones históricas de los paralelos inscritos
    materia.estado = False
    db.session.commit()
    flash('Materia dada de baja correctamente.', 'success')
    return redirect(url_for('configuracion.lista_materias'))