document.addEventListener("DOMContentLoaded", function () {
    var modeButtons = document.querySelectorAll(".mode-button");
    var panels = document.querySelectorAll(".mode-panel");
    var submitButton = document.querySelector(".submit-button");
    var contextText = document.getElementById("context-text");

    // Camera
    var cameraPreview = document.querySelector(".camera-preview");
    var captureButton = document.querySelector(".capture-button");
    var cameraCanvas = document.querySelector(".camera-canvas");
    var cameraStream = null;
    var capturedBlob = null;

    // Upload
    var fileInput = document.getElementById("file-input");
    var dropzone = document.querySelector(".upload-dropzone");
    var uploadPreview = document.querySelector(".upload-preview");
    var previewImage = document.querySelector(".preview-image");
    var previewFilename = document.querySelector(".preview-filename");
    var previewRemove = document.querySelector(".preview-remove");
    var uploadedFile = null;

    // Voice
    var recordButton = document.querySelector(".record-button");
    var voiceStatus = document.querySelector(".voice-status");
    var voiceVisualizer = document.querySelector(".voice-visualizer");
    var voiceTimer = document.querySelector(".voice-timer");
    var voiceRecorder = document.querySelector(".voice-recorder");
    var mediaRecorder = null;
    var audioChunks = [];
    var recordedBlob = null;
    var timerInterval = null;
    var recordStartTime = null;

    // Results
    var resultsCard = document.querySelector(".results-card");
    var resultsDismiss = document.querySelector(".results-dismiss");
    var resultsReasoning = document.querySelector(".results-reasoning");
    var reasoningText = document.querySelector(".reasoning-text");
    var resultsFields = document.querySelector(".results-fields");

    // Chat
    var chatRolePicker = document.getElementById("chat-role-picker");
    var chatContainer = document.getElementById("chat-container");
    var chatProgress = document.getElementById("chat-progress");
    var chatMessages = document.getElementById("chat-messages");
    var chatInput = document.getElementById("chat-input");
    var chatSendBtn = document.getElementById("chat-send");
    var chatMicBtn = document.getElementById("chat-mic");
    var chatMuteBtn = document.getElementById("chat-mute");
    var chatSessionId = null;
    var chatSummaryText = null;
    var chatStarted = false;
    var chatHasUserMessage = false;
    var chatRole = null;

    // TTS / STT state
    var ttsEnabled = true;
    var ttsAudio = null;
    var chatMicRecorder = null;
    var chatMicChunks = [];
    var chatMicRecording = false;

    var activeMode = "chat";

    // --- Mode switching ---

    modeButtons.forEach(function (btn) {
        btn.addEventListener("click", function () {
            activeMode = btn.getAttribute("data-mode");

            modeButtons.forEach(function (b) {
                b.setAttribute("aria-selected", b === btn ? "true" : "false");
            });
            panels.forEach(function (p) {
                p.classList.toggle("active", p.getAttribute("data-panel") === activeMode);
            });

            if (activeMode === "camera") startCamera();
            else stopCamera();

            if (activeMode !== "voice") stopRecording();

            if (activeMode === "chat" && !chatStarted) showRolePicker();

            updateSubmitState();
        });
    });

    function updateSubmitState() {
        var hasInput =
            (activeMode === "text" && contextText.value.trim().length > 0) ||
            (activeMode === "camera" && capturedBlob) ||
            (activeMode === "upload" && uploadedFile) ||
            (activeMode === "voice" && recordedBlob) ||
            (activeMode === "chat" && chatHasUserMessage);
        submitButton.disabled = !hasInput;
    }

    // --- Chat ---

    function createStreamBubble(role) {
        var bubble = document.createElement("div");
        bubble.className = "chat-bubble chat-" + role;
        chatMessages.appendChild(bubble);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return bubble;
    }

    function addSpeakerButton(bubble) {
        var btn = document.createElement("button");
        btn.className = "bubble-speaker";
        btn.setAttribute("aria-label", "Play audio");
        btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="14" height="14"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>';
        bubble.appendChild(btn);
    }

    function renderMarkdown(text) {
        if (typeof marked !== "undefined" && marked.parse) {
            return marked.parse(text, { breaks: true });
        }
        return text.replace(/\n/g, "<br>");
    }

    function finalizeBubbleText(bubble) {
        if (!bubble) return;
        // Store plain text for TTS before rendering markdown
        bubble.setAttribute("data-text", bubble.textContent);
        // Render markdown to HTML for assistant bubbles
        if (bubble.classList.contains("chat-assistant") && !bubble.classList.contains("chat-typing")) {
            var rawText = bubble.textContent;
            bubble.innerHTML = renderMarkdown(rawText);
            bubble.classList.add("markdown-body");
            addSpeakerButton(bubble);
        }
    }

    function appendChatBubble(text, role) {
        var bubble = createStreamBubble(role);
        bubble.textContent = text;
        if (role === "assistant") {
            bubble.setAttribute("data-text", text);
            addSpeakerButton(bubble);
        }
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return bubble;
    }

    function setChatLoading(on) {
        var existing = chatMessages.querySelector(".chat-typing");
        if (on && !existing) {
            var el = document.createElement("div");
            el.className = "chat-bubble chat-assistant chat-typing";
            el.innerHTML = '<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>';
            chatMessages.appendChild(el);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        } else if (!on && existing) {
            existing.remove();
        }
    }

    function readSSE(url, options, onToken, onDone) {
        fetch(url, options).then(function (res) {
            var reader = res.body.getReader();
            var decoder = new TextDecoder();
            var buffer = "";

            function processLines(lines) {
                lines.forEach(function (line) {
                    if (line.startsWith("data: ")) {
                        var data = JSON.parse(line.slice(6));
                        if (data.token) onToken(data.token);
                        if (data.done) onDone(data);
                    }
                });
            }

            function read() {
                reader.read().then(function (result) {
                    if (result.done) {
                        // Process any remaining data in buffer when stream ends
                        if (buffer.trim()) {
                            processLines(buffer.split("\n"));
                        }
                        return;
                    }
                    buffer += decoder.decode(result.value, { stream: true });
                    var lines = buffer.split("\n");
                    buffer = lines.pop();
                    processLines(lines);
                    read();
                });
            }
            read();
        }).catch(function () {
            onDone({ error: true });
        });
    }

    function updateFieldProgress(status) {
        if (!status) return;
        var collected = status.collected || [];
        var missing = status.missing || [];
        var allFields = collected.concat(missing);
        if (allFields.length === 0) return;

        chatProgress.innerHTML = "";
        allFields.forEach(function (field) {
            var pill = document.createElement("span");
            var done = collected.indexOf(field) !== -1;
            pill.className = "progress-pill" + (done ? " progress-done" : "");
            pill.textContent = field;
            chatProgress.appendChild(pill);
        });
        chatProgress.hidden = false;
    }

    function trimStatusFromBubble(bubble) {
        if (!bubble) return;
        bubble.textContent = bubble.textContent.replace(/\s*<!--STATUS::[\s\S]*?-->\s*$/, "").trimEnd();
    }

    function showRolePicker() {
        chatRolePicker.hidden = false;
        chatContainer.hidden = true;
    }

    function startChat(role) {
        chatRole = role;
        chatStarted = true;
        chatHasUserMessage = false;
        chatMessages.innerHTML = "";
        chatSummaryText = null;
        chatProgress.innerHTML = "";
        chatProgress.hidden = true;
        chatRolePicker.hidden = true;
        chatContainer.hidden = false;
        setChatLoading(true);
        chatInput.disabled = true;

        var bubble = null;
        readSSE("/chat-start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ role: role })
        },
            function (token) {
                if (!bubble) {
                    setChatLoading(false);
                    bubble = createStreamBubble("assistant");
                }
                bubble.textContent += token;
                chatMessages.scrollTop = chatMessages.scrollHeight;
            },
            function (data) {
                setChatLoading(false);
                if (data.error) {
                    appendChatBubble("Failed to start chat. Please try again.", "assistant");
                    chatStarted = false;
                    return;
                }
                chatSessionId = data.session_id;
                if (data.field_status) updateFieldProgress(data.field_status);
                trimStatusFromBubble(bubble);
                finalizeBubbleText(bubble);
                speakText(bubble ? bubble.getAttribute("data-text") : "", bubble);
                chatInput.disabled = false;
                chatInput.focus();
                updateInputButtons();
            }
        );
    }

    document.querySelectorAll(".role-picker-btn").forEach(function (btn) {
        btn.addEventListener("click", function () {
            startChat(btn.getAttribute("data-role"));
        });
    });

    function sendChatMessage() {
        var text = chatInput.value.trim();
        if (!text || !chatSessionId) return;

        appendChatBubble(text, "user");
        chatInput.value = "";
        chatInput.disabled = true;
        chatHasUserMessage = true;
        updateSubmitState();
        setChatLoading(true);

        var bubble = null;
        readSSE("/chat-message", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: chatSessionId, message: text })
        },
            function (token) {
                if (!bubble) {
                    setChatLoading(false);
                    bubble = createStreamBubble("assistant");
                }
                bubble.textContent += token;
                chatMessages.scrollTop = chatMessages.scrollHeight;
            },
            function (data) {
                setChatLoading(false);
                if (data.error) {
                    appendChatBubble("Something went wrong. Please try again.", "assistant");
                }
                if (data.field_status) updateFieldProgress(data.field_status);
                trimStatusFromBubble(bubble);
                finalizeBubbleText(bubble);
                speakText(bubble ? bubble.getAttribute("data-text") : "", bubble);
                chatInput.disabled = false;
                chatInput.focus();
                updateInputButtons();
            }
        );
    }

    chatSendBtn.addEventListener("click", sendChatMessage);
    chatInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });

    // --- Mic / Send button swap ---

    function updateInputButtons() {
        var hasText = chatInput.value.trim().length > 0;
        chatSendBtn.hidden = !hasText;
        chatMicBtn.hidden = hasText || chatMicRecording;
    }

    chatInput.addEventListener("input", function () {
        updateInputButtons();
        updateSubmitState();
    });

    // --- TTS ---

    function stopTTS() {
        if (ttsAudio) {
            ttsAudio.pause();
            ttsAudio.currentTime = 0;
            ttsAudio = null;
        }
    }

    function speakText(text, bubble) {
        if (!ttsEnabled || !text) return;
        stopTTS();

        fetch("/tts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: text })
        })
            .then(function (res) { return res.blob(); })
            .then(function (blob) {
                var url = URL.createObjectURL(blob);
                ttsAudio = new Audio(url);
                ttsAudio.play();
                if (bubble) bubble.classList.add("chat-speaking");
                ttsAudio.addEventListener("ended", function () {
                    if (bubble) bubble.classList.remove("chat-speaking");
                    URL.revokeObjectURL(url);
                    ttsAudio = null;
                });
            })
            .catch(function () { });
    }

    // Mute toggle
    chatMuteBtn.addEventListener("click", function () {
        ttsEnabled = !ttsEnabled;
        chatMuteBtn.querySelector(".mute-icon-on").hidden = !ttsEnabled;
        chatMuteBtn.querySelector(".mute-icon-off").hidden = ttsEnabled;
        chatMuteBtn.classList.toggle("muted", !ttsEnabled);
        if (!ttsEnabled) stopTTS();
    });

    // Click speaker icon on bubble to replay
    chatMessages.addEventListener("click", function (e) {
        var btn = e.target.closest(".bubble-speaker");
        if (!btn) return;
        var bubble = btn.closest(".chat-bubble");
        if (bubble) speakText(bubble.getAttribute("data-text"), bubble);
    });

    // --- STT (chat mic) ---

    function startChatMic() {
        chatMicChunks = [];
        chatMicRecording = true;
        chatMicBtn.classList.add("recording");
        chatMicBtn.hidden = false;
        chatSendBtn.hidden = true;
        chatInput.disabled = true;
        chatInput.placeholder = "Listening...";

        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(function (stream) {
                chatMicRecorder = new MediaRecorder(stream);
                chatMicRecorder.addEventListener("dataavailable", function (e) {
                    if (e.data.size > 0) chatMicChunks.push(e.data);
                });
                chatMicRecorder.addEventListener("stop", function () {
                    stream.getTracks().forEach(function (t) { t.stop(); });
                    var blob = new Blob(chatMicChunks, { type: "audio/webm" });
                    chatMicRecording = false;
                    chatMicBtn.classList.remove("recording");
                    chatInput.placeholder = "Transcribing...";
                    transcribeChatAudio(blob);
                });
                chatMicRecorder.start();
            })
            .catch(function () {
                chatMicRecording = false;
                chatMicBtn.classList.remove("recording");
                chatInput.disabled = false;
                chatInput.placeholder = "Type your response...";
            });
    }

    function stopChatMic() {
        if (chatMicRecorder && chatMicRecorder.state === "recording") {
            chatMicRecorder.stop();
        }
    }

    function transcribeChatAudio(blob) {
        var fd = new FormData();
        fd.append("file", blob, "chat_audio.webm");

        fetch("/stt", { method: "POST", body: fd })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                chatInput.disabled = false;
                chatInput.placeholder = "Type your response...";
                if (data.transcript) {
                    chatInput.value = data.transcript;
                    updateInputButtons();
                    sendChatMessage();
                }
            })
            .catch(function () {
                chatInput.disabled = false;
                chatInput.placeholder = "Type your response...";
            });
    }

    chatMicBtn.addEventListener("click", function () {
        if (chatMicRecording) {
            stopChatMic();
        } else {
            startChatMic();
        }
    });

    contextText.addEventListener("input", updateSubmitState);

    // --- Camera ---

    function startCamera() {
        if (cameraStream) return;
        navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } })
            .then(function (stream) {
                cameraStream = stream;
                cameraPreview.srcObject = stream;
            })
            .catch(function () { });
    }

    function stopCamera() {
        if (!cameraStream) return;
        cameraStream.getTracks().forEach(function (t) { t.stop(); });
        cameraStream = null;
        cameraPreview.srcObject = null;
    }

    captureButton.addEventListener("click", function () {
        if (!cameraStream) return;
        cameraCanvas.width = cameraPreview.videoWidth;
        cameraCanvas.height = cameraPreview.videoHeight;
        cameraCanvas.getContext("2d").drawImage(cameraPreview, 0, 0);
        cameraCanvas.toBlob(function (blob) {
            capturedBlob = blob;
            captureButton.setAttribute("aria-pressed", "true");
            updateSubmitState();
        }, "image/jpeg", 0.9);
    });

    // --- Upload ---

    fileInput.addEventListener("change", function () {
        if (fileInput.files.length > 0) handleFile(fileInput.files[0]);
    });

    dropzone.addEventListener("dragover", function (e) {
        e.preventDefault();
        dropzone.classList.add("dragover");
    });
    dropzone.addEventListener("dragleave", function () {
        dropzone.classList.remove("dragover");
    });
    dropzone.addEventListener("drop", function (e) {
        e.preventDefault();
        dropzone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) handleFile(e.dataTransfer.files[0]);
    });

    function handleFile(file) {
        uploadedFile = file;
        previewFilename.textContent = file.name;
        if (file.type.startsWith("image/")) {
            var reader = new FileReader();
            reader.onload = function (e) { previewImage.src = e.target.result; };
            reader.readAsDataURL(file);
        } else {
            previewImage.src = "";
        }
        dropzone.hidden = true;
        uploadPreview.hidden = false;
        updateSubmitState();
    }

    previewRemove.addEventListener("click", function () {
        uploadedFile = null;
        fileInput.value = "";
        dropzone.hidden = false;
        uploadPreview.hidden = true;
        updateSubmitState();
    });

    // --- Voice ---

    recordButton.addEventListener("click", function () {
        if (mediaRecorder && mediaRecorder.state === "recording") {
            stopRecording();
        } else {
            startRecording();
        }
    });

    function startRecording() {
        recordedBlob = null;
        audioChunks = [];
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(function (stream) {
                mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.addEventListener("dataavailable", function (e) {
                    if (e.data.size > 0) audioChunks.push(e.data);
                });
                mediaRecorder.addEventListener("stop", function () {
                    recordedBlob = new Blob(audioChunks, { type: "audio/webm" });
                    stream.getTracks().forEach(function (t) { t.stop(); });
                    updateSubmitState();
                });
                mediaRecorder.start();
                recordStartTime = Date.now();
                recordButton.setAttribute("aria-pressed", "true");
                voiceRecorder.classList.add("recording");
                voiceStatus.textContent = "Recording...";
                voiceVisualizer.hidden = false;
                voiceTimer.hidden = false;
                timerInterval = setInterval(function () {
                    var s = Math.floor((Date.now() - recordStartTime) / 1000);
                    voiceTimer.textContent =
                        String(Math.floor(s / 60)).padStart(2, "0") + ":" +
                        String(s % 66).padStart(2, "0");
                }, 250);
            })
            .catch(function () {
                voiceStatus.textContent = "Microphone access denied";
            });
    }

    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state === "recording") mediaRecorder.stop();
        clearInterval(timerInterval);
        timerInterval = null;
        recordButton.setAttribute("aria-pressed", "false");
        voiceRecorder.classList.remove("recording");
        voiceVisualizer.hidden = true;
        if (recordedBlob) {
            voiceStatus.textContent = "Recording saved. Tap to re-record.";
        } else if (audioChunks.length > 0) {
            voiceStatus.textContent = "Processing...";
        } else {
            voiceStatus.textContent = "Tap to start recording";
            voiceTimer.hidden = true;
        }
    }

    // --- Results ---

    var confirmButton = document.querySelector(".confirm-button");
    var fieldSchema = {};

    function showResults(data) {
        resultsFields.innerHTML = "";
        fieldSchema = data.field_schema || {};

        if (data.reasoning) {
            reasoningText.textContent = data.reasoning;
            resultsReasoning.hidden = false;
        } else {
            resultsReasoning.hidden = true;
        }

        var formData = data.form_data || {};
        Object.keys(formData).forEach(function (key) {
            var val = formData[key];
            var schema = fieldSchema[key] || {};
            var li = document.createElement("li");
            li.className = "result-field";

            var label = document.createElement("div");
            label.className = "field-label";
            label.textContent = key;
            li.appendChild(label);

            if (schema.type === "array" && schema.items && schema.items.enum) {
                // Render checkboxes for array fields with enum options
                var options = schema.items.enum;
                var selected = Array.isArray(val) ? val : [];
                var checkboxGroup = document.createElement("div");
                checkboxGroup.className = "field-checkboxes";
                checkboxGroup.setAttribute("data-key", key);

                options.forEach(function (opt) {
                    var cbLabel = document.createElement("label");
                    cbLabel.className = "field-checkbox-label";
                    var cb = document.createElement("input");
                    cb.type = "checkbox";
                    cb.value = opt;
                    cb.checked = selected.indexOf(opt) !== -1;
                    cbLabel.appendChild(cb);
                    cbLabel.appendChild(document.createTextNode(" " + opt));
                    checkboxGroup.appendChild(cbLabel);
                });
                li.appendChild(checkboxGroup);
            } else {
                // Render text input for string fields
                var input = document.createElement("textarea");
                input.className = "field-input";
                input.setAttribute("data-key", key);
                input.value = val || "";
                input.rows = 2;
                li.appendChild(input);
            }

            resultsFields.appendChild(li);
        });

        resultsCard.hidden = false;
        resultsCard.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    function collectFormData() {
        var data = {};
        // Collect text inputs
        resultsFields.querySelectorAll(".field-input").forEach(function (input) {
            data[input.getAttribute("data-key")] = input.value;
        });
        // Collect checkbox groups
        resultsFields.querySelectorAll(".field-checkboxes").forEach(function (group) {
            var key = group.getAttribute("data-key");
            var checked = [];
            group.querySelectorAll("input[type=checkbox]:checked").forEach(function (cb) {
                checked.push(cb.value);
            });
            data[key] = checked;
        });
        return data;
    }

    function hideResults() {
        resultsCard.hidden = true;
    }

    resultsDismiss.addEventListener("click", hideResults);

    // --- Confirm & Fill ---

    confirmButton.addEventListener("click", function () {
        var edited = collectFormData();
        confirmButton.disabled = true;
        confirmButton.textContent = "Filling form...";

        fetch("/fill-form", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ form_data: edited })
        })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                confirmButton.textContent = data.success ? "Done!" : "Fill failed";
                setTimeout(function () {
                    confirmButton.textContent = "Confirm & Fill Form";
                    confirmButton.disabled = false;
                }, 2000);
            })
            .catch(function () {
                confirmButton.textContent = "Error";
                setTimeout(function () {
                    confirmButton.textContent = "Confirm & Fill Form";
                    confirmButton.disabled = false;
                }, 2000);
            });
    });

    // --- Submit ---

    function submitToParseContext(summaryText) {
        var fd = new FormData();
        fd.append("type", "text");
        fd.append("text", summaryText);

        fetch("/parse-context", { method: "POST", body: fd })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                submitButton.textContent = "Submit";
                updateSubmitState();
                if (data.form_data) showResults(data);
            })
            .catch(function () {
                submitButton.textContent = "Error";
                setTimeout(function () {
                    submitButton.textContent = "Submit";
                    updateSubmitState();
                }, 2000);
            });
    }

    submitButton.addEventListener("click", function () {
        if (submitButton.disabled) return;

        submitButton.disabled = true;
        hideResults();

        if (activeMode === "chat" && chatSessionId) {
            submitButton.textContent = "Summarizing...";
            chatInput.disabled = true;

            var bubble = null;
            readSSE("/chat-summary", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ session_id: chatSessionId })
            },
                function (token) {
                    if (!bubble) {
                        bubble = createStreamBubble("assistant");
                        bubble.classList.add("chat-summary");
                    }
                    bubble.textContent += token;
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                },
                function (data) {
                    if (data.error) {
                        submitButton.textContent = "Error";
                        setTimeout(function () {
                            submitButton.textContent = "Submit";
                            submitButton.disabled = false;
                        }, 2000);
                        chatInput.disabled = false;
                        return;
                    }
                    finalizeBubbleText(bubble);
                    speakText(bubble ? bubble.getAttribute("data-text") : "", bubble);
                    chatSummaryText = data.summary;
                    submitButton.textContent = "Analyzing...";
                    submitToParseContext(chatSummaryText);
                }
            );
            return;
        }

        var fd = new FormData();

        if (activeMode === "text") {
            fd.append("type", "text");
            fd.append("text", contextText.value.trim());
        } else if (activeMode === "camera" && capturedBlob) {
            fd.append("type", "image");
            fd.append("file", capturedBlob, "capture.jpg");
        } else if (activeMode === "upload" && uploadedFile) {
            fd.append("type", uploadedFile.type.startsWith("image/") ? "image" : "document");
            fd.append("file", uploadedFile, uploadedFile.name);
        } else if (activeMode === "voice" && recordedBlob) {
            fd.append("type", "audio");
            fd.append("file", recordedBlob, "recording.webm");
        }

        submitButton.textContent = "Analyzing...";

        fetch("/parse-context", { method: "POST", body: fd })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                submitButton.textContent = "Submit";
                updateSubmitState();
                if (data.form_data) showResults(data);
            })
            .catch(function () {
                submitButton.textContent = "Error";
                setTimeout(function () {
                    submitButton.textContent = "Submit";
                    updateSubmitState();
                }, 2000);
            });
    });

    updateSubmitState();

    // Show role picker on initial load if chat is active
    if (activeMode === "chat" && !chatStarted) showRolePicker();
});
