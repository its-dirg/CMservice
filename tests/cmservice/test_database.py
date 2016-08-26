import datetime
import os
from unittest.mock import patch

import pytest

from cmservice.consent import Consent
from cmservice.database import ConsentDatasetDB, ConsentRequestDatasetDB


@pytest.fixture
def consent_database():
    return ConsentDatasetDB("salt", 999)


@pytest.fixture
def consent_request_database():
    return ConsentRequestDatasetDB("salt")


class TestConsentRequestDB():
    @pytest.fixture(autouse=True)
    def setup(self):
        self.ticket = 'ticket_123'

    def test_save_consent_request(self, consent_request, consent_request_database):
        consent_request_database.save_consent_request(self.ticket, consent_request)
        assert consent_request_database.get_consent_request(self.ticket) == consent_request

    def test_remove_ticket(self, consent_request, consent_request_database):
        consent_request_database.save_consent_request(self.ticket, consent_request)
        consent_request_database.remove_consent_request(self.ticket)
        assert not consent_request_database.get_consent_request(self.ticket)


class TestConsentDB():
    @pytest.fixture(autouse=True)
    def setup(self):
        self.consent_id = 'id_123'
        self.attributes = ['name', 'email']
        self.consent = Consent(self.attributes, 1)

    def test_save_consent(self, consent_database):
        consent_database.save_consent(self.consent_id, self.consent)
        assert self.consent == consent_database.get_consent(self.consent_id)

    @pytest.mark.parametrize('start_time, current_time, months_valid', [
        (datetime.datetime(2015, 1, 1), datetime.datetime(2015, 3, 1), 1),
        (datetime.datetime(2015, 1, 1), datetime.datetime(2016, 2, 1), 12),
    ])
    @patch('cmservice.consent.datetime')
    def test_if_nothing_is_return_if_policy_has_expired(self, mock_datetime, start_time, current_time, months_valid,
                                                        consent_database):
        consent = Consent(self.attributes, months_valid, timestamp=start_time)
        mock_datetime.now.return_value = current_time
        consent_database.save_consent(self.consent_id, consent)
        assert not consent_database.get_consent(self.consent_id)

    @pytest.mark.parametrize('start_time, current_time, months_valid', [
        (datetime.datetime(2015, 1, 1), datetime.datetime(2015, 1, 30), 1),
        (datetime.datetime(2015, 1, 1), datetime.datetime(2015, 12, 31), 12),
    ])
    @patch('cmservice.consent.datetime')
    def test_if_policy_has_not_yet_expired(self, mock_datetime, start_time, current_time, months_valid,
                                           consent_database):
        consent = Consent(self.attributes, months_valid, timestamp=start_time)
        mock_datetime.now.return_value = current_time
        consent_database.save_consent(self.consent_id, consent)
        assert consent_database.get_consent(self.consent_id)

    def test_remove_consent_from_db(self, consent_database):
        consent_database.save_consent(self.consent_id, self.consent)
        assert consent_database.get_consent(self.consent_id)
        consent_database.remove_consent(self.consent_id)
        assert not consent_database.get_consent(self.consent_id)

    def test_save_consent_for_all_attributes_by_entering_none(self, consent_database):
        consent = Consent(None, 999)
        consent_database.save_consent(self.consent_id, consent)
        assert consent_database.get_consent(self.consent_id) == consent


class TestSQLite3ConsentDB(object):
    def test_store_db_in_file(self, tmpdir):
        consent_id = 'id1'
        consent = Consent(['attr1'], months_valid=1)
        tmp_file = os.path.join(str(tmpdir), 'db')
        db_url = 'sqlite:///' + tmp_file
        consent_db = ConsentDatasetDB('salt', 1, db_url)
        consent_db.save_consent(consent_id, consent)
        assert consent_db.get_consent(consent_id) == consent

        # make sure it was persisted to file
        consent_db = ConsentDatasetDB('salt', 1, db_url)
        assert consent_db.get_consent(consent_id) == consent


class TestSQLite3ConsentRequestDB(object):
    def test_store_db_in_file(self, tmpdir, consent_request):
        ticket = 'ticket1'
        tmp_file = os.path.join(str(tmpdir), 'db')
        db_url = 'sqlite:///' + tmp_file
        consent_req_db = ConsentRequestDatasetDB('salt', db_url)
        consent_req_db.save_consent_request(ticket, consent_request)
        assert consent_req_db.get_consent_request(ticket) == consent_request

        # make sure it was persisted to file
        consent_db = ConsentRequestDatasetDB('salt', db_url)
        assert consent_db.get_consent_request(ticket) == consent_request
