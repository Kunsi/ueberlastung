#!/usr/bin/python

import time
import smbus2 as smbus
import signal
import sys
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import itertools
import configparser
import os

schlossstatus = False
clubstatus = False
last_clubstatus = 0
stromstatus = False

ampel = 'unknown'


class Relay:

    global bus

    def __init__(self):
        self.DEVICE_ADDRESS = 0x20
        self.DEVICE_REG_MODE1 = 0x06
        self.DEVICE_REG_DATA = 0xff
        bus.write_byte_data(self.DEVICE_ADDRESS, self.DEVICE_REG_MODE1, self.DEVICE_REG_DATA)
        self.state = {
                        "red": False,
                        "yellow": False,
                        "green": False,
                        "power": False
                    }

    def __set_relay__(self, relay, state):
        """ Set the relay state
        :param relay: Relay to set
        :type relay: int
        :param state: Target state of the relay
        :type state: bool
        :return: None
        """
        if relay not in range(0, 3):
            raise IndexError("You are trying to set relay %d" % relay)
        if state:
            self.DEVICE_REG_DATA &= ~(0x1 << relay)
            bus.write_byte_data(self.DEVICE_ADDRESS, self.DEVICE_REG_MODE1, self.DEVICE_REG_DATA)
        else:
            self.DEVICE_REG_DATA |= (0x1 << relay)
            bus.write_byte_data(self.DEVICE_ADDRESS, self.DEVICE_REG_MODE1, self.DEVICE_REG_DATA)

    def strom(self, state):
        """
        :param state: Target state for the power switch
        :type state: bool
        :return: None
        """
        self.__set_relay__(0, state)
        self.state["power"] = state


    def red(self, state):
        """
        :param state: Target state for the red light switch
        :type state: bool
        :return: None
        """
        self.__set_relay__(2, state)
        self.state["red"] = state

    def yellow(self, state):
        """
        :param state: Target state for the yellow light switch
        :type state: bool
        :return: None
        """
        self.__set_relay__(1, state)
        self.state["yellow"] = state

    def green(self, state):
        """
        :param state: Target state for the green light switch
        :type state: bool
        :return: None
        """
        self.__set_relay__(3, state)
        self.state["green"] = state

    def set_trafficlight(self, red=False, yellow=False, green=False):
        """
        Set the trafficlight state
        :param red: State of the red light
        :type red: bool
        :param yellow: State of the yellow light
        :type yellow: bool
        :param green: State of the green light
        :type green: bool
        :return: None
        """
        self.red(red)
        self.yellow(yellow)
        self.green(green)

    def __get_trafficlight_state__(self):
        """
        :return: Colours that are on
        :rtype: str
        """
        relais_state = self.state
        light_state = ""
        for colour in relais_state.keys():
            if light_state:
                light_state += "-"
            if relais_state[colour]:
                light_state += colour

        if light_state == "":
            light_state = "Undefined"

        return light_state

    def __str__(self):
        self.__get_trafficlight_state__()


def main():
    path = os.path.dirname(os.path.realpath(__file__))

    # read config
    config = configparser.ConfigParser()
    config['mqtt'] = {'host': 'localhost', 'port': 1883, 'auth': 'no'}
    config.read(path + '/configuration.ini')
    
    # init relay
    bus = smbus.SMBus(1)
    relay = Relay()

    # catch SIGINT
    def endProcess(signalnum=None, handler=None):
        relay.strom(True)
        relay.set_trafficlight(red=True, green=True)

        try:
            client.loop_stop()
        finally:
            sys.exit()
    
    signal.signal(signal.SIGINT, endProcess)

    # connect to MQTT
    client = mqtt.Client()
    if config.getboolean('mqtt', 'auth'):
        client.username_pw_set(config.get('mqtt', 'user'), config.get('mqtt', 'password'))

    client.connect(config.get('mqtt', 'host'), config.getint('mqtt', 'port'), 60)
    client.loop_start()
    
    # setup GPIO pins
    #
    # pin 7 (GPIO  4): clubstatus, high == off, low == on
    # pin 11 (GPIO 17: state of lock, high == locked, low == unlocked
    GPIO.setmode(GPIO.BOARD) 
    GPIO.setup(7, GPIO.IN)
    GPIO.setup(11, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    
    last_state = None

    # loop forever
    for i in itertools.count():
        time.sleep(1)
        
        # Clubstatus
        state = not bool(GPIO.input(7))

        if state != last_state or i % 10 == 0:
            client.publish("/public/eden/clubstatus", int(state))
        last_state = state

        if state:
            last_clubstatus = int(time.time())

        clubstatus = state
        
        # Schloss
        schlossstatus = bool(GPIO.input(11))

        # Strom
        if last_clubstatus > (int(time.time())-20) and not stromstatus:
            relay.strom(True)
            stromstatus = True

        if last_clubstatus < (int(time.time())-20) and stromstatus:
            relay.strom(False)
            stromstatus = False

        # Ampel
        
        # Club ist offen, Schloss ist offen -> Gruen
        if clubstatus and not schlossstatus and ampel != 'green':
            ampel = relay.set_trafficlight(green=True)

        # Club ist zu, Schloss ist offen -> Gelb
        elif not clubstatus and not schlossstatus and ampel != 'yellow':
            ampel = relay.set_trafficlight(yellow=True)

        # Club ist offen, Schloss ist zu -> Gelb-Rot
        elif clubstatus and schlossstatus and ampel != 'red-yellow':
            ampel = relay.set_trafficlight(red=True, yellow=True)

        # everything else -> Rot
        elif not clubstatus and schlossstatus and ampel != 'red':
            ampel = relay.set_trafficlight(red=True)

        # print log
        print(time.strftime("%Y-%m-%d %H:%M:%S")
              + " | Club: " + str(clubstatus)
              + " - Schloss: " + str(schlossstatus)
              + " - Strom: " + str(stromstatus)
              + " - Ampel: " + ampel)

if __name__ == "__main__":
    main()

#EOF