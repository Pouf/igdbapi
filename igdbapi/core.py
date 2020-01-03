#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import json
import sys
from collections import namedtuple
from enum import Enum
from argparse import Namespace

import requests

from . import errors
from .decorators import Singleton


V3_ENDPOINT = "https://api-v3.igdb.com/"


@Singleton
class APIClient(object):

    def __init__(self, api_key=None):
        self._api_key = api_key
        self._command = None
        self._data = None
        self._headers = {'Accept': 'application/json; charset=UTF-8',
                         'user-key': self._api_key}
        if api_key is None:
            raise ValueError('You must set an API key.')

    def call(self, command, data):
        self._command = command
        base_url = str(self)
        if data:
            self._data = '; '.join(data) + ';'
        else:
            self._data = ''

        response = requests.post(base_url,
                                 data=self._data,
                                 headers=self._headers,
                                 allow_redirects=False)
        errors.check(response)
        return APIResponse(response.text)

    @property
    def command(self):
        return self._command

    @property
    def data(self):
        return self._data

    @property
    def api_key(self):
        return self._api_key

    @property
    def headers(self):
        return self._headers

    def __str__(self):
        v3_endpoint = V3_ENDPOINT
        return '{v3_endpoint}{self._command}'.format(**locals())


class APIResponse(object):

    def __init__(self, response):
        # Parse JSON into an object with attributes corresponding to dict keys.
        self._response = response

    def as_single_result(self):
        json_response = self.json_response()
        if type(json_response) == list:
            if not json_response:
                return None
            elif len(json_response) == 1:
                return json_response[0]
            else:
                nb_results = len(json_response)
                raise errors.APIError('Expected single result, found {nb_results}'.format(**locals()))
        return json_response

    def as_collection(self):
        return self.json_response()

    @staticmethod
    def _json_object_hook(d):
        return Namespace(**d)

    def json2obj(self, data):
        return json.loads(data, object_hook=self._json_object_hook)

    def json_response(self):
        return self.json2obj(self._response)

    @property
    def response(self):
        return self._response


class APIObject(object):
    """A base class for all rich Igdb objects.
    
    :param object: [description]
    :type object: [type]
    :raises ValueError: [description]
    :return: [description]
    :rtype: [type]
    """
    
    def __init__(self):
        self._command = None
        self._id = None

    @property
    def id(self):
        return self._id

    @property
    def command(self):
        return self._command

    def __repr__(self):
        clsname = self.__class__.__name__
        try:
            name = _shims.sanitize_for_console(self._name)
            return '<{clsname} "{name}" ({self._id})>'.format(**locals())
        except AttributeError:
            return '<{clsname} ({self._id})>'.format(**locals())

    def __eq__(self, other):
        """
        :type other: APIObject
        """
        # Use a "hash" of each object to prevent cases where derivative classes sharing the
        # same ID, like a user and an app, would cause a match if compared using ".id".
        return hash(self) == hash(other)

    def __ne__(self, other):
        """
        :type other: APIObject
        """
        return not self == other

    def __hash__(self):
        return hash(self.id)

    def find(self, entity=None, fields='*', exclude='', search='', entity_id=None, name='', slug='', filters='', limit=0, sort='', one=False):
        if entity is None:
            raise ValueError('Plase specify entity ("game", "platform", etc)')
        self._command = entity + '/'

        if type(fields) is list:
            fields = ','.join(map(str, fields))

        data = [
            'fields {fields}'.format(**locals())
        ]

        if exclude:
            data.append('exclude {exclude}'.format(**locals()))
        if search:
            data.append('search "{search}"'.format(**locals()))
        if entity_id is not None:
             data.append('where id = {entity_id}'.format(**locals()))
        if name:
             data.append('where name = "{name}"'.format(**locals()))
        if slug:
             data.append('where slug = "{slug}"'.format(**locals()))
        if filters:
            data.append(filters)
        if limit:
            if limit > 500:
                print('Limit ({limit}) set to maximum allowed (500).'.format(**locals()))
                limit = 500
            data.append('limit {limit}'.format(**locals()))
        if sort:
            data.append('sort {sort}'.format(**locals()))

        query = APIClient().call(command=self._command, data=data)

        if one:
            return query.as_single_result()
        else:
            return query.as_collection()
    
    def find_one(self, **kwargs):
        return self.find(**kwargs, one=True)

    def meta(self):
        command = self._command + '/meta'
        return APIClient().call(command=command, data={}).as_collection()


class _shims:
    """
    A collection of functions used at junction points where a Python 3.x solution potentially degrades functionality
    or performance on Python 2.x.
    """

    class Python2:
        @staticmethod
        def sanitize_for_console(string):
            """
            Sanitize a string for console presentation. On Python 2, it decodes Unicode string back to ASCII, dropping
            non-ASCII characters.
            """
            return string.encode(errors="ignore")

    class Python3:
        @staticmethod
        def sanitize_for_console(string):
            """
            Sanitize a string for console presentation. Does nothing on Python 3.
            """
            return string

    if sys.version_info.major >= 3:
        sanitize_for_console = Python3.sanitize_for_console
    else:
        sanitize_for_console = Python2.sanitize_for_console

    sanitize_for_console = staticmethod(sanitize_for_console)


class ESRB(Enum):
    """
    1	RP
    2	EC
    3	E
    4	E10+
    5	T
    6	M
    7	AO
    """
    RP = 1
    EC = 2
    E = 3
    E10plus = 4
    T = 5
    M = 6
    AO = 7

    def __str__(self):
        return self.value
