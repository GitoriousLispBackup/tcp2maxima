tcp2maxima - TCP interface for Maxima
=====================================================

DISCLAIMER: This is not usable software yet!!

This is a project to implement a TCP server in Python,
which receives queries to Maxima instances and sends
them on to different instances of Maxima.

It's intended to be used with one line queries. The 
Maxima instances are controlled by different threads
and are reset after every query. 

Maxima is a open source Computer Algebra System written
in Common Lisp. More information can be found here:

http://maxima.sourceforge.net/

This software is distributed under the GNU GPL v3. For 
full terms see the file gpl.txt.