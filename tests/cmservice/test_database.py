import datetime
import os
from unittest.mock import patch

import pytest

from cmservice.consent import Consent
from cmservice.database import DictConsentDB, SQLite3ConsentDB, DictConsentRequestDB, SQLite3ConsentRequestDB
from cmservice.ticket_data import ConsentRequest

CONSENT_DATABASES = [DictConsentDB("salt", 999), SQLite3ConsentDB("salt", 999)]
TICKET_DATABASES = [DictConsentRequestDB("salt"), SQLite3ConsentRequestDB("salt")]


class TestConsentDB():
    @pytest.fixture(autouse=True)
    def setup(self):
        self.ticket = 'ticket_123'
        self.time = datetime.datetime.now()
        self.data = ConsentRequest({'asd': 'asd'}, timestamp=self.time)
        self.consent_id = 'id_123'
        self.attibutes = ['name', 'email']
        self.consent = Consent(self.attibutes, 1, timestamp=self.time)

    @pytest.mark.parametrize('database', CONSENT_DATABASES)
    def test_save_consent(self, database):
        database.save_consent(self.consent_id, self.consent)
        assert self.consent == database.get_consent(self.consent_id)

    @pytest.mark.parametrize('database', TICKET_DATABASES)
    def test_save_consent_request(self, database):
        database.save_consent_request(self.ticket, self.data)
        assert self.data == database.get_consent_request(self.ticket)

    @pytest.mark.parametrize('database', TICKET_DATABASES)
    def test_remove_ticket(self, database):
        database.save_consent_request(self.ticket, self.data)
        database.remove_consent_request(self.ticket)
        assert not database.get_consent_request(self.ticket)

    @pytest.mark.parametrize('database', CONSENT_DATABASES)
    @pytest.mark.parametrize('start_time, current_time, months_valid', [
        (datetime.datetime(2015, 1, 1), datetime.datetime(2015, 3, 1), 1),
        (datetime.datetime(2015, 1, 1), datetime.datetime(2016, 2, 1), 12),
    ])
    @patch('cmservice.consent.datetime')
    def test_if_nothing_is_return_if_policy_has_expired(self, mock_datetime, database, start_time, current_time,
                                                        months_valid):
        consent = Consent(self.attibutes, months_valid, timestamp=start_time)
        mock_datetime.now.return_value = current_time
        database.save_consent(self.consent_id, consent)
        assert not database.get_consent(self.consent_id)

    @pytest.mark.parametrize('database', CONSENT_DATABASES)
    @pytest.mark.parametrize('start_time, current_time, months_valid', [
        (datetime.datetime(2015, 1, 1), datetime.datetime(2015, 1, 30), 1),
        (datetime.datetime(2015, 1, 1), datetime.datetime(2015, 12, 31), 12),
    ])
    @patch('cmservice.consent.datetime')
    def test_if_policy_has_not_yet_expired(self, mock_datetime, database, start_time, current_time, months_valid):
        consent = Consent(self.attibutes, months_valid, timestamp=start_time)
        mock_datetime.now.return_value = current_time
        database.save_consent(self.consent_id, consent)
        assert database.get_consent(self.consent_id)

    @pytest.mark.parametrize('database', CONSENT_DATABASES)
    def test_remove_consent_from_db(self, database):
        database.save_consent(self.consent_id, self.consent)
        assert database.get_consent(self.consent_id)
        database.remove_consent(self.consent_id)
        assert not database.get_consent(self.consent_id)

    @pytest.mark.parametrize('database', CONSENT_DATABASES)
    def test_save_consent_for_all_attributes_by_entering_none(self, database):
        consent = Consent(None, 999)
        database.save_consent(self.consent_id, consent)
        assert database.get_consent(self.consent_id) == consent


class TestSQLite3ConsentDB(object):
    def test_store_db_in_file(self, tmpdir):
        consent_id = 'id1'
        consent = Consent(['attr1'], months_valid=1)
        tmp_file = os.path.join(str(tmpdir), "db")
        consent_db = SQLite3ConsentDB("salt", 1, tmp_file)
        consent_db.save_consent(consent_id, consent)
        assert consent_db.get_consent(consent_id) == consent

        # make sure it was persisted to file
        consent_db = SQLite3ConsentDB("salt", 1, tmp_file)
        assert consent_db.get_consent(consent_id) == consent


class TestSQLite3ConsentDB(object):
    def test_store_db_in_file(self, tmpdir):
        ticket = 'ticket1'
        consent_req = ConsentRequest({"foo": "bar"})
        tmp_file = os.path.join(str(tmpdir), "db")
        consent_req_db = SQLite3ConsentRequestDB("salt", tmp_file)
        consent_req_db.save_consent_request(ticket, consent_req)
        assert consent_req_db.get_consent_request(ticket) == consent_req

        # make sure it was persisted to file
        consent_db = SQLite3ConsentRequestDB("salt", tmp_file)
        assert consent_db.get_consent_request(ticket) == consent_req
