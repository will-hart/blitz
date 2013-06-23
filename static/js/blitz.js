var Blitz = Ember.Application.create({
    LOG_TRANSITIONS: false,
    LOG_BINDINGS: false,
    LOG_VIEW_LOOKUPS: false,
    LOG_STACKTRACE_ON_DEPRECATION: false,
    LOG_VERSION: false,
    debugMode: false
});


/*********************************************************
 * UTILITY FUNCTIONS
*********************************************************/

/**
 * The base URL for api requests
 * @type {string}
 */
Blitz.blitz_api_url = "http://willhart.apiary.io/";

/**
 * A JSON Handler which uses jQuery to send a JSON request and pushes
 * the response objects onto the given model.
 *
 * @param url the API endpoint to send to (e.g. "categories" will request from "{{api_url}}/categories"
 * @param model The model to add the new object to
 * @returns {*} list of model instances
 */
Blitz.HandleJsonMultiple = function (url, model) {
    // console.log("Sending request for multiple results to " + url);

    var responseVals = [];

    $.ajax({
        url: Blitz.blitz_api_url + url,
        type: "GET",
        dataType: "json"
    }).success(function (response) {
        // console.log("Parsing JSON response for multiple results from " + url);
        response.data.forEach(function (item) {
            var instance = model.create(item);
            responseVals.addObject(instance)
        });
    }).error(function (request, status, error) {
        console.log("ERROR parsing response - ");
        console.log("     " + status);
        console.log("     " + error);
    });

    return responseVals;
};

/**
 * Performs a JSON request
 * @param url the API endpoint to send to (e.g. "categories" will request from "{{api_url}}/categories"
 * @param model The model to add the new object to
 * @returns {*} A single object retrieved from a JSON response
 * @constructor
 */
Blitz.HandleJsonSingle = function (url, model) {
    // console.log("Sending request for one result to " + url);
    var obj = model.create({});

    // perform the AJAX request
    $.ajax({
        url: Blitz.blitz_api_url + url,
        type: "GET",
        dataType: "json"
    }).success(function (response) {
        //console.log("Parsing JSON response for one result from " + url);
        obj.setProperties(response);
    }).error(function (request, status, error) {
        console.log("ERROR parsing response - ");
        console.log("     " + status);
        console.log("     " + error);
    });

    return obj;
};

/**
 * Performs an asynchronous post request to the given URL and sends the supplied JSON data
 *
 * @param url the API endpoint to send to (e.g. "categories" will request from "{{api_url}}/categories"
 * @param json the JSON to send to the endpoint
 */
Blitz.PostJson = function (url, json) {
    // TODO implement a success/failure reporting mechanism
    $.ajax({
        type: "POST",
        dataType: 'json',
        contentType: 'json',
        url: Blitz.blitz_api_url + url,
        data: json
    });
};


/*********************************************************
 * MODELS
*********************************************************/

/* The data line object stores rows of data. */
Blitz.Reading = Ember.Object.extend({
    timeLogged: new Date(),

    /**
     * A property which returns a moment date from the raw timeLogged value
     */
    loggedAt: function () {
        return moment(this.get('timeLogged'), "DD-MM-YYYY HH:m:s.SSS").toDate();
    }.property('timeLogged')
});
Blitz.Reading.reopenClass({
    /**
     * Gets at most 50 recent readings for each variable in the cache
     */
    findAll: function () {
        return Blitz.HandleJsonMultiple("cache", Blitz.Reading);
    },

    /**
     * Requests the latest variables since the given timestamp
     *
     * @param timestamp the UNIX timestamp to retrieve records after
     */
    findUpdated: function (timestamp) {
        return Blitz.HandleJsonMultiple("cache/" + timestamp, Blitz.Reading);
    }
});

/* The variable name model for tracking which variables are visible in the chart */
Blitz.Category = Ember.Object.extend({
    sparkClass: function () {
        return 'spark-%@'.fmt(this.get('id'));
    }.property('id')
});
Blitz.Category.reopenClass({
    /**
     * Gets all the available variables for the current logging session
     */
    findAll: function () {
        return Blitz.HandleJsonMultiple("categories", Blitz.Category);
    }
});

/* The settings model stores setting information */
Blitz.Config = Ember.Object.extend({
    save: function (model) {
        var json = "{ \n" +
            "\t'loggerPort': " + this.get("loggerPort") + ", \n" +
            "\t'loggerIp': '" + this.get("loggerIp") + "', \n" +
            "\t'clientPort': " + this.get("clientPort") + ", \n" +
            "\t'clientIp': '" + this.get("clientIp") + "', \n" +
            "}";

        Blitz.PostJson('config', json);
    }
});
Blitz.Config.reopenClass({
    /**
     * Gets configuration information from the server
     *
     * @returns A configuration object
     */
    find: function () {
        return Blitz.HandleJsonSingle("config", Blitz.Config);
    }
});


/*********************************************************
 * ROUTES
*********************************************************/

Blitz.Router.map(function () {
    this.route("category");
    this.route("config");
});

Blitz.IndexRoute = Ember.Route.extend({
    model: function () {
        return Blitz.Reading.findAll();
    },

    setupController: function (controller, model) {
        // check if we have already saved controller data
        var content = controller.get("content");
        if (content === undefined || content.length === 0) {

            // load all data
            controller.set('content', model);
            this.controllerFor("category").set('content', Blitz.Category.findAll());

        } else {

            // load updates only and don't touch the category data
            controller.set('content', Blitz.Reading.findUpdated(
                controller.get("lastUpdated")
            ));
        }
    }
});

Blitz.ConfigRoute = Ember.Route.extend({
    model: function () {
        return Blitz.Config.find();
    }
});

/*********************************************************
 * CONTROLLERS
*********************************************************/

