from flask import Blueprint

coordinator_bp = Blueprint('coordinator', __name__)

from app.coordinator import routes
