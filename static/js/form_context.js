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

    var activeMode = "text";

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

            updateSubmitState();
        });
    });

    function updateSubmitState() {
        var hasInput =
            (activeMode === "text" && contextText.value.trim().length > 0) ||
            (activeMode === "camera" && capturedBlob) ||
            (activeMode === "upload" && uploadedFile) ||
            (activeMode === "voice" && recordedBlob);
        submitButton.disabled = !hasInput;
    }

    contextText.addEventListener("input", updateSubmitState);

    // --- Camera ---

    function startCamera() {
        if (cameraStream) return;
        navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } })
            .then(function (stream) {
                cameraStream = stream;
                cameraPreview.srcObject = stream;
            })
            .catch(function () {});
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
                        String(s % 60).padStart(2, "0");
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

    submitButton.addEventListener("click", function () {
        if (submitButton.disabled) return;

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

        submitButton.disabled = true;
        submitButton.textContent = "Analyzing...";
        hideResults();

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
});
