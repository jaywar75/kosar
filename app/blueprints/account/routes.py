# kosar/app/blueprints/account/routes.py

import random
import string
from bson.objectid import ObjectId
from flask import (
    render_template, request, session, redirect, url_for, flash
)
from werkzeug.security import generate_password_hash, check_password_hash
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
            # If user doesn't exist, create one (for test purposes)
            hashed_pw = generate_password_hash(password)
            mongo.db.users.insert_one({"username": username, "password": hashed_pw})
            user = {"username": username, "password": hashed_pw}

        # Check password
        if user and check_password_hash(user["password"], password):
            session["username"] = username
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
        return redirect(url_for("account.login"))

    # Query total accounts
    total_accounts = mongo.db.account.count_documents({})

    # Query total users
    total_users = mongo.db.users.count_documents({})

    return render_template(
        "account/dashboard.html",
        username=session["username"],
        total_accounts=total_accounts,
        total_users=total_users
    )

###########################
# 3aa. Add Account Route
###########################
@account_bp.route("/add", methods=["GET", "POST"])
def add_account():
    """
    Allows the user to create a new account doc in the 'account' collection.
    Final URL = '/account/add' (due to url_prefix='/account').
    Endpoint = 'account.add_account'.
    """
    if "username" not in session:
        return redirect(url_for("account.login"))

    if request.method == "POST":
        username = session["username"]

        account_number = request.form.get("account_number")
        subscription_level = request.form.get("subscription_level")
        renewal_frequency = request.form.get("renewal_frequency")
        company_name = request.form.get("company_name")
        billing_address = request.form.get("billing_address")

        # Auto-generate if blank
        if not account_number:
            account_number = generate_account_number()

        new_doc = {
            "username": username,
            "account_number": account_number,
            "subscription_level": subscription_level,
            "renewal_frequency": renewal_frequency,
            "company_name": company_name,
            "billing_address": billing_address
        }
        mongo.db.account.insert_one(new_doc)

        flash("New account created!", "success")
        return redirect(url_for("account.dashboard"))

    return render_template(
        "account/account_manage.html",
        new_account=True,
        account_doc=None
    )


def generate_account_number():
    """
    Example function to create a simple random account number.
    Feel free to refine the format or complexity.
    """
    prefix = "ACCT-"
    rand_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return prefix + rand_part


###########################
# 3ab. Manage (Edit) Account Route
###########################
@account_bp.route("/manage", methods=["GET", "POST"])
def manage_account():
    """
    Displays/updates account details in the 'account' collection.
    If an account_number query param is provided (e.g. /manage?account_number=ACCT-123),
    we retrieve that account doc for editing.
    """
    if "username" not in session:
        return redirect(url_for("account.login"))

    acc_num = request.args.get("account_number")
    account_doc = None

    if acc_num:
        account_doc = mongo.db.account.find_one({"account_number": acc_num})

    if request.method == "POST":
        account_number = request.form.get("account_number")
        subscription_level = request.form.get("subscription_level")
        renewal_frequency = request.form.get("renewal_frequency")
        company_name = request.form.get("company_name")
        billing_address = request.form.get("billing_address")

        if account_doc:
            mongo.db.account.update_one(
                {"_id": account_doc["_id"]},
                {
                    "$set": {
                        "account_number": account_number,
                        "subscription_level": subscription_level,
                        "renewal_frequency": renewal_frequency,
                        "company_name": company_name,
                        "billing_address": billing_address
                    }
                }
            )
            flash("Account details updated!", "success")
        else:
            new_doc = {
                "username": session["username"],
                "account_number": account_number or generate_account_number(),
                "subscription_level": subscription_level,
                "renewal_frequency": renewal_frequency,
                "company_name": company_name,
                "billing_address": billing_address
            }
            mongo.db.account.insert_one(new_doc)
            flash("A new account was created since none existed for this ID!", "success")

        return redirect(url_for("account.list_all_accounts"))

    return render_template("account/account_manage.html", account_doc=account_doc)


###########################
# 3ac. List All Accounts Route
###########################
@account_bp.route("/listing", methods=["GET"])
def list_all_accounts():
    """
    Fetches all documents from the 'account' collection and
    displays them in a dedicated template (e.g., account_list.html).
    """
    if "username" not in session:
        return redirect(url_for("account.login"))

    all_accounts = list(mongo.db.account.find({}))
    return render_template("account/account_list.html", all_accounts=all_accounts)


###########################
# 4. Logout
###########################
@account_bp.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("account.login"))


