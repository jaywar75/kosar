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
# 0. Helper / Utility
###########################
def generate_account_number():
    """
    Example function to create a simple random account number.
    Feel free to refine the format or complexity.
    """
    prefix = "ACCT-"
    rand_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return prefix + rand_part


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

    # Already present logic:
    total_accounts = mongo.db.account.count_documents({})
    total_users = mongo.db.users.count_documents({})

    # New: fetch all accounts
    accounts = list(mongo.db.account.find({}))

    # For each account, count how many users reference it
    account_user_counts = []
    for acc in accounts:
        user_count = mongo.db.users.count_documents({"account_id": acc["_id"]})
        account_user_counts.append({
            "company_name": acc.get("company_name", "N/A"),
            "user_count": user_count
        })

    return render_template(
        "account/dashboard.html",
        username=session["username"],
        total_accounts=total_accounts,
        total_users=total_users,
        account_user_counts=account_user_counts  # pass the list to template
    )


###########################
# 3a. Add Account
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

    # If GET
    return render_template(
        "account/account_manage.html",
        new_account=True,
        account_doc=None
    )


###########################
# 3b. Manage/Edit Account
###########################
@account_bp.route("/manage", methods=["GET", "POST"])
def manage_account():
    """
    Displays/updates account details in the 'account' collection.
    If an account_number query param is provided (e.g. /manage?account_number=ACCT-123),
    we retrieve that account doc for editing. Otherwise, we let user create a new account.
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
            # Update existing
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
            # Create new
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
# 3c. List All Accounts
###########################
@account_bp.route("/listing", methods=["GET"])
def list_all_accounts():
    """
    Fetches all documents from the 'account' collection and displays them.
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
#     ***Includes an 'account_id' association via a company dropdown.***
###########################################################################


###########################
# A. List All Users
###########################
@account_bp.route("/users", methods=["GET"])
def user_list():
    """
    Lists all users from the 'users' collection (active or inactive).
    If you want to display 'company_name', do a quick join below.
    """
    if "username" not in session:
        return redirect(url_for("account.login"))

    all_users = list(mongo.db.users.find({}))

    # OPTIONAL: If you want to show each user's associated company name:
    # for user in all_users:
    #     if user.get("account_id"):
    #         acct = mongo.db.account.find_one({"_id": user["account_id"]})
    #         user["company_name"] = acct["company_name"] if acct else None

    return render_template("account/user_list.html", users=all_users)


###########################
# B. Create or Edit User - Step 1
###########################
@account_bp.route("/users/manage", defaults={"user_id": None}, methods=["GET", "POST"])
@account_bp.route("/users/manage/<user_id>", methods=["GET", "POST"])
def user_manage(user_id):
    """
    Unifies user creation and editing into a single route.
    Step 1 (GET): If user_id is provided, we fetch that user doc for editing.
                  Also fetch all accounts for the dropdown.
    Step 1 (POST): Gather form data, look up company_name if desired, pass everything
                   to confirm_user_update.html
    """
    if "username" not in session:
        return redirect(url_for("account.login"))

    # Distinguish create vs. edit
    if user_id:
        user_obj = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if not user_obj:
            flash("User not found.", "error")
            return redirect(url_for("account.user_list"))
    else:
        user_obj = None  # Creating a new user

    if request.method == "GET":
        # Fetch accounts for the dropdown
        all_accounts = list(mongo.db.account.find({}))
        action = "edit" if user_obj else "create"
        return render_template(
            "account/user_manage.html",
            user=user_obj,
            accounts=all_accounts,
            action=action
        )

    # POST => Gather form data, optionally do a DB lookup for the company name
    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    email = request.form.get("email")
    new_username = request.form.get("username")
    new_password = request.form.get("password")
    selected_account_id = request.form.get("account_id")

    # Basic validations
    if not first_name or not last_name or not email or not new_username:
        flash("Missing required fields for user create/edit.", "error")
        return redirect(
            url_for("account.user_manage", user_id=user_id) if user_id else url_for("account.user_manage")
        )

    # (Optional) If you'd like to show the chosen company name on the confirm page:
    selected_company_name = None
    if selected_account_id:
        acct = mongo.db.account.find_one({"_id": ObjectId(selected_account_id)})
        selected_company_name = acct["company_name"] if acct else None

    # Decide if it's a create or edit
    mode = "edit" if user_obj else "create"
    user_id_str = str(user_obj["_id"]) if user_obj else ""

    return render_template(
        "account/confirm_user_update.html",
        mode=mode,
        user_id=user_id_str,
        first_name=first_name,
        last_name=last_name,
        email=email,
        username=new_username,
        password=new_password,
        selected_account_id=selected_account_id,
        selected_company_name=selected_company_name
    )


###########################
# C. Final Confirm - Step 2
###########################
@account_bp.route("/users/confirm", methods=["POST"])
def user_confirm():
    """
    Step 2 (POST only): Perform the actual DB write (create or update).
    Then redirect to user_list.
    """
    if "username" not in session:
        return redirect(url_for("account.login"))

    mode = request.form.get("mode")  # "create" or "edit"
    user_id = request.form.get("user_id")

    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    email = request.form.get("email")
    username = request.form.get("username")
    password = request.form.get("password")
    selected_account_id = request.form.get("selected_account_id")

    # Convert to ObjectId if provided
    account_obj_id = ObjectId(selected_account_id) if selected_account_id else None

    if mode == "create":
        new_user_doc = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "username": username,
            "status": "Active",
            "inactivate_reason": None,
            "account_id": account_obj_id
        }
        if password:
            new_user_doc["password"] = generate_password_hash(password)

        mongo.db.users.insert_one(new_user_doc)
        flash("New user created successfully!", "success")

    elif mode == "edit" and user_id:
        update_doc = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "username": username,
            "account_id": account_obj_id
        }
        if password:
            update_doc["password"] = generate_password_hash(password)

        mongo.db.users.update_one({"_id": ObjectId(user_id)}, {"$set": update_doc})
        flash("User updated successfully!", "success")

    else:
        flash("Invalid mode or missing data. No changes saved.", "error")

    return redirect(url_for("account.user_list"))


###########################
# D. Inactivate User
###########################
@account_bp.route("/users/inactivate/<user_id>", methods=["GET", "POST"])
def user_inactivate(user_id):
    """
    Inactivate a user instead of permanently deleting them.
    """
    if "username" not in session:
        return redirect(url_for("account.login"))

    user_obj = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if not user_obj:
        flash("User not found.", "error")
        return redirect(url_for("account.user_list"))

    if request.method == "GET":
        return render_template("account/user_inactivate_confirm.html", user=user_obj)

    # POST => finalize inactivation
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