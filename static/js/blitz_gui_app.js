App = Ember.Application.create({
    LOG_TRANSITIONS: true
});


/*********************************************************
 * MODELS
*********************************************************/
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

/* The variable name model for tracking which variables are visible in the chart */
App.LoggedVariables = DS.Model.extend({
    variableName: DS.attr('string'),
    visible: DS.attr('bool')
})

/* The settings model stores setting information */
App.Config = DS.Model.extend({
    loggerPort: DS.attr('int'),
    loggerIp: DS.attr('string'),
    clientPort: DS.attr('int'),
    sampleRate: DS.attr('int')
});


/*********************************************************
 * CONTROLLERS
*********************************************************/

App.ApplicationController = Ember.ArrayController.extend({

    content: [],
    displayed: [],

    /* Toggles whether a variable is displayed or not */
    updateDisplayed: function updateDisplayed(variableName) {
        var disp = this.get('displayed'),
            idx = disp.indexOf(variableName);

        // check if the variable name is in the box
        if (idx >= 0) {
            disp.splice(idx);
        } else {
            disp.push(variableName);
        }

        this.set('displayed', disp);
    }
});

App.ApplicationView = Ember.View.extend({

    chart: {},
    line: {},

    /* the colours to use on the (max 5) chart series */
    colours: [
        "#0078e7", // blue
        "#198A34", // green
        "#202020", // dark grey
        "#CA3C3C", // red
        "#DF7514" // yellow
    ],

    /* Initialise and draw the chart  */
    didInsertElement: function didInsertElement() {

        /* set up the main chart variables and layout */
        var margin = { top: 60, right: 60, bottom: 60, left: 60 },
            width = innerWidth - margin.left - margin.right,
            height = innerHeight - margin.top - margin.bottom,
            x = d3.scale.linear().range([0, width]),
            y = d3.scale.linear().range([height, 0]),
            xAxis = d3.svg.axis().scale(x).orient('bottom'),
            yAxis = d3.svg.axis().scale(y).orient('left'),
            color = d3.scale.linear().domain([0, 1]).range([0, 4]),

            /* set up the line for drawing the series */
            line = d3.svg.line()
                .interpolate("basis")
                .x(function (d) { return x(d.timeLogged); })
                .y(function (d) { return y(d.variableValue); }),

            /* add the axis to the SVG */
            svg = d3.select("svg")
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

        /* dave the required variables */
        this.set('chart', svg);
        this.set('line', line);
    },

    /* Update the chart */
    updateChart: function updateChart() {
        var content = this.get('content'),
            chart = this.get('chart'),
            line = this.get('line');

        chart.selectAll('path.line')
            .data(content)
            .transition()
            .duration(500)
            .ease('sin')
            .attr('d', line(content));
    }.observes('controllers.content.@each')
});


/*********************************************************
 * ROUTES
*********************************************************/

// when opening the page go directly to the live route
App.IndexRoute = Ember.Route.extend({
    model: function () {
        return App.DataLine.find();
    },
    setupController: function (controller, index) {
        controller.set('models', index.get('content'));
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

