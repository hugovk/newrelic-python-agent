import logging
import re

from newrelic.packages import requests
from newrelic.core.internal_metrics import internal_metric


_logger = logging.getLogger(__name__)


def valid_length(data):
    b = data.encode('utf-8')
    return len(b) <= 255


VALID_CHARS_RE = re.compile(r'[0-9a-zA-Z_ ./-]')


def valid_chars(data):
    for c in data:
        if not VALID_CHARS_RE.match(c) and ord(c) < 0x80:
            return False
    return True


class CommonUtilization(object):
    METADATA_URL = ''
    EXPECTED_KEYS = []
    VENDOR_NAME = ''
    TIMEOUT = 0.5

    @classmethod
    def record_error(cls, resource, data):
        # As per spec
        internal_metric(
                'Supportability/utilization/%s/error' % cls.VENDOR_NAME, 1)
        _logger.warning('Fetched invalid %r data for "%r": %r',
                cls.VENDOR_NAME, cls.METADATA_URL, data)

    @classmethod
    def fetch(cls):
        # Create own requests session and disable all environment variables,
        # so that we can bypass any proxy set via env var for this request.

        session = requests.Session()
        session.trust_env = False

        try:
            resp = session.get(cls.METADATA_URL, timeout=cls.TIMEOUT)
            resp.raise_for_status()
        except Exception as e:
            resp = None
            _logger.debug('Error fetching %s data from %r: %r',
                    cls.VENDOR_NAME, cls.METADATA_URL, e)

        return resp

    @classmethod
    def get_values(cls, response):
        try:
            j = response.json()
        except ValueError:
            _logger.debug('Fetched invalid %s data from %r: %r',
                    cls.VENDOR_NAME, cls.METADATA_URL, response.text)
            return

        return j

    @staticmethod
    def normalize(key, data):
        try:
            stripped = data.strip()

            if stripped and valid_length(stripped) and valid_chars(stripped):
                return stripped
        except:
            pass

    @classmethod
    def sanitize(cls, values):
        out = {}
        for key in cls.EXPECTED_KEYS:
            metadata = values.get(key, None)
            if not metadata:
                cls.record_error(key, metadata)
                return

            normalized = cls.normalize(key, metadata)
            if not normalized:
                cls.record_error(key, metadata)
                return

            out[key] = normalized

        return out

    @classmethod
    def detect(cls):
        response = cls.fetch()

        if response:
            values = cls.get_values(response)

            d = cls.sanitize(values)
            return d
