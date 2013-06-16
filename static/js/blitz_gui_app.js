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


/* Set up the routes */
App.Router.map(function () {
    this.resource('live', function () {
        this.resource('variable', { path: ':variableName' });
    });
});

// live route shows main data page
App.LiveRoute = Ember.Route.extend({
    model: function () {
        return App.DataLine.find();
    }
});

// when opening the page go directly to the live route
App.IndexRoute = Ember.Route.extend({
    redirect: function () {
        this.transitionTo('live');
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

/*********************************************************
 * CHARTING FUNCTION
*********************************************************/

/* A function to generate chart axis */
var chart_builder = function () {

    /* set up the main chart variables and layout */
    var margin = { top: 50, right: 50, bottom: 50, left: 50 },
        width = innerWidth - margin.left - margin.right,
        height = innerHeight - margin.top - margin.bottom,
        parseDate = d3.time.format("%Y%m%d %h:%m%s").parse,
        x = d3.scale.linear().range([0, width]),
        y = d3.scale.linear().range([height, 0]),
        colour = d3.scale.category10(),
        xAxis = d3.svg.axis().scale(x).orient('bottom'),
        yAxis = d3.svg.axis().scale(y).orient('left');

    /* set up the line for drawing the series */
    var line = d3.svg.line()
        .interpolate("basis")
        .x(function (d) { return x(d.timeLogged); })
        .y(function (d) { return y(d.variableValue); });

    /* add the axis to the SVG */
    var svg = d3.select("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .attr("viewBox", "0, 0, " + innerWidth + ", " + innerHeight)
        .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    /* draw the x-axis */
    svg.append("g")
        .attr("class", "x_axis")
        .attr("transform", "translate(0, " + height + ")")
        .call(xAxis);

    /* draw the y-axis */
    svg.append("g")
        .attr("class", "y_axis")
        .call(yAxis);
};

