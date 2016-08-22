import json
from urllib.parse import urlencode

import pytest
from jwkest.jwk import RSAKey, rsa_load
from jwkest.jws import JWS

from cmservice.service.wsgi import create_app


class TestWSGIApp:
    @pytest.fixture(autouse=True)
    def create_test_client(self, app_config, cert_and_key):
        self.app = create_app(config=app_config).test_client()
        self.signing_key = RSAKey(key=rsa_load(cert_and_key[1]), alg="RS256")

    def test_full_flow(self):
        attributes = {
            "k0": ["v0"],
            "k1": ["v1.1", "v1.2"],
            "k2": ["v2"]
        }
        consented_attributes = ["k0", "k1"]

        # register a consent request for some attributes
        jws = JWS(json.dumps(attributes), alg=self.signing_key.alg).sign_compact([self.signing_key])
        path = "/creq/{}".format(jws)
        resp = self.app.get(path)
        assert resp.status_code == 200
        resp.data.decode("utf-8")

        # give consent for the requested attributes
        redirect_url = "https://client.example.com"
        state = "test_state"
        id = "test_id"
        with self.app as c:
            with c.session_transaction() as sess:
                sess["redirect_endpoint"] = redirect_url
                sess["state"] = state
                sess["attr"] = list(attributes.keys())
                sess["id"] = id

            request = {
                "state": state,
                "month": 3,
                "attributes": ",".join(consented_attributes),
                "consent_status": "Yes"
            }
            path = "/save_consent?" + urlencode(request)
            resp = c.get(path)
            assert resp.status_code == 302
            assert resp.headers["Location"] == redirect_url

        # verify consent is given for the requested attributes
        path = "/verify/{}".format(id)
        resp = self.app.get(path)
        assert json.loads(resp.data.decode("utf-8")) == consented_attributes
