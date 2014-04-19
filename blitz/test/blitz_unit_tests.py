__author__ = 'Will Hart'

import unittest
import datetime
from nose.tools import raises
import sqlalchemy
from sqlalchemy import orm

from blitz.data import DataContainer, BaseDataTransform
import blitz.data.transforms as data_transforms
from blitz.communications.boards import *
from blitz.communications.client_states import *
from blitz.data.database import *
from blitz.communications.server_states import *
from blitz.utilities import blitz_timestamp, to_blitz_date

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
        self.db = DatabaseClient(path=":memory:")

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
        assert set(SQL_BASE.metadata.tables.keys()) == {"cache", "reading", "category", "config", "session",
                                                        "notifications"}

    def test_load_test_fixtures(self):

        self.db.create_tables(True)
        self.db.load_fixtures(testing=True)

        assert len(self.db.all(Cache)) == len(CACHE_FIXTURES)
        assert len(self.db.all(Category)) == len(CATEGORY_FIXTURES)
        assert len(self.db.all(Config)) == len(CONFIG_FIXTURES)
        assert len(self.db.all(Reading)) == len(READING_FIXTURES)
        assert len(self.db.all(Session)) == len(SESSION_FIXTURES)
        assert len(self.db.all(Notification)) == 0

    def test_load_production_fixtures(self):

        self.db.create_tables(True)
        self.db.load_fixtures()

        assert len(self.db.all(Cache)) == 0
        assert len(self.db.all(Category)) == 0
        assert len(self.db.all(Config)) == len(CONFIG_FIXTURES)
        assert len(self.db.all(Reading)) == 0
        assert len(self.db.all(Session)) == 0
        assert len(self.db.all(Notification)) == 0

    def test_cache_model_serialisation(self):
        fixture = CACHE_FIXTURES[0]
        r = Cache(**fixture)
        r_dict = r.to_dict()

        expected = fixture.copy()
        expected['id'] = None
        expected['timeLogged'] = fixture['timeLogged']

        for k in expected.keys():
            assert k in r_dict.keys(), "Couldn't find %s in the dictionary [%s]" % \
                                       (k, ','.join([x for x in r_dict.keys()]))
            assert r_dict[k] == expected[k], "Expected %s but found %s" % (r_dict[k], expected[k])

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
        expected['timeLogged'] = fixture['timeLogged']

        for k in expected.keys():
            assert k in r_dict.keys(), "Couldn't find %s in the dictionary [%s]" % \
                                       (k, ','.join([x for x in r_dict.keys()]))
            assert r_dict[k] == expected[k], "Expected %s but found %s" % (r_dict[k], expected[k])

        assert str(r) == json.dumps(r_dict)

    def test_session_model_serialisation(self):
        fixture = SESSION_FIXTURES[0]
        r = Session(**fixture)
        r_dict = r.to_dict()

        expected = fixture.copy()
        del expected['ref_id']
        expected['id'] = 1
        expected['sql_id'] = None
        expected['timeStarted'] = fixture['timeStarted']
        expected['timeStopped'] = fixture['timeStopped']

        for k in expected.keys():
            assert k in r_dict.keys(), "Couldn't find %s in the dictionary [%s]" % \
                                       (k, ','.join([x for x in r_dict.keys()]))
            assert r_dict[k] == expected[k], "Expected %s but found %s for key %s" % (expected[k], r_dict[k], k)

        assert str(r) == json.dumps(r_dict)


