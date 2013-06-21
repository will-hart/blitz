(function (root) {

    /** Get the maximum value from a list of lists
     *
     * @param data the multidimensional array to find the max for
     * @param fn the function to apply to each array element (e.g. d3.max)
     * @param accessor the optional accessor function for max of the inner loop
     */
    function getMinMaxValues(data, fn, accessor) {
        return fn(data.map(function (array) {

            if (accessor === undefined) {
                return fn(array, function (d) {
                    return d.value;
                });
            } else {
                return fn(array, accessor);
            }
        }));
    }

    /** Draws a chart at the node with the given selector
     *
     *  @param data the list of data to be plotted
     *  @param elem the container element to add the svg element to
     */
    var draw_chart = function (data, elem) {

        d3.select("#" + elem + " svg").remove();

        var i = 0,
            max_elements = data === undefined ? 0 : data.length,
            colours = ["#0078e7", "#198A34", "#ff158a", "#cfda20", "#202020"],

            margin = {
                top: 80,
                right: 60,
                bottom: 60,
                left: 60
            },

            domElem = d3.select("#" + elem),
            chart = d3.select("#" + elem).append("svg:svg"),
            elemWidth = domElem.style("width").replace("px", ""),
            elemHeight = domElem.style("height").replace("px", ""),
            width = elemWidth - margin.left - margin.right,
            height = elemHeight - margin.top - margin.bottom,

            x_extents = max_elements === 0 ? [new Date("09/04/2011"), new Date("14/07/2011")] : [getMinMaxValues(data, d3.min, function (d) {
                return d.timeLogged;
            }), getMinMaxValues(data, d3.max, function (d) {
                return d.timeLogged;
            })],
            y_extents = max_elements === 0 ? [0, 1] : [getMinMaxValues(data, d3.min), getMinMaxValues(data, d3.max)],
            x = d3.time.scale.utc()
                .domain(x_extents)
                .range([0, width]),
            y = d3.scale.linear()
                .domain(y_extents)
                .range([height, 0]),
            xAxis = d3.svg.axis().scale(x).orient('bottom'),
            yAxis = d3.svg.axis().scale(y).orient('left'),

            line = d3.svg.line()
                .x(function (d) {
                    return x(d.timeLogged);
                })
                .y(function (d) {
                    return y(d.value);
                });

        // set up the chart area
        if (max_elements > 0) {
            chart.data([data]);
        }

        chart.attr("preserveAspectRatio", "xMidYMid")
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
            .attr("viewBox", "-" + margin.left + ", -" + margin.top + ", " + elemWidth + ", " + elemHeight)
            .append("g")
            .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

        // draw the x-axis
        chart.append("g")
            .attr("class", "x_axis")
            .attr("transform", "translate(0, " + height + ")")
            .call(xAxis);

        // draw the y-axis
        chart.append("g")
            .attr("class", "y_axis")
            .call(yAxis);

        // draw the lines
        for (i = 0; i < max_elements; i += 1) {
            chart.append("svg:path")
                .data([data[i]])
                .attr("class", "line")
                .attr("fill", "none")
                .attr("stroke", colours[i])
                .attr("stroke-width", 2)
                .attr("d", line);
        }

        // draw the legend at the top of the screen
        for (i = 0; i < max_elements; i += 1) {
            // draw the coloured block
            chart.append("svg:rect")
                .attr("x", 25 + 130 * i)
                .attr("y", -46)
                .attr("stroke", colours[i])
                .attr("fill", colours[i])
                .attr("height", 3)
                .attr("width", 22);

            // draw the text
            chart.append("svg:text")
                .attr("x", 50 + 130 * i)
                .attr("y", -40)
                .text("Series " + (i + 1));
        }

        // return the chart object for storage and in-app manipulation
        return chart;
    };

    /** Function for drawing a sparkline
     *
     *  @param data the list of data to be plotted
     *  @param elem the container element to add the svg element to
     */
    var draw_sparkline = function (data, elem) {

        var margin = {
                top: 5,
                right: 5,
                bottom: 5,
                left: 5
            },

            // TODO - get element height and width or set defaults
            width = 200 - margin.left - margin.right,
            height = 40 - margin.top - margin.bottom,

            x = d3.time.scale.utc()
                .domain(d3.extent(data, function (d) {
                    return d.timeLogged;
                }))
                .range([0, width]),
            y = d3.scale.linear()
                .domain([0, d3.max(data, function(d) {
                    return d.value;
                })])
                .range([height, 0]),

            line = d3.svg.line()
                .x(function (d) {
                    return x(d.timeLogged);
                })
                .y(function (d) {
                    return y(d.value);
                }),

            chart = d3.select("#" + elem).append("svg:svg")
                .data([data])
                .attr("width", width + margin.left + margin.right)
                .attr("height", height + margin.top + margin.bottom)
                .attr("viewBox", "0, 0, " + 100 + ", " + 40)
                .append("g")
                .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

        // draw the line
        chart.append("svg:path")
            .data([data])
            .attr("class", "line")
            .attr("fill", "none")
            .attr("stroke", "white")
            .attr("stroke-width", 2)
            .attr("d", line);

        return chart;
    };

    root.BlitzChart = draw_chart;
    root.BlitzSparkline = draw_sparkline;

})(this);
