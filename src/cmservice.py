from enum import Enum
from calendar import monthrange
from datetime import datetime, timedelta
import hashlib
import json
from time import gmtime, mktime

import dataset
from jwkest import jws
from jwkest.jwt import JWT

__author__ = 'haho0032'


class ConectPolicy(Enum):
    year = 0
    month = 1
    never = 2


TIME_PATTERN = "%Y %m %d %H:%M:%S"


def format_datetime(timestamp):
    time_string = timestamp.strftime(TIME_PATTERN)
    return datetime.strptime(time_string, TIME_PATTERN)


class Consent(object):
    def __init__(self, id, timestamp):
        """

        :type id: str
        :timestamp datetime

        :param id:
        :param timestamp:
        :return:
        """
        self.id = id
        self.timestamp = format_datetime(timestamp)

    @staticmethod
    def from_dict(dict):
        try:
            id = dict['consent_id']
            timestamp = datetime.strptime(dict['timestamp'], TIME_PATTERN)
            return Consent(id, timestamp)
        except TypeError:
            return None

    def to_dict(self):
        return {'consent_id': self.id, 'timestamp': self.timestamp.strftime(TIME_PATTERN)}

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__) and
            self.id == other.id and
            self.timestamp == other.timestamp
        )


class TicketData(object):
    def __init__(self, timestamp, data):
        """

        :timestamp datetime
        :data: dict

        :param timestamp:
        :param data:
        :return:
        """
        self.timestamp = format_datetime(timestamp)
        self.data = data

    @staticmethod
    def from_dict(_dict):
        try:
            timestamp = datetime.strptime(_dict['timestamp'], TIME_PATTERN)
            data = _dict['data']
            return TicketData(timestamp, json.loads(data))
        except TypeError:
            return None

    def to_dict(self):
        return {'data': json.dumps(self.data), 'timestamp': self.timestamp.strftime(TIME_PATTERN)}

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__) and
            self.data == other.data and
            self.timestamp == other.timestamp
        )

class ConsentDB(object):
    """This is a base class that defines the method that must be implemented to keep state"""

    def save_consent(self, consent):
        """
        Will save a consent.

        :type consent: Consent

        :param consent: A given consent. A consent is always allow.
        """
        raise NotImplementedError("Must be implemented!")

    def save_consent_request(self, ticket, data):
        """
        Will save a concent request and generate a ticket.

        :type ticket: str
        :type data: TicketData
        :rtype: str

        :param id: A consent ticket.
        :param data: Ticket data.
        """
        raise NotImplementedError("Must be implemented!")

    def get_consent(self, id):
        """
        Will retrive a given consent.
        :type id: str
        :rtype: Consent

        :param id: The identification for a consent.
        :return: A given consent.
        """
        raise NotImplementedError("Must be implemented!")

    def get_ticketdata(self, ticket):
        """
        Will retrive registered data for a ticket.

        :type id: str
        :rtype: TicketData

        :param id: The identification for a consent.
        :return: The data connected to a ticket.
        """
        raise NotImplementedError("Must be implemented!")

    def remove_ticket(self, ticket):
        """
        Removes a ticket from the database.
        :type ticket: str

        :param ticket: A consent ticket.
        """
        raise NotImplementedError("Must be implemented!")


class DictConsentDB(ConsentDB):

    def __init__(self):
        self.c_db = {}
        self.tickets = {}

    def save_consent(self, consent):
        """
        Will save a consent.

        :type consent: Consent

        :param consent: A given consent. A consent is always allow.
        """
        self.c_db[consent.id] = consent

    def save_consent_request(self, ticket, data):
        """
        Will save a concent request and generate a ticket.

        :type ticket: str
        :type data: TicketData
        :rtype: str

        :param id: A consent ticket.
        :param data: Ticket data.
        """
        self.tickets[ticket] = data

    def get_consent(self, id):
        """
        Will retrive a given consent.
        :type id: str
        :rtype: Consent

        :param id: The identification for a consent.
        :return: A given consent.
        """
        if id not in self.c_db:
            return None
        return self.c_db[id]

    def get_ticketdata(self, ticket):
        """
        Will retrive registered data for a ticket.

        :type id: str
        :rtype: TicketData

        :param id: The identification for a consent.
        :return: The data connected to a ticket.
        """
        if ticket in self.tickets:
            return self.tickets[ticket]
        return None

    def remove_ticket(self, ticket):
        """
        Removes a ticket from the database.
        :type ticket: str

        :param ticket: A consent ticket.
        """
        if ticket in self.tickets:
            self.tickets.pop(ticket)


