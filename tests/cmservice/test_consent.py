import datetime
from unittest.mock import patch

import pytest

from cmservice.consent import Consent


class TestConsent():
    @pytest.mark.parametrize('current_time, month', [
        (datetime.datetime(2015, 2, 28), 1),
        (datetime.datetime(2016, 1, 30), 12),
    ])
    @patch('cmservice.consent.datetime')
    def test_valid_consent_date(self, mock_datetime, current_time, month):
        mock_datetime.now.return_value = current_time
        start_date = datetime.datetime(2015, 1, 1)
        consent = Consent('id', None, month, timestamp=start_date)
        assert not consent.has_expired(999)

    @pytest.mark.parametrize('current_time, month, max_month', [
        (datetime.datetime(2015, 5, 1), 1, 999),
        (datetime.datetime(2015, 3, 1), 5, 1),
    ])
    @patch('cmservice.consent.datetime')
    def test_consent_has_expired(self, mock_datetime, current_time, month, max_month):
        mock_datetime.now.return_value = current_time
        start_date = datetime.datetime(2015, 1, 1)
        consent = Consent('id', None, month, timestamp=start_date)
        assert consent.has_expired(max_month)
