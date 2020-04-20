"""C{out [-a|--append FILENAME] [-f|--file FILENAME] [-c | --csv | FORMAT]}

Input objects are passed on as output. As a side-effect, input objects are
printed to stdout or to a file. The output is rendered using the default
converstion to string unless specified otherwise.

-a | --append FILENAME     Append to the named file.

-f | --file FILENAME       Write to the named file, overwriting an existing
                           file if it exists.

-c | --csv                 Format output separating components by commas.
                           Each component is rendered using the default conversion
                           to string.

FORMAT                     A Python formatter specifying how an object should be
                           rendered.
"""

import sys

import marcel.core
import marcel.object.error
import marcel.object.renderable


def out():
    return Out()


class OutArgParser(marcel.core.ArgParser):

    def __init__(self, global_state):
        super().__init__('out',
                         global_state,
                         ['-a', '--append', '-f', '--file', '-c', '--csv'])
        file_group = self.add_mutually_exclusive_group()
        file_group.add_argument('-a', '--append', required=False)
        file_group.add_argument('-f', '--file', required=False)
        self.add_argument('-c', '--csv', action='store_true')
        self.add_argument('format', nargs='?')


class Out(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.append = None
        self.file = None
        self.csv = False
        self.format = None
        self.output = None

    def __repr__(self):
        return f'out(append={self.append}, file={self.file}, csv={self.csv}, format={Out.ensure_quoted(self.format)})'

    # BaseOp

    def doc(self):
        return __doc__

    def setup_1(self):
        if self.csv and self.format:
            raise marcel.exception.KillCommandException('-c/--csv and FORMAT specifications are incompatible')

    def receive(self, x):
        self.ensure_output_initialized()
        if self.format:
            out = self.format.format(*x)
        elif self.csv:
            out = (', '.join([Out.ensure_quoted(y) for y in x])
                   if type(x) in (list, tuple) else
                   str(x))
        else:
            if type(x) in (list, tuple):
                if len(x) == 1:
                    out = x[0]
                    if isinstance(out, marcel.object.renderable.Renderable):
                        out = out.render_full(self.color_scheme())
                else:
                    buffer = []
                    for y in x:
                        if isinstance(y, marcel.object.renderable.Renderable):
                            y = y.render_compact()
                        buffer.append(Out.ensure_quoted(y))
                    out = '(' + ', '.join(buffer) + ')'
            else:
                out = str(x)
        # Relying on print to provide the \n appears to result in a race condition.
        try:
            print(out, file=self.output, flush=True)
        except Exception as e:  # E.g. UnicodeEncodeError
            error = marcel.object.error.Error(e)
            self.print_error(error)
        finally:
            self.send(x)

    def receive_error(self, error):
        self.ensure_output_initialized()
        self.print_error(error)

    def receive_complete(self):
        self.ensure_output_initialized()
        if self.output != sys.stdout and self.output is not None:
            self.output.close()
        self.send_complete()

    # For use by this class

    def ensure_output_initialized(self):
        if self.output is None:
            self.output = (open(self.append, mode='a') if self.append else
                           open(self.file, mode='w') if self.file else
                           sys.stdout)

    def print_error(self, error):
        print(self.render(error, True), file=self.output, flush=True)

    def render(self, x, full):
        if x is None:
            return None
        elif isinstance(x, marcel.object.renderable.Renderable):
            return (x.render_full(self.color_scheme())
                    if full else
                    x.render_compact())
        else:
            return str(x)

    def color_scheme(self):
        return (self.global_state().env.color_scheme()
                if self.output == sys.__stdout__ else
                None)

    @staticmethod
    def ensure_quoted(x):
        if x is None:
            return 'None'
        elif type(x) in (int, float):
            return str(x)
        elif isinstance(x, str):
            if "'" not in x:
                return "'{}'".format(x)
            elif '"' not in x:
                return '"{}"'.format(x)
            else:
                return "'{}'".format(x.replace("'", "\\'"))
        else:
            return str(x)
