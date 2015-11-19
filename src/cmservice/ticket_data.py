from datetime import datetime
import json

from cmservice.consent import format_datetime, TIME_PATTERN


class TicketData(object):
    def __init__(self, data: dict, timestamp: datetime=None):
        """
        :param data: Information needed to show the consent page
        :param timestamp: the the ticket data object where created
        """
        if not timestamp:
            timestamp = datetime.now()
        self.timestamp = format_datetime(timestamp)
        self.data = data

    @staticmethod
    def from_dict(_dict):
        """
        :param dict: The TicketData object represented as a dictionary
        :return: TicketData object created from a dictionary
        """
        try:
            timestamp = datetime.strptime(_dict['timestamp'], TIME_PATTERN)
            data = _dict['data']
            return TicketData(json.loads(data), timestamp=timestamp)
        except TypeError:
            return None

    def to_dict(self):
        """
        :return: TicketData object as a dictionary
        """
        return {'data': json.dumps(self.data), 'timestamp': self.timestamp.strftime(TIME_PATTERN)}

    def __eq__(self, other):
        """
        :return: If all attributes in the TicketData object matches this method will return True
                 else False.
        """
        return (
            isinstance(other, self.__class__) and
            self.data == other.data and
            self.timestamp == other.timestamp
        )
