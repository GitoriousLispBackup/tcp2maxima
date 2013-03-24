# This file is part of tcp2maxima.
#
#    Copyright (c) 2013 Beni Keller
#    Distributed under the GNU GPL v3. For full terms see the file gpl.txt.
#
#    tcp2maxima is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    tcp2maxima is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with tcp2maxima.  If not, see <http://www.gnu.org/licenses/>.
#

import re
import logging

# Use the same logger as everywhere else.
logger = logging.getLogger("tcp2maxima")

class ReplyParser:

    def __init__(self, thread_name):
        # Matches strings which are marked as output
        self.output_re = re.compile(r"^(\(%o\d+\))( *)(.*)")
        # Matches input promts which are not followed by a message
        self.input_re = re.compile(r"^\(%i\d+\) $")
        self.thread = thread_name

    def parse(self, string):
        """Return the type of a line
        
        Return the constant and the relevant part of the line
        """
        
        # Get a list of lines
        lines = string.splitlines()
        # Will be set to true if the string ends with a input prompt
        ready = False 
        output = None # A string containing the actual output
        messages = [] # A list containing all messages which are not marked as output
        for line in lines:
            if self.output_re.match(line):
                # TODO: If  I get a empty reply this fails with a exception
                if output:
                    output += "\n"
                    output += self.output_re.match(line).group(3)
                else:
                    output = self.output_re.match(line).group(3)
        
                #except
            elif self.input_re.match(line):
                ready = True
            else:
                messages.append(line)

        self._log_messages(messages)
        return output, ready

    def _log_messages(self, messages):
        for i in messages:
            if i != '':
                logger.debug("Maxima " + str(self.thread) + " message: " + i)

