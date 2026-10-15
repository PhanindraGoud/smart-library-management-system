
document.addEventListener("DOMContentLoaded", function () {
    const voiceButton = document.getElementById("voiceButton");
    const searchInput = document.getElementById("searchInput");
    const voiceStatus = document.getElementById("voiceStatus");

    if (!voiceButton || !searchInput || !voiceStatus) {
        return;
    }

    const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        voiceButton.disabled = true;
        voiceStatus.textContent =
            "Voice search is not supported in this browser. Please use Chrome or Edge.";
        return;
    }

    const recognition = new SpeechRecognition();

    recognition.lang = "en-IN";
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    voiceButton.addEventListener("click", function () {
        voiceStatus.textContent = "Listening... Please speak a book title.";
        voiceButton.disabled = true;

        try {
            recognition.start();
        } catch (error) {
            voiceButton.disabled = false;
            voiceStatus.textContent =
                "Could not start voice search. Please try again.";
        }
    });

    recognition.addEventListener("result", function (event) {
        const transcript = event.results[0][0].transcript.trim();

        if (transcript) {
            searchInput.value = transcript;
            voiceStatus.textContent = "Searching for: " + transcript;

            searchInput.form.requestSubmit();
        } else {
            voiceStatus.textContent =
                "No speech detected. Please try again.";
        }
    });

    recognition.addEventListener("error", function (event) {
        const messages = {
            "not-allowed": "Please allow microphone access in your browser.",
            "no-speech": "No speech detected. Please try again.",
            "network": "A network error occurred during voice recognition.",
            "audio-capture": "No microphone was detected."
        };

        voiceStatus.textContent =
            messages[event.error] || "Voice search failed. Please try again.";
    });

    recognition.addEventListener("end", function () {
        voiceButton.disabled = false;
    });
});
