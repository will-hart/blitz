__author__ = 'Will Hart'

import datetime
import logging
import time
import unittest

import sqlalchemy
from sqlalchemy import orm

from blitz.data.fixtures import *
from blitz.data.models import *
from blitz.io.boards import *
from blitz.io.client_states import *
from blitz.io.database import DatabaseClient
from blitz.io.server_states import *
from blitz.io.tcp import TcpServer

# set up logging globally for tests
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(asctime)s %(levelname)-10s %(threadName)-10s]:    %(message)s')
ch.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.addHandler(ch)


class TestBlitzUtilities(unittest.TestCase):
    def test_date_formatting(self):
        """Test a date is correctly formatted and output to string"""
        expected = "14-07-2011 15:05:27.517"
        initial = datetime.datetime(2011, 07, 14, 15, 05, 27, 517000)
        parsed = to_blitz_date(initial)

        assert parsed == expected


class TestDatabaseClientSetup(unittest.TestCase):

    def setUp(self):
        self.db = DatabaseClient()  # pass true to DatabaseClient() to get verbose logging from SQLAlchemy

    def test_variables_initialised(self):
        """
        Test that when we initialise the client a database connection is created
        """
        assert type(self.db._database) is sqlalchemy.engine.base.Engine
        assert type(self.db._session) is orm.session.sessionmaker

    def test_database_created(self):
        """
        Test that we can create a database using the built in models
        """

        # call the function which creates the table structure
        self.db.create_tables()

        # check we have the right number of tables and the correct table names
        assert(set(SQL_BASE.metadata.tables.keys()) == {"cache", "reading", "category", "config", "session"})

    def test_load_fixtures(self):

        self.db.create_tables(True)
        self.db.load_fixtures()

        assert len(self.db.all(Cache)) == len(CACHE_FIXTURES)
        assert len(self.db.all(Category)) == len(CATEGORY_FIXTURES)
        assert len(self.db.all(Config)) == len(CONFIG_FIXTURES)
        assert len(self.db.all(Reading)) == len(READING_FIXTURES)
        assert len(self.db.all(Session)) == len(SESSION_FIXTURES)

    def test_cache_model_serialisation(self):
        fixture = CACHE_FIXTURES[0]
        r = Cache(**fixture)
        r_dict = r.to_dict()

        expected = fixture.copy()
        expected['id'] = None
        expected['timeLogged'] = to_blitz_date(fixture['timeLogged'])

        for k in expected.keys():
            assert k in r_dict.keys()
            assert r_dict[k] == expected[k]

        assert str(r) == json.dumps(r_dict)

    def test_category_model_serialisation(self):
        fixture = CATEGORY_FIXTURES[0]
        r = Category(**fixture)
        r_dict = r.to_dict()

        expected = fixture.copy()
        expected['id'] = None

        for k in expected.keys():
            assert k in r_dict.keys()
            assert r_dict[k] == expected[k]

        assert str(r) == json.dumps(r_dict)

    def test_config_model_serialisation(self):
        fixture = CONFIG_FIXTURES[0]
        r = Config(**fixture)
        r_dict = r.to_dict()

        expected = fixture.copy()
        expected['id'] = None

        for k in expected.keys():
            assert k in r_dict.keys()
            assert r_dict[k] == expected[k]

        assert str(r) == json.dumps(r_dict)

    def test_reading_model_serialisation(self):
        fixture = READING_FIXTURES[0]
        r = Reading(**fixture)
        r_dict = r.to_dict()

        expected = fixture.copy()
        expected['id'] = None
        expected['timeLogged'] = to_blitz_date(fixture['timeLogged'])

        for k in expected.keys():
            assert k in r_dict.keys()
            assert r_dict[k] == expected[k]

        assert str(r) == json.dumps(r_dict)

    def test_session_model_serialisation(self):
        fixture = SESSION_FIXTURES[0]
        r = Session(**fixture)
        r_dict = r.to_dict()

        expected = fixture.copy()
        expected['id'] = None
        expected['timeStarted'] = to_blitz_date(fixture['timeStarted'])
        expected['timeStopped'] = to_blitz_date(fixture['timeStopped'])

        for k in expected.keys():
            assert k in r_dict.keys()
            assert r_dict[k] == expected[k]

        assert str(r) == json.dumps(r_dict)