###########################################################################
#        NEW SECTION: Basic (CRUD-like) User Management without Delete
#     Instead of “delete,” we inactivate users and store a reason.
#     Added First/Last Name & Email, plus a two-step confirm flow.
###########################################################################


###########################
# A. List All Users
###########################
@account_bp.route("/users", methods=["GET"])
def user_list():
    """
    Lists all users from the 'users' collection (active or inactive).
    """
    if "username" not in session:
        return redirect(url_for("account.login"))

    all_users = mongo.db.users.find({})
    return render_template("account/user_list.html", users=all_users)


###########################
# B. Create (Add) User - Step 1
###########################
@account_bp.route("/users/new", methods=["GET", "POST"])
def user_create():
    """
    Step 1:
      - GET -> Show user_manage.html form (FirstName, LastName, Email, Username, Password)
      - POST -> Gather form data, show confirm_user_update.html
    """
    if "username" not in session:
        return redirect(url_for("account.login"))

    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")

        # Basic validations
        if not first_name or not last_name or not email or not username:
            flash("Missing required fields: first, last, email, or username.", "error")
            return redirect(url_for("account.user_create"))

        # Show confirmation page instead of directly inserting
        return render_template(
            "account/confirm_user_update.html",
            mode="create",
            first_name=first_name,
            last_name=last_name,
            email=email,
            username=username,
            password=password
        )

    # If GET, show form
    return render_template("account/user_manage.html", user=None, action="create")


###########################
# C. Edit Existing User - Step 1
###########################
@account_bp.route("/users/edit/<user_id>", methods=["GET", "POST"])
def user_edit(user_id):
    """
    Step 1:
      - GET -> Show user_manage.html for editing
      - POST -> Gather updated form data, show confirm_user_update.html
    """
    if "username" not in session:
        return redirect(url_for("account.login"))

    user_obj = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if not user_obj:
        flash("User not found.", "error")
        return redirect(url_for("account.user_list"))

    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        new_username = request.form.get("username")
        new_password = request.form.get("password")

        if not first_name or not last_name or not email or not new_username:
            flash("Missing required fields for user update.", "error")
            return redirect(url_for("account.user_edit", user_id=user_id))

        return render_template(
            "account/confirm_user_update.html",
            mode="edit",
            user_id=str(user_id),
            first_name=first_name,
            last_name=last_name,
            email=email,
            username=new_username,
            password=new_password  # might be empty
        )

    # If GET -> show user_manage.html with existing data
    return render_template("account/user_manage.html", user=user_obj, action="edit")


###########################
# D. Final Confirm Route - Step 2
###########################
@account_bp.route("/users/confirm", methods=["POST"])
def user_confirm():
    """
    Step 2:
      - POST from confirm_user_update.html
      - If mode="create", do insert
      - If mode="edit", do update
      - Then redirect to user_list
    """
    if "username" not in session:
        return redirect(url_for("account.login"))

    mode = request.form.get("mode")
    user_id = request.form.get("user_id")

    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    email = request.form.get("email")
    username = request.form.get("username")
    password = request.form.get("password")

    if mode == "create":
        # Insert logic
        new_user_doc = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "username": username,
            "status": "Active",
            "inactivate_reason": None
        }
        if password:
            new_user_doc["password"] = generate_password_hash(password)
        mongo.db.users.insert_one(new_user_doc)
        flash("New user created successfully!", "success")

    elif mode == "edit" and user_id:
        # Update logic
        update_doc = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "username": username
        }
        if password:
            update_doc["password"] = generate_password_hash(password)

        mongo.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_doc}
        )
        flash("User updated successfully!", "success")

    else:
        flash("Invalid mode or missing data. No changes saved.", "error")

    return redirect(url_for("account.user_list"))


###########################
# E. Inactivate (Instead of Delete)
###########################
@account_bp.route("/users/inactivate/<user_id>", methods=["GET", "POST"])
def user_inactivate(user_id):
    """
    Inactivate a user instead of deleting them; stores an inactivation reason.
    """
    if "username" not in session:
        return redirect(url_for("account.login"))

    user_obj = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if not user_obj:
        flash("User not found.", "error")
        return redirect(url_for("account.user_list"))

    if request.method == "GET":
        # Optionally render a confirmation or reason form
        return render_template("account/user_inactivate_confirm.html", user=user_obj)

    if request.method == "POST":
        reason = request.form.get("inactivate_reason", "No reason provided")
        mongo.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "status": "Inactive",
                    "inactivate_reason": reason
                }
            }
        )
        flash("User inactivated successfully!", "success")
        return redirect(url_for("account.user_list"))