import boto3
import datetime
import json
import logging
from boto3.dynamodb.conditions import Key, Attr

# Lazily copy-pasting the TextTable class code in here.
import re
import math
import sys
import string
import textwrap
from functools import reduce


def len(iterable):
    """Redefining len here so it will be able to work with non-ASCII characters"""
    if not isinstance(iterable, str):
        return iterable.__len__()

    try:
        return len(str(iterable, "utf"))
    except:
        return iterable.__len__()


class ArraySizeError(Exception):
    """Exception raised when specified rows don't fit the required size"""

    def __init__(self, msg):
        self.msg = msg
        Exception.__init__(self, msg, "")

    def __str__(self):
        return self.msg


class bcolors:
    PURPLE = "\x1b[95m"
    BLUE = "\x1b[94m"
    GREEN = "\x1b[92m"
    YELLOW = "\x1b[93m"
    RED = "\x1b[91m"
    ENDC = "\x1b[0m"
    WHITE = ""
    BOLD = "\x1b[1m"
    UNDERLINE = "\x1b[4m"


def get_color_string(type, string):
    end = bcolors.ENDC
    if type == bcolors.WHITE:
        end = ""
    return "%s%s%s" % (type, string, end)


class Texttable:

    BORDER = 1
    HEADER = 1 << 1
    HLINES = 1 << 2
    VLINES = 1 << 3

    def __init__(self, max_width=80):
        """Constructor

        - max_width is an integer, specifying the maximum width of the table
        - if set to 0, size is unlimited, therefore cells won't be wrapped
        """

        if max_width <= 0:
            max_width = False
        self._max_width = max_width
        self._precision = 3

        self._deco = (
            Texttable.VLINES | Texttable.HLINES | Texttable.BORDER | Texttable.HEADER
        )
        self.set_chars(["-", "|", "+", "="])
        self.reset()

    def reset(self):
        """Reset the instance

        - reset rows and header
        """

        self._hline_string = None
        self._row_size = None
        self._header = []
        self._rows = []

    def set_chars(self, array):
        """Set the characters used to draw lines between rows and columns

        - the array should contain 4 fields:

            [horizontal, vertical, corner, header]

        - default is set to:

            ['-', '|', '+', '=']
        """

        if len(array) != 4:
            raise ArraySizeError("array should contain 4 characters")
        array = [x[:1] for x in [str(s) for s in array]]
        (self._char_horiz, self._char_vert, self._char_corner, self._char_header) = (
            array
        )

    def set_deco(self, deco):
        """Set the table decoration

        - 'deco' can be a combinaison of:

            Texttable.BORDER: Border around the table
            Texttable.HEADER: Horizontal line below the header
            Texttable.HLINES: Horizontal lines between rows
            Texttable.VLINES: Vertical lines between columns

           All of them are enabled by default

        - example:

            Texttable.BORDER | Texttable.HEADER
        """

        self._deco = deco

    def set_cols_align(self, array):
        """Set the desired columns alignment

        - the elements of the array should be either "l", "c" or "r":

            * "l": column flushed left
            * "c": column centered
            * "r": column flushed right
        """

        self._check_row_size(array)
        self._align = array

    def set_cols_valign(self, array):
        """Set the desired columns vertical alignment

        - the elements of the array should be either "t", "m" or "b":

            * "t": column aligned on the top of the cell
            * "m": column aligned on the middle of the cell
            * "b": column aligned on the bottom of the cell
        """

        self._check_row_size(array)
        self._valign = array

    def set_cols_dtype(self, array):
        """Set the desired columns datatype for the cols.

        - the elements of the array should be either "a", "t", "f", "e" or "i":

            * "a": automatic (try to use the most appropriate datatype)
            * "t": treat as text
            * "f": treat as float in decimal format
            * "e": treat as float in exponential format
            * "i": treat as int

        - by default, automatic datatyping is used for each column
        """

        self._check_row_size(array)
        self._dtype = array

    def set_cols_width(self, array):
        """Set the desired columns width

        - the elements of the array should be integers, specifying the
          width of each column. For example:

                [10, 20, 5]
        """

        self._check_row_size(array)
        try:
            array = list(map(int, array))
            if reduce(min, array) <= 0:
                raise ValueError
        except ValueError:
            sys.stderr.write("Wrong argument in column width specification\n")
            raise
        self._width = array

    def set_precision(self, width):
        """Set the desired precision for float/exponential formats

        - width must be an integer >= 0

        - default value is set to 3
        """

        if not type(width) is int or width < 0:
            raise ValueError("width must be an integer greater then 0")
        self._precision = width

    def header(self, array):
        """Specify the header of the table"""

        self._check_row_size(array)
        self._header = list(map(str, array))

    def add_row(self, array):
        """Add a row in the rows stack

        - cells can contain newlines and tabs
        """

        self._check_row_size(array)

        if not hasattr(self, "_dtype"):
            self._dtype = ["a"] * self._row_size

        cells = []
        for i, x in enumerate(array):
            cells.append(self._str(i, x))
        self._rows.append(cells)

    def add_rows(self, rows, header=True):
        """Add several rows in the rows stack

        - The 'rows' argument can be either an iterator returning arrays,
          or a by-dimensional array
        - 'header' specifies if the first row should be used as the header
          of the table
        """

        # nb: don't use 'iter' on by-dimensional arrays, to get a
        #     usable code for python 2.1
        if header:
            if hasattr(rows, "__iter__") and hasattr(rows, "next"):
                self.header(next(rows))
            else:
                self.header(rows[0])
                rows = rows[1:]
        for row in rows:
            self.add_row(row)

    def draw(self):
        """Draw the table

        - the table is returned as a whole string
        """

        if not self._header and not self._rows:
            return
        self._compute_cols_width()
        self._check_align()
        out = ""
        if self._has_border():
            out += self._hline()
        if self._header:
            out += self._draw_line(self._header, isheader=True)
            if self._has_header():
                out += self._hline_header()
        length = 0
        for row in self._rows:
            length += 1
            out += self._draw_line(row)
            if self._has_hlines() and length < len(self._rows):
                out += self._hline()
        if self._has_border():
            out += self._hline()
        return out[:-1]

    def _str(self, i, x):
        """Handles string formatting of cell data

        i - index of the cell datatype in self._dtype
        x - cell data to format
        """
        try:
            f = float(x)
            n = str(f)
            if n == "nan" or n == "inf" or n == "-inf":
                raise ValueError("Infinity or NaN considered as string")
        except:
            if type(x) is str:
                return x
            else:
                if x is None:
                    return str(x)
                else:
                    return str(x.encode("utf-8"))

        n = self._precision
        dtype = self._dtype[i]

        if dtype == "i":
            return str(int(round(f)))
        elif dtype == "f":
            return "%.*f" % (n, f)
        elif dtype == "e":
            return "%.*e" % (n, f)
        elif dtype == "t":
            if type(x) is str:
                return x
            else:
                if x is None:
                    return str(x)
                else:
                    return str(x.encode("utf-8"))
        else:
            if f - round(f) == 0:
                if abs(f) > 1e8:
                    return "%.*e" % (n, f)
                else:
                    return str(int(round(f)))
            else:
                if abs(f) > 1e8:
                    return "%.*e" % (n, f)
                else:
                    return "%.*f" % (n, f)

    def _check_row_size(self, array):
        """Check that the specified array fits the previous rows size"""

        if not self._row_size:
            self._row_size = len(array)
        elif self._row_size != len(array):
            raise ArraySizeError("array should contain %d elements" % self._row_size)

    def _has_vlines(self):
        """Return a boolean, if vlines are required or not"""

        return self._deco & Texttable.VLINES > 0

    def _has_hlines(self):
        """Return a boolean, if hlines are required or not"""

        return self._deco & Texttable.HLINES > 0

    def _has_border(self):
        """Return a boolean, if border is required or not"""

        return self._deco & Texttable.BORDER > 0

    def _has_header(self):
        """Return a boolean, if header line is required or not"""

        return self._deco & Texttable.HEADER > 0

    def _hline_header(self):
        """Print header's horizontal line"""

        return self._build_hline(True)

    def _hline(self):
        """Print an horizontal line"""

        if not self._hline_string:
            self._hline_string = self._build_hline()
        return self._hline_string

    def _build_hline(self, is_header=False):
        """Return a string used to separated rows or separate header from
        rows
        """
        horiz = self._char_horiz
        if is_header:
            horiz = self._char_header
        # compute cell separator
        s = "%s%s%s" % (horiz, [horiz, self._char_corner][self._has_vlines()], horiz)
        # build the line
        l = s.join([horiz * n for n in self._width])
        # add border if needed
        if self._has_border():
            l = "%s%s%s%s%s\n" % (self._char_corner, horiz, l, horiz, self._char_corner)
        else:
            l += "\n"
        return l

    def _len_cell(self, cell):
        """Return the width of the cell

        Special characters are taken into account to return the width of the
        cell, such like newlines and tabs
        """

        cell = re.compile(r"\x1b[^m]*m").sub("", cell)

        cell_lines = cell.split("\n")
        maxi = 0
        for line in cell_lines:
            length = 0
            parts = line.split("\t")
            for part, i in zip(parts, list(range(1, len(parts) + 1))):
                length = length + len(part)
                if i < len(parts):
                    length = (length // 8 + 1) * 8
            maxi = max(maxi, length)
        return maxi

    def _compute_cols_width(self):
        """Return an array with the width of each column

        If a specific width has been specified, exit. If the total of the
        columns width exceed the table desired width, another width will be
        computed to fit, and cells will be wrapped.
        """

        if hasattr(self, "_width"):
            return
        maxi = []
        if self._header:
            maxi = [self._len_cell(x) for x in self._header]
        for row in self._rows:
            for cell, i in zip(row, list(range(len(row)))):
                try:
                    maxi[i] = max(maxi[i], self._len_cell(cell))
                except (TypeError, IndexError):
                    maxi.append(self._len_cell(cell))
        items = len(maxi)
        length = reduce(lambda x, y: x + y, maxi)
        if self._max_width and length + items * 3 + 1 > self._max_width:
            max_lengths = maxi
            maxi = [(self._max_width - items * 3 - 1) // items for n in range(items)]

            # free space to distribute
            free = 0

            # how many columns are oversized
            oversized = 0

            # reduce size of columns that need less space and calculate how
            # much space is freed
            for col, max_len in enumerate(max_lengths):
                current_length = maxi[col]

                # column needs less space, adjust and
                # update free space
                if current_length > max_len:
                    free += current_length - max_len
                    maxi[col] = max_len

                # column needs more space, count it
                elif max_len > current_length:
                    oversized += 1

            # as long as free space is available, distribute it
            while free > 0:
                # available free space for each oversized column
                free_part = int(math.ceil(float(free) / float(oversized)))

                for col, max_len in enumerate(max_lengths):
                    current_length = maxi[col]

                    # column needs more space
                    if current_length < max_len:

                        # how much space is needed
                        needed = max_len - current_length

                        # enough free space for column
                        if needed <= free_part:
                            maxi[col] = max_len
                            free -= needed
                            oversized -= 1

                        # still oversized after re-sizing
                        else:
                            maxi[col] = maxi[col] + free_part
                            free -= free_part
        self._width = maxi

    def _check_align(self):
        """Check if alignment has been specified, set default one if not"""

        if not hasattr(self, "_align"):
            self._align = ["l"] * self._row_size
        if not hasattr(self, "_valign"):
            self._valign = ["t"] * self._row_size

    def _draw_line(self, line, isheader=False):
        """Draw a line

        Loop over a single cell length, over all the cells
        """

        line = self._splitit(line, isheader)
        space = " "
        out = ""
        for i in range(len(line[0])):
            if self._has_border():
                out += "%s " % self._char_vert
            length = 0
            for cell, width, align in zip(line, self._width, self._align):
                length += 1
                cell_line = cell[i]

                fill = width - len(re.compile(r"\x1b[^m]*m").sub("", cell_line))
                if isheader:
                    align = "c"
                if align == "r":
                    out += "%s " % (fill * space + cell_line)
                elif align == "c":
                    out += "%s " % (
                        fill // 2 * space + cell_line + (fill // 2 + fill % 2) * space
                    )
                else:
                    out += "%s " % (cell_line + fill * space)
                if length < len(line):
                    out += "%s " % [space, self._char_vert][self._has_vlines()]
            out += "%s\n" % ["", self._char_vert][self._has_border()]
        return out

    def _splitit(self, line, isheader):
        """Split each element of line to fit the column width

        Each element is turned into a list, result of the wrapping of the
        string to the desired width
        """

        line_wrapped = []
        for cell, width in zip(line, self._width):
            array = []
            original_cell = cell
            ansi_keep = []
            for c in cell.split("\n"):
                c = "".join(ansi_keep) + c
                ansi_keep = []
                extra_width = 0
                for a in re.findall(r"\x1b[^m]*m", c):
                    extra_width += len(a)
                    if a == "\x1b[0m":
                        if len(ansi_keep) > 0:
                            ansi_keep.pop()
                    else:
                        ansi_keep.append(a)
                c = c + "\x1b[0m" * len(ansi_keep)
                extra_width += len("\x1b[0m" * len(ansi_keep))
                if type(c) is not str:
                    try:
                        c = str(c, "utf")
                    except UnicodeDecodeError as strerror:
                        sys.stderr.write(
                            "UnicodeDecodeError exception for string '%s': %s\n"
                            % (c, strerror)
                        )
                        c = str(c, "utf", "replace")
                array.extend(textwrap.wrap(c, width + extra_width))
            line_wrapped.append(array)
        max_cell_lines = reduce(max, list(map(len, line_wrapped)))
        for cell, valign in zip(line_wrapped, self._valign):
            if isheader:
                valign = "t"
            if valign == "m":
                missing = max_cell_lines - len(cell)
                cell[:0] = [""] * (missing // 2)
                cell.extend([""] * (missing // 2 + missing % 2))
            elif valign == "b":
                cell[:0] = [""] * (max_cell_lines - len(cell))
            else:
                cell.extend([""] * (max_cell_lines - len(cell)))
        return line_wrapped


if __name__ == "__main__":
    REGION = "us-east-1"
    DISPLAY_LIMIT = 20
    ddb_name = "tabroom_tournaments"

    # Pull a list of the newest DynamoDB entries and save them to a text file to display new tournaments in the website
    ddb_resource = boto3.resource(
        "dynamodb",
        region_name=REGION,
    )
    table = ddb_resource.Table(ddb_name)
    all_items = table.scan()["Items"]
    # Sort all_items (a list of dicts) based on the end_date key's value
    sorted_items = sorted(
        all_items,
        key=lambda x: x["end_date"],
        reverse=True,
    )
    tournaments_with_results = []
    for item in sorted_items:
        if item["prompts_generated"] is False:
            continue
        if len(tournaments_with_results) >= DISPLAY_LIMIT:
            break
        tournaments_with_results.append(
            [item["tourn_id"], item["tourn_name"], item["locality"], item["end_date"]]
        )
    # Generate the table for upload
    table = Texttable()
    table.set_cols_align(["l", "l", "c", "c"])
    table.set_cols_valign(["t", "t", "t", "t"])
    # table.set_max_width(0)
    table.add_rows(
        [["Tournament ID", "Tournament Name", "Locality", "Date"]]
        + tournaments_with_results,
    )
    s3_client = boto3.client("s3")
    s3_client.put_object(
        Body=table.draw(),
        Bucket="tabroomsummary.com",
        Key="recent_tournaments.txt",
    )
