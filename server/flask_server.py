from uuid import uuid4
from flask import render_template
from flask.ext.babel import Babel, gettext
from jwkest.jwk import rsa_load, RSAKey
from cmservice import ConsentManager, ConectPolicy, DictConsentDb, Consent
from flask import Flask
from flask import abort
from flask import request
from flask import session
from flask import redirect
from datetime import datetime


__author__ = 'haho0032'

app = Flask(__name__)
app.config.from_pyfile("settings.cfg")
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
    import ssl
    context = None
    if app.config['SSL']:
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.load_cert_chain(app.config["SERVER_CERT"], app.config["SERVER_KEY"])
    keys = []
    for key in app.config["JWT_PUB_KEY"]:
        _bkey = rsa_load(key)
        pub_key = RSAKey().load_key(_bkey)
        keys.append(pub_key)
    global cm
    cm = ConsentManager(DictConsentDb(), ConectPolicy.month, keys)
    app.secret_key = app.config['SECRET_SESSION_KEY']
    #app.run()
    app.run(host=app.config['HOST'], port=app.config['PORT'], debug=app.config['DEBUG'],
            ssl_context=context)