class TestBasicDatabaseOperations(unittest.TestCase):
    """
    Test retrieve operations on the database
    """

    def setUp(self):

        # create a database
        self.db = DatabaseClient()  # pass true to DatabaseClient() to get verbose logging from SQLAlchemy
        self.db.create_tables()

        # add the fixtures
        self.db.add_many(generate_objects(Category, CATEGORY_FIXTURES))
        self.db.add_many(generate_objects(Config, CONFIG_FIXTURES))
        self.db.add_many(generate_objects(Reading, READING_FIXTURES))
        self.db.add_many(generate_objects(Session, SESSION_FIXTURES))

    def test_add_one_record(self):
        c = Cache(timeLogged=datetime.datetime.now(), categoryId=1, value=3)
        res = self.db.add(c)

        assert type(res) == Cache
        assert res.id == 1

    def test_find_all_readings(self):
        res = self.db.all(Reading)
        assert(len(res) == len(READING_FIXTURES))
        for x in res:
            assert type(x) == Reading

    def test_find_one_reading(self):
        res = self.db.get(Reading, {"id": 1})
        assert(type(res) == Reading)
        assert(res.id == 1)

    def test_filter_readings(self):
        res = self.db.find(Reading, {"categoryId": 2})
        assert(res.count() == 2)
        assert(res[0].id in [3, 4])
        assert(res[1].id in [3, 4])
        for x in res:
            assert type(x) == Reading

    def test_find_all_categories(self):
        res = self.db.all(Category)
        assert len(res) == len(CATEGORY_FIXTURES)
        for x in res:
            assert type(x) == Category

    def test_find_one_category(self):
        res = self.db.get(Category, {"variableName": "Accelerator"})
        assert (type(res) == Category)
        assert (res.variableName == "Accelerator")

    def test_find_all_sessions(self):
        res = self.db.all(Session)
        assert len(res) == len(SESSION_FIXTURES)
        for x in res:
            assert type(x) == Session

    def test_find_one_session(self):
        res = self.db.get(Session, {"available": True})
        assert (type(res) == Session)
        assert (res.numberOfReadings == 2)

    def test_filter_sessions(self):
        res = self.db.find(Session, {"available": False})
        assert (res.count() == 1)
        assert (res[0].id == 2)
        for x in res:
            assert type(x) == Session

    def test_find_all_configs(self):
        res = self.db.all(Config)
        assert len(res) == len(CONFIG_FIXTURES)
        for x in res:
            assert type(x) == Config

    def test_find_one_config(self):
        res = self.db.get(Config, {"key": "loggerPort"})
        assert (type(res) == Config)
        assert (res.value == "8989")

    def test_get_session_by_id(self):
        res = self.db.get_by_id(Session, 2)
        assert(type(res) == Session)
        assert(res.id == 2)

    def test_empty_get_query_result(self):
        """Should return None"""
        res = self.db.get_by_id(Session, 100)
        assert res is None

        res = self.db.get(Session, {"id": 100})
        assert res is None

    def test_empty_find_query_result(self):
        res = self.db.find(Reading, {"sessionId": 4000})
        assert res.count() == 0


