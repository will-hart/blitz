blitz.io
========

.. automodule:: blitz.io

The IO module provides a variety of IO operations for TCP, serial, I2C for both the client and server applications.

 - :mod:`blitz.io.boards` provides BoardManager and ExpansionBoard classes for decoding serial messages on the client
 - :mod:`blitz.io.client_states` provides the states for the client TcpStateMachine
 - :mod:`blitz.io.serial` provides a SerialManager for managing connections with expansion boards from the server
 - :mod:`blitz.io.server_states` provides the states for the server TcpStateMachine
 - :mod:`blitz.io.signals` provides signals that are transmitted between modules
 - :mod:`blitz.io.tcp` provides TCP communication classes and a StateMachine for comms between PC and logger

-------------------

.. toctree::
   :maxdepth: 2

   blitz_io_boards
   blitz_io_client_states
   blitz_io_serial
   blitz_io_server_states
   blitz_io_signals
   blitz_io_tcp
