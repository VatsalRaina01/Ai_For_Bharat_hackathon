/**
 * Voice Module — Web Audio API for voice recording
 */

let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

/**
 * Toggle voice recording on/off
 */
async function toggleVoice() {
    if (isRecording) {
        stopRecording();
    } else {
        await startRecording();
    }
}

/**
 * Start recording audio
 */
async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1,
                sampleRate: 16000,
                echoCancellation: true,
                noiseSuppression: true,
            }
        });

        mediaRecorder = new MediaRecorder(stream, {
            mimeType: 'audio/webm;codecs=opus'
        });

        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });

            // Convert to base64
            const reader = new FileReader();
            reader.onload = async () => {
                const base64 = reader.result.split(',')[1];

                // For now, show a message since voice transcription is being set up
                switchToChat();
                addAssistantMessage(
                    "🎤 Voice input received! Voice transcription via Amazon Transcribe is being configured. " +
                    "Please type your message for now — I understand Hindi, English, and many Indian languages!",
                    null
                );
            };
            reader.readAsDataURL(audioBlob);

            // Stop all tracks
            stream.getTracks().forEach(track => track.stop());
        };

        mediaRecorder.start();
        isRecording = true;
        updateMicButtons(true);

    } catch (err) {
        console.error('Microphone error:', err);
        alert('माइक्रोफ़ोन तक पहुँच नहीं मिली। कृपया अनुमति दें। / Could not access microphone. Please grant permission.');
    }
}

/**
 * Stop recording
 */
function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
    }
    isRecording = false;
    updateMicButtons(false);
}

/**
 * Update mic button visuals
 */
function updateMicButtons(recording) {
    const heroMic = document.getElementById('heroMicBtn');
    const chatMic = document.getElementById('micBtn');

    if (heroMic) {
        heroMic.classList.toggle('recording', recording);
        heroMic.classList.toggle('pulse', !recording);
    }
    if (chatMic) {
        chatMic.classList.toggle('recording', recording);
    }
}
