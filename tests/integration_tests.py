import json
from collections import Counter

import pytest
import requests
from flask.helpers import url_for
from jwkest.jwk import RSAKey, rsa_load
from jwkest.jws import JWS
from selenium import webdriver
from selenium.webdriver.support.select import Select

from cmservice.service.wsgi import create_app


@pytest.fixture
def app(app_config):
    return create_app(config=app_config)


@pytest.fixture
def signing_key(cert_and_key):
    return RSAKey(key=rsa_load(cert_and_key[1]), alg='RS256')


@pytest.yield_fixture
def selenium_driver():
    driver = webdriver.PhantomJS()
    yield driver
    driver.close()


@pytest.mark.usefixtures('live_server')
class TestService:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.attributes = {
            'k0': ['v0'],
            'k1': ['v1.1', 'v1.2'],
            'k2': ['v2']
        }
        self.id = 'test_id'
        self.requester_name = [{'text': 'a ae oo', 'lang': 'en'}, {'text': 'å ä ö', 'lang': 'sv'}]

    def register_consent_request(self, signing_key):
        # register a consent request for some attributes
        consent_args = {
            'attr': self.attributes,
            'id': self.id,
            'redirect_endpoint': 'https://client.example.com/callback',
            'requester_name': self.requester_name
        }
        jws = JWS(json.dumps(consent_args), alg=signing_key.alg).sign_compact([signing_key])
        consent_req_url = url_for('consent_service.creq', jwt=jws, _external=True)
        resp = requests.get(consent_req_url)
        assert resp.status_code == 200

        ticket = resp.text
        return ticket

    def verify_consent(self):
        verify_url = url_for('consent_service.verify', id=self.id, _external=True)
        resp = requests.get(verify_url)
        if resp.status_code == 200:
            return resp.json()
        else:
            return []

    def test_user_gives_consent(self, signing_key, selenium_driver):
        ticket = self.register_consent_request(signing_key)

        # user gives consent
        consent_url = url_for('consent_service.consent', ticket=ticket, _external=True)
        selenium_driver.get(consent_url)
        submit_btn = selenium_driver.find_element_by_xpath('//input[@id="submit_ok"]')
        submit_btn.click()

        consented_attributes = self.verify_consent()
        assert Counter(consented_attributes) == Counter(self.attributes.keys())

    def test_user_denies_consent(self, signing_key, selenium_driver):
        ticket = self.register_consent_request(signing_key)

        # user gives consent
        consent_url = url_for('consent_service.consent', ticket=ticket, _external=True)
        selenium_driver.get(consent_url)
        deny_btn = selenium_driver.find_element_by_xpath('//input[@id="submit_deny"]')
        deny_btn.click()

        conseted_attributes = self.verify_consent()
        assert conseted_attributes == []

    def test_language_change(self, signing_key, selenium_driver):
        ticket = self.register_consent_request(signing_key)

        consent_url = url_for('consent_service.consent', ticket=ticket, _external=True)
        selenium_driver.get(consent_url)

        # switch language: english
        select = Select(selenium_driver.find_element_by_xpath('//select[@name="lang"]'))
        select.options[0].click()
        requester = selenium_driver.find_element_by_xpath('//b')
        assert requester.text == self.requester_name[0]['text']
        # TODO assert some other text one the page is in english

        # switch language: swedish
        select = Select(selenium_driver.find_element_by_xpath('//select[@name="lang"]'))
        select.options[1].click()
        requester = selenium_driver.find_element_by_xpath('//b')
        assert requester.text == self.requester_name[1]['text']
        # TODO assert some other text one the page has changed language