class TestDatabaseHelpers(unittest.TestCase):
    def setUp(self):
        # create a database
        self.db = DatabaseClient()  # pass True to DatabaseClient() to get verbose logging from SQLAlchemy
        self.db.create_tables(True)

        # add the fixtures
        self.db.add_many(generate_objects(Cache, CACHE_FIXTURES))
        self.db.add_many(generate_objects(Category, CATEGORY_FIXTURES))
        self.db.add_many(generate_objects(Config, CONFIG_FIXTURES))
        self.db.add_many(generate_objects(Reading, READING_FIXTURES))
        self.db.add_many(generate_objects(Session, SESSION_FIXTURES))

    def test_get_categories_for_session(self):
        """
        Test retrieving categories for a specific session
        """
        res = self.db.get_session_variables(1)

        assert len(res) == 2
        assert res[0].variableName in ["Accelerator", "Brake"]
        assert res[1].variableName in ["Accelerator", "Brake"]
        assert res[0].variableName != res[1].variableName

    def test_get_categories_for_cache(self):
        """
        Test retrieving categories for a specific session
        """
        res = self.db.get_cache_variables()

        assert len(res) == 2
        assert res[0].variableName in ["Accelerator", "Brake"]
        assert res[1].variableName in ["Accelerator", "Brake"]
        assert res[0].variableName != res[1].variableName

    def test_get_readings_for_session(self):
        """
        Test retrieving readings for a given session ID
        """

        res1 = self.db.get_session_readings(2)
        assert len(res1) == 0

        res2 = self.db.get_session_readings(1)
        assert len(res2) == 4
        for x in res2:
            assert type(x) is Reading

    def test_get_cache_recent_50(self):
        """
        Test retrieving the most recent (max 50) cached variables
        """
        res = self.db.get_cache()

        # check the right number of records was returned
        assert len(res) == 4

        # check the right type of record was returned
        for x in res:
                assert type(x) == Cache

    def test_get_cache_since(self):
        """
        Test retrieving cached variables since a given time
        """
        print time2
        time2_timestamp = time.mktime(time2.timetuple()) + (float(time2.microsecond) / 1000000)
        res = self.db.get_cache(time2_timestamp)

        # check lengths
        assert len(res) == 3

        # check the types are correct
        # and double check all the dates are in range
        for x in res:
                assert type(x) == Cache
                assert x.timeLogged >= time2

    def test_config_get(self):
        res = self.db.get_config("loggerPort")
        assert res.value == "8989"

    def test_config_set(self):
        """
        Tests setting a new config item and ensure when an item
        is updated the length doesn't increase
        """
        configs = self.db.all(Config)
        assert len(configs) == len(CONFIG_FIXTURES)

        self.db.set_config("a new key", "a val")
        configs = self.db.all(Config)
        assert len(configs) == len(CONFIG_FIXTURES) + 1

        self.db.set_config("a new key", "another val")
        configs = self.db.all(Config)
        assert len(configs) == len(CONFIG_FIXTURES) + 1

    def test_get_or_create_category(self):
        id1 = self.db.get_or_create_category("fourth")
        assert id1 == 4

        id2 = self.db.get_or_create_category("fourth")
        assert id1 == id2

    def test_add_reading(self):
        session_id = 1
        timeLogged = datetime.datetime.now()
        category_id = 1
        value = 5.2
        reading = self.db.add_reading(session_id, timeLogged, category_id, value)

        result = self.db.get_by_id(Reading, reading.id)

        assert result.sessionId == session_id
        assert result.timeLogged == timeLogged
        assert result.categoryId == category_id
        assert result.value == str(value)

    def test_add_cache(self):
        timeLogged = datetime.datetime.now()
        category_id = 1
        value = 5.2
        cache = self.db.add_cache(timeLogged, category_id, value)

        result = self.db.get_by_id(Cache, cache.id)

        assert result.timeLogged == timeLogged
        assert result.categoryId == category_id
        assert result.value == str(value)

#
# class TestWebApi(unittest.TestCase):
#
#     #def __init__(self, arg):
#     #    """
#     #     Set up the application
#     #     """
#     #
#     #     # create an application and wait for it to start up
#     #     self.app = Application()
#     #     self.app.run()
#     #     time.sleep(2)
#     #
#     #     # call the base class init
#     #     super(TestWebApi, self).__init__(arg)
#     #
#     #def get_app(self):
#     #    return self.app
#
#     def test_get_sessions(self):
#         assert False
#
#     def test_get_session(self):
#         assert False
#
#     def test_get_config(self):
#         assert False
#
#     def test_post_config(self):
#         assert False
#
#     def test_download(self):
#         assert False
#
#     def test_cache(self):
#         assert False
#
#     def test_cache_since(self):
#         assert False


