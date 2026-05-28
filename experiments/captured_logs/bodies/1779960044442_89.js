console.log("FROM CUSTOM READER JS - TH");

const dateLine = () => {
    console.log('BL REader');
    var dateline = document.getElementsByClassName('dateline')[0];
    console.log(dateline.nextSibling);
    if (dateline.nextSibling) {
        linebreak = document.createElement("br");
        dateline.appendChild(linebreak);
    } else {

    }
}

var count = 0
var intervalID = setInterval(function () {
    count++
    if (count > 20) clearInterval(intervalID)
    
    var dateline = document.getElementsByClassName('dateline')[0];
    if (dateline.nextSibling) {
        linebreak = document.createElement("br");
        dateline.appendChild(linebreak);
        console.log('inter clear')
        clearInterval(intervalID);
    }
}, 1);
