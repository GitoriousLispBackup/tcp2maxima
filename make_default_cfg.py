# This file can be deleted as soon as the default
# configuration exists.
# I will keep it for now.

import configparser as cp

config = cp.RawConfigParser()

# Main configuration
config.add_section('General')
config.set('General', 'daemon', '0')
config.set('General', 'user', '0')
config.set('General', 'loglevel', 'DEBUG')

# Daemon section
config.add_section('Daemon')
config.set('Daemon', 'pid_dir', '/var/run/')
config.set('Daemon', 'log_dir', '/var/log/')
config.set('Daemon', 'user', 'root')

# Server conf
config.add_section('Server')
config.set('Server', 'address', 'localhost')
config.set('Server', 'port', '9666')

# Maxima conf
config.add_section('Maxima')
config.set('Maxima', 'path',  '/usr/bin/maxima')
config.set('Maxima', 'threads', '3')
config.set('Maxima', 'timeout', '10')
config.set('Maxima', 'init', 'reset()$kill(all)$display2d:false$linel:10000$')


# Writing our configuration file to 'example.cfg'
with open('default.cfg', 'w') as configfile:
    config.write(configfile)