class TestBasicDatabaseOperations(unittest.TestCase):
    """
    Test retrieve operations on the database
    """

    def setUp(self):

        # create a database
        self.db = DatabaseClient(path=":memory:")
        self.db.create_tables()

        # add the fixtures
        self.db.add_many(generate_objects(Category, CATEGORY_FIXTURES))
        self.db.add_many(generate_objects(Config, CONFIG_FIXTURES))
        self.db.add_many(generate_objects(Reading, READING_FIXTURES))
        self.db.add_many(generate_objects(Session, SESSION_FIXTURES))

    def test_add_one_record(self):
        c = Cache(timeLogged=blitz_timestamp(), categoryId=1, value=3)
        res = self.db.add(c)

        assert type(res) == Cache
        assert res.id == 1

    def test_find_all_readings(self):
        res = self.db.all(Reading)
        assert (len(res) == len(READING_FIXTURES))
        for x in res:
            assert type(x) == Reading

    def test_find_one_reading(self):
        res = self.db.get(Reading, {"id": 1})
        assert (type(res) == Reading)
        assert (res.id == 1)

    def test_filter_readings(self):
        res = self.db.find(Reading, {"categoryId": 2})
        assert (res.count() == 3), "Expected 2 results, found %s" % res.count()
        assert (res[0].id in [4, 5, 6]), "Expected [4, 5, 6] results, found %s, %s, %s" % (
            res[0].id, res[1].id, res[2].id)
        assert (res[0].id in [4, 5, 6])
        for x in res:
            assert type(x) == Reading

    def test_find_all_categories(self):
        res = self.db.all(Category)
        assert len(res) == len(CATEGORY_FIXTURES)
        for x in res:
            assert type(x) == Category

    def test_find_one_category(self):
        res = self.db.get(Category, {"variableName": "adc_channel_one"})
        assert (type(res) == Category), "Expected type of category, got %s" % type(res)
        assert (res.variableName == "adc_channel_one")

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
        assert (type(res) == Session)
        assert (res.id == 2)

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
        self.db = DatabaseClient(path=":memory:")
        self.db.create_tables(True)

        # add the fixtures
        self.db.add_many(generate_objects(Cache, CACHE_FIXTURES))
        self.db.add_many(generate_objects(Category, CATEGORY_FIXTURES))
        self.db.add_many(generate_objects(Config, CONFIG_FIXTURES))
        self.db.add_many(generate_objects(Reading, READING_FIXTURES))
        self.db.add_many(generate_objects(Session, SESSION_FIXTURES))

    def test_create_error(self):
        self.db.log_error("This is a test error")
        self.db.log_error("This is another error", 2)
        errs = self.db.all(Notification)
        err1got = self.db.get_by_id(Notification, 1)
        err2got = self.db.get_by_id(Notification, 2)

        assert len(errs) == 2, "Expected length 2, found %s" % len(errs)
        assert err1got.description == "This is a test error", \
            "Expected 'This is a test error', found %s " % err1got.description
        assert err1got.severity == 1, "Expected 1, found %s" % err1got.severity
        assert err2got.description == "This is another error", \
            "Expected 'This is a another error', found %s " % err2got.description
        assert err2got.severity == 2, "Expected 2, found %s" % err2got.severity

        self.db.clear_errors()
        errs = self.db.all(Notification)
        assert len(errs) == 0

    def test_delete_error(self):

        errs = self.db.all(Notification)
        assert len(errs) == 0, "Expected 0 errors found %s" % len(errs)

        self.db.log_error("A test error")
        errs = self.db.all(Notification)
        assert len(errs) == 1, "Expected 1 error found %s" % len(errs)

        self.db.handle_error(1)
        errs = self.db.all(Notification)
        assert len(errs) == 0, "Expected 0 errors found %s" % len(errs)

    def test_get_categories_for_session(self):
        """
        Test retrieving categories for a specific session
        """
        res = self.db.get_session_variables(1)

        assert len(res) == 2
        assert res[0].variableName in ["adc_channel_one", "adc_channel_two"]
        assert res[1].variableName in ["adc_channel_one", "adc_channel_two"]
        assert res[0].variableName != res[1].variableName

    def test_get_categories_for_cache(self):
        """
        Test retrieving categories for a specific session
        """
        res = self.db.get_cache_variables()

        assert len(res) == 2, "Got %s" % len(res)
        assert res[0].variableName in ["adc_channel_one", "adc_channel_two"]
        assert res[1].variableName in ["adc_channel_one", "adc_channel_two"]
        assert res[0].variableName != res[1].variableName

    def test_get_readings_for_session(self):
        """
        Test retrieving readings for a given session ID
        """

        res1 = self.db.get_session_readings(2)
        assert len(res1) == 0, "Expected 0 readings, found %s" % len(res1)

        res2 = self.db.get_session_readings(1)
        assert len(res2) == len(READING_FIXTURES), "Expected 4 readings, found %s" % len(READING_FIXTURES)
        for x in res2:
            assert type(x) is Reading

    def test_get_cache_recent_50(self):
        """
        Test retrieving the most recent (max 50) cached variables
        """
        res = self.db.get_cache()

        # check the right number of records was returned
        assert len(res) == len(CACHE_FIXTURES), "Expected %s fixtures, found %s" % (len(res), len(CACHE_FIXTURES))

        # check the right type of record was returned
        for x in res:
            assert type(x) == Cache

    def test_get_cache_since(self):
        """
        Test retrieving cached variables since a given time
        """
        res = self.db.get_cache(time2)

        # check lengths
        assert len(res) == 3

        # check the types are correct
        # and double check all the dates are in range
        for x in res:
            assert type(x) == Cache
            assert x.timeLogged >= time2, "Expected %s >= %s" % (x.timeLogged, time2)

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
        timeLogged = blitz_timestamp()
        category_id = 1
        value = 5.2
        reading = self.db.add_reading(session_id, timeLogged, category_id, value)

        result = self.db.get_by_id(Reading, reading.id)

        assert result.sessionId == session_id, "Expected %s got %s" % (result.sessionId, session_id)
        assert result.timeLogged == timeLogged, "Expected %s got %s" % (result.timeLogged, timeLogged)
        assert result.categoryId == category_id, "Expected %s got %s" % (result.categoryId, category_id)
        assert result.value == str(value), "Expected %s got %s" % (result.value, value)

    def test_add_cache(self):
        timeLogged = blitz_timestamp()
        category_id = 1
        value = 5.2
        cache = self.db.add_cache(timeLogged, category_id, value)

        result = self.db.get_by_id(Cache, cache.id)

        assert result.timeLogged == timeLogged, "Expected %s got %s" % (result.timeLogged, timeLogged)
        assert result.categoryId == category_id, "Expected %s got %s" % (result.categoryId, category_id)
        assert result.value == str(value), "Expected %s got %s" % (result.value, value)

        self.db.clear_cache()
        cached = self.db.all(Cache)
        assert len(cached) == 0, "Expected 0 cached items, found %s" % len(cached)

    def test_clear_session_data(self):
        res1 = self.db.get_session_readings(1)
        assert len(res1) == len(READING_FIXTURES)

        self.db.clear_session_data(1)
        res2 = self.db.get_session_readings(1)
        assert len(res2) == 0, "Expected 0 Readings, found %s" % len(res2)

    def test_update_session_availability(self):
        sess = self.db.get_by_id(Session, 1)
        assert sess.available is True, "Expected session to be available, but availability is %s" % sess.available

        self.db.clear_session_data(1)
        sess2 = self.db.get_by_id(Session, 1)
        assert sess2.available is False, "Expected session to be unavailable, but availability is %s" % sess.available

    def test_update_session_list(self):
        # clear all sessions
        sess = self.db._session()
        sess.query(Session).delete()
        sess.commit()
        assert len(self.db.all(Session)) == 0, "Failed to clear sessions"

        dummy_data = [
            [1, 100000, 100000, 10],
            [2, 100002, 100003, 20]
        ]
        self.db.update_session_list(dummy_data)

        session_list = self.db.all(Session)
        assert len(session_list) == 2, "Expected 2 sessions, found %s" % len(session_list)

        assert session_list[0].ref_id == dummy_data[0][0]
        assert session_list[0].timeStarted == dummy_data[0][1]
        assert session_list[0].timeStopped == dummy_data[0][2]
        assert session_list[0].numberOfReadings == dummy_data[0][3]

        assert session_list[1].ref_id == dummy_data[1][0]
        assert session_list[1].timeStarted == dummy_data[1][1]
        assert session_list[1].timeStopped == dummy_data[1][2]
        assert session_list[1].numberOfReadings == dummy_data[1][3]


