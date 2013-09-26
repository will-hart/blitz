blitz.communications
====================

.. automodule:: blitz.communications

The Communications module provides a variety of IO operations for TCP, serial, I2C for both the client and server applications.

 - :mod:`blitz.communications.boards` provides BoardManager and ExpansionBoard classes for decoding serial messages on the client
 - :mod:`blitz.communications.client_states` provides the states for the client TcpStateMachine
 - :mod:`blitz.communications.rs232` provides a SerialManager for managing connections with expansion boards from the server
 - :mod:`blitz.communications.server_states` provides the states for the server TcpStateMachine
 - :mod:`blitz.communications.signals` provides signals that are transmitted between modules
 - :mod:`blitz.communications.tcp` provides TCP communication classes and a StateMachine for comms between PC and logger

-------------------

.. toctree::
   :maxdepth: 2

   blitz_communications_boards
   blitz_communications_client_states
   blitz_communications_rs232
   blitz_communications_server_states
   blitz_communications_signals
   blitz_communications_tcp
