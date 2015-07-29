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

    :param canonical_ids: Map with old token and new token
    :type result: dict
    :param multicast_id: Unique ID (number) identifying the multicast message.
    :type multicast_id: int
    :param success: Map registration_id with message_id successfully sent.
    :type success: dict
    :param failure: Map registration_id with error message.
    :type failure: dict
    :param unregistered: List with registration_ids not registered.
    :type unregistered: list
    :param unavailables: List with registration_ids to re-send.
    :type unavailables: list
    :param backoff: Estimated time to wait before retry.
    :type backoff: int
    :param message: Related message.
    :type message: :class:`~simplegcm.gcm.Message`
    :param raw_result: JSON returned by GCM server.
    :type raw_result: dict

    """
    def __init__(self, canonical_ids=None, multicast_id=None,
                 success=None, failure=None, unregistered=None,
                 unavailables=None, backoff=None, message=None,
                 raw_result=None):
        self.canonical_ids = canonical_ids
        self.multicast_id = multicast_id
        self.success = success
        self.failure = failure
        self.unregistered = unregistered
        self.unavailables = unavailables
        self.message = message
        self.backoff = backoff
        self._raw_result = raw_result

    def get_retry_message(self):
        """Return a new Message.

        :return: A new message to retry or None.
        :rtype: :class:`~simplegcm.gcm.Message` or None
        """
        if self.unavailables:
            klass = self.message.__class__
            return klass.build_retry_message(message, self.unavailables)
        return None


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
    notification_class = Notification
    options_class = Options
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
            self._notif = self.notification_class(**notification)

        if options is not None:
            self._opt = self.options_class(**options)

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

    @classmethod
    def build_retry_message(cls, message, registration_ids):
        """Return a new Message using the given message as base.

        :return: A new message.
        :rtype: :class:`~simplegcm.gcm.Message`

        """
        data = {
            'registration_ids': registration_ids,
            'data': message._data,
            'notification': message._notif.data if message._notif else None,
            'options': message._opt.data if message._opt else None
        }
        retry_msg = cls(**data)
        return retry_msg


class Sender(object):
    """GCM Sender.

    Example:

    >>> import simplegcm
    >>> sender = simplegcm.Sender(api_key='your_api_key')
    >>> r_ids = ['ABC', 'HJK']
    >>> data = {'score': 5.1}
    >>> opt = {'dry_run': True}
    >>> message = simplegcm.Message(registration_ids=r_ids,
                                    data=data, options=opt)
    >>> ret = sender.send(message)
    >>> retry_msg = ret.get_retry_message()
    >>> if retry_msg:
    >>>     print('Retry')
    >>>     ret = g.send(retry_msg)
    >>> else:
    >>>     print('All sent!')

    :param api_key: Service's API key
    :type api_key: str
    :param url: Service's URL
    :type url: str

    """

    GCM_URL = 'https://gcm-http.googleapis.com/gcm/send'
    result_class = Result
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

    def _parse_response(self, message, response):
        r_status = response.status_code
        if r_status == requests.codes.BAD:
            # bad request more info in content
            raise GCMException(response.content)

        if r_status == requests.codes.UNAUTHORIZED:
            # Invalid API key
            raise GCMException('Unauthorized API_KEY')

        retry_after = response.headers.get('Retry-After')
        # 5xx family!
        if (r_status >= 500 and r_status <= 599):
            # this dict will force a retry
            # set all the registration_ids as 'UNAVAILABLES'
            data = {
                'raw_result': None,
                'message': message,
                'canonical_ids': None,
                'multicast_id': None,
                'success': {},
                'failure': {},
                'unregistered': [],
                'unavailables': message._registration_ids,
                'backoff': retry_after
            }
        elif r_status == requests.codes.OK:
            r_ids = message._registration_ids
            resp_data = response.json()

            success = {}
            failure = {}
            canonical_ids = {}
            unregistered = []
            unavailables = []

            for reg_id, resp in zip(r_ids, resp_data['results']):
                if 'message_id' in resp:
                    success[reg_id] = resp['message_id']
                    if 'registration_id' in resp:
                        # new token for reg_id
                        canonical_ids[reg_id] = resp['registration_id']
                else:
                    error = resp['error']
                    if error in ('Unavailable', 'InternalServerError'):
                        unavailables.append(reg_id)
                    elif error == 'NotRegistered':
                        unregistered.append(reg_id)
                    else:
                        failure[reg_id] = error

            data = {
                # HTTP response
                'raw_result': resp_data,
                'message': message,
                # GCM fields
                'canonical_ids': resp_data['canonical_ids'],
                'multicast_id': resp_data['multicast_id'],
                'success': success,
                'failure': failure,
                'unregistered': unregistered,
                'unavailables': unavailables,
                'backoff': retry_after
            }
        return data

    def _make_request(self, message):
        payload = self._build_payload(message)
        headers = self._build_headers()
        data = json.dumps(payload)
        try:
            response = requests.post(self.url, data, headers=headers)
        except Exception as e:
            logger.error(e)
            raise
        else:
            result_data = self._parse_response(message, response)
            gcm_result = self.result_class(**result_data)
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

        return self._make_request(message)