@unittest.skip("Tests need to be rewritten")
class TestTcpClientStateMachine(unittest.TestCase): #(unittest.TestCase):
    """
    Tests that the TCP state machine on the client side enters and exits the
    correct states
    """

    def setUp(self):
        # simulate starting a new connection by entering the init state
        self.tcpMock = TcpClientMock()
        self.tcpMock.current_state = BaseState().go_to_state(self.tcpMock, ClientInitState)

    def tearDown(self):
        self.tcpMock.stop()
        self.tcpMock.current_state = None

    def test_enter_init_state_on_load(self):
        assert type(self.tcpMock.current_state) == ClientInitState, "Expected INIT state on load, got %s" % type(
            self.tcpMock.current_state)

    def test_enter_logging_state_after_init_ack(self):
        self.tcpMock.receive_message(CommunicationCodes.Acknowledge)
        assert type(self.tcpMock.current_state) == ClientLoggingState, "Expected Logging state, got %s" % type(
            self.tcpMock.current_state)

    def test_enter_idle_state_from_logging_stop(self):
        self.tcpMock.receive_message(CommunicationCodes.Acknowledge)  # enter logging state
        assert type(self.tcpMock.current_state) == ClientLoggingState, "Expected logging state, found %s" % type(
            self.tcpMock.current_state)

        self.tcpMock.send(CommunicationCodes.Stop)  # enter stopping state
        assert type(self.tcpMock.current_state) == ClientStoppingState, "Expected stopping state, found %s" % type(
            self.tcpMock.current_state)

        self.tcpMock.receive_message(CommunicationCodes.Acknowledge)  # enter idle state
        assert type(self.tcpMock.current_state) == ClientIdleState, "Expected idle state, found %s" % type(
            self.tcpMock.current_state)

    def test_enter_idle_state_after_init_nack(self):
        self.tcpMock.receive_message(CommunicationCodes.Negative)
        assert type(self.tcpMock.current_state) == ClientIdleState, "Expected idle state, found %s" % type(
            self.tcpMock.current_state)

    def test_enter_logging_state_after_idle_start(self):
        self.tcpMock.receive_message(CommunicationCodes.Negative)  # enter idle state
        assert type(self.tcpMock.current_state) == ClientIdleState, "Expected Idle state, got %s" % type(
            self.tcpMock.current_state)

        self.tcpMock.send(CommunicationCodes.Start)
        assert type(self.tcpMock.current_state) == ClientStartingState, "Expected Starting state, got %s" % type(
            self.tcpMock.current_state)

        self.tcpMock.receive_message(CommunicationCodes.Acknowledge)
        assert type(self.tcpMock.current_state) == ClientLoggingState, "Expected Logging state, got %s" % type(
            self.tcpMock.current_state)

    def test_enter_downloading_state_from_idle(self):
        self.tcpMock.receive_message(CommunicationCodes.Negative)  # enter idle state
        assert type(self.tcpMock.current_state) == ClientIdleState, "Expected Idle state, got %s" % type(
            self.tcpMock.current_state)

        self.tcpMock.send(CommunicationCodes.composite(CommunicationCodes.Download, "1"))
        assert type(self.tcpMock.current_state) == ClientDownloadingState, "Expected Downloading state, got %s" % type(
            self.tcpMock.current_state)

        self.tcpMock.receive_message("adfa32df")
        self.tcpMock.receive_message("12345678")
        self.tcpMock.receive_message("87654321")
        assert type(self.tcpMock.current_state) == ClientDownloadingState, "Expected Downloading state, got %s" % type(
            self.tcpMock.current_state)

        self.tcpMock.receive_message(CommunicationCodes.Negative)
        assert type(self.tcpMock.current_state) == ClientIdleState, "Expected Idle state, got %s" % type(
            self.tcpMock.current_state)

    def test_receive_insession_on_start_during_logging(self):
        self.tcpMock.receive_message(CommunicationCodes.Acknowledge)  # enter logging state
        assert type(self.tcpMock.current_state) == ClientLoggingState, "Expected logging but found %s" % type(
            self.tcpMock.current_state)

        self.tcpMock.send(CommunicationCodes.Start)
        assert type(self.tcpMock.current_state) == ClientLoggingState

    def test_sessions_status(self):
        self.tcpMock.receive_message(CommunicationCodes.Negative)
        assert type(self.tcpMock.current_state) == ClientIdleState, "Expected idle state but found %s" % type(
            self.tcpMock.current_state)

        self.tcpMock.send(CommunicationCodes.GetSessions)
        assert type(self.tcpMock.current_state) == ClientSessionListState, "Expected session list state but found %s" % type(
            self.tcpMock.current_state)

        self.tcpMock.receive_message("1 1234567890123 1234567890125")
        assert type(self.tcpMock.current_state) == ClientSessionListState, "Expected session list state but found %s" % type(
            self.tcpMock.current_state)

        self.tcpMock.receive_message("1 1234567890126 1234567890127")
        assert type(self.tcpMock.current_state) == ClientSessionListState, "Expected session list state but found %s" % type(
            self.tcpMock.current_state)

        self.tcpMock.receive_message(CommunicationCodes.Negative)
        assert type(self.tcpMock.current_state) == ClientIdleState, "Expected idle state but found %s" % type(
            self.tcpMock.current_state)


