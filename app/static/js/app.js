/*global ko*/
/*global L*/
/*global topojson*/

function Map(element) {
    // Start the map
    var map = L.map('map').setView([44.09744824027576, -78.3709716796875], 8);
    L.tileLayer('http://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png').addTo(map);

    // Start a new route at the map center
    // Callback function provides the L.layer, or the error
    function addTopoJSONLayer(url, cb) {
        $.getJSON(url)
        .done(function(json) {
            var geojson = topojson.feature(json, json.objects.divisions);
            var layer = L.geoJson(geojson);
            map.addLayer(layer);
            cb(layer);
        })
        .fail(function(jqxhr, textStatus, error) {
            cb(null, textStatus);
        });
    }
    
    function addHeatmapLayer(url, cb) {
        $.getJSON(url)
        .done(function(json) {
            var heat = L.heatLayer(json)
            map.addLayer(heat);
            cb(heat);
        })
        .fail(function(jqxhr, textStatus, error) {
            cb(null, textStatus);
        });
    }
    
    return {
        AddTopoJSONLayer: addTopoJSONLayer,
        AddHeatmapLayer: addHeatmapLayer
    };
}

function ViewModel() {
    var self = this;
    self.map = new Map('map');
    // self.map.AddTopoJSONLayer('js/divisions.topojson', function(json, error) {
    //     console.log(json);
    // });
    self.map.AddHeatmapLayer('heatmap/', function(json, error) {
        console.log(json);
    });
}

$(document).ready(function() {
    ko.applyBindings(new ViewModel());
    $('#cards').css('max-height', $(window).height() - 110 + "px");
});

$(window).resize(function() {
    $('#cards').css('max-height', $(window).height() - 110);
})