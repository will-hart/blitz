App = Ember.Application.create();

/* Set up the data store - fixtures for now */
App.Store = DS.Store.extend({
    revision: 12,
    adapter: 'DS.FixtureAdapter'
});

/* The data line object stores rows of data. */
App.DataLine = DS.Model.extend({
    sessionId: DS.attr('string'),
    timeLogged: DS.attr('date'),
    variableName: DS.attr('string'),
    variableValue: DS.attr('string')
});

/* The settings model stores setting information */
App.Config = DS.Model.extend({
    loggerPort: DS.attr('int'),
    loggerIp: DS.attr('string'),
    clientPort: DS.attr('int'),
    sampleRate: DS.attr('int')
});

App.IndexRoute = Ember.Route.extend({
    model: function () {
        return App.DataLine.find();
    }
});


/*********************************************************
 * FIXTURES
*********************************************************/

App.Config.FIXTURES = [{
    id: 1,
    loggerPort: 9000,
    loggerIp: "192.168.1.20",
    clientPort: 9090,
    sampleRate: 100
}];

App.DataLine.FIXTURES = [{
    id: 1,
    sessionId: 1,
    timeLogged: new Date('"13/1/2014 12:59:05'),
    variableName: "Accelerator",
    variableValue: "0.56"
}, {
    id: 2,
    sessionId: 1,
    timeLogged: new Date('"13/1/2014 12:59:06'),
    variableName: "Accelerator",
    variableValue: "0.59"
}, {
    id: 3,
    sessionId: 1,
    timeLogged: new Date('"13/1/2014 12:59.07'),
    variableName: "Accelerator",
    variableValue: "0.05"
}];