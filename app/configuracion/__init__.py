from flask import Blueprint

# Configuro mi blueprint para toda la gestión de la estructura base del sistema
configuracion_bp = Blueprint('configuracion', __name__, template_folder='templates')

from . import materias