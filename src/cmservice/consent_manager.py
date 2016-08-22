import hashlib
import json
import logging
from datetime import datetime
from time import gmtime, mktime

from jwkest import jws
from jwkest.jwt import JWT

from cmservice.database import ConsentDB, TicketDB
from cmservice.ticket_data import TicketData

LOGGER = logging.getLogger(__name__)


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class ConsentManager(object, metaclass=Singleton):
    def __init__(self, consent_db: ConsentDB, ticket_db: TicketDB, keys: list, ticket_ttl: int,
                 max_month: int):
        """
        :param consent_db: database in which the consent information is stored
        :param ticket_db: database in which the ticket information is stored
        :param keys: Public keys to verify JWT signature.
        :param ticket_ttl: How long the ticket should live in seconds.
        :param max_month: For how long the consent should be valid
        """
        self.consent_db = consent_db
        self.ticket_db = ticket_db
        self.keys = keys
        self.ticket_ttl = ticket_ttl
        self.max_month = max_month

    def find_consent(self, id: str, salt: str):
        """
        :param id: Identifier for a given consent
        :param salt: Salt which is needed in order to receive the same consent
        as the one stored in the database
        :return True if valid consent exists else false
        """
        id = ConsentManager.hash_consent_id(id, salt)
        consent = self.consent_db.get_consent(id)
        if consent:
            if not consent.has_expired(self.max_month):
                return json.dumps(consent.attributes)
        return None

    def verify_ticket(self, ticket: str):
        """
        Verifies if the ticket is valid and removes it from the database.

        :param ticket: Identifier for a ticket
        """
        data = self.ticket_db.get_ticketdata(ticket)
        if (datetime.now() - data.timestamp).total_seconds() > self.ticket_ttl:
            self.ticket_db.remove_ticket(ticket)

    def save_consent_req(self, jwt: str):
        """
        :param jwt: JWT represented as a string
        """
        self.verify_jwt(jwt)
        jso = self.unpack_jwt(jwt)
        ticket = hashlib.sha256((jwt + str(mktime(gmtime()))).encode("UTF-8")).hexdigest()
        data = TicketData(jso)
        self.ticket_db.save_consent_request(ticket, data)
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
            ticketdata = self.ticket_db.get_ticketdata(ticket)
            self.ticket_db.remove_ticket(ticket)
            return ticketdata.data
        except:
            LOGGER.warning("Falied to retrive ticket data from ticket: %s" % ticket)
            return None

    @staticmethod
    def hash_consent_id(id: str, salt: str):
        return hashlib.sha512(id.encode("utf-8") + salt.encode("utf-8")) \
            .hexdigest().encode("utf-8").decode("utf-8")

    def save_consent(self, consent, salt):
        """
        :param consent: The consent object to store
        :param salt: salt used in hash function
        """
        consent.id = ConsentManager.hash_consent_id(consent.id, salt)
        self.consent_db.save_consent(consent)
