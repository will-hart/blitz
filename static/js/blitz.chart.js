(function (root) {

    var draw_chart, draw_sparkline;

    /** Draws a chart at the node with the given selector
     *
     *  @param data the list of data to be plotted
     *  @param elem the container element to add the svg element to
     *  @param labels the optional strings to give the series labels (or Series N if none given)
     */
    draw_chart = function draw_chart(data, elem, labels) {

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

            xExtents = maxElements === 0 ?
                [new Date("04/09/2011 00:00"), new Date("07/14/2011 23:59")] :
                [d3.min(d3.merge(data), function (d) { return d.get('loggedAt'); }), d3.max(d3.merge(data), function (d) { return d.get('loggedAt'); })],
            yExtents = maxElements === 0 ? [0, 1] : [0, d3.max(d3.merge(data), function (d) { return d.get('value'); })],
            xMap = d3.time.scale.utc()
                .domain(xExtents)
                .range([0, width]),
            yMap = d3.scale.linear()
                .domain(yExtents)
                .range([height, 0]),
            xAxis = d3.svg.axis().scale(xMap).orient('bottom'),
            yAxis = d3.svg.axis().scale(yMap).orient('left'),
            xGather = function (d) {
                return xMap(d.get('loggedAt'));
            },
            yGather = function (d) {
                return yMap(d.get('value'));
            },

            line = d3.svg.line()
                .x(xGather)
                .y(yGather),
            lines;

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
            .call(xAxis
                .tickSize(-height, 0, 0));

        // draw the y-axis
        chart.append("g")
            .attr("class", "y_axis")
            .call(yAxis
                .tickSize(-width, 0, 0));

        g = chart.selectAll("g.line")
            .data(data);
        lines = g.enter()
            .append("svg:g")
            .attr("class", "line");

        lines.append("svg:path")
            .attr("d", line)
            .attr("fill", "none")
            .attr("stroke", function (d, i) {
                return colours[i];
            })
            .attr("stroke-width", 2);

        lines.selectAll("circle")
            .data(function (d) { return d; })
            .enter()
            .append("svg:circle")
            .attr("cx", function (d) { return xMap(d.get("loggedAt")); })
            .attr("cy", function (d) { return yMap(d.get("value")); })
            .attr("r", 3)
            .attr("stroke", "none")
            .append("title")
            .text(function (d) {
                return d.get("value") + " @ " + d.get("titleDate");
            });

        for (i = 0; i < maxElements; i += 1) {
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
                .text(labels[i] === undefined ? "Series " + (i + 1) : labels[i]);
        }
    };

    /**
     * Draws a sparkline chart in a small element - no axis or labels
     *
     * @param data The data to use for plotting the sparkline
     * @param elem The element to draw the sparkline into
     */
    draw_sparkline = function (data, elem) {

        if (data.length === 0) {
            return;
        }

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
        chart.append("path")
            .data([data])
            .attr("class", "line")
            .attr("fill", "none")
            .attr("stroke", "white")
            .attr("stroke-width", 2)
            .attr("d", line);

        // draw a circle at the last point (hopefully they are in order :])
        chart.append("circle")
            .attr("cx", xMap(data[data.length - 1].get("loggedAt")))
            .attr("cy", yMap(data[data.length - 1].get("value")))
            .attr("r", 3)
            .attr("stroke", "none")
            .attr("fill", "#CA3C3C");
    };

    root.BlitzChart = draw_chart;
    root.BlitzSparkline = draw_sparkline;

})(this);
