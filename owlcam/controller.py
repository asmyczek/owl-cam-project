# -*- coding: utf-8 -*-

from threading import Thread, Event
from time import sleep, time
import logging
from owlcam.utils import Switch, in_production


# Import pi module only if running on a Raspberry Pi,
# otherwise mock functions for development
if in_production():
    from owlcam.pi import set_pi_switch_state, pi_temperature
    TIME_OUT_TIMER = 60.0
else:
    TIME_OUT_TIMER = 3.0

    def pi_temperature() -> float:
        return 45.0

    def set_pi_switch_state(switch: Switch, state: bool) -> bool:
        return state


DAY_ZERO = 0.0              # Default timer not set value
FAN_ON_TEMPERATURE = 70.0   # Temperature at what fan has to be switched on
FAN_OFF_TEMPERATURE = 66.0  # Temperature at what fan will be switched off


class Timer(Thread):
    """Time backend thread for automated control of lights and fan.
    """

    def __init__(self, controller: 'Controller'):
        Thread.__init__(self, name='Controller Timer')
        self.__controller = controller
        self.__switch_time = {Switch.LIGHT: DAY_ZERO,
                              Switch.IR_LIGHT: DAY_ZERO,
                              Switch.FAN: DAY_ZERO}
        self.__stop = Event()

    def stop(self) -> None:
        """ Stop execution thread called on server shutdown.

        Blocking call till timer thread stopped.
        :return: None
        """
        if not self.__stop.is_set():
            self.__stop.set()
        self.join()

    def __update_light_timer(self, light: Switch) -> None:
        if self.__controller.is_switch_on(light):
            if self.__switch_time[light] == 0.0:
                self.__switch_time[light] = time()
            elif time() - self.__switch_time[light] > TIME_OUT_TIMER:
                self.__controller.set_switch_state(light, False)
                self.__switch_time[light] = 0.0

    def run(self) -> None:
        """Main thread run function
        Triggers automation routing every second till stop() is called.

        :return: None
        """
        while not self.__stop.is_set():
            # Update lights
            self.__update_light_timer(Switch.LIGHT)
            self.__update_light_timer(Switch.IR_LIGHT)

            # Fan temperature based controls
            if self.__controller.is_switch_on(Switch.FAN):
                if self.__switch_time[Switch.FAN] == 0.0:
                    self.__switch_time[Switch.FAN] = time()
                elif (time() - self.__switch_time[Switch.FAN]) > TIME_OUT_TIMER and\
                     pi_temperature() < FAN_OFF_TEMPERATURE:
                        self.__controller.set_switch_state(Switch.FAN, False)
                        self.__switch_time[Switch.FAN] = 0.0
            elif pi_temperature() > FAN_ON_TEMPERATURE:
                self.__controller.set_switch_state(Switch.FAN, True)

            sleep(1)


class Controller(object):
    """Main application controller to activate lights and manage fan.
    """

    def __init__(self):
        self.__switch_on = {Switch.LIGHT: False,
                            Switch.IR_LIGHT: False,
                            Switch.FAN: False}
        self.__timer = Timer(self)
        self.__timer.start()

    def set_switch_state(self, switch: Switch, state: bool) -> bool:
        """Main on/off method for lights and fan

        :param switch: Switch for light, ir light or fan
        :param state: bool for on/off
        :return: new switch state, True of False
        """
        logging.debug("Setting switch {0} to {1}".format(switch.name, state))
        self.__switch_on[switch] = set_pi_switch_state(switch, state)
        return self.__switch_on[switch]

    def is_switch_on(self, switch: Switch) -> bool:
        """Light of fan status

        :param switch: Switch for light, ir light or fan
        :return: bool for on/off
        """
        return self.__switch_on[switch]

    def toggle_switch(self, switch: Switch) -> bool:
        """Helper function to toggle current light or fan status

        :param switch: Switch for light, ir light or fan
        :return: bool, new on/off status
        """
        logging.debug('Toggling switch {0}'.format(switch.name))
        return self.set_switch_state(switch, not self.__switch_on[switch])

    def stop(self) -> None:
        """Stop timer thread called on server exit

        Turns off all switches before exit
        :return: None
        """
        for s in Switch:
            self.set_switch_state(s, False)
        self.__timer.stop()


