const BASE_URL = window.location.origin;
let statusInterval;

function startCamera() {
   
    fetch(`${BASE_URL}/start`)
        .then(res => res.json())
        .then(() => {
            const video = document.getElementById("video");
            video.src = `${BASE_URL}/video_feed?t=${new Date().getTime()}`;
            video.style.display = "block";
            document.getElementById("startBtn").style.display = "none";
            document.getElementById("stopBtn").style.display = "inline-block";
            if (statusInterval) clearInterval(statusInterval);
            statusInterval = setInterval(updateStatus, 500);
        })
        .catch(err => console.error(err));
}

function stopCamera() {
    fetch(`${BASE_URL}/stop`)
        .then(res => res.json())
        .then(() => {
            const video = document.getElementById("video");
            video.src = "";
            video.style.display = "none";
            document.getElementById("startBtn").style.display = "inline-block";
            document.getElementById("stopBtn").style.display = "none";
            document.getElementById("status").innerText = "Camera Off";
            clearInterval(statusInterval);
        });
}

function updateStatus() {
    fetch(`${BASE_URL}/status`)
        .then(res => res.json())
        .then(data => {
            document.getElementById("status").innerText = data.status;
        });
}