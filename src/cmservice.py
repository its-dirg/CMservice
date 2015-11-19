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


class ConsentPolicy(Enum):
    year = "year"
    month = "month"
    never = "never"

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

class ConsentDB(object):
    """This is a base class that defines the method that must be implemented to keep state"""

    def save_consent(self, consent: Consent):
        """
        Will save a consent.

        :param consent: A given consent. A consent is always allow.
        """
        raise NotImplementedError("Must be implemented!")

    def save_consent_request(self, ticket: str, data: TicketData) -> str:
        """
        Will save a concent request and generate a ticket.

        :param id: A consent ticket.
        :param data: Ticket data.
        """
        raise NotImplementedError("Must be implemented!")

    def get_consent(self, id: str) -> Consent:
        """
        Will retrive a given consent.

        :param id: The identification for a consent.
        :return: A given consent.
        """
        raise NotImplementedError("Must be implemented!")

    def get_ticketdata(self, ticket: str) -> TicketData:
        """
        Will retrive registered data for a ticket.

        :param ticket: The identification for a TicketData object.
        :return: The data connected to a ticket.
        """
        raise NotImplementedError("Must be implemented!")

    def remove_ticket(self, ticket: str):
        """
        Removes a ticket from the database.

        :param ticket: A consent ticket.
        """
        raise NotImplementedError("Must be implemented!")


class DictConsentDB(ConsentDB):

    def __init__(self):
        self.c_db = {}
        self.tickets = {}

    def save_consent(self, consent: Consent):
        """
        Will save a consent.

        :param consent: A given consent. A consent is always allow.
        """
        self.c_db[consent.id] = consent

    def save_consent_request(self, ticket: str, data: TicketData) -> str:
        """
        Will save a concent request and generate a ticket.

        :param id: A consent ticket.
        :param data: Ticket data.
        """
        self.tickets[ticket] = data

    def get_consent(self, id: str) -> Consent:
        """
        Will retrive a given consent.

        :param id: The identification for a consent.
        :return: A given consent.
        """
        if id not in self.c_db:
            return None
        return self.c_db[id]

    def get_ticketdata(self, ticket: str) -> TicketData:
        """
        Will retrive registered data for a ticket.

        :param id: The identification for a consent.
        :return: The data connected to a ticket.
        """
        if ticket in self.tickets:
            return self.tickets[ticket]
        return None

    def remove_ticket(self, ticket: str):
        """
        Removes a ticket from the database.

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

    def save_consent(self, consent: Consent):
        """
        Will save a consent.

        :param consent: A given consent. A consent is always allow.
        """
        self.consent_table.upsert(consent.to_dict(), ['consent_id'])

    def save_consent_request(self, ticket: str, data: TicketData) -> str:
        """
        Will save a concent request and generate a ticket.

        :param id: A consent ticket.
        :param data: Ticket data.
        """
        row = {"ticket": ticket}
        row.update(data.to_dict())
        self.ticket_table.upsert(row, ['ticket'])

    def get_consent(self, id: str) -> Consent:
        """
        Will retrive a given consent.

        :param id: The identification for a consent.
        :return: A given consent.
        """
        result = self.consent_table.find_one(consent_id=id)
        consent = Consent.from_dict(result)
        if consent:
            if consent.has_expired():
                self.remove_consent(id)
                return None
        return consent

    def remove_consent(self, id: str):
        """
        Removes a consent from the database.

        :param id: The identification for a consent.
        """
        self.consent_table.delete(consent_id=id)

    def get_ticketdata(self, ticket: str) -> TicketData:
        """
        Will retrive registered data for a ticket.

        :param id: The identification for a consent.
        :return: The data connected to a ticket.
        """
        result = self.ticket_table.find_one(ticket=ticket)
        return TicketData.from_dict(result)

    def remove_ticket(self, ticket: str):
        """
        Removes a ticket from the database.

        :param ticket: A consent ticket.
        """
        self.ticket_table.delete(ticket=ticket)


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class ConsentManager(object, metaclass=Singleton):
    def __init__(self, db: ConsentDB, policy: ConsentPolicy, keys: list, ticket_ttl: int):
        """
        :param db:
        :param policy:
        :param keys: Public keys to verify JWT signature.
        :param ticket_ttl: How long the ticket should live in seconds.
        """
        self.db = db
        self.policy = policy
        self.keys = keys
        self.ticket_ttl = ticket_ttl

    def find_consent(self, id: int):
        """
        :param id: Identifier for a given consent
        :return True if valid consent exists else false
        """
        consent = self.db.get_consent(id)
        if consent is None:
            return False
        # TODO at the moment the user interface don't support policies
        return not consent.has_expired(policy=self.policy)

    def verify_ticket(self, ticket: str):
        """
        Verifies if the ticket is valid and removes it from the database.

        :param ticket: Identifier for a ticket
        """
        data = self.db.get_ticketdata(ticket)
        if (datetime.now()-data.timestamp).total_seconds() > self.ticket_ttl:
            self.db.remove_ticket(ticket)

    def save_consent_req(self, jwt: str):
        """
        Verifies if the ticket is valid and removes it from the database.

        :param jwt: JWT represented as a string
        """
        self.verify_jwt(jwt)
        jso = self.unpack_jwt(jwt)
        ticket = hashlib.sha256((jwt + str(mktime(gmtime()))).encode("UTF-8")).hexdigest()
        data = TicketData(jso)
        self.db.save_consent_request(ticket, data)
        return ticket

    def verify_jwt(self, jwt: str):
        """
        Verifies the signature of the JWT

        :param jwt: JWT represented as a string
        """
        _jw = jws.factory(jwt)
        _jw.verify_compact(jwt, self.keys)

    def unpack_jwt(self, jwt: str):
        """
        :param jwt: JWT represented as a string
        """
        _jwt = JWT().unpack(jwt)
        jso = _jwt.payload()
        if "id" not in jso or "attr" not in jso or "redirect_endpoint" not in jso:
            return None
        return jso

    def get_attributes(self, ticket: str):
        """
        :param ticket: Identifier for the ticket
        :return: Information about the consent request
        """
        try:
            ticketdata = self.db.get_ticketdata(ticket)
            self.db.remove_ticket(ticket)
            return ticketdata.data
        except:
            return None

    def save_consent(self, consent):
        """
        :param consent: The consent object to store
        """
        self.db.save_consent(consent)