Blitz.IndexController = Ember.ArrayController.extend({

    content: [],
    chartContent: [],
    chartVars: [],
    lastUpdate: null,
    chartDataDirty: false,
    chartDirty: false,
    needs: ['category'],

    /**
     * Returns the chart content - which is results form variables
     * that have been selected in the CategoryView.
     */
    updateChartData: function () {

        // get all the currently selected categories
        var chartVars = this.get('chartVars'),
            content = this.get('content'),
            chartContent = this.get('chartContent'),
            chartDataDirty = this.get('chartDataDirty');

        // check we are mean to update data
        if (!chartDataDirty) {
            return;
        }

        // console.log("Updating chart content with " + chartVars.length + " series");

        // clear existing chart content
        chartContent.clear();

        // ensure content is defined
        if (content === undefined) {
            content = [];
        }

        // for each chartVar, add a filtered list to the chartContent
        chartVars.forEach(function (d) {
            var cc = content.filterProperty('category', d);

            if (cc.length > 0) {
                chartContent.push(cc);
            }
        });

        // save the chart content
        this.set('chartContent', chartContent);

        // now set the flags for rendering the chart
        this.set('chartDataDirty', false);
        this.set('chartDirty', true);
    }.observes('chartDataDirty'),

    /**
     * Watches the length of the content variable and saves the UNIX timestamp
     * for when the content was last updated
     */
    updateLastUpdatedTime: function () {
        var content = this.get('content'),
            maxDates = content.mapProperty("loggedAt").sort(),
            timestamp = 0,
            theDate = 0,
            momentDate = 0;

        // check if we have a date
        if (maxDates.length > 0) {
            // get the date from string using moment.js
            timestamp = maxDates[maxDates.length - 1];
            momentDate = moment(timestamp);//, "DD-MM-YYYY HH:m:s.SSS");

            // convert to unix timestamp
            theDate = momentDate.valueOf();
        }
        this.set('lastUpdated', theDate);
    }.observes('content.length'),

    /**
     * Draws the chart inside the "#chart" div element, first
     * removing any previous SVG DOM elements inside this div
     */
    drawChart: function drawChart() {

        var content = this.get("chartContent"),
            dirty = this.get('chartDirty');

        if (!dirty) {
            //console.log("Aborting chart drawing - nothing to plot");
            return;
        }

        // console.log("Drawing chart with " + content.length + " series");

        // check if we have any content to draw
        if (content === undefined || content.length === 0) {
            content = [];
        }

        // draw the chart
        BlitzChart(content, "chart");

        // unset the render chart flag
        this.set('chartDirty', false);
    }.observes('chartDirty')
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
            selected,
            selectedIds,
            i;

        // Check if there is a model
        if (mod === undefined) {
            return;
        }

        // get the selected items
        selected = mod.filterProperty('selected');
        selectedIds = selected.mapProperty('id');

        // set the chart vars
        for (i = 0; i < selectedIds.length; i += 1) {
            if (chartVars.indexOf(selectedIds[i]) == -1) {
                chartVars.addObject(selectedIds[i]);
            }
        }
        for (i = 0; i < chartVars.length; i += 1) {
            if (selectedIds.indexOf(chartVars[i]) === -1) {
                chartVars.removeObject(chartVars[i]);
            }
        }

        // flag the chart data as dirty and in need of an update
        indexController.set('chartDataDirty', true);

        // console.log("Selected chart variables: " + chartVars);
    }.observes('model.@each.selected')
});

Blitz.ConfigController = Ember.ObjectController.extend({

    /**
     * Closes the settings view and returns to index, after saving changes to the model
     * @param model the model to save changes to
     */
    closeSettings: function (model) {
        // commit the changes to the configuration and update via a REST POST command
        model.save();

        // transition to the index page
        this.transitionToRoute("index");
    }
});


/*********************************************************
 * VIEWS
*********************************************************/

Blitz.IndexView = Ember.View.extend({
    /**
     * When the view has finished rendering, set a flag to
     * show that updating the chart is ok
     */
    didInsertElement: function () {
        // Draw the chart
        // console.log("Finished drawing chart view - ready for chart updates");
        var indexController = this.get('controller'),
            rendered;

        if (indexController === undefined) {
            return;
        }
        rendered = indexController.get("chartDirty");

        // hook up jQuery events
        $("#variables_slide_out_handle").on("click", function (e) {
            e.preventDefault();

            // fade in the element
            var elem = $("#variable_pane");
            elem.fadeIn();

            // add a body click handler for fading out
            $("div#chart").one('click', function () {
                elem.fadeOut();
            });

        });

        // when clicking the settings div, ensure the enclosed link is also clicked
        $("#settings_slide_out_handle").on("click", function (e) {
            // no need to handle the click event of a link!
            if (e.target.tagName !== "A") {
                $(this).find("a").click();
            }
        });

        // add a resize event for the chart
        $(window).resize(function () {
            var cht = $("#chart");
            cht.attr("width", $(window).width())
                .attr("height", $(window).height());

            cht.find("svg")
                .attr("viewBox", "0, 0, " + $(window).width() + ", " + $(window).height())
                .attr("width", $(window).width())
                .attr("height", $(window).height());
        });

        // set the flag for updating chart data
        indexController.set('chartDataDirty', true);
    }
});

Blitz.ConfigView = Ember.View.extend({
    classNameBindings: [':settings-container']
});

Blitz.CategoryView = Ember.View.extend({});

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

        // check we have hovered over the list element (and not the button)
        if (li.tagName === "LI") {

            // remove any previous charts (hack to prevent fast mouseLeave stranding SVG sparklines in the DOM
            $('ul.variable_list li svg').remove();


            // get the category readings
            data = category.get("readings");

            if (data === undefined) {
                return;
            }

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
