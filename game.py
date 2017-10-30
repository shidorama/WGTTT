from copy import deepcopy
from random import randint

from settings import CIRCLE, CROSS
from user import User


class Field(object):
    """
    We're presuming that field is organized as
        array of rows

    """

    def __init__(self, size):
        self._field = [[None for i in range(size)] for x in range(size)]
        self._size = size
        self._free_cells = size * size
        pass

    def get_row(self, number):
        if 0 <= number < self._size:
            return deepcopy(self._field[number])
        return False

    def get_column(self, number):
        if not (0 <= number < self._size):
            return False
        return [i[number] for i in self._field]

    def get_diagonal(self, right=True):
        if right:
            return [self._field[i][i] for i in range(self._size)]
        return [self._field[i][self._size - i - 1] for i in range(self._size)]

    def put_cross(self, x, y):
        return self.put_sign(CROSS, x, y)

    def put_circle(self, x, y):
        return self.put_sign(CIRCLE, x, y)

    def check_index(self, index):
        return 0 <= index < self._size

    def put_sign(self, sign, x, y):
        if not (self.check_index(x) and self.check_index(y)):
            return False
        if self._field[y][x] is not None:
            return False
        self._field[y][x] = sign
        self._free_cells -= 1
        return True

    @property
    def field(self):
        return deepcopy(self._field)

    @property
    def is_full(self):
        return self._free_cells == 0

    @property
    def size(self):
        return self._size


class Rules(object):
    def check_win_from_move(self, board, x, y):
        """check if this move resulted in win

        :param board:
        :type board: Field
        :param x:
        :param y:
        """
        lines = []
        lines.append(board.get_column(x))
        lines.append(board.get_row(y))
        if x == y:
            lines.append(board.get_diagonal())
        if x + y == board.size:
            lines.append(board.get_diagonal(False))
        for line in lines:
            if self.check_row_for_win(line):
                return True
        return False

    @staticmethod
    def check_row_for_win(row):
        """check if specific row will result in endgame

        :param row:
        :return:
        """
        starter = row[0]
        if starter is None:
            return False
        for cell in row:
            if cell != starter:
                return False
        return True


class Game(object):
    GAME = 0
    WIN = 1
    TIE = 2

    def __init__(self):
        self.__board = Field(3)
        self.__rules = Rules()
        self.__last_move = CIRCLE
        self.__win_by = None
        self.__state = self.GAME

    @property
    def board(self):
        return self.__board.field

    @property
    def last_move(self):
        return self.__last_move

    def place_cross(self, x, y):
        return self.make_move(CROSS, x, y)

    def place_circle(self, x, y):
        return self.make_move(CIRCLE, x, y)

    def make_move(self, sign, x, y):
        """Place specified sign on a cell if it's available

        :param sign:
        :param x:
        :param y:
        :return:
        """
        if sign not in [CROSS, CIRCLE]:
            return False
        if self.__last_move == sign:
            return False
        if self.__state == self.WIN:
            return False
        outcome = self.__board.put_sign(sign, x, y)
        if not outcome:
            return False
        if self.__rules.check_win_from_move(self.__board, x, y):
            self.__win_by = sign
            self.__state = self.WIN
        elif self.__board.is_full:
            self.__state = self.TIE
        self.__last_move = sign
        return True

    @property
    def state(self):
        return self.__state

    @property
    def winner(self):
        return self.__win_by


class GameAI(User):
    SIZE = 3
    name = 'AI'
    stats = [0, 0, 0]
    user_id = 'AI'

    @property
    def wins(self):
        return 0

    @wins.setter
    def wins(self, value):
        pass

    @property
    def ties(self):
        return 0

    @ties.setter
    def ties(self, value):
        pass

    @property
    def loses(self):
        return 0

    @loses.setter
    def loses(self, value):
        pass

    def __init__(self, controller):
        self.__controller = controller

    def play(self):
        """just randomly tries to make move until gets True

        :return:
        """
        result = False
        while not result:
            x = randint(0, 2)
            y = randint(0, 2)
            result = self.__controller('AI', x, y)
