import json
import os
from urllib.parse import urlencode

import pytest
from OpenSSL import crypto
from jwkest.jwk import RSAKey, rsa_load
from jwkest.jws import JWS

from cmservice.service.wsgi import create_app


@pytest.fixture(scope="session")
def cert_and_key(tmpdir_factory):
    tmpdir = str(tmpdir_factory.getbasetemp())
    cert_path = os.path.join(tmpdir, "cert.pem")
    key_path = os.path.join(tmpdir, "key.pem")
    create_self_signed_cert(cert_path, key_path)
    return cert_path, key_path


def create_self_signed_cert(cert_path, key_path):
    # create a key pair
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 1024)

    # create a self-signed cert
    cert = crypto.X509()
    cert.get_subject().C = "US"
    cert.get_subject().ST = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    cert.get_subject().L = "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
    cert.get_subject().O = "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"
    cert.get_subject().OU = "my organization"
    cert.get_subject().CN = "DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD"
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, "sha1")

    with open(cert_path, "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    with open(key_path, "wb") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))


@pytest.fixture
def config(cert_and_key):
    config = dict(
        TESTING=True,
        JWT_PUB_KEY=[cert_and_key[0]],
        SECRET_SESSION_KEY="fdgfds%€#&436gfjhköltfsdjglök34j5oö43ijtglkfdjgasdftglok432jtgerfd",
        TICKET_TTL=600,
        CONSENT_DATABASE_CLASS_PATH="cmservice.database.DictConsentDB",
        CONSENT_DATABASE_CLASS_PARAMETERS=[],
        AUTO_SELECT_ATTRIBUTES=True,
        MAX_CONSENT_EXPIRATION_MONTH=12,
        USER_CONSENT_EXPIRATION_MONTH=[3, 6],
        TICKET_DATABASE_CLASS_PATH="cmservice.database.DictTicketDB",
        TICKET_DATABASE_CLASS_PARAMETERS=[],
        CONSENT_SALT="VFT0yZ2dXzAHRlGb0cAhsac2ipKueybl8ZfuPzsHUrTZ8o7Vs6HnAlMhwbob",
    )
    return config


class TestWSGIApp:
    @pytest.fixture(autouse=True)
    def create_test_client(self, config, cert_and_key):
        self.app = create_app(config=config).test_client()
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
