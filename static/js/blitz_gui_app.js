App = Ember.Application.create();

/* The data line object stores rows of data. */
App.DataLine = Ember.Object.extend({
    sessionId: null,
    timeLogged: null,
    variableName: "",
    variableValue: null
});

/* The settings model stores setting information */
App.Config = Ember.Object.extend({
    loggerPort: 9000,
    clientPort: 8989,
    clientIp: "192.168.1.20",
    sampleRate: 100
});
App.Router.map(function () {
    // put your routes here
});

App.IndexRoute = Ember.Route.extend({
    model: function () {

        // TODO remove this test data
        // return some test data
        return [
            App.DataLine.create({
                sessionId: 1,
                timeLogged: "13/1/2014 12:59.05",
                variableName: "Accelerator",
                variableValue: "0.56"
            }),
            App.DataLine.create({
                sessionId: 1,
                timeLogged: "13/1/2014 12:59.06",
                variableName: "Accelerator",
                variableValue: "0.59"
            }),
            App.DataLine.create({
                sessionId: 1,
                timeLogged: "13/1/2014 12:59.07",
                variableName: "Accelerator",
                variableValue: "0.05"
            })
        ];
    }
});