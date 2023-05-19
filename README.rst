Enforced vaccination intervals
==============================

This is a plugin for `pretix`_, intended for usage with COVID-19 vaccination scheduling. It allows you to enforce
certain criteria on every booking that is placed:

* Every order must contain bookings for exactly two different dates.

* The first of the two dates must be within **X** days of the booking.

* The second of the two dates must be no earlier than **Y** and no later than **Z** days of the first date.

**This plugin has been written by the pretix team on commission by a client. Since it is specific to a certain
use case of pretix, it is not considered an "official pretix plugin" and therefore not guaranteed to receive updates
with every update of pretix.**

Development setup
-----------------

1. Make sure that you have a working `pretix development setup`_.

2. Clone this repository, eg to ``local/pretix-vaccination-interval``.

3. Activate the virtual environment you use for pretix development.

4. Execute ``pip install -e .`` within this directory to register this application with pretix's plugin registry.

5. Execute ``make`` within this directory to compile translations.

6. Restart your local pretix server. You can now use the plugin from this repository for your events by enabling it in
   the 'plugins' tab in the settings.


License
-------


Copyright 2020 pretix team

Released under the terms of the Apache License 2.0



.. _pretix: https://github.com/pretix/pretix
.. _pretix development setup: https://docs.pretix.eu/en/latest/development/setup.html
