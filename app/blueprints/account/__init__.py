# kosar/app/blueprints/account/__init__.py

from flask import Blueprint

account_bp = Blueprint(
    "account",
    __name__,
    template_folder="templates"
)