(function (root) {

    var draw_chart, draw_sparkline;

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
            }
            return fn(array, accessor);
        }));
    }

    /** Draws a chart at the node with the given selector
     *
     *  @param data the list of data to be plotted
     *  @param elem the container element to add the svg element to
     */
    draw_chart = function draw_chart(data, elem) {

        d3.select("#" + elem + " svg").remove();

        var i = 0,
            maxElements = data === undefined ? 0 : data.length,
            colours = ["#0078e7", "#198A34", "#ff158a", "#cfda20", "#202020"],

            margin = {
                top: 80,
                right: 60,
                bottom: 60,
                left: 60
            },

            domElem = d3.select("#" + elem),
            chart = d3.select("#" + elem).append("svg:svg");

        // run checks to see if the DOM element was found
        if (domElem.empty()) {
            return;
        }

        var elemWidth = domElem.style("width").replace("px", ""),
            elemHeight = domElem.style("height").replace("px", ""),
            width = elemWidth - margin.left - margin.right,
            height = elemHeight - margin.top - margin.bottom,

            xExtents = maxElements === 0 ? [new Date("04/09/2011 00:00"), new Date("07/14/2011 23:59")] : [getMinMaxValues(data, d3.min, function (d) {
                return d.get('loggedAt');
            }), getMinMaxValues(data, d3.max, function (d) {
                return d.get('loggedAt');
            })],
            yExtents = maxElements === 0 ? [0, 1] : [0, getMinMaxValues(data, d3.max)],
            xMap = d3.time.scale.utc()
                .domain(xExtents)
                .range([0, width]),
            yMap = d3.scale.linear()
                .domain(yExtents)
                .range([height, 0]),
            xAxis = d3.svg.axis().scale(xMap).orient('bottom'),
            yAxis = d3.svg.axis().scale(yMap).orient('left'),
            xGather = function (d) { return xMap(d.get('loggedAt')); },
            yGather = function (d) { return yMap(d.get('value')); },

            line = d3.svg.line()
                .x(xGather)
                .y(yGather),
            tooltip;

        // set up the chart area
        if (maxElements > 0) {
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

        // draw a tooltip
        tooltip = chart.append("div")
            .style("position", "absolute")
            .style("z-index", 10)
            .style("visibility", "hidden");

        // draw the lines
        for (i = 0; i < maxElements; i += 1) {

            // draw the line
            chart.append("path")
                .data([data[i]])
                .attr("class", "line")
                .attr("fill", "none")
                .attr("stroke", colours[i])
                .attr("stroke-width", 2)
                .attr("d", line);

            // draw the legend at the top of the screen
            // draw the coloured block
            chart.append("rect")
                .attr("x", 25 + 130 * i)
                .attr("y", -46)
                .attr("stroke", colours[i])
                .attr("fill", colours[i])
                .attr("height", 3)
                .attr("width", 22);

            // draw the text
            chart.append("text")
                .attr("x", 50 + 130 * i)
                .attr("y", -40)
                .text("Series " + (i + 1));
        }
    };

    /**
     * Draws a sparkline chart in a small element - no axis or labels
     *
     * @param data The data to use for plotting the sparkline
     * @param elem The element to draw the sparkline into
     */
    draw_sparkline = function (data, elem) {
        var margin = {
                top: 3,
                right: 5,
                bottom: 3,
                left: 5
            },
            totalWidth = 120,
            totalHeight = 20,

            width = totalWidth - margin.left - margin.right,
            height = totalHeight - margin.top - margin.bottom,

            xMap = d3.time.scale.utc()
                .domain(d3.extent(data, function (d) {
                    return d.get('loggedAt');
                }))
                .range([0, width]),
            yMap = d3.scale.linear()
                .domain(d3.extent(data, function (d) {
                    return d.get('value');
                }))
                .range([height, 0]),

            line = d3.svg.line()
                .x(function (d) {
                    return xMap(d.get('loggedAt'));
                })
                .y(function (d) {
                    return yMap(d.get("value"));
                }),

            chart = d3.select("#" + elem).append("svg:svg")
                .data([data])
                .attr("width", width + margin.left + margin.right)
                .attr("height", height + margin.top + margin.bottom)
                .attr("viewBox", "0, 0, " + totalWidth + ", " + totalHeight)
                .append("g")
                .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

        // draw the line
        chart.append("svg:path")
            .data([data])
            .attr("class", "line")
            .attr("fill", "none")
            .attr("stroke", "white")
            .attr("stroke-width", 1)
            .attr("d", line);
    };

    root.BlitzChart = draw_chart;
    root.BlitzSparkline = draw_sparkline;

})(this);
