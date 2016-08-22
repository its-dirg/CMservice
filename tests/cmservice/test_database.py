import datetime
import tempfile
from unittest.mock import patch

import pytest

from cmservice.consent import Consent
from cmservice.database import DictConsentDB, SQLite3ConsentDB, DictTicketDB, SQLite3TicketDB
from cmservice.ticket_data import TicketData

__author__ = 'danielevertsson'

CONSENT_DATABASES = [DictConsentDB(999), SQLite3ConsentDB(999)]
TICKET_DATABASES = [DictTicketDB(), SQLite3TicketDB()]

class TestConsentDB():
    @pytest.fixture(autouse=True)
    def setup(self):
        self.ticket = "ticket_123"
        self.time = datetime.datetime.now()
        self.data = TicketData({"asd": "asd"}, timestamp=self.time)
        self.consent_id = "id_123"
        self.attibutes = ["name", "email"]
        self.consent = Consent(self.consent_id, self.attibutes, 1,
                               timestamp=self.time)

    @pytest.mark.parametrize("database", CONSENT_DATABASES)
    def test_save_consent(self, database):
        database.save_consent(self.consent)
        assert self.consent == database.get_consent(self.consent_id)

    @pytest.mark.parametrize("database", TICKET_DATABASES)
    def test_save_consent_request(self, database):
        database.save_consent_request(self.ticket, self.data)
        assert self.data == database.get_ticketdata(self.ticket)

    @pytest.mark.parametrize("database", TICKET_DATABASES)
    def test_remove_ticket(self, database):
        database.save_consent_request(self.ticket, self.data)
        database.remove_ticket(self.ticket)
        assert not database.get_ticketdata(self.ticket)

    @pytest.mark.parametrize("database", CONSENT_DATABASES)
    @patch('cmservice.consent.Consent.get_current_time')
    def test_if_nothing_is_return_if_policy_has_expired(self, get_current_time, database):
        parameters = [
            (datetime.datetime(2015, 1, 1), datetime.datetime(2015, 3, 1), 1),
            (datetime.datetime(2015, 1, 1), datetime.datetime(2016, 2, 1), 12),
        ]
        for start_time, current_time, month in parameters:
            consent = Consent(self.consent_id, self.attibutes, month, timestamp=start_time)
            get_current_time.return_value = current_time
            database.save_consent(consent)
            assert not database.get_consent(self.consent_id)

    @pytest.mark.parametrize("database", CONSENT_DATABASES)
    @patch('cmservice.consent.Consent.get_current_time')
    def test_if_policy_has_not_yet_expired(self, get_current_time, database):
        parameters = [
            (datetime.datetime(2015, 1, 1), datetime.datetime(2015, 1, 30), 1),
            (datetime.datetime(2015, 1, 1), datetime.datetime(2015, 12, 31), 12),
        ]
        for start_time, current_time, month in parameters:
            consent = Consent(self.consent_id, self.attibutes, month, timestamp=start_time)
            get_current_time.return_value = current_time
            database.save_consent(consent)
            assert database.get_consent(self.consent_id)

    def test_remove_consent_from_db(self):
        database = SQLite3ConsentDB(999)
        database.save_consent(self.consent)
        assert database.get_consent(self.consent_id)
        database.remove_consent(self.consent_id)
        assert not database.get_consent(self.consent_id)

    def test_save_consent_for_all_attributes_by_entering_none(self):
        database = SQLite3ConsentDB(999)
        consent = Consent(
            self.consent_id,
            None,
            999
        )
        database.save_consent(consent)
        assert database.get_consent(self.consent_id) == consent

    def test_store_consent_in_file_and_ticket_in_memory(self):
        consent_id = "id1"
        tmp_file = tempfile.NamedTemporaryFile()
        consent_db = SQLite3ConsentDB(1, tmp_file.name)
        consent_db.save_consent(Consent(consent_id, ["attr1"], month=1))
        assert consent_db.size() == 1

        ticket_db = DictTicketDB()
        ticket_db.save_consent_request("ticket1", TicketData({}))
        assert ticket_db.size() == 1

        ticket_db = DictTicketDB()
        consent_db = SQLite3ConsentDB(1, tmp_file.name)
        assert ticket_db.size() == 0
        assert consent_db.size() == 1
