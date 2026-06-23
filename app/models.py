from .extensions import db
from flask_login import UserMixin
from datetime import datetime

class Rol(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False, unique=True)
    estado = db.Column(db.Boolean, default=True)
    
    usuarios = db.relationship('Usuario', backref='rol', lazy=True)

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nombres = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    ci = db.Column(db.String(20), unique=True, nullable=False)
    ru = db.Column(db.String(20), unique=True, nullable=True) # Opcional para los de primer ingreso
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    estado = db.Column(db.Boolean, default=True)
    
    # Relaciones para facilitar el filtrado de datos
    inscripciones = db.relationship('Inscripcion', backref='estudiante', lazy=True)
    calificaciones = db.relationship('Calificacion', backref='estudiante', lazy=True)

class Materia(db.Model):
    __tablename__ = 'materias'
    id = db.Column(db.Integer, primary_key=True)
    sigla = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    estado = db.Column(db.Boolean, default=True)
    
    paralelos = db.relationship('Paralelo', backref='materia', lazy=True)

class Paralelo(db.Model):
    __tablename__ = 'paralelos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    materia_id = db.Column(db.Integer, db.ForeignKey('materias.id'), nullable=False)
    auxiliar_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    codigo_inscripcion = db.Column(db.String(20), unique=True, nullable=True)
    estado = db.Column(db.Boolean, default=True)
    
    nota_maxima = db.Column(db.Float, default=10.0)


    auxiliar = db.relationship('Usuario', foreign_keys=[auxiliar_id], backref='paralelos_asignados', lazy=True)

    parametros = db.relationship('ParametroEvaluacion', backref='paralelo', lazy=True)
    inscripciones = db.relationship('Inscripcion', backref='paralelo', lazy=True)


class Inscripcion(db.Model):
    __tablename__ = 'inscripciones'
    id = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    paralelo_id = db.Column(db.Integer, db.ForeignKey('paralelos.id'), nullable=False)
    fecha_inscripcion = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.Boolean, default=True)

class ParametroEvaluacion(db.Model):
    __tablename__ = 'parametros_evaluacion'
    id = db.Column(db.Integer, primary_key=True)
    nombre_parametro = db.Column(db.String(100), nullable=False)
    ponderacion = db.Column(db.Float, nullable=False)
    paralelo_id = db.Column(db.Integer, db.ForeignKey('paralelos.id'), nullable=False)
    estado = db.Column(db.Boolean, default=True)
    tipo = db.Column(db.String(20), default='normal') # 'normal', 'asistencia', 'liberacion'
    
    # --- Estrategia de cálculo para la liberación ---
    modo_liberacion = db.Column(db.String(20), default='maximo') # 'maximo' o 'reemplazo'

    actividades = db.relationship('Actividad', backref='parametro', lazy=True)

class Actividad(db.Model):
    __tablename__ = 'actividades'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    fecha = db.Column(db.DateTime, nullable=False)
    codigo_asistencia = db.Column(db.String(20), nullable=True)
    parametro_id = db.Column(db.Integer, db.ForeignKey('parametros_evaluacion.id'), nullable=False)
    estado = db.Column(db.Boolean, default=True)
    
    # --- NUEVO: Interruptor para que los alumnos puedan o no marcar su asistencia ---
    esta_abierta = db.Column(db.Boolean, default=False)

    calificaciones = db.relationship('Calificacion', backref='actividad', lazy=True)
    
class Calificacion(db.Model):
    __tablename__ = 'calificaciones'
    id = db.Column(db.Integer, primary_key=True)
    puntaje = db.Column(db.Float, nullable=False)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    actividad_id = db.Column(db.Integer, db.ForeignKey('actividades.id'), nullable=False)
    estado = db.Column(db.Boolean, default=True)



from .extensions import login_manager

# Esta función es obligatoria para que Flask-Login funcione
@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))