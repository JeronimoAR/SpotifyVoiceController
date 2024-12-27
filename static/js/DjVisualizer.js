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
        this.spotifyToken = null;
        
        this.setupCanvas();
        this.bindEvents();
        
        // Don't auto-start audio, wait for user interaction
        const startButton = document.getElementById('start');
        startButton.addEventListener('click', () => this.startAudioVisualization());
        
        this.animate();
    }

    async startAudioVisualization() {
        if (!this.audioContext) {
            await this.setupAudioContext();
        }
        
        try {
            await this.audioContext.resume();
            this.isPlaying = true;
            console.log('Audio context started:', this.audioContext.state);
        } catch (error) {
            console.error('Error starting audio context:', error);
        }
    }

    async setupSpotifyAudio() {
        try {
            const response = await fetch('/get-current-playback');
            const data = await response.json();
            
            if (data.is_playing) {
                console.log('Setting up audio for:', data.item.name);
                
                // Create audio element if it doesn't exist
                if (!this.audioElement) {
                    this.audioElement = new Audio();
                    this.audioElement.crossOrigin = "anonymous";
                    const source = this.audioContext.createMediaElementSource(this.audioElement);
                    source.connect(this.analyzer);
                }
                
                // Only try to play after user interaction
                if (this.audioContext.state === 'running') {
                    this.audioElement.src = data.item.preview_url;
                    await this.audioElement.play();
                }
            }
        } catch (error) {
            console.error('Error setting up Spotify audio:', error);
        }
    }

    async initializeAudio() {
        try {
            console.log('Initializing audio...');
            await this.setupAudioContext();
            console.log('Audio context setup complete');
            
            // Test if audio context is running
            console.log('AudioContext state:', this.audioContext.state);
            if (this.audioContext.state === 'suspended') {
                console.log('Audio context suspended, waiting for user interaction');
                // Add a button to start audio context
                const startButton = document.createElement('button');
                startButton.textContent = 'Start Audio';
                startButton.onclick = () => this.audioContext.resume();
                document.body.appendChild(startButton);
            }
        } catch (error) {
            console.error('Error initializing audio:', error);
        }
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

    async getSpotifyToken() {
        try {
            const response = await fetch('/get-spotify-token');
            if (!response.ok) {
                throw new Error('Failed to fetch token');
            }
            const data = await response.json();
            return data.access_token;
        } catch (error) {
            console.error('Error fetching token:', error);
            return null;
        }
    }

    setupSpotifyPlayer() {
        return new Promise(async (resolve, reject) => {
            try {
                // First get the token
                const token = await this.getSpotifyToken();
                if (!token) {
                    throw new Error('No token available');
                }

                // Create the player
                this.player = new Spotify.Player({
                    name: 'Voice Control Visualizer',
                    getOAuthToken: cb => { cb(token); },
                    volume: 0.5
                });

                // Error handling
                this.player.addListener('initialization_error', ({ message }) => {
                    console.error('Failed to initialize:', message);
                    reject(message);
                });

                this.player.addListener('authentication_error', ({ message }) => {
                    console.error('Failed to authenticate:', message);
                    reject(message);
                });

                this.player.addListener('account_error', ({ message }) => {
                    console.error('Failed to validate Spotify account:', message);
                    reject(message);
                });

                // Ready handling
                this.player.addListener('ready', ({ device_id }) => {
                    console.log('Ready with Device ID', device_id);
                    this.deviceId = device_id;
                    this.setupAudioContext();
                    resolve();
                });

                this.player.addListener('not_ready', ({ device_id }) => {
                    console.log('Device ID has gone offline', device_id);
                });

                // Connect to the player
                const connected = await this.player.connect();
                if (!connected) {
                    throw new Error('Failed to connect to Spotify');
                }

            } catch (error) {
                console.error('Error setting up Spotify player:', error);
                reject(error);
            }
        });
    }

    async setupAudioContext() {
        console.log('Setting up audio context');
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        
        // Create analyzer
        this.analyzer = this.audioContext.createAnalyser();
        this.analyzer.fftSize = 256;
        
        // Create gain node for volume control
        this.gainNode = this.audioContext.createGain();
        this.gainNode.gain.value = 0.5; // Set initial volume
        
        // Connect analyzer through gain node to destination
        this.gainNode.connect(this.audioContext.destination);
        this.analyzer.connect(this.gainNode);
        
        // Setup Spotify audio input
        await this.setupSpotifyAudio();
    }

    setupAudioAnalysis() {
        // Subscribe to state changes to get currently playing track
        this.player.addListener('player_state_changed', state => {
            if (state) {
                // Update audio element source when track changes
                const trackUri = state.track_window.current_track.uri;
                this.audioElement.src = `spotify:track:${trackUri}`;
                
                if (state.paused) {
                    this.audioElement.pause();
                } else {
                    this.audioElement.play();
                }
            }
        });
    }

    async setupMicrophone() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.micSource = this.audioContext.createMediaStreamSource(stream);
            this.micSource.connect(this.micAnalyzer);
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
                this.setupAudioContext();
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
        if (!this.analyzer || !this.isPlaying) return;

        const dataArray = new Uint8Array(this.analyzer.frequencyBinCount);
        this.analyzer.getByteFrequencyData(dataArray);

        const segments = 128;
        const angleStep = (Math.PI * 2) / segments;

        this.ctx.beginPath();
        for (let i = 0; i < segments; i++) {
            const angle = i * angleStep - Math.PI / 2;
            const value = dataArray[i] || 0;
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
window.addEventListener('load', async ()  => {
    await new Promise((resolve) => {
        if (window.Spotify) {
            resolve();
        } else {
            window.onSpotifyWebPlaybackSDKReady = resolve;
            const script = document.createElement('script');
            script.src = 'https://sdk.scdn.co/spotify-player.js';
            document.body.appendChild(script);
        }
    });

    const tipeo1 = new Typed(".multiple-message", {
        strings: ["Subir Volumen...", "Pausa...", "Siguiente...", "Continuar..."],
        typeSpeed: 70,
        backSpeed: 70,
        backDelay: 1000,
        loop: true,
        showCursor: false,
    });
    const visualizer = new DJVisualizer();
    const voiceControlToggle = document.getElementById('start');

    try {
        await visualizer.setupSpotifyPlayer();
        console.log('Spotify player setup complete');
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
                visualizer.recognition.stop();
                visualizer.message.innerHTML = `Inicia el reconocimiento de voz y dí: <span class="multiple-message"></span>`
                const tipeo2 = new Typed(".multiple-message", {
                    strings: ["Subir Volumen...", "Pausa...", "Siguiente...", "Continuar..."],
                    typeSpeed: 70,
                    backSpeed: 70,
                    backDelay: 1000,
                    loop: true,
                    showCursor: false,
                })
                voiceControlToggle.textContent = 'Start';
            }
        });
    } catch (error) {
        console.error('Failed to setup Spotify player:', error);
    }

    
});