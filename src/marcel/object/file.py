import os
import pathlib
import stat
import time

import marcel.object.renderable
import marcel.op.filenames
from marcel.util import *

DIR_MASK = 0o040000
FILE_MASK = 0o100000
LINK_MASK = 0o120000
FILE_TYPE_MASK = DIR_MASK | FILE_MASK | LINK_MASK


class File(marcel.object.renderable.Renderable):
    """Represents a file or directory.
    """

    def __init__(self, path, base=None):
        assert path is not None
        if not isinstance(path, pathlib.Path):
            path = pathlib.Path(path)
        self.path = path
        self.display_path = path.relative_to(base) if base else path
        self.lstat = None
        self.executable = None
        # Used only to survive pickling
        self.path_str = None
        self.display_path_str = None

    def __repr__(self):
        return self.render_compact()

    def __getattr__(self, attr):
        return getattr(self.path, attr)

    def __getstate__(self):
        # Ensure metadata is present before transmission
        self._is_executable()
        self._lstat()
        # Send strings, not paths
        if self.path is not None:
            self.path_str = str(self.path)
            self.path = None
        if self.display_path is not None:
            self.display_path_str = str(self.display_path)
            self.display_path = None
        return self.__dict__

    def __setstate__(self, state):
        self.__dict__.update(state)
        if self.path_str:
            self.path = pathlib.Path(self.path_str)
            self.path_str = None
        if self.display_path_str:
            self.display_path = pathlib.Path(self.display_path_str)
            self.display_path_str = None

    stat = property(lambda self: self._lstat(),
                     doc="""lstat of this file""")
    mode = property(lambda self: self._lstat()[0],
                    doc="""mode of this file.""")
    inode = property(lambda self: self._lstat()[1],
                     doc="""inode of this file.""")
    device = property(lambda self: self._lstat()[2],
                      doc="""device of this file.""")
    links = property(lambda self: self._lstat()[3],
                     doc=""" Number of links of this file.""")
    uid = property(lambda self: self._lstat()[4],
                   doc="""Owner of this file.""")
    gid = property(lambda self: self._lstat()[5],
                   doc="""Owning group of this file.""")
    size = property(lambda self: self._lstat()[6],
                    doc="""Size of this file (bytes).""")
    atime = property(lambda self: self._lstat()[7],
                     doc="""Access time of this file.""")
    mtime = property(lambda self: self._lstat()[8],
                     doc="""Modify time of this file.""")
    ctime = property(lambda self: self._lstat()[9],
                     doc="""Change time of this file.""")

    # Renderable

    def render_compact(self):
        return str(self.display_path)

    def render_full(self, color_scheme):
        line = self._formatted_metadata()
        if color_scheme:
            line[-1] = colorize(line[-1], self._highlight_color(self, color_scheme))
        if self._is_symlink():
            line.append('->')
            link_target = pathlib.Path(os.readlink(self.path))
            if color_scheme:
                link_target = colorize(link_target, self._highlight_color(link_target, color_scheme))
            if isinstance(link_target, pathlib.Path):
                link_target = link_target.as_posix()
            line.append(link_target)
        return ' '.join(line)

    # For use by this class

    def _is_executable(self):
        # is_executable must check path.resolve(), not path. If the path is relative, and the name
        # is also an executable on PATH, then highlighting will be incorrect. See bug 8.
        if self.executable is None:
            self.executable = is_executable(self.path.resolve().as_posix())
        return self.executable

    def _formatted_metadata(self):
        lstat = self._lstat()  # Not stat. Don't want to follow symlinks here.
        return [
            self._mode_string(lstat.st_mode),
            ' ',
            '{:8s}'.format(username(lstat.st_uid)),
            '{:8s}'.format(groupname(lstat.st_gid)),
            '{:12}'.format(lstat.st_size),
            ' ',
            self._formatted_mtime(lstat.st_mtime),
            ' ',
            self.display_path.as_posix()]

    def _lstat(self):
        if self.lstat is None:
            self.lstat = self.path.lstat()
        return self.lstat

    @staticmethod
    def _mode_string(mode):
        buffer = [
            'l' if (mode & LINK_MASK) == LINK_MASK else
            'd' if (mode & DIR_MASK) == DIR_MASK else
            '-',
            File._rwx((mode & 0o700) >> 6),
            File._rwx((mode & 0o70) >> 3),
            File._rwx(mode & 0o7)
        ]
        return ''.join(buffer)

    @staticmethod
    def _formatted_mtime(mtime):
        return time.strftime('%Y %b %d %H:%M:%S', time.localtime(mtime))

    def _highlight_color(self, path, color_scheme):
        extension = path.suffix.lower()
        highlight = color_scheme.file_extension.get(extension)
        if highlight is None:
            highlight = (
                # Check symlink first, because is_executable (at least) follows symlinks.
                color_scheme.file_link if self._is_symlink() else
                color_scheme.file_executable if self._is_executable() else
                color_scheme.file_dir if self._is_dir() else
                color_scheme.file_file)
        return highlight

    # Use stat.S_... methods instead of methods relying on pathlib. First, pathlib
    # doesn't cache lstat results. Second, if the file has been transmitted as part
    # of a sudo command, then the recipient can't necessarily run lstat.

    def _is_symlink(self):
        return stat.S_ISLNK(self._lstat().st_mode)

    def _is_dir(self):
        return stat.S_ISDIR(self._lstat().st_mode)

    @staticmethod
    def _rwx(m):
        buffer = [
            'r' if (m & 0o4) != 0 else '-',
            'w' if (m & 0o2) != 0 else '-',
            'x' if (m & 0o1) != 0 else '-'
        ]
        return ''.join(buffer)
