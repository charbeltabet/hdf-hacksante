from flask import Flask, render_template, request, jsonify
import pyautogui
import time
import os

from services.form_filler import process_field, process_fields_batch
from services.form_schema_generator import (
    generate_json_schema,
    generate_empty_form_data,
    fill_form_with_data,
    load_form_definition
)

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/submit', methods=['POST'])
def submit():
    try:
        data = request.get_json()
        text = data.get('text', '')
        x_ratio = float(data.get('x', 0.5))
        y_ratio = float(data.get('y', 0.5))

        # Validate ratios are between 0 and 1
        x_ratio = max(0, min(1, x_ratio))
        y_ratio = max(0, min(1, y_ratio))

        # Get screen size
        screen_width, screen_height = pyautogui.size()

        # Calculate actual pixel position
        x_pos = int(x_ratio * screen_width)
        y_pos = int(y_ratio * screen_height)

        # Small delay to allow user to switch windows if needed
        time.sleep(0.5)

        # Click at the position
        pyautogui.click(x_pos, y_pos)

        # Small delay before typing
        time.sleep(0.1)

        # Type the text
        if text:
            pyautogui.typewrite(text, interval=0.02)

        return jsonify({
            'success': True,
            'message': f'Clicked at ({x_pos}, {y_pos}) and typed text',
            'screen_size': {'width': screen_width, 'height': screen_height},
            'click_position': {'x': x_pos, 'y': y_pos}
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/intake', methods=['GET'])
def intake_route():
    return render_template('intake.html')


@app.route('/process-field', methods=['POST'])
def process_field_route():
    """
    Process a single field interaction.

    Expected JSON payload for form_input/checkbox:
    {
        "field_type": "form_input" | "checkbox",
        "x": <int>,
        "y": <int>,
        "value": <str>  # Required for form_input only
    }

    Expected JSON payload for searchable_select:
    {
        "field_type": "searchable_select",
        "coordinates": {
            "dropdown": {"x": <int>, "y": <int>},
            "input": {"x": <int>, "y": <int>},
            "result": {"x": <int>, "y": <int>}
        },
        "value": <str>
    }
    """
    try:
        data = request.get_json()

        field_type = data.get('field_type')
        if not field_type:
            return jsonify({"success": False, "error": "field_type is required"}), 400

        # Add a small delay to allow user to switch windows
        time.sleep(0.5)

        result = process_field(data)

        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 400

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route('/process-fields-batch', methods=['POST'])
def process_fields_batch_route():
    """
    Process multiple field interactions in sequence.

    Expected JSON payload:
    {
        "fields": [
            {"field_type": "form_input", "x": 100, "y": 200, "value": "John"},
            {
                "field_type": "searchable_select",
                "coordinates": {
                    "dropdown": {"x": 100, "y": 300},
                    "input": {"x": 100, "y": 330},
                    "result": {"x": 100, "y": 360}
                },
                "value": "Option1"
            },
            {"field_type": "checkbox", "x": 100, "y": 400}
        ],
        "delay_between_fields": 0.3
    }
    """
    try:
        data = request.get_json()

        fields = data.get('fields', [])
        delay_between = float(data.get('delay_between_fields', 0.3))

        if not fields:
            return jsonify({"success": False, "error": "No fields provided"}), 400

        # Initial delay to allow user to switch windows
        time.sleep(1.0)

        result = process_fields_batch(fields, delay_between)

        return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route('/test-mock-data', methods=['GET'])
def test_mock_data():
    """
    Returns mock data for testing the field processing functions.
    """
    mock_data = {
        "form_fields": [
            {
                "field_type": "form_input",
                "label": "First Name",
                "x": 500,
                "y": 200,
                "value": "John"
            },
            {
                "field_type": "form_input",
                "label": "Last Name",
                "x": 500,
                "y": 250,
                "value": "Doe"
            },
            {
                "field_type": "form_input",
                "label": "Email",
                "x": 500,
                "y": 300,
                "value": "john.doe@example.com"
            },
            {
                "field_type": "searchable_select",
                "label": "Country",
                "coordinates": {
                    "dropdown": {"x": 500, "y": 350},
                    "input": {"x": 500, "y": 380},
                    "result": {"x": 500, "y": 410}
                },
                "value": "France"
            },
            {
                "field_type": "searchable_select",
                "label": "City",
                "coordinates": {
                    "dropdown": {"x": 500, "y": 450},
                    "input": {"x": 500, "y": 480},
                    "result": {"x": 500, "y": 510}
                },
                "value": "Paris"
            },
            {
                "field_type": "checkbox",
                "label": "Accept Terms",
                "x": 500,
                "y": 550
            },
            {
                "field_type": "checkbox",
                "label": "Subscribe Newsletter",
                "x": 500,
                "y": 580
            }
        ],
        "description": "Mock form data for testing automation functions",
        "instructions": {
            "single_field": "POST to /process-field with field data",
            "batch_processing": "POST to /process-fields-batch with array of fields"
        }
    }

    return jsonify(mock_data)


@app.route('/run-mock-test', methods=['POST'])
def run_mock_test():
    """
    Runs a test using mock data.
    Allows specifying which field types to test.

    Expected JSON payload (optional):
    {
        "include_types": ["form_input", "searchable_select", "checkbox"],
        "custom_delay": 0.5
    }
    """
    try:
        data = request.get_json() or {}

        include_types = data.get('include_types', ['form_input', 'searchable_select', 'checkbox'])
        custom_delay = float(data.get('custom_delay', 0.5))

        # Mock test data
        test_fields = [
            {"field_type": "form_input", "x": 500, "y": 200, "value": "TestUser", "label": "Username"},
            {"field_type": "form_input", "x": 500, "y": 250, "value": "test@example.com", "label": "Email"},
            {
                "field_type": "searchable_select",
                "coordinates": {
                    "dropdown": {"x": 500, "y": 300},
                    "input": {"x": 500, "y": 330},
                    "result": {"x": 500, "y": 360}
                },
                "value": "Option1",
                "label": "Country"
            },
            {"field_type": "checkbox", "x": 500, "y": 400, "label": "Accept Terms"}
        ]

        # Filter by included types
        filtered_fields = [f for f in test_fields if f['field_type'] in include_types]

        if not filtered_fields:
            return jsonify({"success": False, "error": "No fields match the specified types"}), 400

        # Initial delay
        time.sleep(1.5)

        results = []
        for i, field in enumerate(filtered_fields):
            result = process_field(field)
            result['field_index'] = i
            result['label'] = field.get('label', f"Field {i}")
            results.append(result)

            if i < len(filtered_fields) - 1:
                time.sleep(custom_delay)

        return jsonify({
            "success": all(r["success"] for r in results),
            "tested_types": include_types,
            "total_fields": len(filtered_fields),
            "results": results
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route('/forms', methods=['GET'])
def list_forms():
    """List all available form definitions."""
    forms_dir = os.path.join(os.path.dirname(__file__), "forms_schema")
    if not os.path.exists(forms_dir):
        return jsonify({"forms": []})

    forms = [f.replace(".json", "") for f in os.listdir(forms_dir) if f.endswith(".json")]
    return jsonify({"forms": forms})


@app.route('/forms/<form_name>/schema', methods=['GET'])
def get_form_schema(form_name):
    """
    Get the JSON Schema for a form (without coordinates).
    Use this to know what data the form needs.
    """
    try:
        forms_dir = os.path.join(os.path.dirname(__file__), "forms_schema")
        form_path = os.path.join(forms_dir, f"{form_name}.json")

        if not os.path.exists(form_path):
            return jsonify({"success": False, "error": f"Form '{form_name}' not found"}), 404

        form_def = load_form_definition(form_path)
        schema = generate_json_schema(form_def)

        return jsonify(schema)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route('/forms/<form_name>/template', methods=['GET'])
def get_form_template(form_name):
    """
    Get an empty data template for a form.
    Fill in the values and POST to /forms/<form_name>/fill
    """
    try:
        forms_dir = os.path.join(os.path.dirname(__file__), "forms_schema")
        form_path = os.path.join(forms_dir, f"{form_name}.json")

        if not os.path.exists(form_path):
            return jsonify({"success": False, "error": f"Form '{form_name}' not found"}), 404

        form_def = load_form_definition(form_path)
        template = generate_empty_form_data(form_def)

        return jsonify(template)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route('/forms/<form_name>/fill', methods=['POST'])
def fill_form(form_name):
    """
    Fill a form with provided data.

    Expected JSON payload:
    {
        "data": {
            "Field Label 1": "value1",
            "Field Label 2": "value2",
            "Checkbox Group Label": ["option1", "option2"]
        },
        "delay_between_fields": 0.3
    }
    """
    try:
        forms_dir = os.path.join(os.path.dirname(__file__), "forms_schema")
        form_path = os.path.join(forms_dir, f"{form_name}.json")

        if not os.path.exists(form_path):
            return jsonify({"success": False, "error": f"Form '{form_name}' not found"}), 404

        req_data = request.get_json()
        form_data = req_data.get("data", {})
        delay = float(req_data.get("delay_between_fields", 0.3))

        if not form_data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        form_def = load_form_definition(form_path)

        # Initial delay to allow user to switch windows
        time.sleep(1.0)

        result = fill_form_with_data(form_def, form_data, delay)

        return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=7500)
