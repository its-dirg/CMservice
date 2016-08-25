import datetime
import os
from unittest.mock import patch

import pytest

from cmservice.consent import Consent
from cmservice.database import DictConsentDB, SQLite3ConsentDB, SQLite3ConsentRequestDB, DictConsentRequestDB


class TestConsentRequestDB():
    @pytest.fixture(autouse=True)
    def setup(self):
        self.ticket = 'ticket_123'

    @pytest.mark.parametrize('database', [DictConsentRequestDB('salt'), SQLite3ConsentRequestDB('salt')])
    def test_save_consent_request(self, consent_request, database):
        database.save_consent_request(self.ticket, consent_request)
        assert database.get_consent_request(self.ticket) == consent_request

    @pytest.mark.parametrize('database', [DictConsentRequestDB('salt'), SQLite3ConsentRequestDB('salt')])
    def test_remove_ticket(self, consent_request, database):
        database.save_consent_request(self.ticket, consent_request)
        database.remove_consent_request(self.ticket)
        assert not database.get_consent_request(self.ticket)


class TestConsentDB():
    @pytest.fixture(autouse=True)
    def setup(self):
        self.consent_id = 'id_123'
        self.attributes = ['name', 'email']
        self.consent = Consent(self.attributes, 1)

    @pytest.mark.parametrize('db_cls', [DictConsentDB, SQLite3ConsentDB])
    def test_save_consent(self, db_cls):
        database = db_cls('salt', 999)
        database.save_consent(self.consent_id, self.consent)
        assert self.consent == database.get_consent(self.consent_id)

    @pytest.mark.parametrize('db_cls', [DictConsentDB, SQLite3ConsentDB])
    @pytest.mark.parametrize('start_time, current_time, months_valid', [
        (datetime.datetime(2015, 1, 1), datetime.datetime(2015, 3, 1), 1),
        (datetime.datetime(2015, 1, 1), datetime.datetime(2016, 2, 1), 12),
    ])
    @patch('cmservice.consent.datetime')
    def test_if_nothing_is_return_if_policy_has_expired(self, mock_datetime, db_cls, start_time, current_time,
                                                        months_valid):
        consent = Consent(self.attributes, months_valid, timestamp=start_time)
        mock_datetime.now.return_value = current_time
        database = db_cls('salt', 999)
        database.save_consent(self.consent_id, consent)
        assert not database.get_consent(self.consent_id)

    @pytest.mark.parametrize('db_cls', [DictConsentDB, SQLite3ConsentDB])
    @pytest.mark.parametrize('start_time, current_time, months_valid', [
        (datetime.datetime(2015, 1, 1), datetime.datetime(2015, 1, 30), 1),
        (datetime.datetime(2015, 1, 1), datetime.datetime(2015, 12, 31), 12),
    ])
    @patch('cmservice.consent.datetime')
    def test_if_policy_has_not_yet_expired(self, mock_datetime, db_cls, start_time, current_time, months_valid):
        consent = Consent(self.attributes, months_valid, timestamp=start_time)
        mock_datetime.now.return_value = current_time
        database = db_cls('salt', 999)
        database.save_consent(self.consent_id, consent)
        assert database.get_consent(self.consent_id)

    @pytest.mark.parametrize('db_cls', [DictConsentDB, SQLite3ConsentDB])
    def test_remove_consent_from_db(self, db_cls):
        database = db_cls('salt', 999)
        database.save_consent(self.consent_id, self.consent)
        assert database.get_consent(self.consent_id)
        database.remove_consent(self.consent_id)
        assert not database.get_consent(self.consent_id)

    @pytest.mark.parametrize('db_cls', [DictConsentDB, SQLite3ConsentDB])
    def test_save_consent_for_all_attributes_by_entering_none(self, db_cls):
        consent = Consent(None, 999)
        database = db_cls('salt', 999)
        database.save_consent(self.consent_id, consent)
        assert database.get_consent(self.consent_id) == consent


class TestSQLite3ConsentDB(object):
    def test_store_db_in_file(self, tmpdir):
        consent_id = 'id1'
        consent = Consent(['attr1'], months_valid=1)
        tmp_file = os.path.join(str(tmpdir), 'db')
        consent_db = SQLite3ConsentDB('salt', 1, tmp_file)
        consent_db.save_consent(consent_id, consent)
        assert consent_db.get_consent(consent_id) == consent

        # make sure it was persisted to file
        consent_db = SQLite3ConsentDB('salt', 1, tmp_file)
        assert consent_db.get_consent(consent_id) == consent


class TestSQLite3ConsentRequestDB(object):
    def test_store_db_in_file(self, tmpdir, consent_request):
        ticket = 'ticket1'
        tmp_file = os.path.join(str(tmpdir), 'db')
        consent_req_db = SQLite3ConsentRequestDB('salt', tmp_file)
        consent_req_db.save_consent_request(ticket, consent_request)
        assert consent_req_db.get_consent_request(ticket) == consent_request

        # make sure it was persisted to file
        consent_db = SQLite3ConsentRequestDB('salt', tmp_file)
        assert consent_db.get_consent_request(ticket) == consent_request
