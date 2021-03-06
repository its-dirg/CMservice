from datetime import datetime, timedelta


class ConsentRequest(object):
    def __init__(self, data: dict, timestamp: datetime = None):
        """
        :param data: params in the consent request, will be displayed on the consent page
        :param timestamp: when the request object was created
        """
        mandatory_params = {'id', 'attr', 'redirect_endpoint'}
        if not mandatory_params.issubset(set(data.keys())):
            # missing required info
            raise ValueError('Incorrect consent request, missing some mandatory params'.format(mandatory_params))

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
