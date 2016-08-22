import copy
import traceback
from uuid import uuid4

from flask import abort
from flask import redirect
from flask import request
from flask import session
from flask.blueprints import Blueprint
from flask.globals import current_app
from flask.helpers import send_from_directory
from flask_mako import render_template

from cmservice.consent import Consent

consent_views = Blueprint('consent_service', __name__, url_prefix='')


@consent_views.route('/static/<path:path>')
def send_js(path):
    return send_from_directory('static', path)


@consent_views.route("/verify/<id>")
def verify(id):
    attributes = current_app.cm.find_consent(id, current_app.config['CONSENT_SALT'])
    if attributes:
        return attributes
    abort(401)


@consent_views.route("/creq/<jwt>")
def creq(jwt):
    try:
        ticket = current_app.cm.save_consent_req(jwt)
        return ticket
    except Exception as e:
        abort(400)


@consent_views.route('/consent/<ticket>', methods=['GET'])
def consent(ticket):
    try:
        data = current_app.cm.get_attributes(ticket)
        if data is None:
            abort(403)
        session["id"] = data["id"]
        session["state"] = uuid4().urn
        session["redirect_endpoint"] = data["redirect_endpoint"]
        session["attr"] = data["attr"]
        session["locked_attrs"] = data.get("locked_attrs", [])
        session["requester_name"] = data["requester_name"]

        return render_consent(language=request.accept_languages.best_match(['sv', 'en']))
    except Exception as ex:
        if current_app.debug:
            traceback.print_exc()
        abort(400)


def render_consent(language):
    session['language'] = language

    requester_name = find_requester_name(language)
    if not requester_name:
        requester_name = find_requester_name("en")
    if not requester_name:
        requester_name = session["requester_name"][0]['text']

    locked_attr = session["locked_attrs"]
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
        months=current_app.config["USER_CONSENT_EXPIRATION_MONTH"],
        select_attributes=str(current_app.config["AUTO_SELECT_ATTRIBUTES"])
    )


def find_requester_name(language):
    match = None
    for requester_name in session["requester_name"]:
        if requester_name["lang"] == language:
            match = requester_name['text']
    return match


@consent_views.route('/set_language', methods=['GET'])
def set_language():
    try:
        return render_consent(request.args['lang'])
    except Exception as ex:
        if current_app.debug:
            traceback.print_exc()
        abort(400)


def isSubset(list_, sub_list):
    return set(sub_list) <= set(list_)


@consent_views.route('/save_consent', methods=['GET'])
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
        consent = Consent(session["id"], attributes, int(month))
        current_app.cm.save_consent(consent, current_app.config["CONSENT_SALT"])
        session.clear()
    return redirect(redirect_uri)
