from datetime import datetime

import requests
from qtpy.QtCore import QTimer
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QInputDialog

from xicam.core import msg
from xicam.plugins.settingsplugin import ParameterSettingsPlugin
from xicam.gui.static import path

from xicam.Acquire.runengine import get_run_engine


api_base = 'https://experiment-staging.als.lbl.gov/'


class ALSHubSettingsPlugin(ParameterSettingsPlugin):
    """Settings plugin for logging information and parameterization.
    """

    def __init__(self):
        self.query_timer = QTimer()
        self.query_timer.setInterval(int(1e3*10*60))  # 10 minutes
        self.query_timer.timeout.connect(self.check_event)

        user_email, accepted = QInputDialog.getText(None, 'User Email', 'Please enter the email address associated with your ALSHub account.')
        if not accepted:
            user_email = ''

        super(ALSHubSettingsPlugin, self).__init__(
            QIcon(str(path("icons/als.png"))),
            'ALSHub',
            [
                dict(
                    name="Endstation",
                    value='7.0.1.1',
                    type="str",
                    tip='The endstation numeral name (i.e. "7.0.1.1").',
                ),
                dict(
                    name="PI email address",
                    value='',
                    type="str",
                    tip="The email address associated with the PI's ALS Hub email account. This will be associated with all new acquired data.",
                    readonly=True,
                ),
                # Allow users to configure the default log level for the xicam logger's FileHandler
                dict(
                    name="Set PI automatically",
                    value=True,
                    type="bool",
                    tip="When enabled, the PI will be determined automatically using ALS Hub's ESAF database.",
                    # readonly=True,
                ),
                # Allow users to configure the default log level for the xicam logger's StreamHandler
                dict(
                    name="User email address",
                    value=user_email,
                    type="str",
                    tip="Your email address, associated with your ALSHub account.",

                ),
            ],
        )

        self.child('Set PI automatically').sigValueChanged.connect(self.update_readonly)

        self.check_event()

        get_run_engine().subscribe_kwargs_callable(self.to_kwargs)

    def update_readonly(self, param, readonly):
        self.child('PI email address').setOpts(readonly=readonly)
        if readonly:
            self.check_event()

    def apply(self):
        if self["Set PI automatically"]:
            self.query_timer.timeout.emit()
            self.query_timer.start()
        else:
            self.query_timer.stop()
        super(ALSHubSettingsPlugin, self).apply()

    def check_event(self):
        if self["Set PI automatically"]:
            # check for current PI
            PI = self.get_PI()
            if PI:
                PI_email = PI['Email']
            else:
                PI_email = ''

            if PI_email != self["PI email address"]:
                if PI_email:
                    msg.notifyMessage(f'Welcome {PI["Name"]}!')
                self["PI email address"] = PI_email

    def get_PI(self, when: datetime = None):
        try:
            if when is None:
                when = datetime.now()
            url = f"{api_base}{self['Endstation']}?start={when}&stop={when}&tz_id=America%2FLos_Angeles&include_unscheduled=false&api-key=6bdcc7fcb3e55b7e995b27e229e172ac"
            json = requests.get(url).json()
            if not json:
                return None
            return json[0]['PI']

        finally:
            return None

    def to_kwargs(self):
        return {'PI': self["PI email address"], 'PI overridden': not self["Set PI automatically"], 'User': self['User email address']}

    def fromState(self, state):
        del state['children']['User email address']  # Never restore this from state
        super(ALSHubSettingsPlugin, self).fromState(state)