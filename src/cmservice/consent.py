from enum import Enum
from calendar import monthrange
from datetime import datetime, timedelta
import json


class ConsentPolicy(Enum):
    year = "year"
    month = "month"
    never = "never"

    @staticmethod
    def to_list():
        return [e.value for e in ConsentPolicy]

    def __str__(self):
        return self._name_


TIME_PATTERN = "%Y %m %d %H:%M:%S"


def format_datetime(datetime: datetime, format=None) -> datetime:
    """
    :param datetime: A datetime object to format using a given pattern
    :param format: the format to use, if non is defined TIME_PATTERN will be used
    :return: Formatted datetime object
    """
    if not format:
        format = TIME_PATTERN
    time_string = datetime.strftime(format)
    return datetime.strptime(time_string, format)


class Consent(object):
    def __init__(self, id: str, policy: ConsentPolicy, attributes: list, timestamp: datetime=None):
        """

        :param id: Identifier for the consent
        :param timestamp: Datetime for when the consent where created
        :param policy: The policy for how long the
        :param attributes: A list of attribute for which the user has given consent. None equals
               that consent has been given for all attributes
        """
        if not timestamp:
            timestamp = datetime.now()
        self.id = id
        self.timestamp = format_datetime(timestamp)
        self.policy = policy
        self.attributes = attributes

    @staticmethod
    def from_dict(dict: dict):
        """
        :param dict: The consent object as a dictionary
        :return: Consent object created from a dictionary
        """
        try:
            id = dict['consent_id']
            timestamp = datetime.strptime(dict['timestamp'], TIME_PATTERN)
            policy = ConsentPolicy(dict['policy'])
            attributes = json.loads(dict['attributes'])
            return Consent(id, policy, attributes, timestamp=timestamp)
        except TypeError:
            return None

    def to_dict(self):
        """
        :return: Consent object presented as a dictionary
        """
        return {
            'consent_id': self.id,
            'timestamp': self.timestamp.strftime(TIME_PATTERN),
            'policy': str(self.policy),
            'attributes': json.dumps(self.attributes)
        }

    def __eq__(self, other) -> bool:
        """
        :return: If all attributes in the consent object matches this method will return True else
                 false.
        """
        return (
            isinstance(other, self.__class__) and
            self.id == other.id and
            self.timestamp == other.timestamp,
            self.policy == other.policy,
            self.attributes == other.attributes
        )

    def get_current_time(self) -> datetime:
        """
        :return: The current datetime
        """
        return datetime.now()

    def has_expired(self, policy=None):
        if not policy:
            policy = self.policy

        current_date = self.get_current_time()
        if policy == ConsentPolicy.never:
            return False
        elif policy == ConsentPolicy.month and Consent.monthdelta(self.timestamp,
                                                                  current_date) >= 1:
            return True
        if policy == ConsentPolicy.year and Consent.monthdelta(self.timestamp, current_date) >= 12:
            return True
        return False

    @staticmethod
    def monthdelta(start_date: datetime, current_date: datetime) -> int:
        """
        :param start_date: The first date FROM which the delta should be calculated
        :param current_date: The second date TO which the delta should be calculated
        :return: Number of months from start_date to current_date
        """
        if start_date > current_date:
            raise StartDateInFuture("The start date, %s, is after current date, %s" %
                                    (start_date, current_date))
        delta = 0
        while True:
            mdays = monthrange(start_date.year, start_date.month)[1]
            start_date += timedelta(days=mdays)
            if start_date <= current_date:
                delta += 1
            else:
                break
        return delta


class StartDateInFuture(Exception):
    pass
