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
    
    function addMarker(tweet) {
        var myIcon = L.divIcon();
        tweet.marker = L.marker([tweet.coordinates[1], tweet.coordinates[0]], { icon: myIcon }).addTo(map);
        return tweet;
    }
    
    return {
        addTopoJSONLayer: addTopoJSONLayer,
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
        data = self.map.addMarker(data);
        self.tweets.unshift(data);
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
                this.map.addHeatmapLayer('tweets/heatmap', function(l, error) {
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