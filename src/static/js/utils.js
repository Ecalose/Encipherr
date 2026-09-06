function HideErrorMsg() {
        var error_message = document.getElementById('tohide');
        if (error_message && error_message.style.display == 'block') {
            error_message.style.display = 'none';
        }
}

function CloseMsg(){
        var error_message = document.getElementById('tohide');
        if (error_message) {
            error_message.style.display = 'none';
        }

}

// disable genkey button when key in custom mode.

$("#pwd").click( function() {
    $(':button.genkey').attr('disabled','disabled');
})

$("#aes").click( function(){
    $(':button.genkey').removeAttr("disabled");
})
