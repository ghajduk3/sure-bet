import re
import logging
import requests


import simplejson

from abc import ABC, abstractmethod

from bettings.integrations.direct import exceptions as direct_exceptions

logger = logging.getLogger(__name__)
_LOG_PREFIX = "[API-BASE-CLIENT]"


class ApiBaseClient(object):

    OK_RESPONSE_CODES = [200, 201, 202, 203, 204, 205, 206]

    # todo construct headers
    @classmethod
    def _request(cls, method, url, data=None, params=None, headers=None):
        try:
            response = requests.request(
                method=method,
                url=url,
                data=data,
                params=params if params is not None else {},
                headers=headers
            )

            if response.status_code not in cls.OK_RESPONSE_CODES:
                msg = '{} Response code {} is not a valid successful code.'.format(_LOG_PREFIX, response.status_code)
                logger.exception(msg)
                raise direct_exceptions.ClientBadResponseCodeError(msg)

        except requests.exceptions.ConnectTimeout as e:
            msg = '{} Connection timeout. Error: {}'.format(_LOG_PREFIX, str(e))
            logger.exception(msg)
            raise direct_exceptions.ApiClientError(msg)
        except requests.exceptions.RequestException as e:
            msg = '{} Exception occured while requesting. Error: {} '.format(_LOG_PREFIX, str(e))
            logger.exception(msg)
            raise direct_exceptions.ApiClientError(msg)

        return response

    @staticmethod
    def _get_normalized_soccer_team_info(team_name):
        text = re.sub(r"[^a-zA-Z0-9\sčČšŠžŽ]", "", team_name)
        # remove multiple white spaces
        text = re.sub(' +', ' ', text)
        # convert all letters to lower case
        text = text.lower().strip()
        text = sorted(text.split(' '), key=len)
        if len(text) >= 2:
            first, second = text[-2:]
            if len(first) == len(second):
                return first + " " + second
            else:
                return second

        return text[0]



