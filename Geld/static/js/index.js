let user_id = '';
    function post_request(){
        const user = document.querySelector("#username");
        const email = document.querySelector("#email");
        const pass1 = document.querySelector("#password1");
        const pass2 = document.querySelector("#password2");
        const alert = document.querySelector("#alert_bar");

        data_ = {"username": user.value, "email": email.value,  "password1": pass1.value, "password2":pass2.value}
        $.ajax({
            type: 'GET',
            url: 'http://127.0.0.1:8000/signup/',
            dataType: 'json',
            data: data_,
            success: function (data) {
                if (data.hasOwnProperty('message')){
                    user.value = '';
                    email.value = '';
                    pass1.value = '';
                    pass2.value = '';
                    alert.setAttribute('style', 'display: block;');
                    alert.setAttribute('class','m-3 alert alert-success text-center');
                    alert.innerText = data.message.toString();
                    $("#alert_bar").fadeOut(5000);
                    window.open('login.html', '_self');
                }else if (data.hasOwnProperty('error')){
                    alert.setAttribute('style', 'display: block;');
                    alert.setAttribute('class','m-3 alert alert-danger text-center');
                    alert.innerText = data.error.toString();

                }else{
                console.log(data)
            }
        }},)

    }
    function login_request(){
    let username =  document.querySelector("#username").value;
    let password = document.querySelector("#password").value;
    const alert = document.querySelector("#login_alert");

    login_data = {'username': username, 'password': password}

    $.ajax({
            type: 'GET',
            url: 'http://127.0.0.1:8000/login/',
            dataType: 'json',
            data: login_data,
            success: function (data) {
                if (data.hasOwnProperty("message")){
                    console.log(data.message);
                    username = '';
                    password = '';
                    alert.setAttribute('style', 'display: block;');
                    alert.setAttribute('class','m-3 alert alert-success text-center');
                    alert.innerText = data.message;
                    $("#login_alert").fadeOut(5000);
                    console.log(data.id);
                    window.open('index.html','_self');
                    window.onload =()=>{
        $.ajax({
            type: 'GET',
            url: 'http://127.0.0.1:8000/dashboard/',
            dataType: 'json',
            success: function (data) {
                if (data.hasOwnProperty('username')){
                    $('#user_username').innerText = data.username;
                    console.log(data)
                }else if (data.hasOwnProperty('error')){
                    console.log(data.error);
                    const login_alert = document.querySelector('#dashboard_alert');
                    login_alert.setAttribute('style','display: block');
                    login_alert.setAttribute('class','m-3 alert alert-danger text-center');
                    login_alert.innerText = data.error
                }else{
                    console.log(data)
                }
            },})

    }

                }else if (data.hasOwnProperty("error")){
                    console.log(data.error);
                    alert.setAttribute('style', 'display: block;');
                    alert.setAttribute('class','col-sm-12 alert alert-danger text-center ');
                    alert.innerText = data.error;

                }else{
                    console.log(data);
                }
            }
        },);


}

function signout() {
    
}