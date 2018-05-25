import json
import re
import os
import time

import aiohttp
import aioredis


def condense(string):
    return (re.sub(r'[^A-Za-z0-9]', '', string)).lower()


async def login(username, password, challstr):
    url = 'https://play.pokemonshowdown.com/action.php'
    values = {'act': 'login',
              'name': username,
              'pass': password,
              'challstr': challstr
              }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=values) as r:
            resp = await r.text()
            resp = json.loads(resp[1:])
            return resp['assertion']


async def unreg_login(username, challstr):
    url = 'https://play.pokemonshowdown.com/action.php'
    values = {'act': 'getassertion',
              'userid': condense(username),
              'challstr': challstr
              }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=values) as r:
            resp = await r.text()
            return resp


async def make_msg_info(msg, room, ws, id, config):
    info = {'where': msg[0],
            'ws': ws,
            'all': msg,
            'me': config[id]['username']
            }

    info['where'] = info['where'].lower()

    if info['where'] == 'c:':
        info.update({'where': 'c',
                     'room': room,
                     'who': msg[2][1:],
                     'allwho': msg[2],
                     'when': int(msg[1]),
                     'what': '|'.join(msg[3:])})

    elif info['where'] == 'c':
        info.update({'room': room,
                     'who': msg[1][1:],
                     'allwho': msg[1],
                     'when': int(time.time()),
                     'what': '|'.join(msg[2:])})

    elif info['where'] == 'j' or info['where'] == 'l':
        info.update({'room': room,
                     'who': msg[1][1:],
                     'allwho': msg[1],
                     'when': int(time.time()),
                     'what': ''})

    elif info['where'] == 'n':
        info.update({'room': room,
                     'who': msg[1][1:],
                     'allwho': msg[1],
                     'oldname': msg[2],
                     'when': int(time.time()),
                     'what': ''})

    elif info['where'] == 'users':
        info.update({'room': room,
                     'who': '',
                     'what': msg[1]})

    elif info['where'] == 'pm':
        info.update({'who': msg[1][1:],
                     'allwho': msg[1],
                     'target': msg[2][1:],
                     'when': int(time.time()),
                     'what': msg[3]})

    elif info['where'] == 'html':
        info.update({'who': '',
                     'when': int(time.time()),
                     'what': msg[1]})

    return info


async def haste(message):
    async with aiohttp.ClientSession() as session:
        async with session.post('https://hastebin.com/documents',
                                data=message) as r:
            resp = await r.text()
            j = json.loads(resp)
    if 'key' in j:
        result = f"https://hastebin.com/{j['key']}"
    else:
        result = "Didn't work"
    return result


# Holds the loaded databases (so we don't create another
# instance of the same database).
_databases = {}


def _read_tables(filename='data/tables.txt'):
    """Reads the list of databases from the given database file,
    defaulting to "data/tables.txt" for the main bot instance."""
    mode = 'r' if os.path.isfile(filename) else 'w'
    with open(filename, mode) as f:
        if mode == 'w':
            f.write('')
        return f.read().splitlines()


_tables = _read_tables()


def _save_tables(filename='data/tables.txt'):
    """Saves the list of databases to the given database file,
    defaulting to "data/tables.txt" for the main bot instance."""
    with open(filename, 'w') as f:
        f.write("\n".join(_tables))


async def getdatabase(db_name, cb):
    """Fetches the `db_name` Redis database. It will be created
    if it hasn't been initialised OR if it doesn't yet exist in
    the bot's tables file (default is data/tables.txt).
    """
    global _databases
    global _tables

    if db_name in _databases:
        return _databases[db_name]

    # The database may exist, but it hasn't been initialised
    # yet.
    # So, we find the index of the database. If the database
    # doesn't exist in _tables, then it's entirely new.
    try:
        _tables.index(db_name)
    except ValueError:
        _tables.append(db_name)
        _save_tables()
    finally:
        db_idx = _tables.index(db_name)

    db = await aioredis.create_redis(cb.redis_url, db=db_idx, loop=cb.loop)
    _databases[db_name] = db
    return db
