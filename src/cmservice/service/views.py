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
def send_js(path):
    return send_from_directory(pkg_resources.resource_filename('cmservice.service', 'site/static'), path)


@consent_views.route("/verify/<id>")
def verify(id):
    attributes = current_app.cm.fetch_consented_attributes(id)
    if attributes:
        return jsonify(attributes)

    # no consent for the given id or it has expired
    logging.debug('no consent found for id \'%s\'', id)
    abort(401)


@consent_views.route("/creq/<jwt>")
def creq(jwt):
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
    return render_consent(language=request.accept_languages.best_match(['sv', 'en']))


@consent_views.route('/set_language')
def set_language():
    return render_consent(request.args['lang'])


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


def render_consent(language: str) -> None:
    session['language'] = language
    requester_name = find_requester_name(session['requester_name'], language)

    locked_attr = session['locked_attrs']
    if not isinstance(locked_attr, list):
        locked_attr = [locked_attr]

    released_claims = copy.deepcopy(session['attr'])
    locked_claims = {}
    for l_attr in locked_attr:
        locked_claims[l_attr] = released_claims[l_attr]
        del released_claims[l_attr]

    return render_template(
        'consent.mako',
        consent_question=None,
        state=session['state'],
        released_claims=released_claims,
        locked_claims=locked_claims,
        form_action='/set_language',
        language=language,
        requester_name=requester_name,
        months=current_app.config['USER_CONSENT_EXPIRATION_MONTH'],
        select_attributes=str(current_app.config['AUTO_SELECT_ATTRIBUTES'])
    )


def find_requester_name(requester_name: list, language: str) -> str:
    requester_names = {entry['lang']: entry['text'] for entry in requester_name}
    # fallback to english, or if all else fails, use the first entry in the list of names
    fallback = requester_names.get('en', requester_name[0]['text'])
    return requester_names.get(language, fallback)
