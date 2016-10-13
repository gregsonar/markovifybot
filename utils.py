import logging

import redis


class Logger(object):
    def __init__(self):
        for i in ('requests', 'urllib3', 'tweepy'):
            logging.getLogger(i).setLevel(logging.WARNING)

        format = ('[{filename:>16}:{lineno:<4} {funcName:>16}()] ' +
                  '{asctime}: {message}')
        logging.basicConfig(format=format,
                            style='{',
                            datefmt='%Y-%m-%d %H:%M:%S',
                            level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.info('Logger initialised.')

    def get_logger(self):
        return self.logger

logger = Logger().get_logger()


class DB(object):
    def __init__(self):
        self.server = redis.Redis(socket_connect_timeout=1)
        try:
            self.server.ping()
            logger.warning('Redis initialised.')
            self.server_available = True
        except Exception as e:
            logger.warning('Redis server unavailable: ' + str(e))
            self.server_available = False

db = DB()


class RateLimit(object):
    # allowed: whether the action was accepted
    # left: how many requests are left until next reset
    # reset: how many seconds until the rate limit is reset
    def hit(self, prefix, user, max=50, ttl=60 * 10):
        def r(x, y, z): return {'allowed': x, 'left': y, 'reset': z}
        # if the server is not available, let it through
        if not db.server_available:
            return r(True, 1, 0)

        key = str(prefix) + ':' + str(user)
        value = db.server.get(key)

        if not value:
            # if key does not exist...
            db.server.set(key, 1)
            db.server.expire(key, ttl)
            return r(True, max - 1, ttl)
        else:
            current_ttl = db.server.ttl(key)
            if int(value) >= max:
                return r(False, 0, current_ttl)
            else:
                db.server.incr(key)
                return r(True, max - 1 - int(value), current_ttl)

    # similar to hit(), but read-only
    def is_allowed(self, prefix, user):
        if not db.server_available:
            return True

        key = str(prefix) + ':' + str(user)
        value = db.server.get(key)

        if not value:
            return True
        else:
            if int(value) >= max:
                return False
            else:
                return True

rate_limit = RateLimit()


def timedelta(time):
    elapsed = time

    if not time:
        return 'a moment'
    elif time > 3600:
        elapsed //= 3600
        if elapsed == 1:
            return 'one hour'
        else:
            return str(elapsed) + ' hours'
    elif time > 60:
        elapsed //= 60
        if elapsed == 1:
            return 'one minute'
        else:
            return str(elapsed) + ' minutes'
    else:
        if elapsed == 1:
            return 'one second'
        else:
            return str(elapsed) + ' seconds'


def ellipsis(text, max_length):
    if len(text) > max_length:
        return text[:max_length - 1] + '…'
    else:
        return text
