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
                geojson.features = $.map(geojson.features, function(g) {
                    // Find the ID's in the histogram and add it to the geojson properties
                    g.properties.histogram = $.grep(histogram, function(h) {
                        return h.division_id == g.properties.id
                    });
                    return g;
                });
                console.log(geojson);

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
	    cb(null, "Connected");
	};

	// Restart the connection if it closes
	ws.onclose = function() { 
		window.setTimeout(function() {
		    new LiveFeed(url, cb);
		}, 1000);
		cb(null, "Disconnected");
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
    this.hiddenTweets = ko.observableArray();
    this.pauseLiveFeed = ko.observable(false);
    this.map = new Map('map');
    this.overlayLayer = null;
    
    this.toggleSpinner = function() {
        this.showSpinner(!this.showSpinner());
    };
    
    this.incomingTweetCallback = function(data, msg) {
        if (data !== null) {
            data = self.map.addMarker(data);
            
            if (self.pauseLiveFeed()) {
                self.hiddenTweets.unshift(data);
            } else {
                self.tweets.unshift(data);
            }
            
            // Delete the incoming tweet after 10 mins
            setTimeout(function() {
                self.map.removeLayer(data.marker);
                self.tweets.remove(data);
                self.hiddenTweets.remove(data);
            }, 600000);
        }
        
        // Only display messages when the livefeed is the active overlay
        if (msg !== null && self.activeOverlay() === "livefeed") {
            Materialize.toast(msg, 3000);
        }
    };
    
    this.feed = new LiveFeed(LIVEFEED_URL, this.incomingTweetCallback);
    
    this.setOverlay = function(newOverlay) {
        var oldLayer = self.activeOverlay();
        
        if (newOverlay === oldLayer) {
            return;
        }
        
        self.toggleSpinner();
        self.activeOverlay(newOverlay);
        
        if (self.overlayLayer !== null) {
            self.map.removeLayer(self.overlayLayer);
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
                self.map.addStatisticsLayer(function(l, error) {
                    self.toggleSpinner();
                    if (error) {
                        alert(error);
                        return;
                    }
                    self.overlayLayer = l;
                });
                break;
            case 'heatmap':
                self.map.addHeatmapLayer(HEATMAP_LAYER_URL, function(l, error) {
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
    
    this.checkFeedScroll = function() {
        // Determine scroll position
        var pos = $('#cards').scrollTop();
        if (pos > 0) {
            $('#new-tweets').css({top: pos + 10});
            self.pauseLiveFeed(true);
        } else {
            self.pauseLiveFeed(false);
            
            var hiddenLength = self.hiddenTweets().length;
            if (hiddenLength > 0) {
                for (var i = hiddenLength; i > 0; --i) {
                    self.tweets.unshift(self.hiddenTweets.shift());
                }
            }
        }
    };
    
    this.scrollToTop = function() {
        $('#cards').scrollTop(0);
    }
    
    this.newTweetsMessage = ko.computed(function() {
        return self.hiddenTweets().length + ' New'; 
    });
}

window.loadImages = function(obj) {
    Materialize.fadeInImage(obj);
    $(obj).parent().parent().css({height: $(obj).height()});  
};

$(document).ready(function() {
    function ResizeCards() {
        $('#cards').css('max-height', $(window).height() - 110);
    }
    
    var vm = new ViewModel();
    ko.applyBindings(vm);
    $(window).resize(ResizeCards);
    $('#cards').scroll(vm.checkFeedScroll);
    ResizeCards();
});