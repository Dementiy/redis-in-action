import unittest
import redis
import uuid
import threading

from listing_source import *


class TestFakeWebRetailer(unittest.TestCase):

    def setUp(self):
        self.conn = redis.Redis(db=15)

    def tearDown(self):
        to_del = (
            self.conn.keys('login:*') + self.conn.keys('recent:*') +
            self.conn.keys('viewed:*') + self.conn.keys('cart:*') +
            self.conn.keys('cache:*') + self.conn.keys('delay:*') +
            self.conn.keys('schedule:*') + self.conn.keys('inv:*')
        )
        if to_del:
            self.conn.delete(*to_del)

    def test_login_cookies(self):
        token = str(uuid.uuid4())
        update_token(self.conn, token, 'username', 'IPhoneX')
        login = check_token(self.conn, token)
        self.assertEqual('username', login.decode())

    def test_clean_sessions(self):
        bob = {
            'user': 'bob',
            'token': str(uuid.uuid4())
        }
        alice = {
            'user': 'alice',
            'token': str(uuid.uuid4())
        }

        update_token(self.conn, item='IPhone X', **bob)
        update_token(self.conn, item='MacBook Air', **bob)
        update_token(self.conn, item='MacBook Pro', **bob)

        update_token(self.conn, item='MacBook Pro', **alice)
        update_token(self.conn, item='IPad', **alice)
        update_token(self.conn, item='Samsung Galaxy Tab A', **alice)

        n_users = self.conn.hlen('login:')
        self.assertEqual(n_users, 2)

        quit = threading.Event()
        thread = threading.Thread(
            target=clean_sessions,
            args=(self.conn, 0, quit))
        thread.daemon = True
        thread.start()
        time.sleep(0.5)
        quit.set()

        n_users = self.conn.hlen('login:')
        self.assertEqual(n_users, 0)

    def test_shopping_cart_cookies(self):
        bob = {
            'user': 'bob',
            'token': str(uuid.uuid4())
        }
        update_token(self.conn, item='IPhone X', **bob)
        update_token(self.conn, item='MacBook Air', **bob)
        update_token(self.conn, item='MacBook Pro', **bob)

        add_to_cart(self.conn, bob['token'], 'IPhoneX', 2)
        add_to_cart(self.conn, bob['token'], 'Samsung Galaxy Tab A', 1)
        items = self.conn.hgetall('cart:' + bob['token'])
        self.assertEqual(sum(map(lambda v: int(v), items.values())), 3)

        add_to_cart(self.conn, bob['token'], 'IPhoneX', 0)
        items = self.conn.hgetall('cart:' + bob['token'])
        self.assertEqual(sum(map(lambda v: int(v), items.values())), 1)

        quit = threading.Event()
        thread = threading.Thread(
            target=clean_full_sessions,
            args=(self.conn, 0, quit))
        thread.daemon = True
        thread.start()
        time.sleep(0.5)
        quit.set()
        cart = self.conn.hgetall('cart:' + bob['token'])
        self.assertFalse(cart)

    def test_cache_request(self):
        bob = {
            'user': 'bob',
            'token': str(uuid.uuid4())
        }
        update_token(self.conn, item='IPhone X', **bob)
        update_token(self.conn, item='MacBook Air', **bob)
        update_token(self.conn, item='MacBook Pro', **bob)

        callback = lambda request: "content for " + request
        url = 'http://test.com/?item=MacBook Air'
        content = cache_request(self.conn, url, callback)
        self.assertEqual(
            "content for http://test.com/?item=MacBook Air", content)
        cached_content = cache_request(self.conn, url, None)
        self.assertEqual(content, cached_content)

        self.assertFalse(can_cache(self.conn, 'http://test.com/'))
        self.assertFalse(can_cache(self.conn, 'http://test.com/?item=itemX&_=1234536'))

    def test_cache_rows(self):
        schedule_row_cache(self.conn, 'MacBook Air', 5)
        s = self.conn.zrange('schedule:', 0, -1, withscores=True)

        quit = threading.Event()
        thread = threading.Thread(
            target=cache_rows,
            args=(self.conn, quit))
        thread.daemon = True
        thread.start()
        time.sleep(1)

        record = json.loads(self.conn.get('inv:MacBook Air').decode())
        self.assertEqual(record['id'], 'MacBook Air')
        time.sleep(5)
        record_upd = json.loads(self.conn.get('inv:MacBook Air').decode())
        self.assertEqual(record_upd['id'], 'MacBook Air')
        self.assertTrue(record['cached'] < record_upd['cached'])

        schedule_row_cache(self.conn, 'MacBook Air', -1)
        time.sleep(1)
        record = self.conn.get('inv:MacBook Air')
        self.assertIsNone(record)

        quit.set()


if __name__ == '__main__':
    unittest.main()
