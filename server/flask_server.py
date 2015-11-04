from uuid import uuid4
from flask.ext.babel import Babel
from babel.support import LazyProxy
from flask.ext.mako import MakoTemplates, render_template
from jwkest.jwk import rsa_load, RSAKey
from mako.lookup import TemplateLookup
from cmservice import ConsentManager, ConectPolicy, DictConsentDb, Consent
from flask import Flask
from flask import g
from flask import abort
from flask import request
from flask import session
from flask import redirect
from datetime import datetime
import traceback

__author__ = 'haho0032'

app = Flask(__name__)
app.config.from_pyfile("settings.cfg")
mako = MakoTemplates()
mako.init_app(app)
app._mako_lookup = TemplateLookup(directories=["templates"],
                                  input_encoding='utf-8', output_encoding='utf-8',
                                  imports=["from flask.ext.babel import gettext as _"])

babel = Babel(app)


def ugettext(s):
    # we assume a before_request function
    # assigns the correct user-specific
    # translations
    return g.translations.ugettext(s)


ugettext_lazy = LazyProxy(ugettext)


@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(['sv', 'en', "sv_se"])


@app.route("/verify/<id>")
def verify(id):
    if cm.find_consent(id):
        return ""
    abort(401)


@app.route("/creq/<jwt>")
def creq(jwt):
    try:
        ticket = cm.save_consent_req(jwt)
        return ticket
    except:
        abort(400)


@app.route('/consent', methods=['GET'])
def consent():
    try:
        # gettext("test")
        ticket = request.args["ticket"]
        data = cm.get_attributes(ticket)
        if data is None:
            abort(403)
        session["id"] = data["id"]
        session["state"] = uuid4().urn
        session["redirect_endpoint"] = data["redirect_endpoint"]
        client_name = "TODO"

        # question = ugettext_lazy("{client_name} requires the information below to be transferred:").format(
        #     client_name=client_name)
        question = "{client_name} requires the information below to be transferred:".format(
            client_name=client_name)

        return render_template('consent.mako',
                               consent_question=question,
                               state=session["state"],
                               released_claims=data["attr"],
                               form_action='/consent',
                               name="mako",
                               language=request.accept_languages.best_match(['sv', 'en', "sv_se"]))
    except Exception as ex:
        if app.debug:
            traceback.print_exc()
        abort(400)


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
    cm = ConsentManager(DictConsentDb(), ConectPolicy.month, keys, app.config["TICKET_TTL"])
    app.secret_key = app.config['SECRET_SESSION_KEY']
    app.run(host=app.config['HOST'], port=app.config['PORT'], debug=app.config['DEBUG'],
            ssl_context=context)
