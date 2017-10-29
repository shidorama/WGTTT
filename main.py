import uuid

from twisted.internet import reactor, task
from twisted.protocols.basic import LineReceiver
from twisted.internet.protocol import ServerFactory
from base64 import b64decode, b64encode
from json import dumps, loads
from collections import deque
from time import time

from user import user_mananger, User

users = {}


class CQueue(deque):
    def push(self, value):
        self.appendleft(value)

    def isEmpty(self):
        return len(self) > 0

class TTTServer(LineReceiver):
    def __init__(self):
        # super(TTTServer, self).__init__()
        # self.__manager = gm
        self.__kill_flag = False
        self.authorized = False
        self.__updated = time()

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

    def game_reactor(self, command, packet):
        pass

    def auth_reactor(self, command, packet):
        if command == 'auth':
            user_id = packet.get('user_id')
            result = user_mananger.auth_user(user_id)
            answer = {'cmd': command, 'success': result}
            if result:
                self.authorized = True
            self.responder(answer)
        elif command == 'reg':
            user = user_mananger.register_new_user()
            result = {'cmd': 'reg', 'success': True, 'user_id': user.user_id}
            self.responder(result)
        else:
            self.send_error(True)

    def responder(self, data):
        packet = dumps(data).encode()
        self.transport.write(packet)
        self.transport.write('\r\n')
        if self.__kill_flag:
            self.transport.loseConnection()


class Protocol(object):
    pass

class GameManager():
    def __init__(self):
        self.queue = CQueue()
        self.command_queue = CQueue()



class VirtualPlayer():
    pass

if __name__ == '__main__':
    game_manager = GameManager()

    factory = ServerFactory()
    factory.protocol = TTTServer

    reactor.listenTCP(8899, factory)
    reactor.run()