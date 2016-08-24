import hashlib
import json
import logging
from time import gmtime, mktime

import jwkest
from jwkest import jws

from cmservice.consent import Consent
from cmservice.database import ConsentDB, ConsentRequestDB
from cmservice.consent_request import ConsentRequest

logger = logging.getLogger(__name__)


class InvalidConsentRequestError(ValueError):
    pass


class ConsentManager(object):
    def __init__(self, consent_db: ConsentDB, ticket_db: ConsentRequestDB, trusted_keys: list, ticket_ttl: int,
                 max_months_valid: int):
        """
        :param consent_db: database in which the consent information is stored
        :param ticket_db: database in which the ticket information is stored
        :param trusted_keys: trusted public keys to verify JWT signature.
        :param ticket_ttl: how long the ticket should live in seconds.
        :param max_months_valid: how long the consent should be valid
        """
        self.consent_db = consent_db
        self.ticket_db = ticket_db
        self.trusted_keys = trusted_keys
        self.ticket_ttl = ticket_ttl
        self.max_months_valid = max_months_valid

    def fetch_consented_attributes(self, id: str):
        """
        :param id: Identifier for a given consent
        :param salt: Salt which is needed in order to receive the same consent
        as the one stored in the database
        :return True if valid consent exists else false
        """
        consent = self.consent_db.get_consent(id)
        if consent and not consent.has_expired(self.max_months_valid):
            return consent.attributes

        logger.debug('No consented attributes for id: \'%s\'', id)
        return None

    def save_consent_request(self, jwt: str):
        """
        :param jwt: JWT represented as a string
        """
        try:
            request = jws.factory(jwt).verify_compact(jwt, self.trusted_keys)
        except jwkest.Invalid as e:
            logger.debug('invalid signature: %s', str(e))
            raise InvalidConsentRequestError('Invalid signature') from e

        try:
            data = ConsentRequest(request)
        except ValueError:
            logger.debug('invalid consent request: %s', json.dumps(request))
            raise InvalidConsentRequestError('Invalid consent request')

        ticket = hashlib.sha256((jwt + str(mktime(gmtime()))).encode("UTF-8")).hexdigest()
        self.ticket_db.save_consent_request(ticket, data)
        return ticket

    def fetch_consent_request(self, ticket: str):
        """
        :param ticket: Identifier for the ticket
        :return: Information about the consent request
        """
        ticketdata = self.ticket_db.get_consent_request(ticket)
        if ticketdata:
            self.ticket_db.remove_consent_request(ticket)
            logger.debug('found consent request: %s', ticketdata.data)
            return ticketdata.data
        else:
            logger.debug('failed to retrieve ticket data from ticket: %s' % ticket)
            return None

    def save_consent(self, id: str, consent: Consent):
        """
        :param consent: The consent object to store
        :param salt: salt used in hash function
        """
        self.consent_db.save_consent(id, consent)
