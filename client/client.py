import os
from twisted.protocols.basic import LineReceiver
from twisted.internet.protocol import ClientCreator, ClientFactory, connectionDone
from twisted.internet import reactor

import curses
import curses.wrapper

from json import load, dump, loads, dumps

class TextTooLongError(Exception):
    pass

CREDENTIALS = 'creds.json'
DEBUG = True

class TTTClient(LineReceiver):
    STATE_AUTH = 0
    STATE_IDLE = 1
    STATE_QUEUE = 2
    STATE_GAME = 3
    def __init__(self, screen):
        self.state = self.STATE_AUTH
        self.__screen = screen
        self.__screen.client = self
        self.stats = None

    def process_key_input(self, command):
        """

        :param command:
        :type str:
        :return:
        """
        self.__screen.addLine('Got input "%s", len: %s'%(command, len(command)))
        if self.state == self.STATE_IDLE:
            if command.upper() == 'Q':
                net_cmd = {"cmd": "queue"}
                self.state = self.STATE_QUEUE
                self.send_data(net_cmd)
                reactor.removeReader(sobj)
        elif self.state == self.STATE_GAME:
            cmd_pairs = [int(x) for x in command.split()]
            if len(cmd_pairs) == 2:
                net_cmd = {"cmd": "move", "pos": cmd_pairs}
                self.send_data(net_cmd)
                reactor.removeReader(sobj)

    def connectionLost(self, reason=connectionDone):
        self.__screen.addLine('Connection lost! Restart client')


    def connectionMade(self):
        creds = self.get_credentials()
        if not creds:
            command = {'cmd': 'reg'}
        else:
            command = {'cmd': 'auth', 'user_id': creds.get('user_id')}
        self.send_data(command)

    def lineReceived(self, line):
        if DEBUG:
            self.__screen.addLine('>> %s' % line)
        data = self.parse_packet(line)
        command = data.get("cmd")
        if self.state == self.STATE_AUTH:
            if command == 'reg':
                user_id = data.get('user_id')
                if user_id:
                    self.save_credentials(user_id)
                self.state = self.STATE_IDLE
                self.stats = [0,0,0]
                self.__screen.addLine('Registered!')
            elif command == 'auth':
                self.state = self.STATE_IDLE
                self.stats = data.get('stats')
                self.__screen.addLine('Authorized!')
            if self.state == self.STATE_IDLE:
                self.idle_message()
                self.__screen.set_status_idle(self.stats)

        elif self.state == self.STATE_QUEUE:
            if command == 'state':
                self.state = self.STATE_GAME
                field = data.get('field')
                your_sign = data.get('your_type')
                opponent_sign = "x"
                if your_sign == "x":
                    opponent_sign = "o"
                opponent = data.get("player_%s" % opponent_sign)
                you = data.get("player_%s" % your_sign)
                is_human = (opponent['name'] != 'AI')
                self.__screen.set_status_game(your_sign, opponent['stats'], is_human)
                self.__screen.addLine(' ')
                self.__screen.addLine('Games started')
                self.draw_field(field)
                self.should_i_move(data)
        elif self.state == self.STATE_GAME:
            if command == 'state':
                finished = data.get('ended')
                if not finished:
                    field = data.get('field')
                    self.draw_field(field)
                    self.should_i_move(data)
                else:
                    self.__screen.addLine('Game ended!')
                    your_sign = data.get('your_type')
                    winner = data.get('winner')
                    if winner is None:
                        message = "It's a TIE!"
                    elif winner == your_sign:
                        message = "Congratulations! You've won!"
                    else:
                        message = 'You lose.'
                    self.__screen.addLine(message)
                    self.stats = data.get('player_%s'%your_sign).get('stats')
                    self.state = self.STATE_IDLE
                    self.idle_message(self.stats)

    def should_i_move(self, data):
        if data.get('your_type') != data.get('last_turn'):
            self.__screen.addLine("It's your turn now!")
            self.__screen.addLine("Input number of row, then number of column (Like 'x y')")
            reactor.addReader(sobj)

    def idle_message(self):
        self.__screen.addLine('Press Q and press enter to enter gaming queue')
        reactor.addReader(sobj)

    @staticmethod
    def prepare_field_row(val):
        if val is None:
            val = ' '
        return val

    def draw_field(self, field):
        delimiter ='    -*-*-*-'
        header =   '     |0|1|2'
        lines = []
        for i, val in enumerate(field):
            v = map(self.prepare_field_row, val)
            lines.append('    %s|%s|%s|%s' % (i, v[0], v[1], v[2]))
        self.__screen.addLine(header)
        self.__screen.addLine(delimiter)
        self.__screen.addLine(lines[0])
        self.__screen.addLine(delimiter)
        self.__screen.addLine(lines[1])
        self.__screen.addLine(delimiter)
        self.__screen.addLine(lines[2])

    @staticmethod
    def parse_packet(packet):
        try:
            data = loads(packet)
        except Exception:
            return False
        return data

    def save_credentials(self, user_id):
        credentials = {"user_id": user_id}
        with open(CREDENTIALS, 'w') as fp:
            dump(credentials, fp)

    def get_credentials(self):
        if os.path.exists(CREDENTIALS):
            with open(CREDENTIALS, 'r') as fp:
                creds = load(fp)
                if 'user_id' in creds:
                    return creds
        return False

    def send_data(self, data):
        command = dumps(data)
        if DEBUG:
            self.__screen.addLine('<< %s' % command)
        self.sendLine(command)

