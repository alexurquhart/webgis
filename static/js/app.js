var LIVEFEED_URL = "wss://" + window.location.hostname + (window.location.port ? ':' + window.location.port: '') + '/webgis/ws/';
var TILE_URL = 'http://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png';
var STATISTICS_LAYER_URL = 'data/divisions.topojson';
var HEATMAP_LAYER_URL = 'tweets/heatmap';
var PICTURES_URL = 'pictures/';


// Tweet card component for the live feed
ko.components.register('tweet-card', {
	template: { element: 'card-template' },
	viewModel: function (params) {
		var self = this;

		// Keep references to the parent map, and tweet data to display
		this.tweet = params.tweet;
		this.map = params.root.map;

		// Highlight the marker via the map controller when hovered over
		this.beginHover = function () {
			 self.map.highlightMarker(self.tweet.marker);
		};

		// End hightlight via the map controller when mouse out
		this.endHover = function () {
			self.map.unhighlightMarker(self.tweet.marker)
		};

		// Pan to tweet via the map controller when clicked
		this.panToTweet = function () {
			self.map.panToMarker(self.tweet.marker);
			return true;
		}

		// Zoom to the tweet via the map controller when double clicked
		this.zoomToTweet = function() {
			self.map.zoomToMarker(self.tweet.marker);
			return true;
		};
	}
});

function DivStatsViewModel(params) {
	var self = this;
	this.division = params.division;
	this.chart = null;

	// Startup Chart
	// Does a query for the latest data for the selected division, and either creates the chart
	// or updates the currently drawn one.
	this.startupChart = function() {
		$.getJSON('division/' + self.division().feature.id + '/histogram', function(data) {

			// First thing to do is separate the labels from the count data
			// The labels will only show every second hour, and midnight for
			// each day
			var labels = $.map(data, function(i) {
				var label = moment.utc(i.time).local();
				if (label.hours() === 0) {
					return label.format("MMM DD");
				} else if (label.hours() % 2 == 0) {
					return label.format("HH");
				} else {
					return '';
				}
			});

			var count = $.map(data, function(i) {
				return i.count;
			});

			// If no chart already - create a new bar chart
			if (!self.chart) {
				self.chart = new Chartist.Bar(
					'.div-barchart',
					{
						labels: labels,
						series: [count]
					},
					{
						chartPadding: {
							top: 0,
							right: 10,
							bottom: 30,
							left: 0
						},
						axisY: {
							onlyInteger: true
						},
						plugins: [
							Chartist.plugins.ctAxisTitle({
								axisX: {
									axisTitle: 'Hour',
									axisClass: 'ct-axis-title',
									offset: {
										x: 0,
										y: 40
									},
									textAnchor: 'middle'
								},
								axisY: {
									axisTitle: 'Tweets/Hour',
									axisClass: 'ct-axis-title',
									offset: {
										x: 0,
										y: 0
									},
									textAnchor: 'middle',
									flipTitle: false
								}
							})
						]
					}
				);
			} else {
				// Update the chart if one exists
				self.chart.update({labels: labels, series: [count]})
			}
		})
	};

	// Startup the chart on component start
	this.startupChart();

	// Subscribe to changes to the selected division and redraw the chart
	this.divSubscription = this.division.subscribe(function(newValue) {
		self.startupChart();
	});
};


// Get rid of the subscription when the component is disposed - 
// happens every time the back arrow on the statistics card is clicked
// or the user navigates to another layer
DivStatsViewModel.prototype.dispose = function() {
	this.divSubscription.dispose();
}

// Register the component
ko.components.register('div-stats', {
	template: { element: 'div-stats' },
	viewModel: DivStatsViewModel
});

