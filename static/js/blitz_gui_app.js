var Blitz = Ember.Application.create({
    LOG_TRANSITIONS: true,
    LOG_BINDINGS: true,
    LOG_VIEW_LOOKUPS: true,
    LOG_STACKTRACE_ON_DEPRECATION: true,
    LOG_VERSION: true,

    debugMode: true,

    log: function (message, location, data) {

        var ret;
        if (this.debugMode) {
            if (data != null) {
                if (typeof data === 'object') {
                    data = Ember.inspect(data);
                }

                console.log('DEBUG: ' + this.appName + ' : ' + location + ' : ' + message);
                ret = console.log('DEBUG: ' + this.appName + ' : (continued) data: ' + data);

            } else {
                ret = console.log('DEBUG: ' + this.appName + ' : ' + location + ' : ' + message);
            }
        }

        return ret;
    }
});

/*********************************************************
 * MODELS
*********************************************************/
/* Set up the data store - fixtures for now */
Blitz.Store = DS.Store.extend({
    revision: 13,
    adapter: DS.FixtureAdapter.extend({
        simulateRemoteResponse: false
    })
});

/* The data line object stores rows of data. */
Blitz.Reading = DS.Model.extend({
    sessionId: DS.attr('string'),
    category: DS.belongsTo('Blitz.Category'),
    timeLogged: DS.attr('date'),
    value: DS.attr('string')
});

/* The variable name model for tracking which variables are visible in the chart */
Blitz.Category = DS.Model.extend({
    variableName: DS.attr('string'),
    selected: DS.attr('bool'),
    readings: DS.hasMany('Blitz.Reading')
});

/* The settings model stores setting information */
Blitz.Config = DS.Model.extend({
    loggerPort: DS.attr('number'),
    loggerIp: DS.attr('string'),
    clientPort: DS.attr('number'),
    sampleRate: DS.attr('number')
});


/*********************************************************
 * FIXTURES
*********************************************************/

Blitz.Config.FIXTURES = [{
    id: 1,
    loggerPort: 9000,
    loggerIp: "192.168.1.20",
    clientPort: 9090,
    sampleRate: 100
}];

Blitz.Category.FIXTURES = [{
    id: 1,
    variableName: "Acceleration",
    selected: false,
    readings: []
}, {
    id: 2,
    variableName: "Steering Input",
    selected: true,
    readings: []
}, {
    id: 3,
    variableName: "Brake",
    selected: false,
    readings: []
}, {
    id: 4,
    variableName: "Temperature",
    selected: false,
    readings: []
}];

Blitz.Reading.FIXTURES = [{
    id: 1,
    sessionId: 1,
    category: 1,
    timeLogged: new Date('"13/1/2014 12:59:05'),
    value: "0.56"
}, {
    id: 2,
    sessionId: 1,
    category: 1,
    timeLogged: new Date('"13/1/2014 12:59:06'),
    value: "0.59"
}, {
    id: 3,
    sessionId: 1,
    category: 1,
    timeLogged: new Date('"13/1/2014 12:59.07'),
    value: "0.05"
}];


/*********************************************************
 * ROUTES
*********************************************************/

Blitz.Router.map(function () {
    this.route("category");
});

Blitz.CategoryRouter = Ember.Route.extend({
    model: function () {
        return Blitz.Category.find();
    }
});

// when opening the page go directly to the live route
Blitz.IndexRoute = Ember.Route.extend({
    model: function () {
        return Blitz.Reading.find();
    },
    setupController: function (controller, model) {
        controller.set('content', model);
        this.controllerFor("category").set('model', Blitz.Category.find());
        this.controllerFor("config").set('model', Blitz.Config.find());
    }
});


/*********************************************************
 * CONTROLLERS
*********************************************************/

Blitz.IndexController = Ember.ArrayController.extend();

Blitz.CategoryController = Ember.ArrayController.extend();

Blitz.ConfigController = Ember.ObjectController.extend();


/*********************************************************
 * VIEWS
*********************************************************/

Blitz.IndexView = Ember.View.extend({

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

Blitz.ConfigView = Ember.View.extend({
    templateName: 'config'
});

Blitz.CategoryView = Ember.View.extend();

Blitz.CategoryLineView = Ember.View.extend({
    tagName: 'li',
    category: null,
    templateName: "category_line",
    classNameBindings: ['category.selected:active'],
    click: function (event) {
        console.log("triggered!");
        console.log(event);
        this.get('category').toggleProperty('selected');
    }
});