class CursesStdIO:
    """fake fd to be registered as a reader with the twisted reactor.
       Curses classes needing input should extend this"""

    def fileno(self):
        """ We want to select on FD 0 """
        return 0

    def doRead(self):
        """called when input is ready"""

    def logPrefix(self):
        return 'CursesClient'

class Screen(CursesStdIO):
    def __init__(self, stdscr):
        self.timer = 0
        self.statusText = "TEST CURSES APP -"
        self.searchText = ''
        self.stdscr = stdscr
        self.client = None
        self.game_data = {}

        # set screen attributes
        self.stdscr.nodelay(1) # this is used to make input calls non-blocking
        curses.cbreak()
        self.stdscr.keypad(1)
        curses.curs_set(0)     # no annoying mouse cursor

        self.rows, self.cols = self.stdscr.getmaxyx()
        self.lines = []

        curses.start_color()

        # create color pair's 1 and 2
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)

        self.paintStatus(self.statusText)

    def connectionLost(self, reason):
        self.close()

    def addLine(self, text):
        """ add a line to the internal list of lines"""
        if len(text) > self.cols:
            text = text[0:self.cols-1]
        self.lines.append(text)
        self.redisplayLines()

    def redisplayLines(self):
        """ method for redisplaying lines
            based on internal list of lines """

        self.stdscr.clear()
        self.paintStatus(self.statusText)
        i = 0
        index = len(self.lines) - 1
        while i < (self.rows - 3) and index >= 0:
            self.stdscr.addstr(self.rows - 3 - i, 0, self.lines[index],
                               curses.color_pair(2))
            i = i + 1
            index = index - 1
        self.stdscr.refresh()

    def paintStatus(self, text):
        if len(text) > self.cols: raise TextTooLongError
        self.stdscr.addstr(self.rows-2,0,text + ' ' * (self.cols-len(text)),
                           curses.color_pair(1))
        # move cursor to input line
        self.stdscr.move(self.rows-1, self.cols-1)

    def doRead(self):
        """ Input is ready! """
        curses.noecho()
        self.timer = self.timer + 1
        c = self.stdscr.getch() # read a character

        if c == curses.KEY_BACKSPACE:
            self.searchText = self.searchText[:-1]

        elif c == curses.KEY_ENTER or c == 10:
            self.addLine(self.searchText)
            # for testing too
            # self.client.process_key_input(self.searchText)
            try: self.client.process_key_input(self.searchText)
            except Exception as e: self.addLine(str(e))
            self.stdscr.refresh()
            self.searchText = ''

        else:
            if len(self.searchText) == self.cols-2: return
            self.searchText = self.searchText + chr(c)

        self.stdscr.addstr(self.rows-1, 0,
                           self.searchText + (' ' * (
                           self.cols-len(self.searchText)-2)))
        self.stdscr.move(self.rows-1, len(self.searchText))
        self.paintStatus(self.statusText + ' %d' % len(self.searchText))
        self.stdscr.refresh()

    def set_status_game(self, your_sign, stats, human=True):
        opponent = 'AI'
        stats_template = 'W-{:.2%}, L-{:.2%}, T-{:.2%}'
        stats_string = stats_template.format(*stats)
        if human:
            opponent = 'Human'
        status = 'Playing with: %s | Playing against: %s (%s)' % (your_sign.upper(), opponent, stats_string)
        self.statusText = status
        self.redisplayLines()

    def set_status_idle(self, stats):
        self.__screen.statusText = 'State: authorized. Your stats: W-{:.2%}, L-{:.2%}, T-{:.2%}'.format(*stats)
        self.redisplayLines()

    def close(self):
        """ clean up """

        curses.nocbreak()
        self.stdscr.keypad(0)
        curses.echo()
        curses.endwin()

class TTTProtocolFactory(ClientFactory):
    def __init__(self, screen):
        self.__screen = screen

    def buildProtocol(self, addr):
        return TTTClient(self.__screen)

    def clientConnectionLost(self, conn, reason):
        pass



# factory.protocol = TTTClient
scr = curses.initscr()
sobj = Screen(scr)
scr.refresh()
factory = TTTProtocolFactory(sobj)

reactor.connectTCP("192.168.0.54", 8899, factory)
reactor.run()



# c = ClientCreator(reactor, TTTClient)
# c.connectTCP("192.168.0.54", 8899).addCallback(got_protocol)