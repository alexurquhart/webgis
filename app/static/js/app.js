/*global ko*/
/*global L*/
/*global topojson*/
/*global twemoji*/
/*global Materialize*/

function Map(element) {
    // Start the map
    var self = this;
    var map = L.map('map').setView([44.09744824027576, -78.3709716796875], 8);
    L.tileLayer('http://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png').addTo(map);

    function addTopoJSONLayer(url, cb) {
        $.getJSON(url)
        .done(function(json) {
            var geojson = topojson.feature(json, json.objects.divisions);
            var layer = L.geoJson(geojson);
            map.addLayer(layer);
            cb(layer, null);
        })
        .fail(function(jqxhr, textStatus, error) {
            cb(null, textStatus);
        });
    }
    
    function addHeatmapLayer(url, cb) {
        $.getJSON(url)
        .done(function(json) {
            var heat = L.heatLayer(json, {radius: 25});
            map.addLayer(heat);
            cb(heat);
        })
        .fail(function(jqxhr, textStatus, error) {
            cb(null, textStatus);
        });
    }
    
    function removeLayer(layer) {
        map.removeLayer(layer);
    }

    // Adds an array of tweet markers to the map, and returns the array of tweet data with a 'marker' field added
    // function addTweetMarkers(tweets) {
    //     $.map(tweets, function(tweet) {
    //         var marker = L.
    //     });
    //     return tweets;
    // }
    
    return {
        addTopoJSONLayer: addTopoJSONLayer,
        addHeatmapLayer: addHeatmapLayer,
        removeLayer: removeLayer
    };
}

function LiveFeed(url, cb) {
    var self = this;
    
	var ws = new WebSocket(url);

	ws.onopen = function() {
        Materialize.toast("Connected", 4000);
	};

	// Restart the connection if it closes
	ws.onclose = function() { 
		Materialize.toast("Disconnected", 4000);
		window.setTimeout(function() {
		    new LiveFeed(url, cb);
		}, 1000);
	};

	// Message received...
	ws.onmessage = function(message) {
		var data = JSON.parse(message.data);

		// Make sure it isn't a "nodata" message
		if (typeof(data.coordinates) !== 'undefined') {
			// Push data to callback
			
			cb(data);
		}
	};
}

function ViewModel() {
    var self = this;
    this.activeOverlay = ko.observable("livefeed");
    this.showSpinner = ko.observable(false);
    this.tweets = ko.observableArray();
    
    this.map = new Map('map');
    this.feed = new LiveFeed("ws://webgis-alexurquhart.c9users.io/ws/", function(data) {
        data.text = twemoji.parse(data.text, { size: 16 });
        self.tweets.unshift(data);
    });
    this.overlayLayer = null;
    
    this.toggleSpinner = function() {
        this.showSpinner(!this.showSpinner());
    };
    
    this.setOverlay = function(newOverlay) {
        var oldLayer = this.activeOverlay();
        
        if (newOverlay !== oldLayer) {
            this.toggleSpinner();
            this.activeOverlay(newOverlay);
            
            if (this.overlayLayer !== null) {
                this.map.removeLayer(this.overlayLayer);
            }
            
            switch(newOverlay) {
                case 'livefeed':
                    self.toggleSpinner();
                    break;
                case 'statistics':
                    this.map.addTopoJSONLayer('js/divisions.topojson', function(l, error) {
                        self.toggleSpinner();
                        if (error) {
                            alert(error);
                            return;
                        }
                        self.overlayLayer = l;
                    });
                    break;
                case 'heatmap':
                    this.map.addHeatmapLayer('heatmap/', function(l, error) {
                        self.toggleSpinner();
                        if (error) {
                            alert(error);
                            return;
                        }
                        self.overlayLayer = l;
                    });
                    break;
            }
        }
    };
}

function ResizeCards() {
    $('#cards').css('max-height', $(window).height() - 110);
}

$(document).ready(function() {
    var vm = new ViewModel();
    ko.applyBindings(vm);
    $(window).resize(ResizeCards);
    ResizeCards();
});