class TestTcpClientStateMachine(unittest.TestCase):
    """
    Tests that the TCP state machine on the client side enters and exits the
    correct states
    """

    # set up a TCP server
    tcpServer = None

    # set up a tcp client
    tcp = None

    def setUp(self):
        # simulate starting a new connection by entering the init state
        self.tcpServer = TcpServer(8999)
        self.tcp = TcpClientMock("127.0.0.1", 8999)

    def tearDown(self):
        self.tcp.disconnect()
        self.tcpServer.shutdown()

    def test_enter_init_state_on_load(self):
        assert type(self.tcp.current_state) == ClientInitState

    def test_enter_logging_state_after_init_ack(self):
        self.tcp.process_message("ACK")
        assert type(self.tcp.current_state) == ClientLoggingState

    def test_enter_idle_state_from_logging_stop(self):
        self.tcp.process_message("ACK")  # enter logging state
        assert type(self.tcp.current_state) == ClientLoggingState

        self.tcp.request_stop()  # enter stopping state
        assert type(self.tcp.current_state) == ClientStoppingState

        self.tcp.process_message("ACK")  # enter idle state
        assert type(self.tcp.current_state) == ClientIdleState

    def test_enter_idle_state_after_init_nack(self):
        self.tcp.process_message("NACK")
        assert type(self.tcp.current_state) == ClientIdleState

    def test_enter_logging_state_after_idle_start(self):
        self.tcp.process_message("NACK")  # enter idle state
        assert type(self.tcp.current_state) == ClientIdleState

        self.tcp.request_start()
        assert type(self.tcp.current_state) == ClientStartingState

        self.tcp.process_message("ACK")
        assert type(self.tcp.current_state) == ClientLoggingState

    def test_enter_downloading_state_from_idle(self):
        self.tcp.process_message("NACK")  # enter idle state
        assert type(self.tcp.current_state) == ClientIdleState

        self.tcp.request_download(1)
        assert type(self.tcp.current_state) == ClientDownloadingState

        self.tcp.process_message("asdfasdf")
        self.tcp.process_message("12345678")
        self.tcp.process_message("87654321")
        assert type(self.tcp.current_state) == ClientDownloadingState

        self.tcp.process_message("NACK")
        assert type(self.tcp.current_state) == ClientIdleState

    def test_receive_insession_on_start_during_logging(self):
        self.tcp.process_message("ACK")  # enter idle state
        assert type(self.tcp.current_state) == ClientLoggingState

        self.tcp.request_start()
        assert type(self.tcp.current_state) == ClientLoggingState