@unittest.skip("Tests need to be rewritten")
class TestTcpServerStateMachine(unittest.TestCase): #(unittest.TestCase):
    """
    Tests whether the state machine for the TcpServer follows the expected process
    """

    def setUp(self):
        # simulate starting a new connection by entering the init state
        self.tcpMock = TcpClientMock()
        state = BaseState().go_to_state(self.tcpMock, ServerIdleState)
        self.tcpMock.current_state = state

    def test_validate_valid_commands(self):
        """test that all valid commands return ERROR 1"""
        valid_commands = ["START", "STOP", "DOWNLOAD 1", "UPDATE", "BOARD 17 MOVE1"]
        for cmd in valid_commands:
            assert validate_command(cmd, VALID_SERVER_COMMANDS) == CommunicationCodes.composite(
                CommunicationCodes.Error, 1)

    def test_validate_invalid_commands(self):
        """tests that invalid commands return ERROR 2"""
        invalid_commands = ["ASDF", "STAP", "DL 1"]
        for cmd in invalid_commands:
            assert validate_command(cmd, VALID_SERVER_COMMANDS) == CommunicationCodes.composite(
                CommunicationCodes.Error, 2)

    def test_enter_idle_state_on_load(self):
        assert type(self.tcpMock.current_state) == ServerIdleState

    def test_enter_logging_state_on_idle_start(self):
        assert type(self.tcpMock.current_state) == ServerIdleState
        self.tcpMock.receive_message(CommunicationCodes.Start)
        assert type(self.tcpMock.current_state) == ServerLoggingState

    def test_stay_in_idle_when_stop_or_status(self):
        assert type(self.tcpMock.current_state) == ServerIdleState
        self.tcpMock.receive_message(CommunicationCodes.Stop)
        assert self.tcpMock.last_sent == CommunicationCodes.NoSession
        assert type(self.tcpMock.current_state) == ServerIdleState
        self.tcpMock.receive_message(CommunicationCodes.Update)
        assert type(self.tcpMock.current_state) == ServerIdleState

    def test_stay_in_idle_on_unknown_command(self):
        assert type(self.tcpMock.current_state) == ServerIdleState

        self.tcpMock.receive_message("ASDF")
        assert self.tcpMock.last_sent == CommunicationCodes.composite(CommunicationCodes.Error, 2)
        assert type(self.tcpMock.current_state) == ServerIdleState

    def test_stop_logging_on_stop_command(self):
        assert type(self.tcpMock.current_state) == ServerIdleState
        self.tcpMock.receive_message(CommunicationCodes.Start)
        assert type(self.tcpMock.current_state) == ServerLoggingState
        assert self.tcpMock.last_sent == CommunicationCodes.Acknowledge
        self.tcpMock.receive_message(CommunicationCodes.Stop)
        assert type(self.tcpMock.current_state) == ServerIdleState

    def test_stay_in_logging_on_status(self):
        assert type(self.tcpMock.current_state) == ServerIdleState
        self.tcpMock.receive_message(CommunicationCodes.Start)
        assert type(self.tcpMock.current_state) == ServerLoggingState
        self.tcpMock.receive_message(CommunicationCodes.Update)
        assert type(self.tcpMock.current_state) == ServerLoggingState

    def test_in_logging_on_unknown_command(self):
        assert type(self.tcpMock.current_state) == ServerIdleState
        self.tcpMock.receive_message(CommunicationCodes.Start)
        assert type(self.tcpMock.current_state) == ServerLoggingState
        self.tcpMock.receive_message("ASDF")
        assert self.tcpMock.last_sent == CommunicationCodes.composite(CommunicationCodes.Error, 2)

        self.tcpMock.receive_message(CommunicationCodes.composite(CommunicationCodes.Download, 3))
        assert self.tcpMock.last_sent == CommunicationCodes.composite(CommunicationCodes.Error, 1)
        assert type(self.tcpMock.current_state) == ServerLoggingState

    def test_download_lifecycle(self):
        assert type(self.tcpMock.current_state) == ServerIdleState

        # enter downloading state
        self.tcpMock.receive_message(CommunicationCodes.composite(CommunicationCodes.Download, 1))
        time.sleep(0.2)
        assert type(
            self.tcpMock.current_state) == ServerDownloadingState, "Expected ServerDownloadingState, found %s" % type(
                self.tcpMock.current_state)

        # Stay in downloading state on unknown command
        self.tcpMock.send("ASDF\nACK")
        self.tcpMock.receive_message("ACK")
        time.sleep(0.2)
        assert type(self.tcpMock.current_state) == ServerDownloadingState, \
            "Expected ServerDownloadingState, found %s" % type(
                self.tcpMock.current_state)

        # leave when download complete
        self.tcpMock.send("ASDF\n" + CommunicationCodes.Negative)
        time.sleep(0.2)
        assert type(self.tcpMock.current_state) == ServerIdleState, \
            "Expected ServerIdleState, found %s" % type(
                self.tcpMock.current_state)

    def test_insession_message_on_logging_start(self):
        assert type(self.tcpMock.current_state) == ServerIdleState

        self.tcpMock.receive_message(CommunicationCodes.Start)
        assert type(self.tcpMock.current_state) == ServerLoggingState

        self.tcpMock.receive_message(CommunicationCodes.Start)
        assert self.tcpMock.last_sent == CommunicationCodes.InSession
        assert type(self.tcpMock.current_state) == ServerLoggingState

    def test_nosession_message_on_logging_stop(self):
        assert type(self.tcpMock.current_state) == ServerIdleState

        self.tcpMock.receive_message(CommunicationCodes.Stop)
        assert self.tcpMock.last_sent == CommunicationCodes.NoSession
        assert type(self.tcpMock.current_state) == ServerIdleState


