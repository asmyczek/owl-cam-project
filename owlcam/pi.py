# -*- coding: utf-8 -*-

"""Raspberry Pi controller

This module is only included if OWLCAM_ENV=prod is set
"""
from gpiozero import LED, CPUTemperature
from time import sleep
import logging
from owlcam.utils import Switch

# Switch hash map
Switches = {
    Switch.LIGHT: LED(4),
    Switch.IR_LIGHT: LED(5),
    Switch.FAN: LED(6)
}

CPUTemperature = CPUTemperature()


def cleanup_pi() -> None:
    """Cleanup on server shutdown

    Turn lights and fan off.
    :return: None
    """
    logging.info('Cleaning up GPIO')
    Switches[Switch.LIGHT].close()
    Switches[Switch.IR_LIGHT].close()
    Switches[Switch.FAN].close()


def set_pi_switch_state(switch: Switch, state: bool) -> bool:
    """ On/off for lights or fan

    :param switch: Switch for light, ir light or fan
    :param state: bool for on/off
    :return: new state from board status
    """
    if state:
        Switches[switch].on()
    else:
        Switches[switch].off()
    sleep(0.1)
    return Switches[switch].is_lit


def pi_temperature() -> float:
    """Return current CPU temperature

    :return: float - current CPU temperature
    """
    return CPUTemperature.temperature
