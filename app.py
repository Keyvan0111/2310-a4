import uuid
import identity.web
import requests
import os
from flask import Flask, redirect, render_template, request, session, url_for, flash
from flask_session import Session

# The following variables are required for the app to run.

# TODO: Use the Azure portal to register your application and generate client id and secret credentials.
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")

# TODO: Figure out your authentication authority id.
AUTHORITY = f'https://login.microsoftonline.com/{TENANT_ID}'

# TODO: generate a secret. Used by flask session for protecting cookies.
SESSION_SECRET = uuid.uuid4()

# TODO: Figure out what scopes you need to use
SCOPES = ["User.Read"]

# TODO: Figure out the URO where Azure will redirect to after authentication. After deployment, this should
#  be on your server. The URI must match one you have configured in your application registration.
REDIRECT_URI = "http://localhost:5000/getAToken"

REDIRECT_PATH = "/getAToken"

app = Flask(__name__)
app.config['SESSION_COOKIE_SAMESITE'] = 'None'  # Allow cross-site redirects
app.config['SESSION_COOKIE_NAME'] = 'session'   # Consistent cookie name
app.config['SECRET_KEY'] = SESSION_SECRET
app.config['SESSION_TYPE'] = 'filesystem'
app.config['TESTING'] = True
app.config['DEBUG'] = True
Session(app)

# The auth object provide methods for interacting with the Microsoft OpenID service.
auth = identity.web.Auth(session=session,
                         authority=AUTHORITY,
                         client_id=CLIENT_ID,
                         client_credential=CLIENT_SECRET)



@app.route("/login")
def login():
    try:
        print(">> /login: Initiating authentication")
        rs = auth.log_in(SCOPES, REDIRECT_URI)
        print(">> /login: Auth URI generated:", rs["auth_uri"])
        return render_template("login.html", auth_uri=rs["auth_uri"])
    except Exception as e:
        print(">> Error in /login:", str(e))
        return f"<h1>Login Error</h1><pre>{str(e)}</pre>", 500

@app.route(REDIRECT_PATH)
def auth_response():
    try:
        print(">> GET /getAToken hit")
        result = auth.complete_log_in(request.args)
        print(">> Result from complete_log_in:", result)

        if result.get("error"):
            print(">> Auth error:", result["error_description"])
            return render_template("auth_error.html", result=result)

        print(">> Authentication successful, redirecting to /")
        return redirect("/")
    except Exception as e:
        print(">> Exception in /getAToken:", str(e))
        import traceback
        traceback.print_exc()
        return f"<h1>Auth Error</h1><pre>{str(e)}</pre>", 500

@app.route("/logout")
def logout():
    auth.log_out(url_for("index"))
    return redirect("/")

@app.route("/")
def index():
    user = auth.get_user()
    if user:
        return render_template('index.html', user=user)
    return render_template('welcome.html')

@app.route("/profile", methods=["GET"])
def get_profile():
    if not auth.get_user():
        flash("Please log in to access this page.", "error")
        return redirect("/login")

    token = auth.get_token_for_user(SCOPES)
    headers = {"Authorization": "Bearer " + token["access_token"]}

    result = requests.get('https://graph.microsoft.com/v1.0/me', headers=headers)
    return render_template('profile.html', user=result.json(), result=None)

@app.route("/profile", methods=["POST"])
def post_profile():
    if not auth.get_user():
        flash("Please log in to access this page.", "error")
        return redirect("/login")

    token = auth.get_token_for_user(SCOPES)
    headers = {"Authorization": "Bearer " + token["access_token"], "Content-Type": "application/json"}

    user_id = request.form.get("id")
    update_data = {
        "mobilePhone": request.form.get("mobilePhone"),
        "businessPhones": [request.form.get("businessPhones")] if request.form.get("businessPhones") else []
    }

    result = requests.patch(
        f'https://graph.microsoft.com/v1.0/users/{user_id}',
        headers=headers,
        json=update_data
    )

    profile = requests.get('https://graph.microsoft.com/v1.0/me', headers=headers)

    if result.status_code == 204:
        return render_template('profile.html', user=profile.json(), result={"ok": True})
    else:
        return render_template('profile.html', user=profile.json(), result={"error": result.json().get("error", {}).get("message")})

@app.route("/users")
def get_users():
    if not auth.get_user():
        flash("Please log in to access this page.", "error")
        return redirect("/login")

    token = auth.get_token_for_user(SCOPES)
    headers = {"Authorization": "Bearer " + token["access_token"]}

    result = requests.get('https://graph.microsoft.com/v1.0/users', headers=headers)
    return render_template('users.html', result=result.json())

if __name__ == "__main__":
    app.run()
