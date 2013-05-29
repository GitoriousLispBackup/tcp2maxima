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

import configparser 
import os

class Config(configparser.ConfigParser):
    """ A module to read the configuration from files """
    def __init__(self):
         configparser.ConfigParser.__init__(self)
         self._load()

    def _load(self):
         # Read the default configuration 
         # if this doesn't exist it's not good.
         self.read_file(open('default.cfg'))

         # read alternative configuration files
         alt_path = ['/etc/tcp2maxima.cfg']
         alt_path.append('/etc/tcp2maximarc')
         alt_path.append(os.path.expanduser('~/.tcp2maxima.cfg'))
         alt_path.append(os.path.expanduser('~/.tcp2maximarc'))
         self.read(alt_path)
