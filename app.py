from flask import Flask, render_template, request, jsonify
import tempfile
import ast
import json
import os
from services.context_parser import parse_context
from utils.paths import PROJECT_ROOT
from services.form_schema_generator import (
    fill_form_with_data,
    load_form_definition
)

app = Flask(__name__)

SCHEMA_PATH = os.path.join(PROJECT_ROOT, "forms_schema", "questionaire_schema.json")
FORM_DEF_PATH = os.path.join(PROJECT_ROOT, "forms_schema", "questionaire.json")

TYPE_MAP = {
    "text": "text",
    "image": "image",
    "audio": "audio",
    "document": "image",
}


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


@app.route('/fill-form', methods=['POST'])
def fill_form_route():
    data = request.get_json()
    form_data = data.get("form_data", {})

    form_def = load_form_definition(FORM_DEF_PATH)
    result = fill_form_with_data(form_def, form_data)

    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=7500)
