from flask import Flask, render_template, request, jsonify, Response, redirect
import tempfile
import ast
import json
import os
import uuid
import requests as http_requests
from services.context_parser import parse_context
from services.form_schema_chat import (
    create_chat_session,
    chat_message_stream,
    finalize_stream,
    parse_status_from_reply,
    request_summary_stream,
)
from utils.paths import PROJECT_ROOT
from utils.clients import DEEPGRAM_API_KEY, DEEPGRAM_BASE_URL
from services.form_schema_generator import (
    fill_form_with_data,
    load_form_definition
)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

chat_sessions = {}

SCHEMA_PATH = os.path.join(PROJECT_ROOT, "forms_schema", "questionaire_schema.json")
FORM_DEF_PATH = os.path.join(PROJECT_ROOT, "forms_schema", "questionaire.json")

TYPE_MAP = {
    "text": "text",
    "image": "image",
    "audio": "audio",
    "document": "pdf",
    "spreadsheet": "spreadsheet",
    "json": "json",
}

@app.route('/')
def index():
    return redirect('/form-context')

@app.route('/form-context', methods=['GET'])
def form_context_route():
    mode = request.args.get('mode', 'text')
    return render_template('form_context.html', mode=mode)


@app.route('/parse-context', methods=['POST'])
def parse_context_route():
    print("\n" + "=" * 60)
    print("[parse-context] REQUEST RECEIVED")
    print("=" * 60)
    print(f"[parse-context] Content-Type header: {request.content_type}")
    print(f"[parse-context] Form fields: {list(request.form.keys())}")
    print(f"[parse-context] Files: {list(request.files.keys())}")

    context_type = request.form.get("type", "text")
    print(f"[parse-context] context_type: '{context_type}'")
    tmp_path = None

    try:
        if context_type == "text":
            path_or_text = request.form.get("text", "")
            print(f"[parse-context] Text input length: {len(path_or_text)} chars")
            print(f"[parse-context] Text preview: '{path_or_text[:200]}{'...' if len(path_or_text) > 200 else ''}'")
        else:
            file = request.files.get("file")
            print(f"[parse-context] File object: {file}")
            if file:
                print(f"[parse-context] File name: '{file.filename}'")
                print(f"[parse-context] File content_type: '{file.content_type}'")
            if not file:
                print("[parse-context] ERROR: No file found in request")
                return jsonify({"success": False, "error": "No file provided"}), 400

            suffix = os.path.splitext(file.filename)[1] or ".bin"
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            file.save(tmp)
            tmp.close()
            tmp_path = tmp.name
            file_size = os.path.getsize(tmp_path)
            path_or_text = tmp_path
            print(f"[parse-context] Saved to temp file: '{tmp_path}' ({file_size} bytes)")

        parser_type = TYPE_MAP.get(context_type, "text")
        print(f"[parse-context] Mapped parser_type: '{parser_type}'")

        print(f"[parse-context] Loading schema from: {SCHEMA_PATH}")
        with open(SCHEMA_PATH, "r") as f:
            result_schema = f.read()
        print(f"[parse-context] Schema loaded ({len(result_schema)} chars)")

        print(f"[parse-context] Calling parse_context(path_or_text, '{parser_type}', schema)...")
        prediction = parse_context(path_or_text, parser_type, result_schema)
        print(f"[parse-context] parse_context returned: {type(prediction)}")
        form_data = prediction.json_result
        if isinstance(form_data, str):
            try:
                form_data = json.loads(form_data)
            except json.JSONDecodeError:
                form_data = ast.literal_eval(form_data)
        reasoning = prediction.reasoning
        print(f"[parse-context] form_data (type={type(form_data).__name__}): {form_data}")
        print(f"[parse-context] reasoning: {reasoning[:300] if reasoning else 'None'}{'...' if reasoning and len(reasoning) > 300 else ''}")

        print(f"[parse-context] Loading schema for field types...")
        with open(SCHEMA_PATH, "r") as sf:
            schema_obj = json.loads(sf.read())
        field_schema = schema_obj.get("properties", {})

        print("[parse-context] SUCCESS - returning response")
        print("=" * 60 + "\n")

        return jsonify({
            "success": True,
            "form_data": form_data,
            "reasoning": reasoning,
            "field_schema": field_schema,
        })

    except Exception as e:
        print(f"[parse-context] EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise e

    finally:
        if tmp_path and os.path.exists(tmp_path):
            print(f"[parse-context] Cleaning up temp file: {tmp_path}")
            os.unlink(tmp_path)


@app.route('/chat-start', methods=['POST'])
def chat_start_route():
    data = request.get_json(silent=True) or {}
    role = data.get("role", "patient")

    with open(SCHEMA_PATH, "r") as f:
        schema_str = f.read()
    session_id = str(uuid.uuid4())
    messages = create_chat_session(schema_str, role=role)
    chat_sessions[session_id] = messages

    greeting = "Hello, I'm here for my appointment." if role == "patient" else "I need to enter patient intake data."

    def generate():
        stream, msgs = chat_message_stream(messages, greeting)
        full_reply = ""
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                full_reply += delta.content
                yield f"data: {json.dumps({'token': delta.content})}\n\n"
        visible_text, field_status = parse_status_from_reply(full_reply)
        finalize_stream(msgs, full_reply)
        # Remove the fake user message, keep system + assistant
        chat_sessions[session_id] = [m for m in msgs if m["role"] != "user"]
        done_payload = {'done': True, 'session_id': session_id}
        if field_status:
            done_payload['field_status'] = field_status
            done_payload['visible_end'] = len(visible_text)
        yield f"data: {json.dumps(done_payload)}\n\n"

    return Response(generate(), mimetype="text/event-stream")


@app.route('/chat-message', methods=['POST'])
def chat_message_route():
    data = request.get_json()
    session_id = data.get("session_id")
    user_msg = data.get("message", "")

    if not session_id or session_id not in chat_sessions:
        return jsonify({"error": "Invalid session"}), 400

    messages = chat_sessions[session_id]

    def generate():
        stream, msgs = chat_message_stream(messages, user_msg)
        full_reply = ""
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                full_reply += delta.content
                yield f"data: {json.dumps({'token': delta.content})}\n\n"
        visible_text, field_status = parse_status_from_reply(full_reply)
        finalize_stream(msgs, full_reply)
        chat_sessions[session_id] = msgs
        done_payload = {'done': True}
        if field_status:
            done_payload['field_status'] = field_status
            done_payload['visible_end'] = len(visible_text)
        yield f"data: {json.dumps(done_payload)}\n\n"

    return Response(generate(), mimetype="text/event-stream")


@app.route('/chat-summary', methods=['POST'])
def chat_summary_route():
    data = request.get_json()
    session_id = data.get("session_id")

    if not session_id or session_id not in chat_sessions:
        return jsonify({"error": "Invalid session"}), 400

    messages = chat_sessions[session_id]

    def generate():
        stream, msgs = request_summary_stream(messages)
        full_reply = ""
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                full_reply += delta.content
                yield f"data: {json.dumps({'token': delta.content})}\n\n"
        finalize_stream(msgs, full_reply)
        chat_sessions[session_id] = msgs
        yield f"data: {json.dumps({'done': True, 'summary': full_reply})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


@app.route('/tts', methods=['POST'])
def tts_route():
    data = request.get_json()
    text = data.get("text", "")
    text = text.replace("*", "").replace("_", "").replace("`", "")
    if not text:
        return jsonify({"error": "No text provided"}), 400

    resp = http_requests.post(
        "https://api.deepgram.com/v1/speak?model=aura-2-thalia-en",
        headers={
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"text": text},
        stream=True,
    )

    return Response(
        resp.iter_content(chunk_size=4096),
        mimetype="audio/mpeg",
    )


@app.route('/stt', methods=['POST'])
def stt_route():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No audio file"}), 400

    audio_data = file.read()
    resp = http_requests.post(
        f"{DEEPGRAM_BASE_URL}/listen?smart_format=true&model=nova-3",
        headers={
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": file.content_type or "audio/webm",
        },
        data=audio_data,
    )
    result = resp.json()
    transcript = result["results"]["channels"][0]["alternatives"][0]["transcript"]
    return jsonify({"transcript": transcript})


@app.route('/fill-form', methods=['POST'])
def fill_form_route():
    data = request.get_json()
    form_data = data.get("form_data", {})

    form_def = load_form_definition(FORM_DEF_PATH)
    result = fill_form_with_data(form_def, form_data)

    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=7500)
