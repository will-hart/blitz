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
 * TODO: get this from config
 * @type {string}
 */
Blitz.blitz_api_url = "http://localhost:8989/";

/**
 * A JSON Handler which uses jQuery to send a JSON request and pushes
 * the response objects onto the given model.
 *
 * @param url the API endpoint to send to (e.g. "categories" will request from "{{api_url}}/categories"
 * @param modelClass The model class to use to create the objects
 * @param callback An optional callback that runs after the data has been decoded
 * @param initialItems An optional argument specifying initial content for this content to be appended to
 * @returns {*} list of model instances
 */
Blitz.HandleJsonMultiple = function (url, modelClass, callback, initialItems) {
    // console.log("Sending request for multiple results to " + url);

    var responseVals = initialItems === undefined ? [] : initialItems;

    $.ajax({
        url: Blitz.blitz_api_url + url,
        type: "GET",
        dataType: "json"
    }).success(function (response) {
        // console.log("Parsing JSON response for multiple results from " + url);
        response.data.forEach(function (item) {
            var instance = modelClass.create(item);
            responseVals.addObject(instance);
        });

        // run callback, if supplied
        if (callback !== undefined) {
            callback();
        }
    }).error(function (request, status, error) {
        console.log("ERROR parsing response - ");
        console.log("     " + status);
        console.log("     " + error);
        Blitz.RemoveLoadingIndicator();
    });

    return responseVals;
};

/**
 * Performs a JSON request
 *
 * @param url the API endpoint to send to (e.g. "categories" will request from "{{api_url}}/categories"
 * @param model The model to add the new object to
 * @param callback An optional callback that runs after the data has been decoded
 *
 * @returns {Ember.Object} A single object retrieved from a JSON response
 */
Blitz.HandleJsonSingle = function (url, model, callback) {
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

        // run the callback if supplied
        if (callback !== undefined) {
            callback();
        }
    }).error(function (request, status, error) {
        console.log("ERROR parsing response - ");
        console.log("     " + status);
        console.log("     " + error);
        Blitz.RemoveLoadingIndicator();
    });

    return obj;
};

/**
 * Performs a GET request to the given URL and returns the JSON result
 * @param url  The URL to request from
 * @param callback The callback function, passed the result of the AJAX request
 */
Blitz.HandleJsonRaw = function (url, callback) {
    $.ajax({
        url: Blitz.blitz_api_url + url,
        type: "GET",
        dataType: "json"
    }).success(function (response) {
        if (callback !== undefined) {
            callback(response);
        }
    });
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

/**
 * Removes a loading indicator from the screen
 */
Blitz.RemoveLoadingIndicator = function () {
    $("#loading-indicator").remove();
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
        return moment(this.get('timeLogged')).toDate();
    }.property('timeLogged'),

    /**
     * Formats the date for chart titles
     */
    titleDate: function () {
        return moment(this.get('timeLogged')).format("MMM Do h:mm:ss.SSS");
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
     * @param callback An optional callback that runs after the data has been decoded
     * @param initial The initial array of items to append the updates to
     */
    findUpdated: function (timestamp, callback, initial) {
        return Blitz.HandleJsonMultiple("cache/" + timestamp, Blitz.Reading, callback, initial);
    }
});

/* The variable name model for tracking which variables are visible in the chart */
Blitz.Category = Ember.Object.extend({
    selected: false,

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

    /**
     * A property to determine if the data logger is currently logging
     */
    isLogging: function () {
        return this.get('sessionId') !== -1;
    }.property('sessionId'),

    /**
     * Performs a custom AJAX POST request to update the saved configuration
     */
    save: function () {
        var json = "{ \n" +
            "\t'loggerPort': " + this.get("loggerPort") + ", \n" +
            "\t'loggerIp': '" + this.get("loggerIp") + "', \n" +
            "\t'clientPort': " + this.get("clientPort") + ", \n" +
            "\t'clientIp': '" + this.get("clientIp") + "', \n" +
            "\t'sampleRate': " + this.get("sampleRate") + ", \n" +
            "\t'clientRefreshRate': '" + this.get("clientRefreshRate") + ", \n" +
            "}";

        Blitz.PostJson('config', json);
    }
});
Blitz.Config.reopenClass({
    /**
     * Gets configuration information from the server
     *
     * @param callback an optional callback function triggered after the REST request is successful
     * @returns A configuration object
     */
    find: function (callback) {
        return Blitz.HandleJsonSingle("config", Blitz.Config, callback);
    }
});