class SQLite3ConsentDB(ConsentDB):
    CONSENT_TABLE_NAME = 'consent'
    TICKET_TABLE_NAME = 'ticket'

    def __init__(self, database_path=None):
        self.c_db = dataset.connect('sqlite:///:memory:')
        if database_path:
            self.c_db = dataset.connect('sqlite:///' + database_path)
        self.consent_table = self.c_db[self.CONSENT_TABLE_NAME]
        self.ticket_table = self.c_db[self.TICKET_TABLE_NAME]

    def save_consent(self, consent):
        """
        Will save a consent.

        :type consent: Consent

        :param consent: A given consent. A consent is always allow.
        """
        self.consent_table.upsert(consent.to_dict(), ['consent_id'])

    def get_consent(self, id):
        """
        Will retrive a given consent.
        :type id: str
        :rtype: Consent

        :param id: The identification for a consent.
        :return: A given consent.
        """
        result = self.consent_table.find_one(consent_id=id)
        return Consent.from_dict(result)

    def save_consent_request(self, ticket, data):
        """
        Will save a concent request and generate a ticket.

        :type ticket: str
        :type data: TicketData
        :rtype: str

        :param id: A consent ticket.
        :param data: Ticket data.
        """
        row = {"ticket": ticket}
        row.update(data.to_dict())
        self.ticket_table.upsert(row, ['ticket'])

    def get_ticketdata(self, ticket):
        """
        Will retrive registered data for a ticket.

        :type id: str
        :rtype: TicketData

        :param id: The identification for a consent.
        :return: The data connected to a ticket.
        """
        result = self.ticket_table.find_one(ticket=ticket)
        return TicketData.from_dict(result)

    def remove_ticket(self, ticket):
        """
        Removes a ticket from the database.
        :type ticket: str

        :param ticket: A consent ticket.
        """
        self.ticket_table.delete(ticket=ticket)


class ConsentManager(object):

    def __init__(self, db, policy, keys, ticket_ttl):
        """

        :type db: ConsentDB
        :type policy: ConectPolicy
        :type keys: []
        :type ticket_ttl: int

        :param db:
        :param policy:
        :param keys: Public keys to verify JWT signature.
        :param ticket_ttl: How long the ticket should live in seconds.
        :return:
        """
        self.db = db
        self.policy = policy
        self.keys = keys
        self.ticket_ttl = ticket_ttl

    def find_consent(self, id):
        consent = self.db.get_consent(id)
        if consent is None:
            return False
        if self.policy == ConectPolicy.never:
            return True
        now = datetime.now()
        if self.policy == ConectPolicy.month and self.monthdelta(now, consent.timestamp) == 0:
            return True
        if self.policy == ConectPolicy.year and self.monthdelta(now, consent.timestamp) < 12:
            return True
        return False

    def verify_ticket(self, ticket):
        """
        Verifies if the ticket is valid and removes it from the database.
        :param ticket:
        :return:
        """
        data = self.db.get_ticketdata(ticket)
        if (datetime.now()-data.timestamp).total_seconds() > self.ticket_ttl:
            self.db.remove_ticket(ticket)

    def save_consent_req(self, jwt):
        self.verify_jwt(jwt)
        jso = self.unpack_jwt(jwt)
        ticket = hashlib.sha256((jwt + str(mktime(gmtime()))).encode("UTF-8")).hexdigest()
        data = TicketData(datetime.now(), jso)
        self.db.save_consent_request(ticket, data)
        return ticket

    def verify_jwt(self, jwt):
        _jw = jws.factory(jwt)
        _jw.verify_compact(jwt, self.keys)

    def unpack_jwt(self, jwt):
        _jwt = JWT().unpack(jwt)
        jso = _jwt.payload()
        if "id" not in jso or "attr" not in jso or "redirect_endpoint" not in jso:
            return None
        return jso

    def get_attributes(self, ticket):
        try:
            ticketdata = self.db.get_ticketdata(ticket)
            self.db.remove_ticket(ticket)
            return ticketdata.data
        except:
            return None

    def save_consent(self, consent):
        self.db.save_consent(consent)

    def monthdelta(self, date_1, date_2):
        delta = 0
        while True:
            mdays = monthrange(date_1.year, date_1.month)[1]
            date_1 += timedelta(days=mdays)
            if date_1 <= date_2:
                delta += 1
            else:
                break
        return delta
