class DJVisualizer {
    constructor() {
        this.canvas = document.getElementById('visualization-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.isPlaying = false;
        this.rotation = 0;
        this.audioData = new Uint8Array(128);
        this.micData = new Uint8Array(128);
        this.isRecognitionActive = false;
        this.recognition;
        this.message = document.getElementById('message');
        this.setupCanvas();
        this.setupAudioContext();
        this.bindEvents();
        this.animate();
    }

    setupCanvas() {
        const resize = () => {
            const container = this.canvas.parentElement;
            const size = container.offsetWidth;
            this.canvas.width = size;
            this.canvas.height = size;
            this.center = size / 2;
            this.radius = (size / 2) * 0.8;
        };

        resize();
        window.addEventListener('resize', resize);
    }

    setupAudioContext() {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.analyzer = this.audioContext.createAnalyser();
        this.analyzer.fftSize = 256;
        this.micAnalyzer = this.audioContext.createAnalyser();
        this.micAnalyzer.fftSize = 256;
    }

    async setupMicrophone() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const micSource = this.audioContext.createMediaStreamSource(stream);
            micSource.connect(this.micAnalyzer);
            return true;
        } catch (error) {
            console.error('Error accessing microphone:', error);
            return false;
        }
    }

    bindEvents() {
        document.getElementById('start').addEventListener('click', () => {
            this.isPlaying = !this.isPlaying;
            if (this.isPlaying) {
                this.audioContext.resume();
            }
        });

        document.getElementById('start').addEventListener('click', async () => {
            const success = await this.setupMicrophone();
        });

    }

    drawVinylDetails() {
        // Draw vinyl grooves
        for (let i = 0; i < 20; i++) {
            const radius = this.radius * (0.3 + i * 0.03);
            this.ctx.beginPath();
            this.ctx.arc(this.center, this.center, radius, 0, Math.PI * 2);
            this.ctx.strokeStyle = `rgba(40, 40, 40, ${0.5 - i * 0.02})`;
            this.ctx.lineWidth = 1;
            this.ctx.stroke();
        }

        // Draw label
        this.ctx.beginPath();
        this.ctx.arc(this.center, this.center, this.radius * 0.25, 0, Math.PI * 2);
        this.ctx.fillStyle = '#1DB954';
        this.ctx.fill();
    }

    drawWaveform() {
        this.analyzer.getByteFrequencyData(this.audioData);
        this.micAnalyzer.getByteFrequencyData(this.micData);

        const segments = 128;
        const angleStep = (Math.PI * 2) / segments;

        this.ctx.beginPath();
        for (let i = 0; i < segments; i++) {
            const angle = i * angleStep - Math.PI / 2;
            const value = (this.audioData[i] + this.micData[i]) / 2;
            const radius = this.radius + (value / 255) * 100;

            const x = this.center + Math.cos(angle) * radius;
            const y = this.center + Math.sin(angle) * radius;

            if (i === 0) {
                this.ctx.moveTo(x, y);
            } else {
                this.ctx.lineTo(x, y);
            }
        }
        this.ctx.closePath();
        this.ctx.strokeStyle = '#1DB954';
        this.ctx.lineWidth = 2;
        this.ctx.stroke();
    }


    startSpeechRecognition() {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            this.recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            this.recognition.continuous = true;  // Change to continuous
            this.recognition.interimResults = false;
            this.recognition.lang = 'es-ES';

            this.recognition.onstart = function () {
                this.isRecognitionActive = true;
            };

            this.recognition.onend = function () {
                this.isRecognitionActive = false;
            };

            this.recognition.onresult = function (event) {
                const command = event.results[event.results.length - 1][0].transcript;

                fetch('/process_voice_command', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ command: command })
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data != null) {
                            if (data.message != null) {
                                message.textContent = data.message;
                            } else if (data.action != null) {
                                console.log(data);
                                message.textContent = data.action;
                            }
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        alert('There was a problem processing the voice command');
                    });
            };

            this.recognition.onerror = function (event) {

                switch (event.error) {
                    case 'not-allowed':
                        alert('Speech recognition blocked. Please allow microphone access in your browser settings.');
                        this.isRecognitionActive = false;
                        break;
                    case 'no-speech':
                        // Ignore no-speech errors, continue listening
                        console.log('No speech detected, continuing...');
                        break;
                    case 'network':
                        alert('Network error occurred during speech recognition.');
                        this.isRecognitionActive = false;
                        break;
                    default:
                        alert('Speech recognition error: ' + event.error);
                        this.isRecognitionActive = false;
                }
            };
        } else {
            alert('Speech recognition not supported in this browser');
            voiceControlToggle.style.display = 'none';
        }
    }

    animate() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        if (this.isPlaying) {
            this.ctx.save();
            this.ctx.translate(this.center, this.center);
            this.ctx.rotate(this.rotation);
            this.ctx.translate(-this.center, -this.center);

            this.drawVinylDetails();

            this.ctx.restore();

            this.drawWaveform();

            this.rotation += 0.005;
        }

        requestAnimationFrame(() => this.animate());
    }
}

// Initialize visualizer when the page loads
window.addEventListener('load', () => {
    const visualizer = new DJVisualizer();
    const voiceControlToggle = document.getElementById('start');

    voiceControlToggle.addEventListener('click', function () {
        // Toggle recognition
        if (!visualizer.isRecognitionActive) {
            // Start recognition
            if (!visualizer.recognition) {
                visualizer.startSpeechRecognition();
            }
            visualizer.recognition.start();
            visualizer.isRecognitionActive = true;
            voiceControlToggle.textContent = 'Stop';
        } else {
            // Stop recognition
            visualizer.isRecognitionActive = false;
            visualizer .recognition.stop();
            voiceControlToggle.textContent = 'Start';
        }
    });
});