/* A model for storing information about sessions */
Blitz.Session = Ember.Object.extend({
    /**
     * A property which determines if the session can be downloaded
     * from the data logger
     */
    isDownloadable: function() {
        return this.get("available");
    }.property("available")
});
Blitz.Session.reopenClass({
    /**
     * Gets the available sessions
     *
     * @param callback
     * @returns {*}
     */
    findAll: function (callback) {
        return Blitz.HandleJsonMultiple('sessions', Blitz.Session, callback);
    }
});


/*********************************************************
 * ROUTES
*********************************************************/

Blitz.Router.map(function () {
    this.resource("category");
    this.resource("config");
    this.resource("sessions", function () {
        this.resource('session', { path: ':session_id' });
    });
});

Blitz.IndexRoute = Ember.Route.extend({
    model: function () {
        var controller = this.controllerFor('index'),
            content = controller.get('content');

        if (content === undefined || content.length === 0) {
            return Blitz.Reading.findAll();
        }

        return content;
    },

    setupController: function (controller, model) {

        // check if we have already saved controller data
        var content = controller.get("content"),
            lastUpdated = controller.get("lastUpdated"),
            callbackFn = function () {
                controller.updateChartData(true);
                Blitz.RemoveLoadingIndicator();
            };

        // get an initial status update
        Blitz.HandleJsonRaw("status", function (response) {
            controller.handleSettings(response);
            Blitz.RemoveLoadingIndicator();
        });

        if (content === undefined || content.length === 0) {

            // load all data
            controller.set('content', model);
            this.controllerFor('category').set('content', Blitz.Category.findAll());

        } else {
            // Append updated chart values only - don't touch the category data
            controller.set('content', Blitz.Reading.findUpdated(lastUpdated, callbackFn, content));
        }
    }
});

Blitz.ConfigRoute = Ember.Route.extend({
    model: function () {
        return Blitz.Config.find(Blitz.RemoveLoadingIndicator);
    }
});

Blitz.SessionsRoute = Ember.Route.extend({
    model: function () {
        return Blitz.Session.findAll(Blitz.RemoveLoadingIndicator);
    },
    setupController: function(controller, model) {
        controller.set('content', model);
    }
});


/*********************************************************
 * CONTROLLERS
*********************************************************/

