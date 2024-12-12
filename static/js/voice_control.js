document.addEventListener('DOMContentLoaded', function () {
    const voiceControlToggle = document.getElementById('voice-control-toggle');
    const voiceInstructions = document.getElementById('voice-instructions');

    voiceControlToggle.addEventListener('click', function () {
        fetch('/toggle_voice_control', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    if (data.status === 'active') {
                        voiceControlToggle.textContent = '🔊 Deactivate Voice Control';
                        voiceControlToggle.classList.remove('btn-success');
                        voiceControlToggle.classList.add('btn-danger');
                        voiceInstructions.style.display = 'block';
                    } else {
                        voiceControlToggle.textContent = '🎙️ Activate Voice Control';
                        voiceControlToggle.classList.remove('btn-danger');
                        voiceControlToggle.classList.add('btn-success');
                        voiceInstructions.style.display = 'none';
                    }
                } else {
                    alert(data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('There was a problem toggling voice control');
            });
    });
});