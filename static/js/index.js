
const signup=()=>{
    const alert = document.querySelector('#alert_signup');
    const username = document.querySelector('#username');
    const email = document.querySelector('#email');
    const pass1 = document.querySelector('#password1');
    const pass2 = document.querySelector('#password2');
    const data = {"username": username.value, "email": email.value, "password1": pass1.value, "password2": pass2.value};
    $.ajax({
            type: 'POST',
            url: 'http://127.0.0.1:8000/',
            dataType: 'json',
            data : data,
            success: function (data) {
                alert.className = 'm-3 alert alert-' + data.status + ' text-center';
                alert.innerText = data.message;
                if (data.status === 'info') {
                    pass1.value = pass2.value = email.value = username.value='';
                }
            }

            });
};
