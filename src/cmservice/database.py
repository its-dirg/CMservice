import dataset

from cmservice.consent import Consent
from cmservice.ticket_data import TicketData


class TicketDB(object):
    def save_consent_request(self, ticket: str, data: TicketData) -> str:
        """
        Will save a concent request and generate a ticket.

        :param id: A consent ticket.
        :param data: Ticket data.
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

    def size(self):
        """
        :return: The number of entries in the database
        """
        raise NotImplementedError("Must be implemented!")


class DictTicketDB(TicketDB):
    def __init__(self):
        super(DictTicketDB, self).__init__()
        self.tickets = {}

    def save_consent_request(self, ticket: str, data: TicketData) -> str:
        """
        Will save a concent request and generate a ticket.

        :param id: A consent ticket.
        :param data: Ticket data.
        """
        self.tickets[ticket] = data

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

    def size(self):
        """
        :return: The number of entries in the database
        """
        return len(self.tickets)


class SQLite3TicketDB(TicketDB):
    TICKET_TABLE_NAME = 'ticket'

    def __init__(self, ticket_db_path=None):
        super(SQLite3TicketDB, self).__init__()
        self.ticket_db = dataset.connect('sqlite:///:memory:')
        if ticket_db_path:
            self.ticket_db = dataset.connect('sqlite:///' + ticket_db_path)
        self.ticket_table = self.ticket_db[self.TICKET_TABLE_NAME]

    def save_consent_request(self, ticket: str, data: TicketData) -> str:
        """
        Will save a concent request and generate a ticket.

        :param id: A consent ticket.
        :param data: Ticket data.
        """
        row = {"ticket": ticket}
        row.update(data.to_dict())
        self.ticket_table.upsert(row, ['ticket'])

    def get_ticketdata(self, ticket: str) -> TicketData:
        """
        Will retrive registered data for a ticket.

        :param id: The identification for a ticket.
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

    def size(self):
        """
        :return: The number of entries in the database
        """
        return self.ticket_table.count()


class ConsentDB(object):
    """This is a base class that defines the method that must be implemented to keep state"""

    def __init__(self, max_month):
        self.max_month = max_month

    def save_consent(self, consent: Consent):
        """
        Will save a consent.

        :param consent: A given consent. A consent is always allow.
        """
        raise NotImplementedError("Must be implemented!")

    def get_consent(self, id: str) -> Consent:
        """
        Will retrive a given consent.

        :param id: The identification for a consent.
        :return: A given consent.
        """
        raise NotImplementedError("Must be implemented!")

    def remove_consent(self, id: str):
        """
        Removes a consent from the database.

        :param id: A consent id.
        """
        raise NotImplementedError("Must be implemented!")

    def size(self):
        """
        :return: The number of entries in the database
        """
        raise NotImplementedError("Must be implemented!")

class DictConsentDB(ConsentDB):
    def __init__(self, max_month):
        super(DictConsentDB, self).__init__(max_month)
        self.consent_db = {}

    def save_consent(self, consent: Consent):
        """
        Will save a consent.

        :param consent: A given consent. A consent is always allow.
        """
        self.consent_db[consent.id] = consent

    def get_consent(self, id: str) -> Consent:
        """
        Will retrive a given consent.

        :param id: The identification for a consent.
        :return: A given consent.
        """
        if id not in self.consent_db:
            return None
        consent = self.consent_db[id]
        if consent.has_expired(self.max_month):
            self.remove_consent(id)
            return None
        return self.consent_db[id]

    def remove_consent(self, id: str):
        """
        Removes a consent from the database.

        :param id: The identification for a consent.
        """
        del self.consent_db[id]

    def size(self):
        """
        :return: The number of entries in the database
        """
        return len(self.consent_db)

class SQLite3ConsentDB(ConsentDB):
    CONSENT_TABLE_NAME = 'consent'

    def __init__(self, max_month, consent_db_path=None):
        super(SQLite3ConsentDB, self).__init__(max_month)
        self.consent_db = dataset.connect('sqlite:///:memory:')
        if consent_db_path:
            self.consent_db = dataset.connect('sqlite:///' + consent_db_path)
        self.consent_table = self.consent_db[self.CONSENT_TABLE_NAME]

    def save_consent(self, consent: Consent):
        """
        Will save a consent.

        :param consent: A given consent. A consent is always allow.
        """
        self.consent_table.upsert(consent.to_dict(), ['consent_id'])

    def get_consent(self, id: str) -> Consent:
        """
        Will retrive a given consent.

        :param id: The identification for a consent.
        :return: A given consent.
        """
        result = self.consent_table.find_one(consent_id=id)
        consent = Consent.from_dict(result)
        if consent:
            if consent.has_expired(self.max_month):
                self.remove_consent(id)
                return None
        return consent

    def remove_consent(self, id: str):
        """
        Removes a consent from the database.

        :param id: The identification for a consent.
        """
        self.consent_table.delete(consent_id=id)

    def size(self):
        """
        :return: The number of entries in the database
        """
        return self.consent_table.count()
