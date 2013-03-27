# This file can be deleted as soon as the default
# configuration exists.
# I will keep it for now.

import configparser as cp

config = cp.RawConfigParser()

# Logging
config.add_section('Logging')
config.set('Logging', 'level', 'DEBUG')

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
