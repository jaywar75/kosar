# kosar/app/blueprints/account/routes.py

from flask import (
    render_template, request, session, redirect, url_for, flash
)
from werkzeug.security import generate_password_hash, check_password_hash
import random, string
from . import account_bp
from app.extensions import mongo

###########################
# 1. Login Route
###########################
@account_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = mongo.db.users.find_one({"username": username})
        if not user:
            hashed_pw = generate_password_hash(password)
            mongo.db.users.insert_one({"username": username, "password": hashed_pw})
            user = {"username": username, "password": hashed_pw}

        if user and check_password_hash(user["password"], password):
            session["username"] = username
            # Redirect to the account blueprint's dashboard endpoint
            return redirect(url_for("account.dashboard"))
        else:
            return "Incorrect password!"

    # If GET, show the login form
    return render_template("account/login.html")


###########################
# 2. Dashboard Route
###########################

@account_bp.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("account.login"))  # or url_for(".login")
    return render_template("account/dashboard.html", username=session["username"])


###########################
# 3. Account Manage Route
###########################
@account_bp.route("/manage", methods=["GET", "POST"])
def manage_account():
    """
    Displays/updates account details in the 'account' collection.
    Final URL = '/account/manage' due to url_prefix='/account'.
    Endpoint = 'account.manage_account'.
    """
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    account_doc = mongo.db.account.find_one({"username": username})

    # POST: handle form submission
    if request.method == "POST":
        account_number = request.form.get("account_number")
        subscription_level = request.form.get("subscription_level")
        renewal_frequency = request.form.get("renewal_frequency")

    def generate_account_number():
        """
        Example function to create a simple random account number.
        Feel free to refine the format or complexity.
        """
        # e.g., prefix 'ACCT-' + 5 random alphanumeric characters
        prefix = "ACCT-"
        rand_part = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=5)
        )
        return prefix + rand_part

    # ---------------------------
    # AUTO-GENERATE IF MISSING
    # ---------------------------
    if account_doc:
        # If doc exists but no account_number, generate one
        if "account_number" not in account_doc or not account_doc["account_number"]:
            generated_number = generate_account_number()
            # update the doc in the DB
            mongo.db.account.update_one(
                {"_id": account_doc["_id"]},
                {"$set": {"account_number": generated_number}}
            )
            account_doc["account_number"] = generated_number
    else:
        # If there's no doc at all, create one with an auto-generated account_number
        generated_number = generate_account_number()
        new_doc = {
            "username": username,
            "account_number": generated_number,
            "subscription_level": None,
            "renewal_frequency": None
        }
        mongo.db.account.insert_one(new_doc)
        account_doc = new_doc

    # Now handle POST updates (saving the form data to Mongo)
    if request.method == "POST":
        # We already extracted account_number, etc. above
        mongo.db.account.update_one(
            {"_id": account_doc["_id"]},
            {
                "$set": {
                    "account_number": account_number,
                    "subscription_level": subscription_level,
                    "renewal_frequency": renewal_frequency
                }
            }
        )
        flash("Account details updated!", "success")
        return redirect(url_for("dashboard"))

    # If GET, just render the form with existing fields
    return render_template("account/account_manage.html", account_doc=account_doc)


###########################
# 4. Logout
###########################
@account_bp.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("account/login"))