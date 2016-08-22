import datetime
from unittest.mock import patch

import pytest

from cmservice.consent import Consent, StartDateInFuture


class TestConsent():
    def test_does_not_diff_a_single_month(self):
        current_date = datetime.datetime(2015, 1, 30)
        start_date = datetime.datetime(2015, 1, 1)
        assert Consent.monthdelta(start_date, current_date) == 0

    def test_does_diff_one_month(self):
        current_date = datetime.datetime(2015, 2, 1)
        start_date = datetime.datetime(2015, 1, 1)
        assert Consent.monthdelta(start_date, current_date) == 1

    def test_identifies_if_start_is_in_future(self):
        current_date = datetime.datetime(2015, 1, 1)
        start_date = datetime.datetime(2015, 2, 1)
        with pytest.raises(StartDateInFuture):
            Consent.monthdelta(start_date, current_date)

    @pytest.mark.parametrize("current_time, month", [
        (datetime.datetime(2015, 2, 28), 1),
        (datetime.datetime(2016, 1, 30), 12),
    ])
    @patch('cmservice.consent.Consent.get_current_time')
    def test_valid_consent_date(self, get_current_time, current_time, month):
        get_current_time.return_value = current_time
        start_date = datetime.datetime(2015, 1, 1)
        consent = Consent("id", None, month, timestamp=start_date)
        assert not consent.has_expired(999)

    @pytest.mark.parametrize("current_time, month, max_month", [
        (datetime.datetime(2015, 5, 1), 1, 999),
        (datetime.datetime(2015, 3, 1), 5, 1),
    ])
    @patch('cmservice.consent.Consent.get_current_time')
    def test_consent_has_expired(self, get_current_time, current_time, month, max_month):
        get_current_time.return_value = current_time
        start_date = datetime.datetime(2015, 1, 1)
        consent = Consent("id", None, month, timestamp=start_date)
        assert consent.has_expired(max_month)

    @patch('cmservice.consent.Consent.get_current_time')
    def test_start_date_in_the_future(self, get_current_time):
        get_current_time.return_value = datetime.datetime(2015, 1, 1)
        start_date = datetime.datetime(2015, 2, 1)
        consent = Consent("id", None, 1, timestamp=start_date)
        with pytest.raises(StartDateInFuture):
            consent.has_expired(999)

    def test_returns_none_when_dict_is_none(self):
        assert Consent.from_dict(None) == None
