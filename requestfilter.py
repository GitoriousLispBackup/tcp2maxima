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



class RequestFilter:
    """Class filters requests sent to maxima.
    It not only filters, it also sanitizes strings
    """
    def __init__(self):
        # Regular expressions which exclude a request
        self.blacklist = []
        # Regular expressions at least part of the request has to match
        self.whitelist = []
        # Filter functions to modify our requests
        self.filters = []

        self.filters.append(lambda x: x.replace('\n', ''))

    def filter(self, string):
        # TODO: Use regular expressions 

        for fltr in self.filters:
            string = fltr(string)

        return string
