import logging
import sys
from importlib import import_module

import pkg_resources
from flask import Flask
from flask.globals import session
from flask_babel import Babel
from flask_mako import MakoTemplates
from jwkest.jwk import RSAKey, rsa_load
from mako.lookup import TemplateLookup

from cmservice.consent_manager import ConsentManager
from cmservice.database import ConsentDB, ConsentRequestDB, ConsentDatasetDB, ConsentRequestDatasetDB


def import_database_class(db_module_name: str) -> type:
    path, cls = db_module_name.rsplit('.', 1)
    module = import_module(path)
    database_class = getattr(module, cls)
    return database_class


def load_consent_db_class(db_class: str, salt: str, consent_expiration_time: int, init_args: list):
    consent_db_class = import_database_class(db_class)
    if not issubclass(consent_db_class, ConsentDB):
        raise ValueError("%s does not inherit from ConsentDB" % consent_db_class)
    consent_db = consent_db_class(salt, consent_expiration_time, *init_args)
    return consent_db


def load_consent_request_db_class(db_class: str, salt: str, init_args: list):
    consent_request_db_class = import_database_class(db_class)
    if not issubclass(consent_request_db_class, ConsentRequestDB):
        raise ValueError("%s does not inherit from ConsentRequestDB" % consent_request_db_class)
    consent_request_db = consent_request_db_class(salt, *init_args)
    return consent_request_db


def init_consent_manager(app: Flask):
    consent_db = ConsentDatasetDB(app.config['CONSENT_SALT'], app.config['MAX_CONSENT_EXPIRATION_MONTH'],
                                  app.config.get('CONSENT_DATABASE_URL'))
    consent_request_db = ConsentRequestDatasetDB(app.config['CONSENT_SALT'],
                                                 app.config.get('CONSENT_REQUEST_DATABASE_URL'))

    trusted_keys = [RSAKey(key=rsa_load(key)) for key in app.config['TRUSTED_KEYS']]
    cm = ConsentManager(consent_db, consent_request_db, trusted_keys, app.config['TICKET_TTL'],
                        app.config['MAX_CONSENT_EXPIRATION_MONTH'])
    return cm


def setup_logging(logging_level: str):
    logger = logging.getLogger('')
    base_formatter = logging.Formatter('[%(asctime)-19.19s] [%(levelname)-5.5s]: %(message)s')
    hdlr = logging.StreamHandler(sys.stdout)
    hdlr.setFormatter(base_formatter)
    hdlr.setLevel(logging_level)
    logger.setLevel(logging_level)
    logger.addHandler(hdlr)


def create_app(config: dict = None):
    app = Flask(__name__, static_url_path='', instance_relative_config=True)

    if config:
        app.config.update(config)
    else:
        app.config.from_envvar("CMSERVICE_CONFIG")

    mako = MakoTemplates()
    mako.init_app(app)
    app._mako_lookup = TemplateLookup(directories=[pkg_resources.resource_filename('cmservice.service', 'templates')],
                                      input_encoding='utf-8', output_encoding='utf-8',
                                      imports=['from flask_babel import gettext as _'])

    app.cm = init_consent_manager(app)

    babel = Babel(app)
    babel.localeselector(get_locale)
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = pkg_resources.resource_filename('cmservice.service',
                                                                                  'data/i18n/locales')

    from .views import consent_views
    app.register_blueprint(consent_views)

    setup_logging(app.config.get('LOGGING_LEVEL', 'INFO'))

    logger = logging.getLogger(__name__)
    logger.info("Running CMservice version %s", pkg_resources.get_distribution("CMservice").version)
    return app


def get_locale():
    return session['language']
