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

import sys
import os 
import pwd
import time
import atexit
import logging
import logging.handlers
from signal import SIGTERM
 
# Get out logger
logger = logging.getLogger("tcp2maxima")

# The standard I/O file descriptors are redirected to /dev/null by default.
if (hasattr(os, "devnull")):
   REDIRECT_TO = os.devnull
else:
   REDIRECT_TO = "/dev/null"


class Daemon:
        """
        A generic daemon class.
       
        Usage: subclass the Daemon class and override the run() method
        """
        def __init__(self, piddir, logdir, user='root'):
                self.logdir = logdir
                self.piddir = piddir
                self.user = user
                self.logfile = None # Will be set later
                self.pidfile = None # Will be set later  
                self._set_security()


        def _set_security(self):
            # Only root is able to swich the user under which the daemon runs.
            if self.user != 'root' and os.geteuid() == 0:
                uid = pwd.getpwnam(self.user).pw_uid
                gid = pwd.getpwnam(self.user).pw_gid
                
                # We need subdirectories owned by the user in order
                # to write the log and the pid file
                self.logdir = os.path.join(self.logdir, 'tcp2maxima/')
                self.piddir = os.path.join(self.piddir, 'tcp2maxima/')
                
                # Make directories
                if not os.path.exists(self.logdir):
                    os.mkdir(self.logdir)
                if not os.path.exists(self.piddir):
                    os.mkdir(self.piddir)
                os.chown(self.logdir, uid, gid)
                os.chown(self.piddir, uid, gid)
                
                # Switch the user and group id
                os.setregid(gid, gid)
                logger.info("Switched to group %d" % gid)
                os.setreuid(uid, uid)
                logger.info("Switched to uid %d" % uid)
            
            self.pidfile = os.path.join(self.piddir, 'tcp2maxima.pid')
                        
                

        def daemonize(self):
                """
                do the UNIX double-fork magic, see Stevens' "Advanced
                Programming in the UNIX Environment" for details (ISBN 0201563177)
                http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
                """
                try:
                        pid = os.fork()
                        if pid > 0:
                                # exit first parent
                                sys.exit(0)
                except OSError as e:
                        sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
                        sys.exit(1)
       
                # decouple from parent environment
                os.chdir("/")
                os.setsid()
                os.umask(0)
       
                # do second fork
                try:
                        pid = os.fork()
                        if pid > 0:
                                # exit from second parent
                                sys.exit(0)
                except OSError as e:
                        sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
                        sys.exit(1)

                # Since we don't have a stdout to log to open anymore
                # we need to set the logger to log to a file.
                # We use a WatchedFileHandler to be able to let logrotate 
                # rotate the log.
                self.logfile = os.path.join(self.logdir, 'tcp2maxima.log')
                logger.info("Logging to %s" % self.logfile)
                handler = logging.handlers.WatchedFileHandler(self.logfile)
                logger.addHandler(handler)
       
                # Close open file descriptors. This is done the way described here:
                # http://code.activestate.com/recipes/278731-creating-a-daemon-the-python-way/
                # Don't blame me if it's wrong, I barely understand what I'm doing...
                # logger.debug("Determine how many file descriptors should be closed.")
                # import resource         # Resource usage information.
                # maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
                #if (maxfd == resource.RLIM_INFINITY):
                #        maxfd = MAXFD
  
                # Iterate through and close all file descriptors.
                #logger.debug("Try to close all file descriptors")
                #for fd in range(0, maxfd):
                #    try:
                #            os.close(fd)
                #    except OSError:
                #            pass

                # This call to open is guaranteed to return the lowest file descriptor,
                # which will be 0 (stdin), since it was closed above.
		
		# TODO This doesn't work!!!!
                logger.debug("Redirect std descriptors to /dev/null")
                os.open(REDIRECT_TO, os.O_RDWR) # standard input (0)

                # Duplicate standard input to standard output and standard error.
                os.dup2(0, 1)                   # standard output (1)
                os.dup2(0, 2)                   # standard error (2)

                # write pidfile
                atexit.register(self.delpid)
                pid = str(os.getpid())
                with open(self.pidfile,'w+') as pf:
                    pf.write("%s\n" % pid)

        def delpid(self):
            os.remove(self.pidfile)
            if self.user != 'root':
                os.rmdir(self.piddir)

        def start(self):
                """
                Start the daemon
                """
                # Check for a pidfile to see if the daemon already runs
                try:
                        pf = open(self.pidfile,'r')
                        pid = int(pf.read().strip())
                        pf.close()
                except IOError:
                        pid = None
       
                if pid:
                        message = "pidfile %s already exist. Daemon already running?\n"
                        sys.stderr.write(message % self.pidfile)
                        sys.exit(1)
               
                # Start the daemon
                self.daemonize()
                self.run()
 
        def stop(self):
                """
                Stop the daemon
                """
                # Get the pid from the pidfile
                try:
                        pf = open(self.pidfile,'r')
                        pid = int(pf.read().strip())
                        pf.close()
                except IOError:
                        pid = None
       
                if not pid:
                        message = "pidfile %s does not exist. Daemon not running?\n"
                        sys.stderr.write(message % self.pidfile)
                        return # not an error in a restart
 
                # Try killing the daemon process       
                try:
                        while 1:
                                os.kill(pid, SIGTERM)
                                time.sleep(0.1)
                except OSError as err:
                        err = str(err)
                        if err.find("No such process") > 0:
                                if os.path.exists(self.pidfile):
                                        os.remove(self.pidfile)
                        else:
                                print(str(err))
                                sys.exit(1)
 
        def restart(self):
                """
                Restart the daemon
                """
                self.stop()
                self.start()
 
        def run(self):
                """
                This class is overridden in tcp2maxima and is used internally
                to start the daemon.
                """
                pass