class TestExpansionBoardParsing(unittest.TestCase):
    """
    A test case to ensure that expansion boards are initalising correctly
    and are parsing data correctly
    """

    def test_expansion_board_parses_valid_message(self):
        message = "e32800002f19572076ac00000000"  # random message
        board = ExpansionBoardMock()
        board.parse_message(message)

        result = board.get_variables()

        assert result['full_payload'] == 6278148361660923904, "Expected 6278148361660923904, recieved %s" % result[
            'full_payload']
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
        board.parse_message("057500005555cccccccc00000000")
        result = board.get_variables()

        expected = {
            "adc_channel_one": 3276,
            "adc_channel_two": 3276,
            "adc_channel_three": 3264,
            "adc_channel_four": 0,
            "adc_channel_five": 0
        }

        # check get variables
        assert set(result.keys()) == set(expected.keys())
        for k in expected.keys():
            assert result[k] == expected[k], "Expected %s, received %s" % (expected[k], result[k])

        # check other parsed variables
        assert board['id'] == 8
        assert board['sender'] == 5
        assert board['type'] == 3
        assert board['flags'] == [True, False, True, False, True]
        assert board['timestamp'] == 21845

    def test_short_length_raises_exception(self):
        board = BlitzBasicExpansionBoard()
        with(self.assertRaises(Exception)):
            board.parse_message("cc")

    def test_long_length_parses_fine(self):
        board = BlitzBasicExpansionBoard()
        board.parse_message("057500005555cccccccc00000000FAFAFA")
        result = board.get_variables()

        expected = {
            "adc_channel_one": 3276,
            "adc_channel_two": 3276,
            "adc_channel_three": 3264,
            "adc_channel_four": 0,
            "adc_channel_five": 0
        }

        # check get variables
        assert set(result.keys()) == set(expected.keys())
        for k in expected.keys():
            assert result[k] == expected[k], "Expected %s, received %s" % (expected[k], result[k])

        # check other parsed variables
        assert board['id'] == 8
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
        # the BlitzBasic board should be registered as ID 1, no other boards currently registered
        assert len(self.bm.boards) == 6 # not sure if there is a better way to check this, currently have to
                                        # update every time the expansion boards are changed :/
        assert type(self.bm.boards[8]) == BlitzBasicExpansionBoard

    @raises(Exception)
    def test_double_registering_a_board(self):
        self.bm.register_board(8, BlitzBasicExpansionBoard())

        # clear the board manager and start again
        self.bm = BoardManager(self.data)