// Active users view model
// Queries the endpoint and updates the data by subscribing to the selected
// division, in the same manner as the chart component
function ActiveUsersViewModel(params) {
	var self = this;
	this.division = params.division;

	this.hour = ko.observable(0);
	this.day = ko.observable(0);
	this.week = ko.observable(0);

	// Convert data to localeString for nice formatting
	this.updateData = function() {
		$.getJSON('division/' + self.division().feature.id + '/users', function(data) {
			self.hour(data.hour.toLocaleString());
			self.day(data.day.toLocaleString());
			self.week(data.week.toLocaleString());
		});
	};

	this.updateData();

	this.divSubscription = this.division.subscribe(function(newValue) {
		self.updateData();
	});
};

ActiveUsersViewModel.prototype.dispose = function() {
	this.divSubscription.dispose();
}

ko.components.register('active-users', {
	template: { element: 'active-users' },
	viewModel: ActiveUsersViewModel
});

function MapController() {
	var self = this;
	this.map = L.map('map').setView([44.09744824027576, -78.3709716796875], 8);
/*	this.map.on('moveend', function(e) {
		var bnds = self.map.getBounds().toBBoxString();
		var url = 
		$.get(PICTURES_URL + self.map.getBounds().toBBoxString(), function (data) {
			 console.log(data);
		})

	});*/
	this.activeLayer = null;
	L.tileLayer(TILE_URL).addTo(this.map);

	this.activateStatisticsLayer = function(selectCb) {
		var dfd = jQuery.Deferred();

		$.when($.getJSON(STATISTICS_LAYER_URL))
		.then(function(json) {
			var geojson = topojson.feature(json, json.objects.divisions);
			
			if (self.activeLayer !== null) {
				self.map.removeLayer(self.activeLayer);
			}

			self.activeLayer = L.geoJson(geojson, {
				onEachFeature: function(feature, layer) {
					layer.on('click', function(e) {
						selectCb({
							feature: e.target.feature.properties,
							selected: true
						});
					});

					layer.on('mouseover', function(e) {
						selectCb({
							feature: e.target.feature.properties,
							selected: false
						});
					});
				}
			});
			self.map.addLayer(self.activeLayer);
			dfd.resolve();

		}, function(jqxhr, textStatus, error) {
			dfd.reject(error);
		});
		return dfd.promise();
	};

	this.activateHeatmapLayer = function() {
		var dfd = jQuery.Deferred();
		
		$.getJSON(HEATMAP_LAYER_URL)
		.done(function(json) {
			self.activeLayer = L.heatLayer(json, {radius: 25});
			self.map.addLayer(self.activeLayer);
			dfd.resolve();
		})
		.fail(function(jqxhr, textStatus, error) {
			dfd.reject(error);
		});
		return dfd.promise();
	};

	this.removeActiveLayer = function () {
		if (self.activeLayer) {
			self.map.removeLayer(self.activeLayer);
			self.activeLayer = null;
		}
	};

	this.addMarker = function(tweet) {
		var myIcon = L.divIcon();
		tweet.marker = L.marker([tweet.coordinates[1], tweet.coordinates[0]], { icon: myIcon, title: tweet.unformattedText }).addTo(self.map);
		return tweet;
	};

	this.highlightMarker = function (marker) {
		var hlIcon = L.divIcon({className: 'marker-hover'});
		marker.setIcon(hlIcon);
	};

	this.unhighlightMarker = function(marker) {
		var myIcon = L.divIcon();
		marker.setIcon(myIcon);
	};

	this.panToMarker = function(marker) {
		self.map.panTo(marker.getLatLng());
	};

	this.zoomToMarker = function (marker) {
		self.map.setView(marker.getLatLng(), 18);
	};
}

