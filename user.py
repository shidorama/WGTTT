import uuid
from random import randint

import os

import settings
from pickle import dump, load

class User(object):
    def __init__(self, user_id):
        self.__connection = None
        self.__wins = 0
        self.__loses = 0
        self.__ties = 0
        self.__id = user_id
        self.__name = 'User-%s' % randint(1,100000) # we can have same names, but I'm not particularly concerned right now

    @property
    def stats(self):
        win_ratio = 0
        lose_ratio = 0
        tie_ratio = 0
        total = self.__wins + self.__loses + self.__ties
        if self.__wins != 0:
            win_ratio = self.__wins / total
        if self.__loses != 0:
            lose_ratio = self.__loses / total
        if self.__ties != 0:
            tie_ratio = self.__ties / total
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
        self.__users = {}
        self.load_users()

    def load_users(self):
        if os.path.exists(settings.DB_FILE):
            if os.path.getsize(settings.DB_FILE) > 0:
                with open(settings.DB_FILE, 'rb') as fp:
                    try:
                        self.__users.update(**load(fp))
                    except ValueError:
                        pass
                    except IOError as e:
                        raise

    def save_users(self):
        """As we're using pickle instead of full-fledged DB - this mean to dump users on disk after each modification
        """
        with open(settings.DB_FILE, 'wb') as fp:
            try:
                dump(self.__users, fp)
            except IOError as e:
                raise

    def register_new_user(self):
        user_id = uuid.uuid1().hex
        user = User(user_id)
        self.__users[user_id] = user
        self.save_users()
        self.auth_user(user_id)
        return user

    def auth_user(self, user_id):
        if user_id not in self.__users:
            return False
        if user_id in self.__lobby:
            self.__users[user_id].exit()
            self.__lobby.remove(user_id)
        self.__lobby.add(user_id)
        return True

    def expunge_user(self, user_id):
        if user_id in self.__lobby:
            self.__lobby.remove(user_id)
            self.__users[user_id].exit()
            return True
        return False

    def remove_user(self, user_id):
        if user_id in self.__lobby:
            self.__lobby.remove(user_id)
            return True
        return False

user_mananger = UserManager()