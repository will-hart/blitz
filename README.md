Blitz GUI 0.2.1
===============

Introduction
------------

The Blitz GUI is an open source data acquisition solution. It is designed to be used with boards implementing the Arduino library that you can find at [the Blitz Expansion github repository](https://github.com/will-hart/BlitzExpansion).  

The source code for this repository is available from [https://github.com/will-hart/blitz](https://github.com/will-hart/blitz)

What is Blitz?
--------------

Blitz is a project that is being completed for my final dissertation on my engineering degree. It is a highly modular and flexible data acquisition system that is currently being used to gather pressure data and move an actuator in our wind tunnel. It has been designed so that it is very easy to set up "expansion boards" which can read for a wide variety of sensor types, allowing different types of data acquisition system to be used. 

Blitz was originally conceived as a standalone data logger that can be run on anything that can run Python. It has been tested on a RaspberryPi, but also on a laptop running Windows 7.  The initial prototypes used a web based UI so that the data logger could be controlled through any device with a web browser, such as a mobile phone.  Whilst the core of this UI is there, it needs to be rewritten using websockets to be truly functional.  The current UI being developed is a Python / PySide (Qt) UI.  

It is written mostly in Python, the programming language of the gods. Blitz is named after an Kelpie (an Australian dog) called Mister Blitz. 

What is the status
------------------

Blitz has been under development for the better part of a year.  It is in a fully functional state and is frequently being improved and worked on. There are some known issues which are in the github issue tracker, as well as some others that are on the long term to-do list.

What is the short term roadmap
------------------------------

The short term focus is on getting stability and improving usability. A list of current issues is on the github issue tracker.

What is the long term roadmap
-----------------------------

EDIT: There isn't one :)

~~Eventually I would like to implement some of these features:~~

 - ~~Build "frozen" (e.g. *.exe) versions of the applications for people who don't want to install Python~~
 - ~~Implement an improved plugin system to make it easier to extend the supported data acquisition sources~~
 - ~~Re-implement the web based GUI for control from mobile devices over wireless~~
 - ~~Implement data "filters" for the desktop UI (such as FFT, moving averages, scale and offsets) that can be applied in various orders and combinations~~

Feedback
--------

Feedback or contributions are more than welcome, you can get in touch @wlhart on twitter or via my website linked above.

License
-------

This software is provided under the AGPLv3 license.  For the full text of the license, look at the LICENSE file.

 > Usually for open source software I prefer a less restrictive license - something like the MIT license.  However in
 > this case I would like to ensure that if anybody makes changes or improvements to the Blitz software then those
 > changes should be available to everybody who uses it!


Change Log
----------

**0.2.1**

Remove deprecated web UI to separate branch

**0.2**

Too many changes to list individually... some highlights are:

- Numerous bug fixes and API documentation improvements
- Fully functional expansion boards
- Vastly improved desktop UI which allows control of expansion boards and server

**0.1**

Initial version
