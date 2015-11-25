from datetime import datetime
import hashlib
import json
from time import gmtime, mktime

from jwkest import jws

from jwkest.jwt import JWT

from cmservice.database import ConsentDB
from cmservice.ticket_data import TicketData


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class ConsentManager(object, metaclass=Singleton):
    def __init__(self, db: ConsentDB, keys: list, ticket_ttl: int, max_month: int):
        """
        :param db:
        :param policy:
        :param keys: Public keys to verify JWT signature.
        :param ticket_ttl: How long the ticket should live in seconds.
        """
        self.db = db
        self.keys = keys
        self.ticket_ttl = ticket_ttl
        self.max_month = max_month

    def find_consent(self, id: str):
        """
        :param id: Identifier for a given consent
        :return True if valid consent exists else false
        """
        consent = self.db.get_consent(id)
        if consent:
            if not consent.has_expired(self.max_month):
                return json.dumps(consent.attributes)
        return None

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
