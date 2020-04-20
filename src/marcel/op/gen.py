"""C{gen [-p|--pad PAD] [COUNT [START]]}

Generate a sequence of C{COUNT} integers, starting at C{START}. C{COUNT} must be non-negative.
If C{START} is not specified, then the sequence starts at 0. If C{COUNT} is 0 or is not specified,
then the sequence does not terminate.

-p | --pad PAD             The generated integers are converted to strings and left-padded with zeros
                           so that each string contains C{PAD} characters. The number of digits in each
                           member of the generated sequence must not exceed C{PAD}. This option queries
                           C{START} >= 0.
"""

import marcel.core


def gen():
    return Gen()


class GenArgParser(marcel.core.ArgParser):

    def __init__(self, global_state):
        super().__init__('gen', global_state, ['-p', '--pad'])
        self.add_argument('-p', '--pad',
                          type=int)
        self.add_argument('count',
                          nargs='?',
                          default='0',
                          type=super().constrained_type(marcel.core.ArgParser.check_non_negative,
                                                        'must be non-negative'))
        self.add_argument('start',
                          nargs='?',
                          default='0',
                          type=int)


class Gen(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.pad = None
        self.count = None
        self.start = None
        self.format = None

    def __repr__(self):
        return f'gen(count={self.count}, start={self.start}, pad={self.pad})'

    # BaseOp

    def doc(self):
        return self.__doc__

    def setup_1(self):
        if self.pad is not None:
            if self.count == 0:
                raise marcel.exception.KillCommandException('Padding incompatible with unbounded output')
            elif self.start < 0:
                raise marcel.exception.KillCommandException('Padding incompatible with START < 0')
            else:
                max_length = len(str(self.start + self.count - 1))
                if max_length > self.pad:
                    raise marcel.exception.KillCommandException('Padding too small.')
                else:
                    self.format = '{:>0' + str(self.pad) + '}'

    def receive(self, _):
        if self.count is None or self.count == 0:
            x = self.start
            while True:
                self.send(self.apply_padding(x))
                x += 1
        else:
            for x in range(self.start, self.start + self.count):
                self.send(self.apply_padding(x))

    # Op

    def must_be_first_in_pipeline(self):
        return True

    # For use by this class

    def apply_padding(self, x):
        return (self.format.format(x)) if self.format else x