class TestTcpServerStateMachine(unittest.TestCase):
    """
    Tests whether the state machine for the TcpServer follows the expected process
    """

    def setUp(self):
        self.tcp = TcpServer(8990)

    def tearDown(self):
        if self.tcp:
            self.tcp.shutdown()

    def test_validate_valid_commands(self):
        """test that all valid commands return ERROR 1"""
        valid_commands = ["START", "STOP", "DOWNLOAD 1", "STATUS", "BOARD 17 MOVE1", "LOGGING"]
        for cmd in valid_commands:
            assert validate_command(cmd, VALID_SERVER_COMMANDS) == "ERROR 1"

    def test_validate_invalid_commands(self):
        """tests that invalid commands return ERROR 2"""
        invalid_commands = ["ASDF", "STAP", "DL 1"]
        for cmd in invalid_commands:
            assert validate_command(cmd, VALID_SERVER_COMMANDS) == "ERROR 2"

    def test_enter_idle_state_on_load(self):
        assert type(self.tcp.current_state) == ServerIdleState
        self.tcp.shutdown()
        assert type(self.tcp.current_state) == ServerClosedState

        # check that trying to send raises and exception
        with self.assertRaises(Exception):
            self.tcp.process_message("ANY")

        with self.assertRaises(Exception):
            self.tcp.send_message("ANY")

        self.tcp = None  # avoid duplicate shutdown calls on self.tearDown

    def test_enter_logging_state_on_start(self):
        assert type(self.tcp.current_state) == ServerIdleState

    def test_enter_logging_state_on_idle_start(self):
        assert type(self.tcp.current_state) == ServerIdleState
        self.tcp.process_message("START")
        assert type(self.tcp.current_state) == ServerLoggingState

    def test_stay_in_idle_when_stop_or_status(self):
        assert type(self.tcp.current_state) == ServerIdleState
        self.tcp.process_message("STOP")
        assert type(self.tcp.current_state) == ServerIdleState
        self.tcp.process_message("STATUS")
        assert type(self.tcp.current_state) == ServerIdleState

    def test_stay_in_idle_on_unknown_command(self):
        assert type(self.tcp.current_state) == ServerIdleState
        self.tcp.process_message("ASDF")
        assert type(self.tcp.current_state) == ServerIdleState

    def test_stop_logging_on_stop_command(self):
        assert type(self.tcp.current_state) == ServerIdleState
        self.tcp.process_message("START")
        assert type(self.tcp.current_state) == ServerLoggingState
        self.tcp.process_message("STOP")
        assert type(self.tcp.current_state) == ServerIdleState

    def test_stay_in_logging_on_status(self):
        assert type(self.tcp.current_state) == ServerIdleState
        self.tcp.process_message("START")
        assert type(self.tcp.current_state) == ServerLoggingState
        self.tcp.process_message("STATUS")
        assert type(self.tcp.current_state) == ServerLoggingState

    def test_in_logging_on_unknown_command(self):
        assert type(self.tcp.current_state) == ServerIdleState
        self.tcp.process_message("START")
        assert type(self.tcp.current_state) == ServerLoggingState
        self.tcp.process_message("ASDF")
        assert type(self.tcp.current_state) == ServerLoggingState

    def test_download_lifecycle(self):
        assert type(self.tcp.current_state) == ServerIdleState

        # enter downloading state
        self.tcp.process_message("DOWNLOAD 1")
        assert type(self.tcp.current_state) == ServerDownloadingState

        # Stay in idle state on unknown command
        self.tcp.process_message("ASDF")
        assert type(self.tcp.current_state) == ServerDownloadingState

        # leave when download complete
        self.tcp.download_complete()
        assert type(self.tcp.current_state) == ServerIdleState


class TestExpansionBoardParsing(unittest.TestCase):
    """
    A test case to ensure that expansion boards are initalising correctly
    and are parsing data correctly
    """

    def test_expansion_board_parses_valid_message(self):
        message = "e3282f19572076ac"  # random message
        board = ExpansionBoardMock()
        board.parse_message(message)

        result = board.get_variables()

        assert result['full_payload'] == 1461745324L
        assert result['flag_one'] is False
        assert result['flag_two'] is True
        assert result['flag_three'] is False
        assert result['flag_four'] is False
        assert result['flag_five'] is False
        assert result['variable_a'] == 22304
        assert result['variable_b'] == 30380

        assert board['type'] == 1
        assert board['timestamp'] == 12057

    def test_blitz_basic_expansion_board(self):
        board = BlitzBasicExpansionBoard()
        board.parse_message("05755555cccccccc")
        result = board.get_variables()

        expected = {
            "adc_channel_one": 819,
            "adc_channel_two": 204,
            "adc_channel_three": 819
        }

        # check get variables
        assert set(result.keys()) == set(expected.keys())
        for k in expected.keys():
            assert result[k] == expected[k]

        # check other parsed variables
        assert board['id'] == 1
        assert board['sender'] == 5
        assert board['type'] == 3
        assert board['flags'] == [True, False, True, False, True]
        assert board['timestamp'] == 21845

    def test_short_length_raises_exception(self):
        board = BlitzBasicExpansionBoard()
        with(self.assertRaises(Exception)):
            board.parse_message("cc")


class TestBoardManager(unittest.TestCase):

    def setUp(self):
        self.data = DatabaseClient()
        self.bm = BoardManager(self.data)

    def test_registering_boards(self):
        # the BlitzBasic board should be registered
        print self.bm.boards
        assert False


