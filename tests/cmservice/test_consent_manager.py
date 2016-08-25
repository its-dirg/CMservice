import json
from datetime import timedelta, datetime

import pytest
from Crypto.PublicKey import RSA
from jwkest.jwk import RSAKey
from jwkest.jws import JWS

from cmservice.consent import Consent
from cmservice.consent_manager import ConsentManager, InvalidConsentRequestError
from cmservice.database import DictConsentDB, DictConsentRequestDB
from cmservice.consent_request import ConsentRequest


class TestConsentManager(object):
    @pytest.fixture(autouse=True)
    def setup(self):
        self.consent_db = DictConsentDB("salt", 12)
        self.ticket_db = DictConsentRequestDB("salt")
        self.max_month = 12
        self.signing_key = RSAKey(key=RSA.generate(1024), alg='RS256')

        self.cm = ConsentManager(self.consent_db, self.ticket_db, [self.signing_key], 3600, self.max_month)

    def test_fetch_consented_attributes(self):
        id = "test"
        consented_attributes = ["a", "b", "c"]
        consent = Consent(consented_attributes, 3)
        self.consent_db.save_consent(id, consent)
        assert self.cm.fetch_consented_attributes(id) == consented_attributes

    def test_fetch_consented_attributes_with_unknown_id(self):
        assert not self.cm.fetch_consented_attributes('unknown')

    def test_fetch_expired_consented_attributes(self):
        id = "test"
        consented_attributes = ['a', 'b', 'c']
        consent = Consent(consented_attributes, 2, datetime.now() - timedelta(weeks=14))
        assert consent.has_expired(self.max_month)
        self.consent_db.save_consent(id, consent)
        assert not self.cm.fetch_consented_attributes(id)

    def test_save_consent_request(self):
        consent_args = {'id': 'test_id', 'attr': ['xyz', 'abc'], 'redirect_endpoint': 'test_redirect'}
        consent_req = JWS(json.dumps(consent_args)).sign_compact([self.signing_key])
        ticket = self.cm.save_consent_request(consent_req)
        assert self.ticket_db.get_consent_request(ticket).data == consent_args

    def test_save_consent_request_should_raise_exception_for_invalid_signature(self):
        consent_args = {'id': 'test_id', 'attr': ['xyz', 'abc'], 'redirect_endpoint': 'test_redirect'}
        new_key = RSAKey(key=RSA.generate(1024), alg='RS256')
        consent_req = JWS(json.dumps(consent_args)).sign_compact([new_key])
        with pytest.raises(InvalidConsentRequestError):
            self.cm.save_consent_request(consent_req)

    @pytest.mark.parametrize('param_to_delete', [
        'id',
        'attr',
        'redirect_endpoint'
    ])
    def test_save_consent_request_should_raise_exception_for_incorrect_consent_request(self, param_to_delete):
        consent_args = {'id': 'test_id', 'attr': ['xyz', 'abc'], 'redirect_endpoint': 'test_redirect'}

        del consent_args[param_to_delete]
        consent_req = JWS(json.dumps(consent_args)).sign_compact([self.signing_key])
        with pytest.raises(InvalidConsentRequestError):
            self.cm.save_consent_request(consent_req)

    def test_fetch_consent_request(self, consent_request):
        ticket = 'test_ticket'
        self.ticket_db.save_consent_request(ticket, consent_request)
        assert self.cm.fetch_consent_request(ticket) == consent_request.data
        assert self.ticket_db.get_consent_request(ticket) is None

    def test_fetch_consent_request_should_raise_exception_for_unknown_ticket(self):
        assert self.cm.fetch_consent_request("unknown") is None

    def test_save_consent(self):
        id = 'test_id'
        consent = Consent(['foo', 'bar'], 2, datetime.now())
        self.cm.save_consent(id, consent)
        assert self.consent_db.get_consent(id) == consent
