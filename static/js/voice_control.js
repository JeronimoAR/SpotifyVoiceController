document.addEventListener('DOMContentLoaded', function () {
    const voiceControlToggle = document.getElementById('voice-control-toggle');
    const voiceInstructions = document.getElementById('voice-instructions');
    let recognition;

    // Cross-browser media access request
    function requestMediaAccess() {
        // Prioritize modern methods
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            return navigator.mediaDevices.getUserMedia({ audio: true });
        }

        // Fallback to older methods
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

        // If no method works
        return Promise.reject(new Error('No getUserMedia method available'));
    }

    function startSpeechRecognition() {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'es-ES';

            recognition.onstart = function() {
                console.log('Speech recognition started');
                voiceControlToggle.textContent = '🔊 Deactivate Voice Control';
                voiceControlToggle.classList.remove('btn-success');
                voiceControlToggle.classList.add('btn-danger');
                voiceInstructions.style.display = 'block';
            };

            recognition.onend = function() {
                console.log('Speech recognition ended');
                voiceControlToggle.textContent = '🎙️ Activate Voice Control';
                voiceControlToggle.classList.remove('btn-danger');
                voiceControlToggle.classList.add('btn-success');
                voiceInstructions.style.display = 'none';
            };

            recognition.onresult = function(event) {
                const command = event.results[0][0].transcript;
                console.log('Recognized command:', command);

                fetch('/process_voice_command', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ command: command })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        console.log('Command executed:', data.action);
                        alert(`Executed: ${data.action}`);
                    } else {
                        console.error('Command failed:', data.message);
                        alert('Command not recognized');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('There was a problem processing the voice command');
                });
            };

            recognition.onerror = function(event) {
                console.error('Speech recognition error:', event.error);

                switch(event.error) {
                    case 'not-allowed':
                        alert('Speech recognition blocked. Please allow microphone access in your browser settings.');
                        break;
                    case 'no-speech':
                        alert('No speech was detected. Please try again.');
                        break;
                    case 'network':
                        alert('Network error occurred during speech recognition.');
                        break;
                    default:
                        alert('Speech recognition error: ' + event.error);
                }
            };
        } else {
            alert('Speech recognition not supported in this browser');
            voiceControlToggle.style.display = 'none';
        }
    }

    voiceControlToggle.addEventListener('click', function () {
        // Use our cross-browser media access method
        requestMediaAccess()
            .then(function() {
                if (!recognition) {
                    startSpeechRecognition();
                }

                if (voiceControlToggle.textContent.includes('Activate')) {
                    recognition.start();
                } else {
                    recognition.stop();
                }
            })
            .catch(function(err) {
                console.error('Microphone access denied:', err);
                alert('Microphone access is required for voice control. Please grant permission or check browser settings.');
            });
    });

});