document.addEventListener('DOMContentLoaded', function () {
    const voiceControlToggle = document.getElementById('voice-control-toggle');
    const voiceInstructions = document.getElementById('voice-instructions');
    let recognition;
    let isRecognitionActive = false;

    // Cross-browser media access request
    function requestMediaAccess() {
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            return navigator.mediaDevices.getUserMedia({ audio: true });
        }

        const getUserMedia =
            navigator.getUserMedia ||
            navigator.webkitGetUserMedia ||
            navigator.mozGetUserMedia ||
            navigator.msGetUserMedia;

        if (getUserMedia) {
            return new Promise((resolve, reject) => {
                getUserMedia.call(navigator, { audio: true }, resolve, reject);
            });
        }

        return Promise.reject(new Error('No getUserMedia method available'));
    }

    function startSpeechRecognition() {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            recognition.continuous = true;  // Change to continuous
            recognition.interimResults = false;
            recognition.lang = 'es-ES';

            recognition.onstart = function() {
                isRecognitionActive = true;
                voiceControlToggle.textContent = '🔊 Desactiva el Control de Voz';
                voiceControlToggle.classList.remove('btn-success');
                voiceControlToggle.classList.add('btn-danger');
                voiceInstructions.style.display = 'block';
            };

            recognition.onend = function() {

                voiceControlToggle.textContent = '🎙️ Activa el Control de Voz';
                voiceControlToggle.classList.remove('btn-danger');
                voiceControlToggle.classList.add('btn-success');
                voiceInstructions.style.display = 'none';

                // Automatically restart if still meant to be active
                if (isRecognitionActive) {
                    recognition.start();
                }

                isRecognitionActive = false;
            };

            recognition.onresult = function(event) {
                const command = event.results[event.results.length - 1][0].transcript;

                fetch('/process_voice_command', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ command: command })
                })
                .then(response => response.json())
                .catch(error => {
                    console.error('Error:', error);
                    alert('There was a problem processing the voice command');
                });
            };

            recognition.onerror = function(event) {

                switch(event.error) {
                    case 'not-allowed':
                        alert('Speech recognition blocked. Please allow microphone access in your browser settings.');
                        isRecognitionActive = false;
                        break;
                    case 'no-speech':
                        // Ignore no-speech errors, continue listening
                        console.log('No speech detected, continuing...');
                        break;
                    case 'network':
                        alert('Network error occurred during speech recognition.');
                        isRecognitionActive = false;
                        break;
                    default:
                        alert('Speech recognition error: ' + event.error);
                        isRecognitionActive = false;
                }
            };
        } else {
            alert('Speech recognition not supported in this browser');
            voiceControlToggle.style.display = 'none';
        }
    }

    voiceControlToggle.addEventListener('click', function () {
        // Toggle recognition
        if (!isRecognitionActive) {
            // Start recognition
            requestMediaAccess()
                .then(function() {
                    if (!recognition) {
                        startSpeechRecognition();
                    }
                    recognition.start();
                })
                .catch(function(err) {
                    console.error('Microphone access denied:', err);
                    alert('Microphone access is required for voice control. Please grant permission or check browser settings.');
                });
        } else {
            // Stop recognition
            isRecognitionActive = false;
            recognition.stop();
        }
    });
});