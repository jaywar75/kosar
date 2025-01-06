# /kosar/app/blueprints/main/routes.py

from flask import Blueprint, redirect, url_for

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    # Example: redirect to account login
    return redirect(url_for("account.login"))
