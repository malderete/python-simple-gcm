import unittest

from simplegcm import Sender, Message, GCMException


class MainTestCase(unittest.TestCase):
    def test_invalid_api_key(self):
        s = Sender(api_key='<Your_API_KEY>')
        ids = ['ABC123', 'DEF456']
        data = {'score': 5.0}
        m = Message(registration_ids=ids, data=data)
        send = lambda : s.send(m)
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
        self.assertEquals(m.body, expected)


if __name__ == '__main__':
    unittest.main()
