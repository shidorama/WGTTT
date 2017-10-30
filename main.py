from collections import deque
from json import dumps, loads
from time import time

from twisted.internet import reactor
from twisted.internet.protocol import ServerFactory, connectionDone
from twisted.protocols.basic import LineReceiver
from voluptuous import ExactSequence, Schema, MultipleInvalid

import settings
from game import Game, GameAI
from user import user_mananger

users = {}
user_protocols = {}


class CQueue(deque):
    def push(self, value):
        self.appendleft(value)

    def isEmpty(self):
        return len(self) == 0


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
        self.__game_state_data = None
        self.user = None

    def connectionMade(self):
        pass

    def connectionLost(self, reason=connectionDone):
        if self.__game_state in [self.GAME_STATE_PLAYING, self.GAME_STATE_QUEUE]:
            game_manager.drop_player(self.user.user_id)
        if self.authorized:
            user_mananger.protocols.pop(self.user.user_id)

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
            return self.send_error(True)
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
                self.cmd_state(command, True)
                game_manager.queue_user(self.user)
        elif self.__game_state == self.GAME_STATE_QUEUE:
            if command == 'state':
                pass
        elif self.__game_state == self.GAME_STATE_PLAYING:
            if command == 'move':
                schema = ExactSequence([int, int])
                raw_pos = packet.get('pos')
                position = self.check_data(raw_pos, schema)
                if position is False:
                    return self.responder(self.__game_state_data)
                if not game_manager.make_move(self.user.user_id, *position):
                    return self.responder(self.__game_state_data)
            elif command == 'game':
                pass
            pass
        else:
            self.send_error()

    @staticmethod
    def check_data(data, schema):
        validator = Schema(schema, True)
        try:
            validator(data)
        except MultipleInvalid as e:
            return False
        return data

    def cmd_state(self, cmd, ok=False):
        data = {"cmd": cmd, "success": ok}
        self.responder(data)

    def auth_reactor(self, command, packet):
        if command == 'auth':
            user_id = packet.get('user_id')
            result = user_mananger.auth_user(user_id, self)
            answer = {'cmd': command, 'success': False, "stats": user_mananger.get_user_stats(user_id)}
            if result:
                self.authorized = True
                self.__game_state = self.GAME_STATE_IDLE
                self.user = result
                answer['success'] = True
            self.responder(answer)
        elif command == 'reg':
            user = user_mananger.register_new_user(self)
            result = {'cmd': 'reg', 'success': True, 'user_id': user.user_id}
            self.authorized = True
            self.__game_state = self.GAME_STATE_IDLE
            self.user = user
            self.responder(result)
        else:
            self.send_error(True)

    def responder(self, data):
        packet = dumps(data).encode()
        self.transport.write(packet)
        self.transport.write('\r\n')
        if self.__kill_flag:
            self.transport.loseConnection()

    def send_game_update(self, data):
        self.__game_state_data = data
        self.responder(data)

    def end_game(self):
        self.__game_state = self.GAME_STATE_IDLE


