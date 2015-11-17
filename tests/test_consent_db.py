import datetime

import pytest

from cmservice import DictConsentDB, Consent, SQLite3ConsentDB

__author__ = 'danielevertsson'


class TestConsentDB():
    @pytest.fixture(autouse=True)
    def setup(self):
        self.ticket = "ticket_123"
        self.data = "DATA"

    @pytest.mark.parametrize("database", [
        DictConsentDB(),
        SQLite3ConsentDB()
    ])
    def test_save_consent(self, database):
        consent_id = "id_123"
        consent = Consent()
        consent.set(consent_id, datetime.datetime.now())
        database.save_consent(consent)
        assert consent == database.get_consent(consent_id)

    @pytest.mark.parametrize("database", [
        DictConsentDB(),
        SQLite3ConsentDB()
    ])
    def test_save_consent_request(self, database):
        database.save_consent_request(self.ticket, self.data)
        assert self.data == database.get_ticketdata(self.ticket)

    @pytest.mark.parametrize("database", [
        DictConsentDB(),
        SQLite3ConsentDB()
    ])
    def test_remove_ticket(self, database):
        database.save_consent_request(self.ticket, self.data)
        database.remove_ticket(self.ticket)
        assert not database.get_ticketdata(self.ticket)
