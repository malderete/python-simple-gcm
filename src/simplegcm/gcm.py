# -*- coding: utf-8 -*-

"""
simplegcm.gcm.

This module implements the Google Cloud Service API.

:copyright: (c) 2015 by Martin Alderete.
:license: BSD License, see LICENSE for more details.

"""

import collections
import json
import logging

import requests


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


__all__ = ('GCMException', 'Message', 'Notification',
           'Options', 'Sender')


class GCMException(Exception):
    """Exception related to GCM service."""

    pass


class InnerDictSerializeMixin:
    """Mixin which add the data property."""

    @property
    def data(self):
        """Return the object data.

        :rtype: dict
        """
        d = {k: v for (k, v) in self.__dict__.items() if v}
        return d


class Notification(InnerDictSerializeMixin, object):
    """Notificication.

    :param title: Notification title.
    :type title: str
    :param body: Notification body.
    :type body: str
    :param icon: Notification icon.
    :type icon: str
    :param sound: Sound to be played.
    :type sound: str
    :param badge: Badge to be used.
    :type badge: str
    :param tag: Indicates whether each notification results in a new entry or not.
    :type tag: bool
    :param color: Color of the icon.
    :type color: str
    :param click_action: Action binded to notification click.
    :type click_action: str
    :param body_loc_key: Corresponds to "loc-key" in APNS payload.
    :type body_loc_key: str
    :param body_loc_args: Arguments. Corresponds to "loc-args" in APNS payload.
    :type body_loc_args: list
    :param title_loc_key: Corresponds to "title-loc-key" in APNS payload.
    :type title_loc_key: str
    :param title_loc_args: Arguments. Corresponds to "title-loc-args" in APNS payload.
    :type title_loc_args: list

    .. note:: All of the above parameters are platform dependent.
        See https://developers.google.com/cloud-messaging/server-ref#table1b

    """

    ANDROID = 'android'
    IOS = 'ios'
    _MANDATORY_FIELS_BY_PLATFORM = {
        'android': ('title', 'icon'),
        'ios': ()
    }
    def __init__(self, title=None, body=None, icon=None, sound=None,
                 badge=None, tag=None, color=None, click_action=None,
                 body_loc_key=None, body_loc_args=None,
                 title_loc_key=None, title_loc_args=None):
        self.title = title
        self.body = body
        self.icon = icon
        self.sound = sound
        self.badge = badge
        self.tag = tag
        self.color = color
        self.click_action = click_action
        self.body_loc_key = body_loc_key
        self.body_loc_args = body_loc_args
        self.title_loc_key = title_loc_key
        self.title_loc_args = title_loc_args


class Options(InnerDictSerializeMixin, object):
    """Options.

    :param collapse_key: Identifies a group of messages.
    :type collapse_key: str
    :param priority: Messages priority.
    :type priority: int
    :param content_available: Flag to wakes up an inactivce device (iOS).
    :type content_available: bool
    :param delay_while_idle: Flag to sends when the device becomes available.
    :type delay_while_idle: bool
    :param time_to_live: How long the message should be store in GCM.
    :type time_to_live: int
    :param delivery_receipt_requested: Flag to confirm a delivered message.
    :type delivery_receipt_requested: bool
    :param restricted_package_name: Specifies the package name of the application.
    :type restricted_package_name: str
    :param dry_run: Flag to sets testing mode.
    :type dry_run: bool

    .. note:: All of the above parameters are optionals.
        See https://developers.google.com/cloud-messaging/server-ref#table1

    """

    def __init__(self, collapse_key=None,
                 priority=None, content_available=None,
                 delay_while_idle=None, time_to_live=None,
                 delivery_receipt_requested=None, dry_run=None,
                 restricted_package_name=None):
        self.collapse_key = collapse_key
        self.priority = priority
        self.content_available = content_available
        self.delay_while_idle = delay_while_idle
        self.time_to_live = time_to_live
        self.delivery_receipt_requested = delivery_receipt_requested
        self.dry_run = dry_run
        self.restricted_package_name = restricted_package_name


