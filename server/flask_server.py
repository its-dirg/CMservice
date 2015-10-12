from uuid import uuid4
from flask import render_template
from flask.ext.babel import Babel, gettext
from jwkest import jws
from jwkest.jwk import rsa_load, RSAKey
from jwkest.jwt import JWT
from cmservice import ConsentManager, ConectPolicy, DictConsentDb, Consent
from flask import Flask
from flask import abort
from flask import request
from flask import session
from flask import redirect
from datetime import datetime


__author__ = 'haho0032'

app = Flask(__name__)
babel = Babel(app)


@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(['sv_se', 'en'])


@app.route("/verify/<id>")
def verify(id):
    if cm.find_consent(id):
        return ""
    abort(401)


@app.route('/consent', methods=['GET'])
def consent():
    gettext("test")
    jwt = request.args["jwt"]
    jso = cm.get_attributes(jwt)
    if jso is None:
        abort(403)
    session["id"] = jso["id"]
    session["state"] = uuid4().urn
    session["redirect_endpoint"] = jso["redirect_endpoint"]
    return render_template('consent.html', state=session["state"],
                           attributes=jso["attr"])


@app.route('/save_consent', methods=['GET'])
def save_cocent():
    state = request.args["state"]
    redirect_uri = session["redirect_endpoint"]
    if state != session["state"]:
        abort(403)
    ok = request.args["ok"]
    if ok == "Yes":
        cm.save_consent(Consent(session["id"], datetime.now()))
        session.clear()
    return redirect(redirect_uri)

if __name__ == "__main__":
    _bkey = rsa_load("./keys/test.pub")
    p_key = RSAKey().load_key(_bkey)
    app.config["key"] = [p_key]
    global cm
    cm = ConsentManager(DictConsentDb(), ConectPolicy.month, [p_key])
    app.secret_key = 'fdgfds%€#&436gfjhköltfsdjglök34j5oö43ijtglkfdjgasdftglok432jtgerfd'
    app.run()
