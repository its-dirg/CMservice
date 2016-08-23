from datetime import datetime, timedelta


class TicketData(object):
    def __init__(self, data: dict, timestamp: datetime = None):
        """
        :param data: information needed to show the consent page
        :param timestamp: when the ticket data object was created
        """
        if not timestamp:
            timestamp = datetime.now()
        self.timestamp = timestamp
        self.data = data

    def __eq__(self, other):
        return (
            isinstance(other, type(self)) and
            self.data == other.data and
            abs(self.timestamp - other.timestamp) < timedelta(seconds=1)
        )
