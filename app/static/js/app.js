/*globals ko L topojson twemoji Materialize*/

var LIVEFEED_URL = "ws://" + window.location.hostname + (window.location.port ? ':' + window.location.port: '') + '/ws/';
var TILE_URL = 'http://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png';
var STATISTICS_LAYER_URL = 'js/divisions.topojson';
var HEATMAP_LAYER_URL = 'tweets/heatmap';
var HISTOGRAM_URL = 'division/histogram/all'

function Map(element) {
    // Start the map
    var self = this;
    var map = L.map('map').setView([44.09744824027576, -78.3709716796875], 8);
    L.tileLayer(TILE_URL).addTo(map);

    // Gets the geoJSON geometry, as well as the histogram information,
    // joins them, and then calls the callback with the finished data
    function getStatisticsLayerData(cb) {
        $.getJSON(STATISTICS_LAYER_URL)
        .done(function(json) {
            var geojson = topojson.feature(json, json.objects.divisions);
            
            // Get the histogram statistics
            $.getJSON(HISTOGRAM_URL)
            .done(function(histogram) {
                geojson = $.map(geojson, function(g) {
                    return g;
                });
                
                cb(geojson, null);
            })
            .fail(function(jqxhr, textStatus, error) {
                cb(null, textStatus);
            });
        })
        .fail(function(jqxhr, textStatus, error) {
            cb(null, textStatus);
        });
    }

    function addStatisticsLayer(cb) {
        getStatisticsLayerData(function(data, error) {
            if (error !== null) {
                cb(null, error);
            }
            
            var layer = L.geoJson(data, { style: symbolizeChloropleth });
            map.addLayer(layer);
            cb(layer, null);
        });
    }
    
    // Symbolize Chloropleth
    // Given an array of geoJSON
    function symbolizeChloropleth(geoJson) {
        // console.log(geoJson);
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
    
    function addMarker(tweet) {
        var myIcon = L.divIcon();
        tweet.marker = L.marker([tweet.coordinates[1], tweet.coordinates[0]], { icon: myIcon, title: tweet.text }).addTo(map);
        return tweet;
    }
    
    return {
        addStatisticsLayer: addStatisticsLayer,
        addHeatmapLayer: addHeatmapLayer,
        removeLayer: removeLayer,
        addMarker: addMarker
    };
}

function LiveFeed(url, cb) {
    var self = this;
    
	var ws = new WebSocket(url);

    function makeLinks(text) {
        // Make t.co links work
        var tco = /(https:\/\/t.co\/[A-Za-z0-9]+)/g;
        var matches = text.match(tco);
        if (matches) {
            $.each(matches, function(index, match) {
                text = text.replace(match, '<a href="' + match + '" target="new">' + match + '</a>');
            });
        }
        return text;
    }
    
    // Adds emoji's, and links to URL's and hashtags
    function formatTweetText(tweet) {
        tweet.text = twemoji.parse(tweet.text, { size: 16 });
        tweet.text = makeLinks(tweet.text);
        return tweet;
    }
    
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
			data = formatTweetText(data);
			cb(data, null);
		}
	};
}

function ViewModel() {
    var self = this;
    this.activeOverlay = ko.observable("livefeed");
    this.showSpinner = ko.observable(false);
    this.tweets = ko.observableArray();
    
    // Delay 5 minutes before deleting received tweets from the live feed
    var delayBeforeDelete = 10 * 60 * 1000;
    
    this.map = new Map('map');
    this.feed = new LiveFeed(LIVEFEED_URL, function(data, msg) {
        if (data !== null) {
            data = self.map.addMarker(data);
            self.tweets.unshift(data);
            
            // Delete the incoming tweet after 5 mins
            setTimeout(function() {
                self.map.removeLayer(data.marker);
                self.tweets.remove(data);
            }, delayBeforeDelete);
        }
        
        // Only display messages when the livefeed is the active overlay
        if (msg !== null && self.activeOverlay() === "livefeed") {
            Materialize.toast(msg, 3000);
        }

    });
    this.overlayLayer = null;
    
    this.toggleSpinner = function() {
        this.showSpinner(!this.showSpinner());
    };
    
    this.setOverlay = function(newOverlay) {
        var oldLayer = this.activeOverlay();
        
        if (newOverlay === oldLayer) {
            return;
        }
        
        this.toggleSpinner();
        this.activeOverlay(newOverlay);
        
        if (this.overlayLayer !== null) {
            this.map.removeLayer(this.overlayLayer);
        }
        
        if (oldLayer === 'livefeed') {
            $('.leaflet-marker-pane').hide();
        }
        
        switch(newOverlay) {
            case 'livefeed':
                self.toggleSpinner();
                $('.leaflet-marker-pane').show();
                break;
            case 'statistics':
                this.map.addStatisticsLayer(function(l, error) {
                    self.toggleSpinner();
                    if (error) {
                        alert(error);
                        return;
                    }
                    self.overlayLayer = l;
                });
                break;
            case 'heatmap':
                this.map.addHeatmapLayer(HEATMAP_LAYER_URL, function(l, error) {
                    self.toggleSpinner();
                    if (error) {
                        alert(error);
                        return;
                    }
                    self.overlayLayer = l;
                });
                break;
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