@unittest.skip("Tests need to be rewritten")
class TestDatabaseServer(unittest.TestCase): #(unittest.TestCase):
    def setUp(self):
        self.data = DatabaseServer()

    def tearDown(self):
        self.data.flush()

    def test_session_id_increments_on_new_session(self):
        assert self.data.session_id == -1, "Session ID %s is not 0 as expected" % self.data.session_id
        self.data.start_session()
        assert self.data.session_id == 1, "Session ID %s is not 1 as expected" % self.data.session_id

    def test_queue_and_retrieve_variable(self):
        # start a session
        self.data.start_session()
        assert self.data.session_id == 1, "Expected 1, got %s" % self.data.session_id

        # save some variables
        self.data.queue("one")
        self.data.queue("two")

        # retrieve them
        result = self.data.get_all_from_session(1)
        assert len(result) == 2, "Expected list of length 2, got %s" % len(result)
        assert result[0] == "one", "Expected 'one' got '%s'" % result[0]
        assert result[1] == "two", "Expected 'two' got '%s'" % result[1]

    def test_start_and_stop_session_returns_to_not_logging_state(self):
        self.data.start_session()
        assert self.data.session_id == 1, "Expected 1, got %s" % self.data.session_id

        self.data.stop_session()
        assert self.data.session_id == -1, "Expected -1, got %s" % self.data.session_id

    def test_get_ten_from_session(self):
        self.data.start_session()

        # queue four and check length
        for i in range(0, 4):
            self.data.queue(str(i))
        assert len(self.data.get_ten_from_session()) == 4

        # add twelve more and check we only get the last ten
        for i in range(4, 16):
            self.data.queue(str(i))
        result = self.data.get_ten_from_session()
        assert len(result) == 10, "Expected 10 items, found %s" % len(result)
        assert result == ["6", "7", "8", "9", "10", "11", "12", "13", "14", "15"], "Expected [6..15], for %s" % result

    def test_get_data_from_multiple_sessions(self):
        # run the first session
        self.data.start_session()
        self.data.queue("11")
        self.data.queue("12")
        self.data.queue("13")
        self.data.stop_session()

        # run the second session
        self.data.start_session()
        self.data.queue("21")
        self.data.queue("22")
        self.data.queue("23")
        self.data.stop_session()

        sess1 = self.data.get_all_from_session(1)
        sess2 = self.data.get_all_from_session(2)

        assert len(sess1) == 3, "Expected session length 3, got %s: %s" % (len(sess1), sess1)
        assert len(sess2) == 3, "Expected session length 3, got %s: %s" % (len(sess2), sess2)
        assert sess1 == ["11", "12", "13"], "Session received %s" % sess1
        assert sess2 == ["21", "22", "23"], "Session received %s" % sess2

    def test_session_listing(self):
        sessions = self.data.available_sessions()
        assert sessions == [], "Expected empty list, recieved %s" % sessions

        for i in range(0, 10):
            self.data.start_session()
            self.data.stop_session()

        sessions = self.data.available_sessions()
        print sessions
        assert len(sessions) == 10
        assert sessions == [x for x in reversed([str(x) for x in range(1, 11)])]

    def test_delete_session(self):
        assert False, "Not implemented"

    def test_get_latest_from_session(self):
        assert False, "Not implemented"

    def test_build_client_session_list(self):
        assert False, "Not implemented"