Blitz.IndexController = Ember.ArrayController.extend({

    content: [],
    labels: [],
    chartContent: [],
    chartVars: [],
    lastUpdated: null,
    chartDataDirty: false,
    chartDirty: false,
    needs: ['category', 'config'],
    client_errors: [],
    updatesWithoutStatus: 0,

    /* true if we are connected to the logger via TCP */
    connected: false,

    /* true if the client is currently logging */
    logging: false,

    /**
     * Returns the chart content - which is results form variables
     * that have been selected in the CategoryView.
     *
     * @param force An optional argument to force updating chart data
     */
    updateChartData: function (force) {

        // get all the currently selected categories
        var chartVars = this.get('chartVars'),
            content = this.get('content'),
            chartContent = this.get('chartContent'),
            chartDataDirty = this.get('chartDataDirty'),
            labels = this.get('labels'),
            categoryController = this.get("controllers.category"),
            categories = categoryController.get("content");

        // check we are mean to update data
        if (!chartDataDirty && force === undefined) {
            //console.log("Aborting update");
            return;
        }

        // console.log("Updating chart content with " + chartVars.length + " series");

        // clear existing chart content
        chartContent.clear();
        labels.clear();

        // ensure content is defined
        if (content === undefined) {
            content = [];
        }

        // for each chartVar, add a filtered list to the chartContent
        chartVars.forEach(function (d) {
            var cc = content.filterProperty('categoryId', d);
            chartContent.push(cc);
            labels.push(categories.findProperty('id', d).get('variableName'));
        });

        // save the chart content and labels back to the controller
        this.set('chartContent', chartContent);
        this.set('labels', labels);

        // now set the flags for rendering the chart
        this.set('chartDataDirty', false);
        this.set('chartDirty', true);
    }.observes('chartDataDirty'),

    /**
     * Watches the length of the content variable and saves the UNIX timestamp
     * for when the content was last updated
     */
    updateLastUpdatedTime: function () {
        // console.log("New data received - checking for the last update time");

        var content = this.get('content'),
            maxDates = content.mapProperty("timeLogged").sort(),
            timestamp = 0;

        // check if we have a date
        if (maxDates.length > 0) {
            // get the date from string using moment.js
            timestamp = maxDates[maxDates.length - 1];
        }
        console.log(timestamp)
        this.set('lastUpdated', timestamp);
    },

    /**
     * Draws the chart inside the "#chart" div element, first
     * removing any previous SVG DOM elements inside this div
     */
    drawChart: function drawChart() {

        var content = this.get("chartContent"),
            dirty = this.get('chartDirty'),
            labels = this.get('labels');

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
        BlitzChart(content, "chart", labels);

        // unset the render chart flag
        this.set('chartDirty', false);
    }.observes('chartDirty'),

    /*
     * Takes a status reponse from the server and updates the controller state
     */
    handleSettings: function handleSettings(response) {
        // parse the response
        this.set("connected", response.connected);
        this.set("logging", response.logging);
        this.set("client_errors", response.errors);
    },

    /**
     * Handles the connection/disconnection of the TCP socket
     */
    connectToLogger: function connectToLogger() {
        var self = this;
        Blitz.HandleJsonRaw("connect", function (response) {
            self.handleSettings(response);
        });
    },

    /**
     * Starts logging, or marks as disconnected if logging was unable to start
     */
    startLogging: function startLogging() {

        // check f we are currently logging
        if (this.get("logging")) {
            console.log("Unable to start logging - logging is already underway!");
            return;
        }

        var self = this;
        Blitz.HandleJsonRaw("start", function (response) {

            // handle the settings response
            self.handleSettings(response);

            // clear out existing cache and reset "status" update handler
            self.set("content", []);
            self.set("chartContent", []);
            self.set("updatesWithoutStatus", 0);
            self.set("lastUpdated", 0);

            // start the update cycle
            self.getUpdates();
        });
    },

    /**
     * Stops the current logging session
     */
    stopLogging: function stopLogging() {
        // check f we are currently logging
        if (!this.get("logging")) {
            console.log("Unable to stop logging - logging is not underway");
            this.set("logging", false);
            return;
        }

        var self = this;
        Blitz.HandleJsonRaw("stop", function (response) {
            self.handleSettings(response);
        });
    },

    /**
     * Gets updated logging information from the server. Whilst "this.logging"
     *  is TRUE, then it repeats this call on a timeout loop
     */
    getUpdates: function getUpdates() {

        // find out when the updates are required
        var self = this,
            updateCount = this.get('updatesWithoutStatus');

        // request updates
        Blitz.Reading.findUpdated(this.get('lastUpdated'), function () {
            self.updateLastUpdatedTime();
            self.set("chartDataDirty", true);
        }, this.get('content'));

        // check if we need to do a status request (should be done every 10th "update")
        if (updateCount >= 10) {
            Blitz.HandleJsonRaw("status", function (response) {
                self.handleSettings(response);
            });
            this.set("updatesWithoutStatus", 0);
        } else {
            this.set("updatesWithoutStatus", updateCount + 1);
        }

        // reset the timeout
        // TODO - get the timeout from CONFIG
        if (this.get("logging")) {
            setTimeout(function () {
                self.getUpdates();
            }, 2000);
        }
    },

    /*
     * Displays or hides the alert display box in the UI
     */
    showAlerts: function showAlerts() {
        $("#alert_display_box").slideToggle();
    },

    /*
     * Removes a particular error from the error list
     */
    suppressError: function suppressError(errorId) {
        var self = this;
        Blitz.HandleJsonRaw("error/" + errorId, function (response) {
            self.handleSettings(response);
        });
    },

    /*
     * Connects handlers in the event that errors or the alert buttons change
     */
    reconnectButtonHandlers: function reconnectButtonHandlers() {
        var errors = this.get("errors");
        if (errors.length > 0) {
            console.log("Updating handlers");
        }
    }.observes("errors.@each")
});

