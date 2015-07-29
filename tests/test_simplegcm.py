# Python 2 and 3 workarounds
import sys
if sys.version_info < (3,):
    import BaseHTTPServer
    b = lambda x: x
else:
    import codecs
    from http import server as BaseHTTPServer
    b = lambda x: codecs.latin_1_encode(x)[0]

# Regular imports
import json
import threading
import unittest

from simplegcm import Sender, Message, GCMException


class MockGCMHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """Mock HTTP handler for testing."""

    TEST_CASES_DATA = {
        '/200/': {
            'status': 200,
            'headers': {'Content-Type': 'application/json'},
            'response': {
                'multicast_id': 1,
                'canonical_ids': 0,
                'success': 1,
                'failure': 0,
                'results': [
                    {
                        'message_id': 10,
                    }
                ]
            }
        },
        '/200_2/': {
            'status': 200,
            'headers': {'Content-Type': 'application/json'},
            'response': {
                'multicast_id': 1,
                'canonical_ids': 1,
                'success': 1,
                'failure': 3,
                'results': [
                    {
                        'message_id': 100,
                        'registration_id': 'newToken123'
                    },
                    {
                        'error': 'Unavailable',
                    },
                    {
                        'error': 'NotRegistered'
                    },
                    {
                        'error': 'InvalidRegistration'
                    }
                ],
            }
        },
        '/400/': {
            'status': 400,
            'headers': {'Content-Type': 'application/json'},
            'response': 'Something was wrong!'
        },
        '/401/': {
            'status': 401,
            'headers': {'Content-Type': 'application/json'},
            'response': {}
        },
        '/501/': {
            'status': 501,
            'headers': {'Content-Type': 'application/json'},
            'headers': {'Retry-After': 5},
            'response': {}
        }
    }

    def _dispatch(self):
        key = self.path
        test_data = self.TEST_CASES_DATA[key]

        self.send_response(test_data['status'])
        for k, v in test_data.get('headers', {}).items():
            self.send_header(k, v)
        self.end_headers()
        data = json.dumps(test_data['response'])
        self.wfile.write(b(data))

    def do_POST(self):
        self._dispatch()


class MockGCMServer(threading.Thread):
    """Mock server which run in a separated thread."""

    def shutdown(self):
        self.httpd.shutdown()

    def run(self):
        hand = MockGCMHandler
        add = ('', 9000)
        self.httpd = BaseHTTPServer.HTTPServer(add, hand)
        self.httpd.serve_forever()


class MainTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = MockGCMServer()
        cls.httpd.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def test_build_bad_messages(self):
        d = {'score': 5.0}
        ids = ['ABC123']
        t = '/topic/fake'
        build_msg1 = lambda: Message(registration_ids=ids, to=t, data=d)
        build_msg2 = lambda: Message(data=d)
        self.assertRaises(ValueError, build_msg1)
        self.assertRaises(ValueError, build_msg2)

    def test_invalid_api_key(self):
        s = Sender(api_key='fake', url='http://localhost:9000/401/')
        ids = ['ABC123', 'DEF456']
        data = {'score': 5.0}
        m = Message(registration_ids=ids, data=data)
        send = lambda: s.send(m)
        self.assertRaises(GCMException, send)

    def test_message_payload(self):
        expected = {
                'registration_ids': ['ABC', 'DEF'],
                'dry_run': True,
                'data': {
                    'score': 5.0
                },
                'notification': {
                    'title': 'Title',
                    'body': 'Body',
                    'icon': 'icon.png'
                }
        }
        ids = ['ABC', 'DEF']
        d = {'score': 5.0}
        o = {'dry_run': True}
        n = {'title': 'Title', 'body': 'Body', 'icon': 'icon.png'}
        m = Message(registration_ids=ids, data=d,
                    notification=n, options=o)
        self.assertEqual(m.body, expected)
        m = Message(to='/topic/fake', data=d,
                    notification=n, options=o)
        expected['to'] = '/topic/fake'
        del expected['registration_ids']
        self.assertEqual(m.body, expected)

    def test_200(self):
        g = Sender(api_key='fake', url='http://localhost:9000/200/')
        ids = ['ABC123']
        d = {'score': 5.0}
        m = Message(registration_ids=ids, data=d)
        r = g.send(m)
        self.assertEqual(r.get_retry_message(), None)
        self.assertEqual(len(r.success), 1)

    def test_200_2(self):
        g = Sender(api_key='fake', url='http://localhost:9000/200_2/')
        ids = ['oldToken123', 'ABC123', 'CBA123', '123ABC']
        d = {'score': 5.0}
        m = Message(registration_ids=ids, data=d)
        r = g.send(m)
        self.assertNotEqual(r.get_retry_message(), None)
        self.assertEqual(len(r.success), 1)
        self.assertEqual(r.canonicals['oldToken123'], 'newToken123')
        self.assertEqual(len(r.unavailables), 1)
        self.assertEqual(len(r.unregistered), 1)
        self.assertEqual(len(r.failure), 1)
        # test network issues
        g.url = 'http://localhost:1111'  # invalid
        send = lambda: g.send(m)
        self.assertRaises(Exception, send)
        g.api_key = None
        self.assertRaises(ValueError, send)

    def test_400(self):
        g = Sender(api_key='fake', url='http://localhost:9000/400/')
        ids = ['ABC123']
        n = {'icon': 1}  # bad payload!
        m = Message(registration_ids=ids, notification=n)
        send = lambda: g.send(m)
        self.assertRaises(GCMException, send)

    def test_501(self):
        g = Sender(api_key='fake', url='http://localhost:9000/501/')
        ids = ['ABC123']
        d = {'score': 5.0}
        m = Message(registration_ids=ids, data=d)
        r = g.send(m)
        self.assertEqual(int(r.backoff), 5)
        retry_msg = r.get_retry_message()
        self.assertNotEqual(retry_msg, None)
        self.assertEqual(m.body, retry_msg.body)
        self.assertNotEqual(id(m), id(retry_msg))


if __name__ == '__main__':
    unittest.main()
