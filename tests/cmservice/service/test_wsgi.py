import json
from urllib.parse import urlencode

import flask
import pytest
from jwkest.jwk import RSAKey, rsa_load
from jwkest.jws import JWS

from cmservice.service.wsgi import create_app


class TestWSGIApp:
    @pytest.fixture(autouse=True)
    def create_test_client(self, app_config, cert_and_key):
        self.app = create_app(config=app_config).test_client()
        self.signing_key = RSAKey(key=rsa_load(cert_and_key[1]), alg='RS256')

    def test_full_flow(self):
        id = 'test_id'
        attributes = {
            'k0': ['v0'],
            'k1': ['v1.1', 'v1.2'],
            'k2': ['v2']
        }
        consented_attributes = ['k0', 'k1']

        # register a consent request for some attributes
        consent_args = {
            'attr': attributes,
            'id': id,
            'redirect_endpoint': 'https://client.example.com/callback',
            'requester_name': [{'text': 'a ae oo', 'lang': 'en'}, {'text': 'å ä ö', 'lang': 'sv'}]
        }
        jws = JWS(json.dumps(consent_args), alg=self.signing_key.alg).sign_compact([self.signing_key])
        path = '/creq/{}'.format(jws)
        resp = self.app.get(path)
        assert resp.status_code == 200
        ticket = resp.data.decode("utf-8")

        # ask user for consent
        path = '/consent/{}'.format(ticket)
        with self.app as c:
            resp = self.app.get(path)
            state = flask.session['state']
        assert resp.status_code == 200

        # give consent for the requested attributes
        request = {
            'state': state,
            'month': 3,
            'attributes': ",".join(consented_attributes),
            'consent_status': 'Yes'
        }
        path = '/save_consent?' + urlencode(request)
        resp = self.app.get(path)
        assert resp.status_code == 302
        assert resp.headers['Location'] == consent_args['redirect_endpoint']

        # verify consent is given for the requested attributes
        path = '/verify/{}'.format(id)
        resp = self.app.get(path)
        assert json.loads(resp.data.decode('utf-8')) == consented_attributes
