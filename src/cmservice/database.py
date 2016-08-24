import json
from datetime import datetime

import dataset

from cmservice.consent import Consent
from cmservice.ticket_data import ConsentRequest


class ConsentRequestDB(object):
    def save_consent_request(self, ticket: str, consent_request: ConsentRequest) -> str:
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


class DictConsentRequestDB(ConsentRequestDB):
    def __init__(self):
        super(DictConsentRequestDB, self).__init__()
        self.tickets = {}

    def save_consent_request(self, ticket: str, consent_request: ConsentRequest) -> str:
        self.tickets[ticket] = consent_request

    def get_consent_request(self, ticket: str) -> ConsentRequest:
        try:
            return self.tickets[ticket]
        except KeyError:
            return None

    def remove_consent_request(self, ticket: str):
        try:
            del self.tickets[ticket]
        except KeyError:
            pass


class SQLite3ConsentRequestDB(ConsentRequestDB):
    TICKET_TABLE_NAME = 'consent_request'
    TIME_PATTERN = "%Y %m %d %H:%M:%S"

    def __init__(self, ticket_db_path: str = None):
        """
        Constructor.
        :param ticket_db_path:  path to the SQLite db.
                                If not specified an in-memory database will be used.
        """
        super(SQLite3ConsentRequestDB, self).__init__()
        if ticket_db_path:
            self.ticket_db = dataset.connect('sqlite:///' + ticket_db_path)
        else:
            self.ticket_db = dataset.connect('sqlite:///:memory:')
        self.ticket_table = self.ticket_db[self.TICKET_TABLE_NAME]

    def save_consent_request(self, ticket: str, consent_request: ConsentRequest) -> str:
        row = {
            'ticket': ticket,
            'data': json.dumps(consent_request.data),
            'timestamp': consent_request.timestamp.strftime(SQLite3ConsentRequestDB.TIME_PATTERN)
        }
        self.ticket_table.upsert(row, ['ticket'])

    def get_consent_request(self, ticket: str) -> ConsentRequest:
        result = self.ticket_table.find_one(ticket=ticket)
        if result:
            return ConsentRequest(json.loads(result['data']),
                                  timestamp=datetime.strptime(result['timestamp'],
                                                              SQLite3ConsentRequestDB.TIME_PATTERN))
        return None

    def remove_consent_request(self, ticket: str):
        self.ticket_table.delete(ticket=ticket)


class ConsentDB(object):
    def __init__(self, max_months_valid: int):
        self.max_month = max_months_valid

    def save_consent(self, consent: Consent):
        """
        Saves a consent.

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


class DictConsentDB(ConsentDB):
    def __init__(self, max_months_valid: int):
        super(DictConsentDB, self).__init__(max_months_valid)
        self.consent_db = {}

    def save_consent(self, consent: Consent):
        self.consent_db[consent.id] = consent

    def get_consent(self, id: str) -> Consent:
        if id not in self.consent_db:
            return None
        consent = self.consent_db[id]
        if consent.has_expired(self.max_month):
            self.remove_consent(id)
            return None
        return self.consent_db[id]

    def remove_consent(self, id: str):
        del self.consent_db[id]


class SQLite3ConsentDB(ConsentDB):
    CONSENT_TABLE_NAME = 'consent'
    TIME_PATTERN = "%Y %m %d %H:%M:%S"

    def __init__(self, max_months_valid: int, consent_db_path: str = None):
        """
        Constructor.
        :param consent_db_path: path to the SQLite db.
                                If not specified an in-memory database will be used.
        """
        super(SQLite3ConsentDB, self).__init__(max_months_valid)
        if consent_db_path:
            self.consent_db = dataset.connect('sqlite:///' + consent_db_path)
        else:
            self.consent_db = dataset.connect('sqlite:///:memory:')
        self.consent_table = self.consent_db[self.CONSENT_TABLE_NAME]

    def save_consent(self, consent: Consent):
        data = {
            'consent_id': consent.id,
            'timestamp': consent.timestamp.strftime(SQLite3ConsentDB.TIME_PATTERN),
            'months_valid': consent.months_valid,
            'attributes': json.dumps(consent.attributes),
        }
        self.consent_table.upsert(data, ['consent_id'])

    def get_consent(self, id: str) -> Consent:
        result = self.consent_table.find_one(consent_id=id)
        if not result:
            return None

        consent = Consent(result['consent_id'], json.loads(result['attributes']), result['months_valid'],
                          datetime.strptime(result['timestamp'], SQLite3ConsentDB.TIME_PATTERN))
        if consent.has_expired(self.max_month):
            self.remove_consent(id)
            return None
        return consent

    def remove_consent(self, id: str):
        self.consent_table.delete(consent_id=id)
