var Blitz = Ember.Application.create({
    LOG_TRANSITIONS: false,
    LOG_BINDINGS: false,
    LOG_VIEW_LOOKUPS: false,
    LOG_STACKTRACE_ON_DEPRECATION: false,
    LOG_VERSION: false,

    debugMode: false /*,

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
    }*/
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
    category: 2,
    timeLogged: new Date('"13/1/2014 12:59.05'),
    value: "0.05"
}, {
    id: 4,
    sessionId: 1,
    category: 2,
    timeLogged: new Date('"13/1/2014 12:59.06'),
    value: "9.05"
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
    setupController: function (controller, model) {
        controller.set('content', model);
        this.controllerFor("category").set('model', Blitz.Category.find());
        this.controllerFor("config").set('model', Blitz.Config.find());
    }
});


/*********************************************************
 * CONTROLLERS
*********************************************************/

Blitz.IndexController = Ember.ArrayController.extend({

    content: [],
    chartVars: [],

    /**
     * Returns the chart content - which is results form variables
     * that have been selected in the CategoryView.
     */
    chartContent: function () {
        console.log("chart content updating");
        // get all the currently selected categories
        var chartVars = this.get('chartVars'),
            content = this.get('content');

        // filter the content variable
        return content.filter(function (model) {
            chartVars.contains(model.category)
        });
    }.property('chartVars.length')
});

Blitz.CategoryController = Ember.ArrayController.extend({

    needs: ["index"],

    /**
     * Ensures that the IndexController maintains a list of
     * selected IDs from the CategoryView
     *
     * @param category_id the ID number of the category being toggled
     */
    toggleCategory: function toggleCategory(category_id) {
        var indexController = this.get('controllers.index'),
            chartVars = indexController.get('chartVars'),
            mod = this.get("model"),
            selected = mod.filterProperty('selected'),
            selectedIds = selected.mapProperty('id');

        // set the chart vars
        chartVars.clear();
        chartVars.addObjects(selectedIds);

        // log
        console.log("Selected chart variables: " + chartVars);
    }.observes('model.@each.selected')
});

Blitz.ConfigController = Ember.ObjectController.extend();


/*********************************************************
 * VIEWS
*********************************************************/

Blitz.IndexView = Ember.View.extend({

    chart: null,
    line: {},

    // the colours to use on the (max 5) chart series
    colours: [
        "#0078e7", // blue
        "#198A34", // green
        "#202020", // dark grey
        "#CA3C3C", // red
        "#DF7514" // yellow
    ],

    /**
     *  Initialise and draw the chart
     */
    didInsertElement: function didInsertElement() {
        this.drawChart();
    },

    /**
     * Draws the chart inside the "#chart" div element, first
     * removing any previous SVG DOM elements inside this div
     */
    drawChart: function drawChart() {

        console.log("drawing chart");

        // get the data to plot
        var content = this.get("chartContent");

        // check if we have any content to draw
        if (content === undefined || content.length === 0) {
            content = [];
        }

        BlitzChart(content, "chart");
    }.observes('chartContent.length')
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

    /**
     * An event called when the user clicks on an item in the CategoryView
     *
     * @param e the event object
     */
    mouseUp: function (e) {
        this.get('category').toggleProperty('selected');
    },

    /**
     * An event called when the user puts their mouse over an item in the CategoryView
     *
     * @param e the event object
     */
    mouseEnter: function (e) {
        var li = e.target,
            span = null;

        // check we have hovered over the list element (and not the button)
        if (li.tagName === "LI") {
            // use jquery to select the child span
            //console.log("Should show sparkline here");
        }
    }
});
