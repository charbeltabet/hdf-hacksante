import json

import pyautogui
from services.form_filler import process_field


def generate_json_schema(form_definition: dict, require_all: bool = False) -> dict:
    """
    Generate a JSON Schema from a form definition (without coordinates).

    Args:
        form_definition: The form definition dict with coordinates

    Returns:
        A JSON Schema describing what data the form needs
    """
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": form_definition.get("description", "Form Data"),
        "properties": {},
        "required": []
    }

    for field in form_definition.get("form_fields", []):
        field_type = field.get("field_type")
        label = field.get("label", "")
        description = field.get("description", "")

        if not label:
            continue

        if field_type == "form_input":
            schema["properties"][label] = {
                "type": "string",
                "description": description
            }

        elif field_type == "searchable_select":
            schema["properties"][label] = {
                "type": "string",
                "description": description
            }

        elif field_type == "checkbox_group":
            options = field.get("options", [])
            option_labels = [opt.get("option_label", "") for opt in options if opt.get("option_label")]

            schema["properties"][label] = {
                "type": "array",
                "description": description,
                "items": {
                    "type": "string",
                    "enum": option_labels
                },
                "uniqueItems": True
            }

        schema["required"].append(label) if require_all else None

    return schema


def generate_empty_form_data(form_definition: dict) -> dict:
    """
    Generate an empty form data template from a form definition.

    Args:
        form_definition: The form definition dict with coordinates

    Returns:
        A dict template with empty/default values for each field
    """
    data = {}

    for field in form_definition.get("form_fields", []):
        field_type = field.get("field_type")
        label = field.get("label", "")

        if not label:
            continue

        if field_type == "form_input":
            data[label] = ""
        elif field_type == "searchable_select":
            data[label] = ""
        elif field_type == "checkbox_group":
            data[label] = []

    return data


def fill_form_with_data(form_definition: dict, form_data: dict, delay_between: float = 0.3) -> dict:
    """
    Fill a form using the form definition (with coordinates) and user-provided data.

    Args:
        form_definition: The form definition dict with coordinates
        form_data: Dict mapping field labels to values
        delay_between: Delay between filling each field

    Returns:
        dict with success status and results for each field
    """
    import time

    results = []
    fields = form_definition.get("form_fields", [])

    # here switch window
    
    pyautogui.hotkey('win', 'ctrl', 'right')
    time.sleep(2.0)

    for i, field in enumerate(fields):
        field_type = field.get("field_type")
        label = field.get("label", "")

        # Get the value from form_data using the label
        value = form_data.get(label)

        if value is None:
            results.append({
                "success": False,
                "label": label,
                "error": f"No value provided for field '{label}'"
            })
            continue

        # Build the field_data dict for process_field
        field_data = {"field_type": field_type, "value": value}

        if field_type == "form_input":
            field_data["x"] = field.get("x", 0)
            field_data["y"] = field.get("y", 0)

        elif field_type == "searchable_select":
            field_data["coordinates"] = field.get("coordinates", {})

        elif field_type == "checkbox_group":
            field_data["options"] = field.get("options", [])

        result = process_field(field_data)
        result["label"] = label
        result["field_index"] = i
        results.append(result)

        if i < len(fields) - 1:
            time.sleep(delay_between)

    all_success = all(r.get("success", False) for r in results)

    return {
        "success": all_success,
        "total_fields": len(fields),
        "results": results
    }


def load_form_definition(filepath: str) -> dict:
    """Load a form definition from a JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json_schema(schema: dict, filepath: str) -> None:
    """Save a JSON schema to a file."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    import sys
    import os

    if len(sys.argv) < 2:
        print("Usage: python form_schema_generator.py <form_definition.json>")
        sys.exit(1)

    form_path = sys.argv[1]
    form_def = load_form_definition(form_path)

    # Generate schema
    schema = generate_json_schema(form_def)

    # Save schema next to the form definition
    base_name = os.path.splitext(form_path)[0]
    schema_path = f"{base_name}_schema.json"
    save_json_schema(schema, schema_path)
    print(f"Schema saved to: {schema_path}")

    # Also generate empty template
    template = generate_empty_form_data(form_def)
    template_path = f"{base_name}_template.json"
    with open(template_path, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=2, ensure_ascii=False)
    print(f"Template saved to: {template_path}")
