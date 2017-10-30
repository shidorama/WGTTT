import uuid
from random import randint

import os

import settings
from pickle import dump, load

class User(object):
    def __init__(self, user_id):
        self.wins = 0
        self.loses = 0
        self.ties = 0
        self.__id = user_id
        self.__name = 'User-%s' % randint(1,100000) # we can have same names, but I'm not particularly concerned right now

    @property
    def protocol(self):
        return user_mananger.protocols.get(self.__id)

    @property
    def stats(self):
        win_ratio = 0
        lose_ratio = 0
        tie_ratio = 0
        total = float(self.wins + self.loses + self.ties)
        if self.wins != 0:
            win_ratio = self.wins / total
        if self.loses != 0:
            lose_ratio = self.loses / total
        if self.ties != 0:
            tie_ratio = self.ties / total
        return win_ratio, lose_ratio, tie_ratio

    @property
    def name(self):
        return self.__name

    @property
    def user_id(self):
        return self.__id

    def exit(self):
        pass


class UserManager(object):
    def __init__(self):
        self.__lobby = set()
        self.users = {}
        self.load_users()
        self.protocols = {}

    def get_user_stats(self, user_id):
        if user_id in self.users:
            return self.users[user_id].stats
        return False

    def load_users(self):
        if os.path.exists(settings.DB_FILE):
            if os.path.getsize(settings.DB_FILE) > 0:
                with open(settings.DB_FILE, 'rb') as fp:
                    try:
                        self.users.update(**load(fp))
                    except ValueError:
                        pass
                    except IOError as e:
                        raise

    def save_users(self):
        """As we're using pickle instead of full-fledged DB - this mean to dump users on disk after each modification
        """
        with open(settings.DB_FILE, 'wb') as fp:
            try:
                dump(self.users, fp)
            except IOError as e:
                raise

    def register_new_user(self, protocol):
        user_id = uuid.uuid1().hex
        user = User(user_id)
        self.users[user_id] = user
        self.save_users()
        self.auth_user(user_id, protocol)
        return user

    def auth_user(self, user_id, protocol):
        if user_id not in self.users:
            return False
        if user_id in self.__lobby:
            self.users[user_id].exit()
            self.__lobby.remove(user_id)
        self.protocols[user_id] = protocol
        self.__lobby.add(user_id)
        return self.users[user_id]

    def expunge_user(self, user_id):
        if user_id in self.__lobby:
            self.__lobby.remove(user_id)
            self.users[user_id].exit()
            return True
        return False

    def remove_user(self, user_id):
        if user_id in self.__lobby:
            self.__lobby.remove(user_id)
            return True
        return False

user_mananger = UserManager()