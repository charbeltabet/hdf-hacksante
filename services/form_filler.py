import pyautogui
import time
from enum import Enum


class FieldType(Enum):
    FORM_INPUT = "form_input"
    SEARCHABLE_SELECT = "searchable_select"
    CHECKBOX_GROUP = "checkbox_group"


def handle_form_input(x: int, y: int, value: str, delay_before_type: float = 0.1) -> dict:
    """
    Handles a standard form input field.
    Clicks at the specified coordinates and types the value.

    Args:
        x: X coordinate (pixels)
        y: Y coordinate (pixels)
        value: The text value to input
        delay_before_type: Delay in seconds before typing (default 0.1)

    Returns:
        dict with success status and details
    """
    try:
        pyautogui.click(x, y)
        time.sleep(delay_before_type)

        if value:
            pyautogui.typewrite(value, interval=0.02)

        return {
            "success": True,
            "field_type": FieldType.FORM_INPUT.value,
            "action": "click_and_type",
            "coordinates": {"x": x, "y": y},
            "value_entered": value
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def handle_searchable_select(coordinates: dict, search_value: str,
                              delay_after_open: float = 0.3,
                              delay_after_type: float = 0.5) -> dict:
    """
    Handles a searchable select/dropdown field.

    Args:
        coordinates: Dict with three coordinate pairs:
            - dropdown: {"x": int, "y": int} - The bar to click to open the select
            - input: {"x": int, "y": int} - The search input field
            - result: {"x": int, "y": int} - Where to click to select first result
        search_value: The value to search for in the dropdown
        delay_after_open: Delay after opening dropdown (default 0.3s)
        delay_after_type: Delay after typing before clicking result (default 0.5s)

    Returns:
        dict with success status and details
    """
    try:
        dropdown = coordinates.get('dropdown', {})
        input_field = coordinates.get('input', {})
        result = coordinates.get('result', {})

        pyautogui.hotkey('win', 'ctrl', 'left')
        time.sleep(0.5)

        # Step 1: Click the dropdown bar to open it
        pyautogui.click(dropdown.get('x'), dropdown.get('y'))
        time.sleep(delay_after_open)

        # Step 2: Click the input field to focus it
        pyautogui.click(input_field.get('x'), input_field.get('y'))
        time.sleep(0.1)

        # Step 3: Type the search term
        if search_value:
            pyautogui.typewrite(search_value, interval=0.02)

        # Step 4: Wait for search results to appear
        time.sleep(delay_after_type)

        # Step 5: Click the first result
        pyautogui.click(result.get('x'), result.get('y'))

        return {
            "success": True,
            "field_type": FieldType.SEARCHABLE_SELECT.value,
            "action": "open_search_select",
            "coordinates": coordinates,
            "search_value": search_value
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def handle_checkbox_group(options: list, values: list, delay_between: float = 0.2) -> dict:
    """
    Handles a checkbox group field.
    Clicks on each checkbox whose option_label matches a value in the values list.

    Args:
        options: List of dicts with {"option_label": str, "x": int, "y": int}
        values: List of option_labels to select (checkboxes to click)
        delay_between: Delay between clicking multiple checkboxes (default 0.2s)

    Returns:
        dict with success status and details
    """
    try:
        clicked = []
        for value in values:
            for option in options:
                if option.get('option_label') == value:
                    x = int(option.get('x', 0))
                    y = int(option.get('y', 0))
                    pyautogui.click(x, y)
                    clicked.append({"option_label": value, "x": x, "y": y})
                    time.sleep(delay_between)
                    break

        return {
            "success": True,
            "field_type": FieldType.CHECKBOX_GROUP.value,
            "action": "click_checkboxes",
            "clicked": clicked,
            "values_requested": values
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def process_field(field_data: dict) -> dict:
    """
    Main dispatcher function that routes to the appropriate handler based on field type.

    Args:
        field_data: Dict containing:
            - field_type: One of 'form_input', 'searchable_select', 'checkbox_group'
            - x, y: Coordinates (for form_input)
            - coordinates: Nested coords (for searchable_select)
            - options: List of {"option_label", "x", "y"} (for checkbox_group)
            - value: The value to input (string or list of strings for checkbox_group)

    Returns:
        dict with success status and action details
    """
    field_type = field_data.get('field_type')
    value = field_data.get('value')

    if field_type == FieldType.FORM_INPUT.value:
        if value is None:
            return {"success": False, "error": "Value is required for form_input fields"}
        x = int(field_data.get('x', 0))
        y = int(field_data.get('y', 0))
        return handle_form_input(x, y, value)

    elif field_type == FieldType.SEARCHABLE_SELECT.value:
        if value is None:
            return {"success": False, "error": "Value is required for searchable_select fields"}
        coordinates = field_data.get('coordinates', {})
        if not coordinates:
            return {"success": False, "error": "coordinates required for searchable_select (dropdown, input, result)"}
        return handle_searchable_select(coordinates, value)

    elif field_type == FieldType.CHECKBOX_GROUP.value:
        options = field_data.get('options', [])
        if not options:
            return {"success": False, "error": "options required for checkbox_group"}
        value = field_data.get('value')
        # value can be a single string or a list of strings
        if value is None:
            return {"success": False, "error": "value required for checkbox_group (option_label(s) to select)"}
        values = value if isinstance(value, list) else [value]
        return handle_checkbox_group(options, values)

    else:
        return {"success": False, "error": f"Unknown field type: {field_type}"}


def process_fields_batch(fields: list, delay_between: float = 0.3) -> dict:
    """
    Process multiple field interactions in sequence.

    Args:
        fields: List of field data dicts
        delay_between: Delay between processing each field (default 0.3s)

    Returns:
        dict with success status and results for each field
    """
    if not fields:
        return {"success": False, "error": "No fields provided"}

    results = []
    for i, field in enumerate(fields):
        result = process_field(field)
        result['field_index'] = i
        results.append(result)

        # Delay between fields (except after last one)
        if i < len(fields) - 1:
            time.sleep(delay_between)

    all_success = all(r["success"] for r in results)

    return {
        "success": all_success,
        "total_fields": len(fields),
        "results": results
    }
