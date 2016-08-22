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
from cmservice.database import ConsentDB, TicketDB


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


def load_consent_db_class(db_class, consent_expiration_time, init_args):
    consent_database_class = import_database_class(db_class)
    if not issubclass(consent_database_class, ConsentDB):
        raise MustInheritFromConsentDB(
            "%s does not inherit from ConsentDB" % consent_database_class)
    consent_db = consent_database_class(consent_expiration_time, *init_args)
    return consent_db


def load_ticket_db_class(db_class, init_args):
    ticket_database_class = import_database_class(db_class)
    if not issubclass(ticket_database_class, TicketDB):
        raise MustInheritFromConsentDB("%s does not inherit from TicketDB" % ticket_database_class)
    ticket_db = ticket_database_class(*init_args)
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
                                       app.config['MAX_CONSENT_EXPIRATION_MONTH'],
                                       app.config['CONSENT_DATABASE_CLASS_PARAMETERS'])
    ticket_db = load_ticket_db_class(app.config['TICKET_DATABASE_CLASS_PATH'],
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


def create_app(config_file=None, config={}):
    app = Flask(__name__, static_url_path='')

    if config_file:
        app.config.from_pyfile(config)
    app.config.update(config)

    mako = MakoTemplates()
    mako.init_app(app)
    app._mako_lookup = TemplateLookup(directories=[pkg_resources.resource_filename('cmservice.service', 'templates')],
                                      input_encoding='utf-8', output_encoding='utf-8',
                                      imports=['from flask_babel import gettext as _']
                                      # TODO not necessary according to https://pythonhosted.org/Flask-Mako/#babel-integration
                                      )

    app.cm = init_consent_manager(app)
    app.secret_key = app.config['SECRET_SESSION_KEY']

    babel = Babel(app)
    babel.localeselector(get_locale)

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


if __name__ == '__main__':
    import ssl

    app = create_app('settings.cfg')

    context = None
    if app.config['SSL']:
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.load_cert_chain(app.config['SERVER_CERT'], app.config['SERVER_KEY'])
    keys = []
    for key in app.config['JWT_PUB_KEY']:
        _bkey = rsa_load(key)
        pub_key = RSAKey().load_key(_bkey)
        keys.append(pub_key)
    global cm

    print('CMservice running at %s:%s' % (app.config['HOST'], app.config['PORT']))

    app.run(host=app.config['HOST'], port=app.config['PORT'], debug=app.config['DEBUG'],
            ssl_context=context)
