var MAX_UPDATE_RETRIES = 60;
var update_retries = 0;

toggle_button = function(button) {
    $.post('/api/toggle_' + button, function( data ) {
            set_button_status(button, data.state)
      });
}

set_button_status = function(button, state) {
    if (state) {
        $('#' + button).addClass('button-on');
    } else {
        $('#' + button).removeClass('button-on');
    }
}

update_status = function() {
    $.get('api/status', function(data) {
        $.each(data.switches, function(k, v) { set_button_status(k, v); });
    })
    .done(function() { update_retries = 0; })
    .fail(function() { update_retries++; });

    if (update_retries < MAX_UPDATE_RETRIES) {
        setTimeout(update_status, 1000);
    } else {
        console.log('Unable to reach server. Giving up!');
    }
}