function LiveFeed(cb) {
	var ws = new WebSocket(LIVEFEED_URL);

	// Adds emoji's, and links to URL's and hashtags
	function formatTweetText(tweet) {
		tweet.unformattedText = tweet.text;
		tweet.text = twemoji.parse(tweet.text, { size: 16 });

		// Make t.co links work
		var tco = /(https:\/\/t.co\/[A-Za-z0-9]+)/g;
		var matches = tweet.text.match(tco);
		if (matches) {
			$.each(matches, function(index, match) {
				tweet.text = tweet.text.replace(match, '<a href="' + match + '" target="new">' + match + '</a>');
			});
		}

		return tweet;
	}

	ws.onopen = function() {
		cb(null, "Connected");
	};

	// Restart the connection if it closes
	ws.onclose = function() { 
		window.setTimeout(function() {
			new LiveFeed(cb);
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

function AppViewModel() {
	var self = this;
	this.pane = ko.observable("livefeed");
	this.showSpinner = ko.observable(false);
	this.tweets = ko.observableArray();
	this.hoverDivision = ko.observable(null);
	this.selectedDivision = ko.observable(null);
	this.hiddenTweets = ko.observableArray();
	this.pauseLiveFeed = ko.observable(false);
	this.map = new MapController();
	this.livefeed = new LiveFeed(function (data, msg) {
		if (data !== null) {
			data = self.map.addMarker(data);
			
			if (self.pauseLiveFeed()) {
				self.hiddenTweets.unshift(data);
			} else {
				self.tweets.unshift(data);
			}
			
			// Delete the incoming tweet after 10 mins
			setTimeout(function() {
				self.checkFeedScroll();
				self.map.map.removeLayer(data.marker);
				self.tweets.remove(data);
				self.hiddenTweets.remove(data);
			}, 600000);
		}
		
		// Only display messages when the livefeed is the active overlay
		if (msg !== null && self.pane() === "livefeed") {
			Materialize.toast(msg, 3000);
		}
	});
	
	this.toggleSpinner = function() {
		this.showSpinner(!this.showSpinner());
	};

	this.selectDivision = function(newData) {
		if (!newData.selected) {
			self.hoverDivision(newData);
		} else {
			if (!self.selectedDivision() || self.selectedDivision().feature.id !== newData.feature.id) {
				self.selectedDivision(newData);
			}
		}
	};

	this.setOverlay = function(newLayer) {
		var oldLayer = self.pane();
		
		if (newLayer === oldLayer) {
			return;
		}

		self.pane(newLayer);
		self.toggleSpinner();
		self.selectedDivision(null);
		self.hoverDivision(null);
		
		if (oldLayer === 'livefeed') {
			$('.leaflet-marker-pane').hide();
		} else {
			self.map.removeActiveLayer();
		}
		
		switch(newLayer) {
			case 'livefeed':
				$('.leaflet-marker-pane').show();
				self.toggleSpinner();
				break;
			case 'statistics':
				self.map.activateStatisticsLayer(self.selectDivision)
				.fail(function (error) {
					 alert(error); 
				})
				.always(function () {
					self.toggleSpinner();
				})
				break;
			case 'trends':
				self.toggleSpinner()
				break;
			case 'heatmap':
				self.map.activateHeatmapLayer()
				.fail(function (error) {
					 alert(error); 
				})
				.always(function () {
					self.toggleSpinner();
				})
				break;
		}
	};

	this.checkFeedScroll = function() {
		// Determine scroll position
		var pos = $('#cards').scrollTop();
		if (pos > 0 && self.pane() === 'livefeed') {
			$('#new-tweets').css({top: pos + 10});
			self.pauseLiveFeed(true);
		} else {
			self.pauseLiveFeed(false);
			
			var hiddenLength = self.hiddenTweets().length;
			var hidTweetsRev = self.hiddenTweets.reverse();
			if (hiddenLength > 0) {
				for (var i = 0; i < hiddenLength; i++) {
					self.tweets.unshift(hidTweetsRev.shift());
				}
			}
		}
	};

	this.newTweetsMessage = ko.computed(function() {
		return self.hiddenTweets().length + ' New'; 
	});
	
	this.scrollToTop = function() {
		$('#cards').scrollTop(0);
	};
}

window.loadImages = function(obj) {
	Materialize.fadeInImage(obj);
	$(obj).parent().parent().css({height: $(obj).height()});  
};

$(document).ready(function() {
	var vm = new AppViewModel()
	$(window).resize(function () {
		$('#cards').css('max-height', $(window).height() - 110);
	});
	$('#cards').scroll(vm.checkFeedScroll);
	$(window).trigger('resize');
	ko.applyBindings(vm);
});