class TestDataContainer(unittest.TestCase):
    def setUp(self):
        self.data = DataContainer()

    @raises(ValueError)
    def test_should_throw_value_error_on_mismatched_arrays(self):
        self.data.push('1', "Series 1", [1, 2], [1])

    def test_number_of_series(self):
        assert self.data.number_of_series == 0, "Expected 0 series, found %s" % self.data.number_of_series

        self.data.push('1', "Series 1", [1], [1])
        assert self.data.number_of_series == 1, "Expected 1 series, found %s" % self.data.number_of_series

    def test_pushing_int_id_converts_to_str(self):
        self.data.push(1, "Series 1", [1], [1])
        assert self.data.number_of_series == 1, "Expected 1 series, found %s" % self.data.number_of_series

        self.data.push("1", "Series 1", [2], [2])
        assert self.data.number_of_series == 1, "Expected 1 series, found %s" % self.data.number_of_series

    def test_push_data_series_doesnt_duplicate_series(self):
        self.data.push("1", "Series 1", [1], [1])
        self.data.push("2", "Series 2", [1], [1])
        assert self.data.number_of_series == 2, "Expected 2 series, found %s" % self.data.number_of_series

        self.data.push("2", "Series 2", [1], [1])
        assert self.data.number_of_series == 2, "Expected 2 series, found %s" % self.data.number_of_series

        assert len(self.data.x) == 2, "Expected 2 items, found %s" % len(self.data.x)
        assert len(self.data.x[0]) == 1, "Expected 1 items, found %s" % len(self.data.x[0])
        assert len(self.data.x[1]) == 2, "Expected 2 items, found %s" % len(self.data.x[1])
        assert len(self.data.y) == 2, "Expected 2 items, found %s" % len(self.data.y)
        assert len(self.data.y[0]) == 1, "Expected 1 items, found %s" % len(self.data.y[0])
        assert len(self.data.y[1]) == 2, "Expected 2 items, found %s" % len(self.data.y[1])

    def test_get_series(self):
        self.data.push("1", "Series 1", [1], [1])

        # check the series is correctly returned
        x, y = self.data.get_series("1")
        assert len(x) == 1
        assert len(y) == 1
        assert x[0] == 1
        assert y[0] == 1

        # check a none array is returned for unknown series
        x2, y2 = self.data.get_series(1)
        assert len(x2) == 0
        assert len(y2) == 0

    def test_push_data_series_appends_to_existing_series(self):
        self.data.push("1", "Series 1", [1], [1])
        self.data.push("1", "Series 1", [1], [1])
        self.data.push("1", "Series 1", [1], [1])
        self.data.push("1", "Series 1", [1], [1])
        self.data.push("1", "Series 1", [1], [1])

        assert self.data.number_of_series == 1

        x, y = self.data.get_series("1")
        assert len(x) == 5
        assert len(y) == 5
        for x_val in x:
            assert x_val == 1

    def test_all_series(self):
        self.data.push("1", "Series 1", [1, 2], [3, 4])
        self.data.push("2", "Series 2", [5, 6], [7, 8])
        series_count = 0
        series_data = [
            [[1, 2], [3, 4]],
            [[5, 6], [7, 8]]
        ]

        for series in self.data.all_series():
            key, x, y = series
            expected_x, expected_y = series_data[series_count]
            assert x == expected_x, "Unexpected list found for x values (%s)" % ', '.join([str(x) for x in expected_x])
            assert y == expected_y, "Unexpected list found for y values (%s)" % ', '.join([str(y) for y in expected_y])
            series_count += 1

        assert series_count == 2, "Expected 2 series, found %s" % series_count

    def test_get_series_keeps_series_order(self):
        self.data.push("1", "Series 1", [1, 2], [3, 4])
        self.data.push("2", "Series 2", [1, 2], [3, 4])
        self.data.push("3", "Series 3", [1, 2], [3, 4])
        self.data.push("2", "Series 2", [1, 2], [3, 4])
        self.data.push("4", "Series 4", [1, 2], [3, 4])
        series_names = ["1", "2", "3", "4"]
        series_count = 0

        for series in self.data.all_series():
            key, x, y = series
            assert key == series_names[series_count], "Expected %s for series name but found %s" % (
                series_names[series_count], key)
            series_count += 1

    def test_clear_data(self):
        self.data.push("1", "Series 1", [1], [1])
        self.data.push("2", "Series 2", [1], [1])
        assert self.data.number_of_series == 2, "Expected 2 series, found %s" % self.data.number_of_series

        self.data.clear_data()
        assert self.data.number_of_series == 0, "Expected 0 series, found %s" % self.data.number_of_series

    def test_add_transform(self):
        self.data.add_transform(data_transforms.MultiplierDataTransform(2))
        assert len(self.data.get_transforms()) == 1

        self.data.add_transform(data_transforms.MultiplierDataTransform(5))
        assert len(self.data.get_transforms()) == 2

    @raises(ValueError)
    def test_add_transform_throws_on_incorrect_type_of_transform(self):
        self.data.add_transform(3)

    def test_get_unknown_series(self):
        self.data.push("1", "Series 1", [1], [1])
        assert self.data.get_series("2") == [[], []], "Expected empty list"

    def test_has_series(self):
        self.data.push("1", "Series 1", [1], [1])

        assert self.data.has_series("1") == True
        assert self.data.has_series(1) == True
        assert self.data.has_series("asdf") == False

    def test_get_series_names(self):
        self.data.push("2", "Series 2", [1], [1])
        self.data.push("1", "Series 1", [1], [1])

        series_names = self.data.get_series_names()

        assert series_names[0] == "2"
        assert series_names[1] == "1"

    def test_push_return_values(self):
        assert self.data.push("1", "Series 1", [1], [1]) == True
        assert self.data.push("1", "Series 1", [1], [1]) == False
        assert self.data.push("2", "Series 2", [1], [1]) == True

    def test_get_x_and_get_y(self):
        self.data.push("1", "Series 1", [1], [2])
        self.data.push("2", "Series 2", [3], [4])

        x = self.data.get_x("1")
        y = self.data.get_y("2")

        assert x == [1]
        assert y == [4]

    def test_get_x_and_get_y_unknown_series(self):
        self.data.push("1", "Series 1", [1], [2])
        self.data.push("2", "Series 2", [3], [4])
        x = self.data.get_x("3")
        y = self.data.get_y("3")

        assert x == []
        assert y == []

    def test_get_series_index(self):
        self.data.push("1", "Series 1", [1], [1])
        self.data.push("2", "Series 2", [1], [1])
        self.data.push("1", "Series 1", [1], [1])

        assert self.data.get_series_index("1") == 0
        assert self.data.get_series_index("2") == 1

    def test_container_empty(self):
        assert self.data.empty() == True
        self.data.push("1", "Series 1", [1], [1])
        assert self.data.empty() == False


