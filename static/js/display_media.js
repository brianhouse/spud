
var setup = function() {
    var el = document.getElementById('media_thumbs');
    if (num_media > 1) {
        for (var m=0; m<num_media; m++) {
            var sq = document.createElement('a');
            sq.innerHTML = "&#9675;";
            sq.setAttribute('onClick', 'javascript:displayMedia(' + m + '); return false;'); 
            el.appendChild(sq);
        }
    }
    displayMedia(0);
}

var displayMedia = function(index) {
    index = parseInt(index);    
    if (isNaN(index)) index = 0;
    if (index != 0) {
        stopVideo(document.getElementById('media_0'));
    }
    for (var m=0; m<num_media; m++) {
        el = document.getElementById('media_' + m);
        if (m == index) {
            el.style.display = "block";
        } else {
            el.style.display = "none";
        }
    }
    if (num_media > 1) {
        var el = document.getElementById('media_thumbs');
        for (c in el.childNodes) {
            if (c == index + 1) {
                el.childNodes[c].innerHTML = "&#9679;";
            } else {
                el.childNodes[c].innerHTML = "&#9675;";
            }
        }
    }
}

var stopVideo = function(el) {
    var iframe = el.querySelector('iframe');
    var video = el.querySelector('video');
    if (iframe) {
        var iframeSrc = iframe.src;
        iframe.src = iframeSrc;
    }
    if (video) {
        video.pause();
    }
};

window.onload = setup;
