import re

# Constants
# Reply Types
INPUT = "input"
OUTPUT = "output"
LINE = "message"


class ReplyParser:

    def __init__(self):
        # I guess I need this sonn anyway
        self.output_re = re.compile(r"^(\(%o\d+\))( *)(.*)")
        self.input_re = re.compile(r"^\(%i\d+\)")

    def parse_line(self, line):
        """Return the type of a line
        
        Return the constant and the relevant part of the line
        """
        if self.output_re.match(line):
            return OUTPUT, self.output_re(line).group(3)
        elif self.input_re.match(line):
            return INPUT, ""
        else:
            return LINE, line