class TestDataTransform(unittest.TestCase):
    def setUp(self):
        self.data = DataContainer()

    def test_apply_transforms_one(self):
        start = [1, 2, 3, 4]
        expected = [2, 4, 6, 8]
        self.data.add_transform(data_transforms.MultiplierDataTransform(2))
        self.data.push("1", start, start)

        self.data.apply_transforms()

        # check originals were unchanged
        x, y = self.data.get_series("1")
        assert y == start

        # check transforms have applied correctly
        x, y = self.data.get_transformed_series("1")
        assert y == expected

    def test_apply_transforms_several(self):
        start = [1, 2, 3, 4]
        expected = [1, 3, 5, 7]
        self.data.add_transform(data_transforms.MultiplierDataTransform(2))
        self.data.add_transform(data_transforms.MovingAverageDataTransform(2))
        self.data.push("1", start, start)

        self.data.apply_transforms()

        x, y = self.data.get_transformed_series("1")
        assert y == expected, "Expected [%s], got [%s]" % (
            ', '.join([str(data) for data in expected]),
            ', '.join([str(data) for data in y])
        )

    @raises(NotImplementedError)
    def test_not_overriding_apply_in_derived_transform(self):
        class BrokenDataTransform(BaseDataTransform):
            pass

        self.data.add_transform(BrokenDataTransform())
        self.data.apply_transforms()
