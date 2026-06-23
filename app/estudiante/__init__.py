from flask import Blueprint

estudiante_bp = Blueprint('estudiante',__name__, template_folder='templates', url_prefix='/estudiante')

from . import routes