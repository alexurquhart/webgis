/*global ko*/
/*global L*/

function Map(element) {
    // Start the map
    var map = L.map('map').setView([44.09744824027576, -78.3709716796875], 8);
    L.tileLayer('http://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png').addTo(map);

    // Start a new route at the map center
    var startRoute = function() {
         
    };
    
    return {
        StartRoute: startRoute
    };
}

function ViewModel() {
    var self = this;
    self.map = new Map('map');
    self.map.StartRoute();
}

$(document).ready(function() {
    ko.applyBindings(new ViewModel());
    $('#cards').css('max-height', $(window).height() - 110 + "px");
});

$(window).resize(function() {
    $('#cards').css('max-height', $(window).height() - 110);
})