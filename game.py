from copy import deepcopy

CIRCLE = 'o'
CROSS = 'x'


class Field(object):
    """
    We're presuming that field is organized as
        array of rows

    """

    def __init__(self, size):
        self._field = [[None for i in range(size)] for x in range(size)]
        self._size = size
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
        return True

    @property
    def field(self):
        return deepcopy(self._field)

    @property
    def size(self):
        return self._size


class Rules(object):
    def check_win_from_move(self, board, x, y):
        """

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

    def __init__(self):
        self.__board = Field(3)
        self.__rules = Rules()
        self.__last_move = CIRCLE
        self.__win_by = None
        self.__state = self.GAME

    @property
    def current_move(self):
        return self.__last_move

    def place_cross(self, x, y):
        return self.make_move(CROSS, x, y)

    def place_circle(self, x, y):
        return self.make_move(CIRCLE, x, y)

    def make_move(self, sign, x, y):
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
        self.__last_move = sign

    def is_win_by(self):
        return self.__win_by
