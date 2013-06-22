var Blitz = Ember.Application.create({
    LOG_TRANSITIONS: false,
    LOG_BINDINGS: false,
    LOG_VIEW_LOOKUPS: false,
    LOG_STACKTRACE_ON_DEPRECATION: false,
    LOG_VERSION: false,

    debugMode: false
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
    readings: DS.hasMany('Blitz.Reading'),
    sparkClass: function () {
        return 'spark-%@'.fmt(this.get('id'));
    }.property('id')
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
    chartContent: [],
    chartVars: [],

    /**
     * Returns the chart content - which is results form variables
     * that have been selected in the CategoryView.
     */
    updateChartData: function () {
        console.log("Updating chart content");

        // get all the currently selected categories
        var chartVars = this.get('chartVars'),
            content = this.get('content'),
            chartContent = this.get('chartContent');

        // clear existing chart content
        chartContent.clear();

        // ensure content is defined
        if (content === undefined) {
            content = [];
        }

        // for each chartVar, add a filtered list to the chartContent
        chartVars.forEach(function (d) {
            var cc = content.filterProperty('category', chartVars);

            if (cc.length > 0) {
                chartContent.push(cc);
            }
        });
    }.observes('chartVars.length')
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

    rendered: false,

    /**
     * When the view has finished rendering, set a flag to
     * show that updating the chart is ok
     */
    didInsertElement: function () {
        console.log("Finished drawing chart view - ready for chart updates");
        this.set('rendered', true);
        this.drawChart();
    },

    /**
     * Draws the chart inside the "#chart" div element, first
     * removing any previous SVG DOM elements inside this div
     */
    drawChart: function drawChart() {

        if (!this.get('rendered')) {
            console.log("Aborting chart drawing - page not rendered");
            return;
        }

        console.log("Drawing chart");

        // get the data to plot
        var content = this.get("chartContent");

        // check if we have any content to draw
        if (content === undefined || content.length === 0) {
            content = [];
        }

        BlitzChart(content, "chart");
    }.observes('controller.chartContent.length')
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
        // check if it was a left click
        if (e.button !== 0) return;

        // if left clicking, toggle the property and start a chain of events unlike any other!
        this.get('category').toggleProperty('selected');
    },

    /**
     * An event called when the user puts their mouse over an item in the CategoryView
     *
     * @param e the event object
     */
    mouseEnter: function (e) {
        var li = e.target,
            id = "",
            category = this.get('category'),
            data = null;
        /*[
                { value: Math.random() * 5, timeLogged: new Date("01/01/2001 10:00:00") },
                { value: Math.random() * 5, timeLogged: new Date("01/01/2001 10:00:01") },
                { value: Math.random() * 5, timeLogged: new Date("01/01/2001 10:00:02") },
                { value: Math.random() * 5, timeLogged: new Date("01/01/2001 10:00:03") },
                { value: Math.random() * 5, timeLogged: new Date("01/01/2001 10:00:04") },
                { value: Math.random() * 5, timeLogged: new Date("01/01/2001 10:00:05") },
                { value: Math.random() * 5, timeLogged: new Date("01/01/2001 10:00:06") }
            ];*/

        // check we have hovered over the list element (and not the button)
        if (li.tagName === "LI") {

            // get the category readings
            data = category.get("readings");

            // remove any previous charts (hack to prevent fast mouseLeave stranding SVG sparklines in the DOM
            $('ul.variable_list li svg').remove();

            // Get the ID and draw the sparkline
            id = $(li).attr("id");
            BlitzSparkline(data, id);
        }
    },

    /**
     * An event handler for when the mouse leaves a variable - to hide the sparkline
     *
     * @param e the event object
     */
    mouseLeave: function(e) {
        // remove all sparklines (blanket approach to try to avoid mouseLeaves not
        // firing when the mouse moves quickly
        $('ul.variable_list li svg').remove();
    }
});