class Result(object):
    """Response from GCM.

    :param result: Indicate the status
    :type result: bool
    :param success: A registation token or a topic (multicast)
    :type success: str
    :param failure: A registation token or a topic (multicast)
    :type failure: str
    :param raw_results: A registation token or a topic (multicast)
    :type raw_results: str
    :param response: A registation token or a topic (multicast)
    :type response: str

    """
    def __init__(self, result, success, failure,
                 raw_results, response):
        self.result = result
        self.success = success
        self.failure = failure
        self.raw_results = raw_results
        self.response


class Message(object):
    """GCM Message to send.

    :param to: A registation token or a topic (multicast)
    :type to: str
    :param registration_ids: Registration device tokens
    :type registration_ids: list
    :param data: Custom data to send
    :type data: dict
    :param notification: Notification to send
    :type notification: :class:`~simplegcm.gcm.Notification`
    :param options: Options for the message
    :type options: :class:`~simplegcm.gcm.Options`

    .. note:: Messages MUST contain 'to' or 'registration_ids' at least

    """

    def __init__(self, to=None, registration_ids=None,
                 data=None, notification=None, options=None):
        if not any((to, registration_ids)):
            raise ValueError('You must provide "registration_ids" or "to"')

        if all((to, registration_ids)):
            raise ValueError('You must provide "registration_ids" or "to" no both')

        self._to = to
        self._registration_ids = registration_ids
        self._data = None
        self._notif = None
        self._opt = None

        if data is not None:
            self._data = data

        if notification is not None:
            self._notif = Notification(**notification)

        if options is not None:
            self._opt = Options(**options)

    @property
    def body(self):
        """Return the payload which repesents the message.

        :rtype: dict
        """
        payload = {}
        # Set the receptor
        if self._to:
            payload['to'] = self._to

        if self._registration_ids:
            payload['registration_ids'] = self._registration_ids

        # Notification
        if self._notif:
            payload['notification'] = self._notif.data

        # Options
        if self._opt:
            payload.update(self._opt.data)

        # Custom data
        if self._data:
            payload['data'] = self._data

        return payload


class Sender(object):
    """GCM Sender.

    Example:

    >>> import simplegcm
    >>> sender = simplegcm.Sender(api_key='your_api_key')
    >>> r_ids = ['ABC', 'HJK']
    >>> data = {'score': 5.1}
    >>> opt = {'dry_run': True}
    >>> message = simplegcm.Message(registration_ids=r_ids, data=data,
                             options=opt)
    >>> ret = sender.send(message)
    >>> print(ret.result)
    True

    :param api_key: Service's API key
    :type api_key: str
    :param url: Service's URL
    :type url: str

    """

    GCM_URL = 'https://gcm-http.googleapis.com/gcm/send'
    def __init__(self, api_key=None, url=None):
        self.api_key = api_key
        self.url = self.GCM_URL
        if url:
            self.url = url

    def _build_headers(self):
        headers = {
            'Content-type': 'application/json',
            'Authorization': 'key=%s' % self.api_key,
        }
        return headers

    def _parse_response(self, response):
        result = False
        success = 0
        failure = 0

        if response.status_code == requests.codes.OK:
            json_response = response.json()
            result = True
            success = json_response['success']
            failure = json_response['failure']
            raw_results = json_response['results']
            logger.info('Sent {0}, Failure {1}'.format(success, failure))
        elif response.status_code == requests.codes.UNAUTHORIZED:
            # Invalid API key
            raise GCMException('Unauthorized API_KEY')
        else:
            # Error
            logger.error('The response has errors:\n{0}'.format(
                         response.content))
            raise GCMException('Error sending GCM notification')

        gcm_result = Result(result, success, failure, raw_results, response)
        return gcm_result

    def _make_request(self, payload):
        data = json.dumps(payload)
        headers = self._build_headers()
        try:
            ret = requests.post(self.url, data, headers=headers)
        except Exception as e:
            logger.error(e)
            raise
        else:
            gcm_result = self._parse_response(ret)
        return gcm_result

    def _build_payload(self, message):
        payload = message.body
        return payload

    def send(self, message):
        """Send a message.

        :param message: A :class:`~simplegcm.gcm.Message`
        :return: Result object
        :rtype: :class:`~simplegcm.gcm.Result`
        :raises GCMException: If there was an error.
        """
        if self.api_key is None:
            raise ValueError('The API KEY has not been set yet!')

        payload = self._build_payload(message)
        return self._make_request(payload)
