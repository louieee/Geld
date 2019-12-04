const addhyphen =(element)=> {
    const ele = document.getElementById(element.id);
    ele.value = ele.value.split('-').join('');    // Remove dash (-) if mistakenly entered.
    document.getElementById(element.id).value = ele.value.match(/.{1,5}/g).join('-');
}