class GameManager():
    def __init__(self):
        self.queue = CQueue()
        self.command_queue = CQueue()
        self.__game = None
        self.__players = {}
        self.__ai_countdown_started = None
        self.__ai_countdown_task = None

    def queue_user(self, user):
        # Check if there are more users and if they're not playing to start immediately
        self.queue.push(user)
        self.start_game()

    def start_game(self):
        # try to start game with human
        if self.__game or self.queue.isEmpty():
            return False
        if len(self.queue) > 1:
            self.reset_ai_timer()
            self.__players = {settings.CROSS: self.queue.pop(), settings.CIRCLE: self.queue.pop()}
            self.__game = Game()
            game_state = self.game_state
            for player_sign in self.__players:
                game_state['your_type'] = player_sign
                self.__players[player_sign].protocol.start_game(game_state)
        elif len(self.queue) and not self.__game:
            self.start_ai_timer()

    def start_ai_timer(self):
        self.__ai_countdown_started = time()
        self.__ai_countdown_task = reactor.callLater(settings.WAIT_TIMEOUT, self.start_ai_game)

    def reset_ai_timer(self):
        if self.__ai_countdown_task:
            self.__ai_countdown_started = None
            self.__ai_countdown_task.cancel()
            self.__ai_countdown_task = None

    def make_move(self, user_id, x, y):
        for sign, player in self.__players.iteritems():
            if user_id == player.user_id:
                if self.__game.make_move(sign, x, y):
                    new_state = self.game_state
                    new_state['your_type'] = sign
                    self.broadcast_update(new_state)
                    return True
        return False

    def broadcast_update(self, state):
        # Check what this update means (i.e. win, lose, tie)
        # If endgame -> drop players, Update stats for player
        # if AI -> defer move call

        if self.__game.last_move == settings.CROSS \
                and isinstance(self.__players[settings.CIRCLE], GameAI) \
                and self.__game.state == Game.GAME:
            reactor.callLater(1, self.__players[settings.CIRCLE].play)
        for sign, player in self.__players.iteritems():
            if not isinstance(player, GameAI):
                state['your_type'] = sign
                player.protocol.send_game_update(state)
        if self.__game.state != Game.GAME:
            self.update_stats(self.__game.winner)
            self.endgame()

        pass

    def update_stats(self, winner):
        if winner is None:
            for player in self.__players.values():
                player.ties += 1
        elif winner == settings.CIRCLE:
            self.__players[settings.CIRCLE].wins += 1
            self.__players[settings.CROSS].loses += 1
        else:
            self.__players[settings.CIRCLE].loses += 1
            self.__players[settings.CROSS].wins += 1
        user_mananger.save_users()

    def endgame(self):
        for player in self.__players.values():
            if not isinstance(player, GameAI):
                player.protocol.end_game()
        self.__players = {}
        self.__game = None
        self.start_game()

    def check_endgame(self):
        if self.__game.state != Game.GAME:
            return True

    def start_ai_game(self):
        if not self.__game and len(self.queue) == 1:
            self.__players = {settings.CROSS: self.queue.pop(), settings.CIRCLE: GameAI(self.make_move)}
            self.__game = Game()
            game_state = self.game_state
            game_state['your_type'] = settings.CROSS
            self.__players[settings.CROSS].protocol.start_game(game_state)

    @property
    def game_state(self):
        if not self.__game:
            return False
        game_ended = not (self.__game.state == Game.GAME)
        return_schema = {
            "cmd": "state",
            "field": self.__game.board,
            "player_x": {"name": self.__players[settings.CROSS].name, "stats": self.__players[settings.CROSS].stats},
            "player_o": {"name": self.__players[settings.CIRCLE].name, "stats": self.__players[settings.CIRCLE].stats},
            "your_type": None,
            "last_turn": self.__game.last_move,
            "ended": game_ended,
            "winner": self.__game.winner
        }
        return return_schema

    def drop_player(self, user_id):
        user = user_mananger.users.get(user_id)
        if not user:
            return False
        if user in self.queue:
            self.queue.remove(user)
        else:
            playing = False
            loses = None
            for sign, player in self.__players.iteritems():
                if user_id == player.user_id:
                    playing = True
                    loses = sign
            if playing:
                winner = settings.CROSS
                if loses == settings.CROSS:
                    winner = settings.CIRCLE
                self.update_stats(winner)
                if not isinstance(self.__players[winner], GameAI):
                    state = self.game_state
                    state['winner'] = winner
                    state['your_type'] = winner
                    state['ended'] = True
                    self.__players[winner].protocol.send_game_update(state)
                self.endgame()


class VirtualPlayer():
    pass


if __name__ == '__main__':
    game_manager = GameManager()

    factory = ServerFactory()
    factory.protocol = TTTServer

    reactor.listenTCP(8899, factory)
    reactor.run()