Blitz.SessionsController = Ember.ArrayController.extend({});

Blitz.SessionController = Ember.ObjectController.extend({});

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
    }.observes('model.@each.selected'),

    /**
     * Gets the relevant sparkline data for a given category ID
     * by filtering the content from the IndexController
     */
    getSparklineDataFor: function (category_id) {
        var indexController = this.get('controllers.index'),
            content = indexController.get('content');

        // console.log("getting sparkline data for " + category_id);
        return content.filterProperty('categoryId', category_id);
    }
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
     * When the view has finished rendering, connect all jquery events
     */
    didInsertElement: function () {

        var indexController = this.get('controller'),
            rendered;

        if (indexController === undefined) {
            return;
        }
        rendered = indexController.get("chartDirty");

        // show the variables pane on clicking the handle
        $("#variables_handle").on("click", function (e) {
            e.preventDefault();

            // fade in the element
            var elem = $("#variable_pane");
            elem.slideDown('fast');

            // add a body click handler for fading out
            $("div#chart").one('click', function () {
                elem.slideUp('fast');
            });

        });

        // when clicking the route button divs, click the enclosed link automatically
        $(".slide_out_handle").on("click", function (e) {
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
    classNameBindings: [':settings-container'],

    didInsertElement: function () {
        // when clicking the route button divs, click the enclosed link automatically
        $(".slide_out_handle").on("click", function (e) {
            // no need to handle the click event of a link!
            if (e.target.tagName !== "A") {
                $(this).find("a").click();
            }
        });
    }
});

Blitz.SessionsView = Ember.View.extend({
    didInsertElement: function () {
        // when clicking the route button divs, click the enclosed link automatically
        $(".slide_out_handle").on("click", function (e) {
            // no need to handle the click event of a link!
            if (e.target.tagName !== "A") {
                $(this).find("a").click();
            }
        });
    }
});

Blitz.CategoryView = Ember.View.extend({});

Blitz.CategoryLineView = Ember.View.extend({

    needs: ['index'],
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
        var controller = this.get('controller'),
            category_id = this.get('category.id'),
            li = e.target,
            id,
            data;

        // remove any previous charts
        // (hack to prevent fast mouseLeave stranding SVG sparklines in the DOM)
        $('ul.variable_list li svg').remove();

        // check we have hovered over the list element (and not the button)
        if (li.tagName === "LI"
                && controller !== undefined
                && category_id !== undefined) {

            // get the category readings
            data = controller.getSparklineDataFor(category_id);

            // Get the ID of the element to draw into and get Blitz to spark it up
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


/*********************************************************
 * HELPERS
*********************************************************/

/*
 * Formats a date in a template in a human readable format
 */
Ember.Handlebars.registerBoundHelper("human_date", function (date) {
    return moment(date).fromNow();
});
