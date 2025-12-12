const API_URL = "http://localhost:8000";
let currentUser = null;
let currentToken = null;

async function register() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    try {
        const res = await fetch(`${API_URL}/register`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, password})
        });
        if (res.ok) {
            alert("Registered successfully! Please login.");
        } else {
            const data = await res.json();
            document.getElementById('auth-error').innerText = data.detail;
        }
    } catch (e) {
        document.getElementById('auth-error').innerText = "Connection error";
    }
}

async function login() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    try {
        const res = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, password})
        });
        
        if (res.ok) {
            const data = await res.json();
            currentUser = data.username;
            currentToken = data.token;
            showDashboard();
        } else {
            document.getElementById('auth-error').innerText = "Invalid credentials";
        }
    } catch (e) {
        document.getElementById('auth-error').innerText = "Connection error";
    }
}

function showDashboard() {
    hideAll();
    document.getElementById('dashboard-section').classList.remove('hidden');
    document.getElementById('welcome-msg').innerText = `Welcome, ${currentUser}`;
}

async function buyDiagnosis() {
    try {
        const res = await fetch(`${API_URL}/buy?username=${currentUser}`, {method: 'POST'});
        if (res.ok) {
            alert("Payment successful!");
            document.getElementById('start-btn').classList.remove('hidden');
        }
    } catch (e) {
        alert("Error processing payment");
    }
}

function startDiagnosisFlow() {
    hideAll();
    document.getElementById('consent-section').classList.remove('hidden');
}

function confirmConsent() {
    if (document.getElementById('consent-check').checked) {
        hideAll();
        document.getElementById('instruction-section').classList.remove('hidden');
    } else {
        alert("Please agree to the consent form.");
    }
}

function showRecorder() {
    hideAll();
    document.getElementById('recorder-section').classList.remove('hidden');
    // In a real app, we might autoplay the stimulus video here
    // document.getElementById('stimulus-video').style.display = 'block';
    // document.getElementById('stimulus-video').play();
}

async function uploadVideo() {
    const fileInput = document.getElementById('video-upload');
    if (fileInput.files.length === 0) {
        alert("Please record or select a video first.");
        return;
    }
    
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append("file", file);
    
    document.getElementById('upload-status').innerText = "Uploading...";
    
    try {
        const res = await fetch(`${API_URL}/upload_video?username=${currentUser}`, {
            method: 'POST',
            body: formData
        });
        
        if (res.ok) {
            const data = await res.json();
            const diagnosisId = data.diagnosis_id;
            document.getElementById('upload-status').innerText = "Processing...";
            pollResult(diagnosisId);
        } else {
            document.getElementById('upload-status').innerText = "Upload failed";
        }
    } catch (e) {
        document.getElementById('upload-status').innerText = "Error uploading";
    }
}

async function pollResult(diagnosisId) {
    hideAll();
    document.getElementById('result-section').classList.remove('hidden');
    const resultDiv = document.getElementById('result-content');
    
    const interval = setInterval(async () => {
        try {
            const res = await fetch(`${API_URL}/result/${diagnosisId}`);
            if (res.ok) {
                const data = await res.json();
                if (data.status === 'processing') {
                    resultDiv.innerText = "Analyzing eye movements... Please wait.";
                } else {
                    clearInterval(interval);
                    displayResult(data);
                }
            }
        } catch (e) {
            clearInterval(interval);
            resultDiv.innerText = "Error fetching results.";
        }
    }, 2000);
}

function displayResult(data) {
    const resultDiv = document.getElementById('result-content');
    const colorClass = data.risk_level === 'High' ? 'result-high' : 'result-low';
    
    resultDiv.innerHTML = `
        <h3>Risk Level: <span class="${colorClass}">${data.risk_level}</span></h3>
        <p>Score: ${data.score.toFixed(2)}</p>
        <p><strong>Recommendations:</strong> ${data.recommendations}</p>
    `;
}

function hideAll() {
    const sections = document.querySelectorAll('.container > div');
    sections.forEach(div => div.classList.add('hidden'));
}

function resetApp() {
    showDashboard();
}
