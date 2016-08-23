import logging
from datetime import datetime, timedelta

from dateutil import relativedelta

LOGGER = logging.getLogger(__name__)


class Consent(object):
    def __init__(self, id: str, attributes: list, months_valid: int, timestamp: datetime = None):
        """

        :param id: identifier for the consent
        :param attributes: all attribute the user has given consent for. None implies
               that consent has been given for all attributes
        :param months_valid: policy for how long the consent is valid in months
        :param timestamp: datetime for when the consent was created
        """
        if not timestamp:
            timestamp = datetime.now()
        self.id = id
        self.timestamp = timestamp
        self.attributes = attributes
        self.months_valid = months_valid

    def __eq__(self, other) -> bool:
        return (isinstance(other, type(self))
                and self.id == other.id
                and self.months_valid == other.months_valid
                and self.attributes == other.attributes
                and abs(self.timestamp - other.timestamp) < timedelta(seconds=1))

    def has_expired(self, max_months_valid: int):
        """
        :param max_months_valid: maximum number of months any consent should be valid
        :return: True if this consent has expired, else False
        """
        delta = relativedelta.relativedelta(datetime.now(), self.timestamp)
        months_since_consent = delta.years * 12 + delta.months
        return months_since_consent > min(self.months_valid, max_months_valid)
