const BASE_URL = window.location.origin;
let statusInterval;

function startCamera() {
<<<<<<< HEAD
    fetch(`${BASE_URL}/start`)
        .then(res => res.json())
        .then(data => {
            const video = document.getElementById("video");
            video.src = `${BASE_URL}/video_feed?t=${new Date().getTime()}`;
            video.style.display = "block";
            
            document.getElementById("startBtn").style.display = "none";
            document.getElementById("stopBtn").style.display = "inline-block";
            
            if (statusInterval) clearInterval(statusInterval);
            statusInterval = setInterval(updateStatus, 500);
        })
        .catch(err => console.error("Error starting camera:", err));
=======
   
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
>>>>>>> 8cc50a40e23d187c9bc3ae684cc5be9cbdbbbba7
}

function stopCamera() {
    fetch(`${BASE_URL}/stop`)
        .then(res => res.json())
        .then(() => {
            const video = document.getElementById("video");
            video.src = "";
            video.style.display = "none";
<<<<<<< HEAD
            
            document.getElementById("startBtn").style.display = "inline-block";
            document.getElementById("stopBtn").style.display = "none";
            
            clearInterval(statusInterval);
            document.getElementById("status").innerText = "Camera Off";
=======
            document.getElementById("startBtn").style.display = "inline-block";
            document.getElementById("stopBtn").style.display = "none";
            document.getElementById("status").innerText = "Camera Off";
            clearInterval(statusInterval);
>>>>>>> 8cc50a40e23d187c9bc3ae684cc5be9cbdbbbba7
        });
}

function updateStatus() {
    fetch(`${BASE_URL}/status`)
        .then(res => res.json())
        .then(data => {
<<<<<<< HEAD
            const statusElement = document.getElementById("status");
            statusElement.innerText = data.status;

            if (data.status === "Walking") statusElement.style.color = "#38bdf8";
            else if (data.status === "Sitting") statusElement.style.color = "#facc15";
            else if (data.status === "Standing") statusElement.style.color = "#2af30b";
            else if (data.status === "No Person Detected") statusElement.style.color = "#ff4444";
=======
            document.getElementById("status").innerText = data.status;
>>>>>>> 8cc50a40e23d187c9bc3ae684cc5be9cbdbbbba7
        });
}