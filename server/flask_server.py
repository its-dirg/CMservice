import copy
from importlib import import_module
import logging
from uuid import uuid4
import traceback

from flask.ext.babel import Babel
from babel.support import LazyProxy
from flask.ext.mako import MakoTemplates, render_template
from flask.helpers import send_from_directory
from jwkest.jwk import rsa_load, RSAKey
from mako.lookup import TemplateLookup

from flask import Flask

from flask import g
from flask import abort
from flask import request
from flask import session
from flask import redirect

from cmservice.consent import Consent
from cmservice.consent_manager import ConsentManager
from cmservice.database import ConsentDB

app = Flask(__name__, static_url_path='')
app.config.from_pyfile("settings.cfg")

LOGGER = logging.getLogger("")
LOGFILE_NAME = app.config['LOGGING_FILE']
hdlr = logging.FileHandler(LOGFILE_NAME)
base_formatter = logging.Formatter("[%(asctime)-19.19s] [%(levelname)-5.5s]: %(message)s")
hdlr.setFormatter(base_formatter)
hdlr.setLevel(app.config['LOGGING_LEVEL'])
LOGGER.addHandler(hdlr)

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
    try:
        return session['language']
    except:
        pass


@app.route('/static/<path:path>')
def send_js(path):
    return send_from_directory('static', path)

@app.route("/verify/<id>")
def verify(id):
    attributes = cm.find_consent(id)
    if attributes:
        return attributes
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
        session["attr"] = data["attr"]
        session["locked_attr"] = data["locked_attr"]
        session["requester_name"] = data["requester_name"]
        session["requestor"] = data["requestor"]

        return render_consent(language=request.accept_languages.best_match(['sv', 'en']))
    except Exception as ex:
        if app.debug:
            traceback.print_exc()
        abort(400)


def render_consent(language):
    session['language'] = language

    requester_name = find_requester_name(language)
    if not requester_name:
        requester_name = find_requester_name("en")
    if not requester_name:
        requester_name = session["requester_name"][0]['text']

    locked_attr = session["locked_attr"]
    if not isinstance(locked_attr, list):
        locked_attr = [locked_attr]

    released_claims = copy.deepcopy(session["attr"])
    locked_claims = {}
    for l_attr in locked_attr:
        locked_claims[l_attr] = released_claims[l_attr]
        del released_claims[l_attr]

    return render_template(
        'consent.mako',
        consent_question=None,
        state=session["state"],
        released_claims=released_claims,
        locked_claims=locked_claims,
        form_action='/set_language',
        name="mako",
        language=language,
        requester_name=requester_name,
        months=app.config["USER_CONSENT_EXPIRATION_MONTH"],
        select_attributes=str(app.config["AUTO_SELECT_ATTRIBUTES"])
    )


def find_requester_name(language):
    match = None
    for requester_name in session["requester_name"]:
        if requester_name["lang"] == language:
            match = requester_name['text']
    return match


@app.route('/set_language', methods=['GET'])
def set_language():
    try:
        return render_consent(request.args['lang'])
    except Exception as ex:
        if app.debug:
            traceback.print_exc()
        abort(400)


def isSubset(list_, sub_list):
    return set(sub_list) <= set(list_)


@app.route('/save_consent', methods=['GET'])
def save_consent():
    state = request.args["state"]
    redirect_uri = session["redirect_endpoint"]
    month = request.args["month"]
    attributes = request.args["attributes"].split(",")

    if state != session["state"]:
        abort(403)
    ok = request.args["consent_status"]

    if ok == "Yes" and not isSubset(session["attr"], attributes):
        abort(400)

    if ok == "Yes":
        consent_question = Consent.generate_question_hash(
            session["id"],
            selected_attribute_dict=session["attr"],
            entity_id=session["requestor"]
        )
        consent = Consent(session["id"], attributes, consent_question, int(month))
        cm.save_consent(consent)
        session.clear()
    return redirect(redirect_uri)


def import_database_class():
    db_module = app.config['DATABASE_CLASS_PATH']
    path, _class = db_module.rsplit('.', 1)
    module = import_module(path)
    database_class = getattr(module, _class)
    return database_class


class MustInheritFromConsentDB(Exception):
    pass

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
    database_class = import_database_class()
    if not issubclass(database_class, ConsentDB):
        raise MustInheritFromConsentDB("%s does not inherit from ConsentDB" % database_class)
    database = database_class(
        app.config['MAX_CONSENT_EXPIRATION_MONTH'],
        *app.config['DATABASE_CLASS_PARAMETERS']
    )
    cm = ConsentManager(database, keys, app.config["TICKET_TTL"],
                        app.config["MAX_CONSENT_EXPIRATION_MONTH"])
    app.secret_key = app.config['SECRET_SESSION_KEY']
    print("CMservice running at %s:%s" % (app.config['HOST'], app.config['PORT']))
    app.run(host=app.config['HOST'], port=app.config['PORT'], debug=app.config['DEBUG'],
            ssl_context=context)
