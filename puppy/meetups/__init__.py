from flask import Blueprint

meetups = Blueprint('meetups', __name__)

# from . import views, errors
from . import views
