import logging
import sys
from importlib import import_module

import pkg_resources
from flask import Flask
from flask import g
from flask.globals import session
from flask_babel import Babel
from flask_mako import MakoTemplates
from jwkest.jwk import rsa_load, RSAKey
from mako.lookup import TemplateLookup

from cmservice.consent_manager import ConsentManager
from cmservice.database import ConsentDB, ConsentRequestDB


def ugettext(s):
    # we assume a before_request function
    # assigns the correct user-specific
    # translations
    return g.translations.ugettext(s)


def import_database_class(db_module_name):
    path, _class = db_module_name.rsplit('.', 1)
    module = import_module(path)
    database_class = getattr(module, _class)
    return database_class


class MustInheritFromConsentDB(Exception):
    pass


def load_consent_db_class(db_class, salt, consent_expiration_time, init_args):
    consent_database_class = import_database_class(db_class)
    if not issubclass(consent_database_class, ConsentDB):
        raise MustInheritFromConsentDB(
            "%s does not inherit from ConsentDB" % consent_database_class)
    consent_db = consent_database_class(salt, consent_expiration_time, *init_args)
    return consent_db


def load_consent_request_db_class(db_class, salt, init_args):
    ticket_database_class = import_database_class(db_class)
    if not issubclass(ticket_database_class, ConsentRequestDB):
        raise MustInheritFromConsentDB("%s does not inherit from ConsentRequestDB" % ticket_database_class)
    ticket_db = ticket_database_class(salt, *init_args)
    return ticket_db


def load_keys(path):
    keys = []
    for key in path:
        _bkey = rsa_load(key)
        pub_key = RSAKey().load_key(_bkey)
        keys.append(pub_key)
    return keys


def init_consent_manager(app):
    consent_db = load_consent_db_class(app.config['CONSENT_DATABASE_CLASS_PATH'],
                                       app.config['CONSENT_SALT'],
                                       app.config['MAX_CONSENT_EXPIRATION_MONTH'],
                                       app.config['CONSENT_DATABASE_CLASS_PARAMETERS'])
    ticket_db = load_consent_request_db_class(app.config['TICKET_DATABASE_CLASS_PATH'],
                                              app.config['CONSENT_SALT'],
                                              app.config['TICKET_DATABASE_CLASS_PARAMETERS'])

    cm = ConsentManager(consent_db, ticket_db, load_keys(app.config['JWT_PUB_KEY']), app.config['TICKET_TTL'],
                        app.config['MAX_CONSENT_EXPIRATION_MONTH'])
    return cm


def setup_logging(logging_level):
    logger = logging.getLogger('')
    base_formatter = logging.Formatter('[%(asctime)-19.19s] [%(levelname)-5.5s]: %(message)s')
    hdlr = logging.StreamHandler(sys.stdout)
    hdlr.setFormatter(base_formatter)
    hdlr.setLevel(logging_level)
    logger.addHandler(hdlr)


def create_app(config=None):
    app = Flask(__name__, static_url_path='', instance_relative_config=True)

    if config:
        app.config.update(config)
    else:
        app.config.from_envvar("CMSERVICE_CONFIG")


    mako = MakoTemplates()
    mako.init_app(app)
    app._mako_lookup = TemplateLookup(directories=[pkg_resources.resource_filename('cmservice.service', 'templates')],
                                      input_encoding='utf-8', output_encoding='utf-8',
                                      imports=['from flask_babel import gettext as _']
                                      # TODO not necessary according to https://pythonhosted.org/Flask-Mako/#babel-integration
                                      )

    app.cm = init_consent_manager(app)

    babel = Babel(app)
    babel.localeselector(get_locale)
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = pkg_resources.resource_filename('cmservice.service',
                                                                                  'data/i18n/locales')

    from .views import consent_views
    app.register_blueprint(consent_views)

    setup_logging(app.config.get('LOGGING_LEVEL', 'INFO'))

    return app


def get_locale():
    try:
        return session['language']
    except:
        pass


def ugettext(s):
    # we assume a before_request function
    # assigns the correct user-specific
    # translations
    return g.translations.ugettext(s)