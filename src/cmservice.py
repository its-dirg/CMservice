from enum import Enum
from calendar import monthrange
from datetime import datetime, timedelta
from jwkest import jws
from jwkest.jwt import JWT

__author__ = 'haho0032'


class ConectPolicy(Enum):
    year = 0
    month = 1
    never = 2


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
        self.timestamp = timestamp


class ConsentDb(object):
    """This is a base class that defines the method that must be implemented to keep state"""

    def save_consent(self, consent):
        """
        Will save a consent.

        :type consent: Consent

        :param consent: A given consent. A consent is always allow.
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


class DictConsentDb(ConsentDb):

    def __init__(self):
        self.db = {}

    def save_consent(self, consent):
        """
        Will save a consent.

        :type consent: Consent

        :param consent: A given consent. A consent is always allow.
        """
        self.db[consent.id] = consent

    def get_consent(self, id):
        """
        Will retrive a given consent.
        :type id: str
        :rtype: Consent

        :param id: The identification for a consent.
        :return: A given consent.
        """
        if id not in self.db:
            return None
        return self.db[id]


class ConsentManager(object):

    def __init__(self, db, policy, keys):
        """

        :type db: ConsentDb
        :type policy: ConectPolicy

        :param db:
        :param policy:
        :return:
        """
        self.db = db
        self.policy = policy
        self.keys = keys

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

    def get_attributes(self, jwt):
        try:
            _jw = jws.factory(jwt)
            _jw.verify_compact(jwt, self.keys)
            _jwt = JWT().unpack(jwt)
            jso = _jwt.payload()
            if "id" not in jso or "attr" not in jso or "redirect_endpoint" not in jso:
                return None
            return jso
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
