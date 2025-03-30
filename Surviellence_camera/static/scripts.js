document.addEventListener("DOMContentLoaded", function () {
    const video = document.getElementById("camera-feed");
    const sourceElement = document.getElementById("video-source");
    const selectMode = document.getElementById("video-mode");
    const startBtn = document.getElementById("start-btn");
    const stopBtn = document.getElementById("stop-btn");
    const themeSelect = document.getElementById("theme");
    const body = document.body;
    const alertBox = document.getElementById("alert-box");
    const alertMessage = document.getElementById("alert-message");
    const alertAudio = document.getElementById("alert-audio");

    let cameraIP = null;
    let userInteracted = false; // Tracks if the user has interacted with the page

    // ✅ Fetch settings (Camera IP, Theme)
    function fetchSettings() {
        fetch("/get_settings")
            .then(response => response.json())
            .then(data => {
                cameraIP = data.camera_ip;
                const savedTheme = data.theme || "light";
                body.className = savedTheme;
                if (themeSelect) themeSelect.value = savedTheme;
            })
            .catch(error => console.error("Error fetching settings:", error));
    }

    fetchSettings();

    // ✅ Start live camera feed
    async function startCamera() {
        try {
            stopCamera();
            if (cameraIP) {
                video.src = `http://${cameraIP}/video_feed`;
                video.play();
            } else {
                console.error("Camera IP not set. Configure in settings.");
            }
        } catch (error) {
            console.error("Error accessing camera:", error);
        }
    }

    // ✅ Stop camera feed
    function stopCamera() {
        video.pause();
        video.src = "";
    }

    // ✅ Handle mode selection
    selectMode.addEventListener("change", function () {
        stopCamera();
        if (this.value === "live") {
            startCamera();
        } else {
            sourceElement.src = this.value;
            video.load();
            video.play().catch(error => console.log("Play error:", error));
        }
    });

    // ✅ Start & Stop Button Handlers
    if (startBtn) startBtn.addEventListener("click", startCamera);
    if (stopBtn) stopBtn.addEventListener("click", stopCamera);

    // ✅ Logout Modal
    const logoutBtn = document.getElementById("logout-btn");
    const logoutModal = document.getElementById("logout-modal");
    const confirmLogoutBtn = document.getElementById("confirm-logout");
    const cancelLogoutBtn = document.getElementById("cancel-logout");

    if (logoutBtn && logoutModal) {
        logoutBtn.addEventListener("click", () => logoutModal.style.display = "block");
        cancelLogoutBtn.addEventListener("click", () => logoutModal.style.display = "none");
        confirmLogoutBtn.addEventListener("click", () => window.location.href = "/logout");
    }

    // ✅ Show Alerts (MQTT + Fetch)
    function showAlert(message, audioSrc) {
        alertMessage.textContent = message;
        alertAudio.src = audioSrc;  // Ensure the audio path is correct (static/audio/)
        
        // Pause and reset audio before playing
        alertAudio.pause();
        alertAudio.currentTime = 0;

        // Only play the sound if the user has interacted with the page
        if (userInteracted) {
            alertAudio.play().catch(error => console.error("Error playing alert sound:", error));
        }

        alertBox.classList.remove("hidden");
        setTimeout(() => {
            alertBox.classList.add("hidden");
        }, 5000);
    }

    // ✅ Fetch Alerts Periodically
    function fetchAlerts() {
        fetch("/get_alert")
            .then(response => response.json())
            .then(data => {
                if (data.alert) {
                    showAlert(data.message, data.audio);  // The audio is from static/audio/ folder
                }
            })
            .catch(error => console.error("Error fetching alerts:", error));
    }

    setInterval(fetchAlerts, 5000);

    // ✅ Handle Theme Change
    if (themeSelect) {
        themeSelect.addEventListener("change", function () {
            const selectedTheme = this.value;
            body.className = selectedTheme;
            fetch("/save_theme", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ theme: selectedTheme })
            }).catch(error => console.error("Error saving theme:", error));
        });
    }

    // ✅ MQTT WebSocket Integration (REAL-TIME ALERTS)
    const socket = io();  // Connect WebSocket to Server

    socket.on("mqtt_alert", function (data) {
        console.log("🚨 Alert Received:", data.message);
        showAlert(data.message, data.audio);  // Show alert and play sound only on actual detection
    });

    // ✅ Handle saving settings
    function saveSettings() {
        const settings = {
            camera_ip: cameraIP,
            theme: themeSelect.value
        };

        fetch("/save_settings", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(settings)
        })
        .then(response => response.json())
        .then(data => {
            console.log("Settings saved:", data);
        })
        .catch(error => console.error("Error saving settings:", error));
    }

    // Add event listener to save settings when the form is submitted or settings are changed
    document.getElementById("save-settings-btn").addEventListener("click", saveSettings);

    // ✅ Start Detection Button Handler
    const startDetectionBtn = document.querySelector("#startDetection");
    if (startDetectionBtn) {
        startDetectionBtn.addEventListener("click", function () {
            userInteracted = true; // Mark that the user interacted
            fetch("/start_detection", {
                method: "POST",
            })
            .then(response => response.json())
            .then(data => {
                console.log("Detection started:", data.message);
            })
            .catch(error => console.error("Error starting detection:", error));
        });
    }

    // WebSocket for real-time detection updates
    const detectionSocket = io.connect('http://' + document.domain + ':' + location.port);

    detectionSocket.on('mqtt_alert', function (data) {
        // Display the alert message or trigger an action when an alert is received
        showAlert(data.message, data.audio);  // Show alert and play sound only on actual detection
    });

    detectionSocket.on('detection_result', function (data) {
        // Handle the detection result
        console.log("Detection result received:", data.message);
        // Display the result in the UI, or handle it based on the detection type
    });
});

