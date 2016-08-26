import hashlib
import json
from datetime import datetime

import dataset

from cmservice.consent import Consent
from cmservice.consent_request import ConsentRequest


def hash_id(id: str, salt: str):
    return hashlib.sha512(id.encode("utf-8") + salt.encode("utf-8")) \
        .hexdigest().encode("utf-8").decode("utf-8")


class ConsentRequestDB(object):
    def __init__(self, salt: str):
        """
        Constructor.
        :param salt: salt to use when hashing id's
        """
        self.salt = salt

    def save_consent_request(self, ticket: str, consent_request: ConsentRequest):
        """
        Saves a consent request, associated with the ticket.

        :param ticket: a consent ticket
        :param consent_request: a consent request
        """
        raise NotImplementedError("Must be implemented!")

    def get_consent_request(self, ticket: str) -> ConsentRequest:
        """
        Retrieves the consent request for a ticket.

        :param ticket: a consent ticket
        :return: the consent request
        """
        raise NotImplementedError("Must be implemented!")

    def remove_consent_request(self, ticket: str):
        """
        Removes a ticket from the database.

        :param ticket: a consent ticket
        """
        raise NotImplementedError("Must be implemented!")


class ConsentRequestDatasetDB(ConsentRequestDB):
    """
    Implementation using the `dataset` library.
    """
    TIME_PATTERN = "%Y %m %d %H:%M:%S"

    def __init__(self, salt: str, consent_request_path: str = None):
        """
        Constructor.
        :param consent_request_path:  path to the SQLite db.
                                If not specified an in-memory database will be used.
        """
        super().__init__(salt)
        if consent_request_path:
            self.consent_request_db = dataset.connect(consent_request_path)
        else:
            self.consent_request_db = dataset.connect('sqlite:///:memory:')
        self.consent_request_table = self.consent_request_db['consent_request']

    def save_consent_request(self, ticket: str, consent_request: ConsentRequest):
        row = {
            'ticket': hash_id(ticket, self.salt),
            'data': json.dumps(consent_request.data),
            'timestamp': consent_request.timestamp.strftime(ConsentRequestDatasetDB.TIME_PATTERN)
        }
        self.consent_request_table.insert(row)

    def get_consent_request(self, ticket: str) -> ConsentRequest:
        result = self.consent_request_table.find_one(ticket=hash_id(ticket, self.salt))
        if result:
            return ConsentRequest(json.loads(result['data']),
                                  timestamp=datetime.strptime(result['timestamp'],
                                                              ConsentRequestDatasetDB.TIME_PATTERN))
        return None

    def remove_consent_request(self, ticket: str):
        self.consent_request_table.delete(ticket=hash_id(ticket, self.salt))


class ConsentDB(object):
    def __init__(self, salt: str, max_months_valid: int):
        """
        Constructor.
        :param salt: salt which will be used for hashing id's
        :param max_months_valid: max number of months a consent should be valid
        """
        self.salt = salt
        self.max_month = max_months_valid

    def save_consent(self, id: str, consent: Consent):
        """
        Saves a consent.

        :param id: consent id
        :param consent: consent information
        """
        raise NotImplementedError("Must be implemented!")

    def get_consent(self, id: str) -> Consent:
        """
        Retrieves a consent.

        :param id: consent id
        :return: the associated consent information.
        """
        raise NotImplementedError("Must be implemented!")

    def remove_consent(self, id: str):
        """
        Removes a consent.

        :param id: A consent id.
        """
        raise NotImplementedError("Must be implemented!")


class ConsentDatasetDB(ConsentDB):
    """
    Implementation using the `dataset` library.
    """
    CONSENT_TABLE_NAME = 'consent'
    TIME_PATTERN = "%Y %m %d %H:%M:%S"

    def __init__(self, salt: str, max_months_valid: int, consent_db_path: str = None):
        """
        Constructor.
        :param consent_db_path: path to the SQLite db.
                                If not specified an in-memory database will be used.
        """
        super().__init__(salt, max_months_valid)
        if consent_db_path:
            self.consent_db = dataset.connect(consent_db_path)
        else:
            self.consent_db = dataset.connect('sqlite:///:memory:')
        self.consent_table = self.consent_db[self.CONSENT_TABLE_NAME]

    def save_consent(self, id: str, consent: Consent):
        data = {
            'consent_id': hash_id(id, self.salt),
            'timestamp': consent.timestamp.strftime(ConsentDatasetDB.TIME_PATTERN),
            'months_valid': consent.months_valid,
            'attributes': json.dumps(consent.attributes),
        }
        self.consent_table.insert(data)

    def get_consent(self, id: str) -> Consent:
        hashed_id = hash_id(id, self.salt)
        result = self.consent_table.find_one(consent_id=hashed_id)
        if not result:
            return None

        consent = Consent(json.loads(result['attributes']), result['months_valid'],
                          datetime.strptime(result['timestamp'], ConsentDatasetDB.TIME_PATTERN))
        if consent.has_expired(self.max_month):
            self.remove_consent(id)
            return None
        return consent

    def remove_consent(self, id: str):
        hashed_id = hash_id(id, self.salt)
        self.consent_table.delete(consent_id=hashed_id)
