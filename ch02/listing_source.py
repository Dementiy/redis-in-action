import time
import json
import redis

import utils


def check_token(conn, token):
    # Fetch and return the given user, if available
    return conn.hget('login:', token)


def update_token(conn, token, user, item=None):
    timestamp = time.time()
    # Keep a mapping from the token to the logged-in user
    conn.hset('login:', token, user)
    # Record when the token was last seen
    conn.zadd('recent:', token, timestamp)
    if item:
        # Record that the user viewed the item
        conn.zadd('viewed:' + token, item, timestamp)
        # Remove old items, keeping the most recent 25
        conn.zremrangebyrank('viewed:' + token, 0, -26)
        conn.zincrby('viewed:', item, -1)


def clean_sessions(conn, limit, quit):
    while not quit.is_set():
        # Find out how many tokens are known
        size = conn.zcard('recent:')
        # We're still under our limit; sleep and try again
        if size <= limit:
            time.sleep(1)
            continue
        # Fetch the token IDs that should be removed
        end_index = min(size-limit, 100)
        tokens = conn.zrange('recent:', 0, end_index-1)
        # Prepare the key names for the tokens to delete
        session_keys = ['viewed:' + token.decode() for token in tokens]
        # Remove the oldest tokens
        conn.delete(*session_keys)
        conn.hdel('login:', *tokens)
        conn.zrem('recent:', *tokens)


def add_to_cart(conn, session, item, count):
    if count <= 0:
        # Remove the item from the cart
        conn.hdel('cart:' + session, item)
    else:
        # Add the item to the cart
        conn.hset('cart:' + session, item, count)


def clean_full_sessions(conn, limit, quit):
    while not quit.is_set():
        size = conn.zcard('recent:')
        if size <= limit:
            time.sleep(1)
            continue
        end_index = min(size - limit, 100)
        sessions = conn.zrange('recent:', 0, end_index-1)
        session_keys = []
        for sess in sessions:
            session_keys.append('viewed:' + sess.decode())
            # The required added line to delete the
            # shopping cart for old sessions
            session_keys.append('cart:' + sess.decode())
        conn.delete(*session_keys)
        conn.hdel('login:', *sessions)
        conn.zrem('recent:', *sessions)


def cache_request(conn, request, callback):
    # If we can't cache the request, immediately call the callback
    if not can_cache(conn, request):
        return callback(request)

    # Convert the request into a simple string key for later lookups
    page_key = 'cache:' + utils.hash_request(request)
    # Fetch the cached content if we can, and it's available
    content = conn.get(page_key)
    if content:
        return content.decode()
    else:
        # Generate the content if we can't cache the page, or
        # if it wasn't cached
        content = callback(request)
        # Cache the newly generated content if we can cache it
        conn.setex(page_key, content, 300)
        return content


def schedule_row_cache(conn, row_id, delay):
    # Set the delay for the item first
    conn.zadd('delay:', row_id, delay)
    # Schedule the item to be cached now
    conn.zadd('schedule:', row_id, time.time())


def cache_rows(conn, quit):
    while not quit.is_set():
        # Find the next row that should be cached (if any), including
        # the timestamp, as a list of tuples with zero or one items
        next = conn.zrange('schedule:', 0, 0, withscores=True)
        now = time.time()
        if not next or next[0][1] > now:
            # No rows can be cached now, so wait 50ms and try again
            time.sleep(0.05)
            continue
        row_id = next[0][0].decode()
        # Get the delay before the next schedule
        delay = conn.zscore('delay:', row_id)
        if delay <= 0:
            # The item shouldn't be cached anymore; remove it from the cache
            conn.zrem('delay:', row_id)
            conn.zrem('schedule:', row_id)
            conn.delete('inv:' + row_id)
            continue
        # Get the database row
        row = utils.Inventory.get(row_id)
        # Update the schedule and set the cache value
        conn.zadd('schedule:', row_id, now + delay)
        conn.set('inv:' + row_id, json.dumps(row.to_dict()))


def rescale_viewed(conn, quit):
    while not quit:
        # Remove any item not in the top 20000 viewed items
        conn.zremrangebyrank('viewed:', 20000, -1)
        # Rescale all counts to be 1/2 of what they were before
        conn.zinterstore('viewed:', {'viewed:': 0.5})
        # Do it again in 5 minutes
        time.sleep(300)


def can_cache(conn, request):
    # Get the item ID for the page, if any
    item_id = utils.extract_item_id(request)
    # Check whether the page can be statically cached, and
    # whether this is an item page
    if not item_id or utils.is_dynamic(request):
        return False
    # Get the rank of the item
    rank = conn.zrank('viewed:', item_id)
    # Return whether the item has a high enough view count to be cached
    return rank is not None and rank < 10000

