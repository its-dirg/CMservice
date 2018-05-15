import copy
import logging
from uuid import uuid4

import pkg_resources
from flask import abort, jsonify
from flask import redirect
from flask import request
from flask import session
from flask.blueprints import Blueprint
from flask.globals import current_app
from flask.helpers import send_from_directory
from flask_mako import render_template

from cmservice.consent import Consent
from cmservice.consent_manager import InvalidConsentRequestError

consent_views = Blueprint('consent_service', __name__, url_prefix='')

logger = logging.getLogger(__name__)


@consent_views.route('/static/<path:path>')
def static(path):
    return send_from_directory(pkg_resources.resource_filename('cmservice.service', 'site/static'), path)


@consent_views.route("/verify/<id>")
def verify(id):
    attributes = current_app.cm.fetch_consented_attributes(id)
    if attributes:
        return jsonify(attributes)

    # no consent for the given id or it has expired
    logging.debug('no consent found for id \'%s\'', id)
    abort(401)


@consent_views.route("/creq/<jwt>", methods=['GET','POST'])
def creq(jwt):
    if request.method == 'POST':
        jwt = request.values.get('jwt')
    try:
        ticket = current_app.cm.save_consent_request(jwt)
        return ticket
    except InvalidConsentRequestError as e:
        logger.debug('received invalid consent request: %s, %s', str(e), jwt)
        abort(400)


@consent_views.route('/consent/<ticket>')
def consent(ticket):
    data = current_app.cm.fetch_consent_request(ticket)
    if data is None:
        # unknown ticket
        logger.debug('received invalid ticket: \'%s\'', ticket)
        abort(403)
    session['id'] = data['id']
    session['state'] = uuid4().urn
    session['redirect_endpoint'] = data['redirect_endpoint']
    session['attr'] = data['attr']
    session['locked_attrs'] = data.get('locked_attrs', [])
    session['requester_name'] = data['requester_name']

    # TODO should find list of supported languages dynamically
    session['language'] = request.accept_languages.best_match(['sv', 'en'])
    requester_name = find_requester_name(session['requester_name'], session['language'])
    return render_consent(session['language'], requester_name, session['locked_attrs'], copy.deepcopy(session['attr']),
                          session['state'], current_app.config['USER_CONSENT_EXPIRATION_MONTH'],
                          str(current_app.config['AUTO_SELECT_ATTRIBUTES']))


@consent_views.route('/set_language')
def set_language():
    session['language'] = request.args['lang']
    requester_name = find_requester_name(session['requester_name'], session['language'])
    return render_consent(session['language'], requester_name, session['locked_attrs'], copy.deepcopy(session['attr']),
                          session['state'], current_app.config['USER_CONSENT_EXPIRATION_MONTH'],
                          str(current_app.config['AUTO_SELECT_ATTRIBUTES']))


@consent_views.route('/save_consent')
def save_consent():
    state = request.args['state']
    redirect_uri = session['redirect_endpoint']
    month = request.args['month']
    attributes = request.args['attributes'].split(",")

    if state != session['state']:
        abort(403)
    ok = request.args['consent_status']

    if ok == 'Yes' and not set(attributes).issubset(set(session['attr'])):
        abort(400)

    if ok == 'Yes':
        consent = Consent(attributes, int(month))
        current_app.cm.save_consent(session['id'], consent)
        session.clear()
    return redirect(redirect_uri)


def render_consent(language: str, requester_name: str, locked_attr: list, released_claims: dict, state: str,
                   months: list, select_attributes: bool) -> str:
    if not isinstance(locked_attr, list):
        locked_attr = [locked_attr]
    locked_claims = {k: released_claims.pop(k) for k in locked_attr if k in released_claims}

    return render_template(
        'consent.mako',
        consent_question=None,
        state=state,
        released_claims=released_claims,
        locked_claims=locked_claims,
        form_action='/set_language',
        language=language,
        requester_name=requester_name,
        months=months,
        select_attributes=select_attributes)


def find_requester_name(requester_name: list, language: str) -> str:
    requester_names = {entry['lang']: entry['text'] for entry in requester_name}
    # fallback to english, or if all else fails, use the first entry in the list of names
    fallback = requester_names.get('en', requester_name[0]['text'])
    return requester_names.get(language, fallback)
