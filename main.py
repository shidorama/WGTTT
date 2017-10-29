import uuid

import settings
from twisted.internet import reactor, task
from twisted.protocols.basic import LineReceiver
from twisted.internet.protocol import ServerFactory
from base64 import b64decode, b64encode
from json import dumps, loads
from collections import deque
from time import time

from user import user_mananger, User
from game import Game

users = {}


class CQueue(deque):
    def push(self, value):
        self.appendleft(value)

    def isEmpty(self):
        return len(self) > 0

class TTTServer(LineReceiver):
    GAME_STATE_IDLE = 0
    GAME_STATE_QUEUE = 1
    GAME_STATE_PLAYING = 2

    def __init__(self):
        # super(TTTServer, self).__init__()
        # self.__manager = gm
        self.__kill_flag = False
        self.authorized = False
        self.__updated = time()
        self.__game_state = None
        self.user = None

    def connectionMade(self):
        pass

    @staticmethod
    def packet_prepare(raw_data):
        try:
            # data = b64decode(raw_data)
            data = raw_data
            data_object = loads(data)
        except Exception as e:
            return False
        return data_object

    def send_error(self, kill=False):
        self.__kill_flag = kill
        self.responder({"state": "error"})

    def lineReceived(self, line):
        data = self.packet_prepare(line)
        if data is False or not isinstance(data, dict):
            self.send_error(True)
        self.proto_reactor(data)

    def proto_reactor(self, packet):
        command = packet.get('cmd', None)
        if self.authorized:
            self.game_reactor(command, packet)
        else:
            self.auth_reactor(command, packet)

    def start_game(self, state):
        if self.__game_state == self.GAME_STATE_QUEUE and self.authorized:
            self.__game_state = self.GAME_STATE_PLAYING
            self.responder(state)



    def game_reactor(self, command, packet):
        if self.__game_state == self.GAME_STATE_IDLE:
            if command == 'state':
                pass
            elif command == 'queue':
                self.__game_state = self.GAME_STATE_QUEUE
                pass
        elif self.__game_state == self.GAME_STATE_QUEUE:
            if command == 'state':
                pass
        elif self.__game_state == self.GAME_STATE_PLAYING:
            if command == 'move':
                pass
            elif command == 'game':
                pass
            pass
        else:
            self.send_error()

    def auth_reactor(self, command, packet):
        if command == 'auth':
            user_id = packet.get('user_id')
            result = user_mananger.auth_user(user_id)
            answer = {'cmd': command, 'success': result, "stats": user_mananger.get_user_stats(user_id)}
            if result:
                self.authorized = True
                self.__game_state = self.GAME_STATE_IDLE
                self.user = result
            self.responder(answer)
        elif command == 'reg':
            user = user_mananger.register_new_user()
            result = {'cmd': 'reg', 'success': True, 'user_id': user.user_id}
            self.authorized = True
            self.__game_state = self.GAME_STATE_IDLE
            self.user = result
            self.responder(result)
        else:
            self.send_error(True)

    def responder(self, data):
        packet = dumps(data).encode()
        self.transport.write(packet)
        self.transport.write('\r\n')
        if self.__kill_flag:
            self.transport.loseConnection()



class GameManager():
    def __init__(self):
        self.queue = CQueue()
        self.command_queue = CQueue()
        self.__game = None
        self.__players = {}

    def queue_user(self, user):
        # Check if there are more users and if they're not playing to start immediately
        self.queue.push(user)
        self.start_game()

    def start_game(self):
        # try to start game with human
        if self.__game:
            return False
        if len(self.queue) > 1:
            self.__players = {settings.CROSS: self.queue.pop(), settings.CIRCLE: self.queue.pop()}
            self.__game = Game()
            game_state = self.game_state
            for player_sign in self.__players:
                game_state['your_type'] = player_sign
                self.__players[player_sign].protocol.start_game(game_state)

    def make_move(self, user_id, x, y):
        for sign, player_id in self.__players.iteritems():
            if user_id == player_id:
                if self.__game.make_move(sign, x, y):
                    new_state = self.game_state
                    new_state['your_type'] = sign
                    self.broadcast_update(new_state)
        return False

    def broadcast_update(self, state):
        pass

    def check_endgame(self):
        if self.__game.state != Game.GAME:
            return True

    def start_ai_timer(self):
        pass



    @property
    def game_state(self):
        if not self.__game:
            return False
        game_ended = not (self.__game.state == Game.GAME)
        return_schema = {
            "field": self.__game.board,
            "player_x": self.__players[0],
            "player_y": self.__players[1],
            "your_type": None,
            "last_turn": self.__game.last_move,
            "ended": game_ended,
            "winner": self.__game.winner
        }
        return return_schema





class VirtualPlayer():
    pass

if __name__ == '__main__':
    game_manager = GameManager()

    factory = ServerFactory()
    factory.protocol = TTTServer

    reactor.listenTCP(8899, factory)
    reactor.run()