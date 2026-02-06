import tkinter as tk
from tkinter import simpledialog
from PIL import ImageTk
import pyautogui
import json
import os
from services.form_inputs_detection import Position, DetectedFormInput

INPUT_TYPES = ["checkbox_group", "searchable_select", "form_input"]

def ask_input_type(parent):
	dialog = tk.Toplevel(parent)
	dialog.title("Input Type")
	dialog.grab_set()
	result = tk.StringVar(value=INPUT_TYPES[0])

	tk.Label(dialog, text="Select input type:", font=("Helvetica", 14)).pack(pady=(10, 5))
	for t in INPUT_TYPES:
		tk.Radiobutton(dialog, text=t, variable=result, value=t, font=("Helvetica", 12)).pack(anchor=tk.W, padx=20)

	def confirm():
		dialog.destroy()

	tk.Button(dialog, text="OK", command=confirm, font=("Helvetica", 12)).pack(pady=10)
	dialog.wait_window()
	return result.get()

def run_labeler():
	# Switch to next desktop (Windows: Win+Ctrl+Right)
	pyautogui.hotkey('win', 'ctrl', 'right')
	pyautogui.sleep(0.5)  # Wait for desktop switch animation

	screenshot = pyautogui.screenshot()
	screen_w, screen_h = screenshot.size

	detected_inputs: list[DetectedFormInput] = []

	root = tk.Tk()
	root.title("Form Input Labeler")
	root.attributes("-fullscreen", True)

	canvas = tk.Canvas(root, width=screen_w, height=screen_h)
	canvas.pack()

	tk_image = ImageTk.PhotoImage(screenshot)
	canvas.create_image(0, 0, anchor=tk.NW, image=tk_image)

	status_text = canvas.create_text(
		screen_w // 2, 30,
		text="Press 'n' to add a new field | Press 'q' to finish",
		fill="yellow", font=("Helvetica", 18, "bold"),
	)

	def update_status():
		total = len(detected_inputs)
		canvas.itemconfig(
			status_text,
			text=f"Press 'n' to add a new field | {total} field(s) labeled | Press 'q' to finish",
		)

	def update_status_single_click():
		canvas.itemconfig(
			status_text,
			text=f"Click the field position | Press 'q' to finish",
		)

	def draw_point(x, y, color="red"):
		r = 5
		canvas.create_oval(x - r, y - r, x + r, y + r, fill=color, outline=color)

	def draw_label(x, y, label, description, field_type, extra_info=""):
		text = f"{field_type}: {label}"
		if description:
			text += f"\n{description}"
		if extra_info:
			text += f"\n{extra_info}"
		canvas.create_text(x + 10, y, text=text, anchor=tk.W, fill="lime", font=("Helvetica", 10, "bold"))

	SEARCHABLE_SELECT_STEPS = ["dropdown", "input", "result"]
	pending_field = {"active": False, "type": None, "label": "", "description": "", "step_index": 0, "coordinates": {}, "options": []}

	def update_status_searchable():
		step_index = pending_field["step_index"]
		step_name = SEARCHABLE_SELECT_STEPS[step_index]
		canvas.itemconfig(
			status_text,
			text=f"Searchable select: click the '{step_name}' position ({step_index + 1}/3) | Press 'q' to finish",
		)

	def update_status_checkbox_group():
		count = len(pending_field["options"])
		canvas.itemconfig(
			status_text,
			text=f"Checkbox group: click each option position ({count} added) | Press 'd' when done | Press 'q' to quit",
		)

	def start_new_field():
		input_type = ask_input_type(root)
		label = simpledialog.askstring("Label", "Enter field label:", parent=root) or ""
		description = simpledialog.askstring("Description", "Enter field description:", parent=root) or ""

		pending_field["active"] = True
		pending_field["type"] = input_type
		pending_field["label"] = label
		pending_field["description"] = description
		pending_field["step_index"] = 0
		pending_field["coordinates"] = {}
		pending_field["options"] = []

		if input_type == "searchable_select":
			update_status_searchable()
		elif input_type == "checkbox_group":
			update_status_checkbox_group()
		else:
			update_status_single_click()

	def on_click(event):
		if not pending_field["active"]:
			return

		x, y = event.x, event.y
		draw_point(x, y)

		if pending_field["type"] == "searchable_select":
			step_index = pending_field["step_index"]
			step_name = SEARCHABLE_SELECT_STEPS[step_index]
			pending_field["coordinates"][step_name] = {"x": x, "y": y}
			pending_field["step_index"] += 1

			if pending_field["step_index"] == 3:
				coords = pending_field["coordinates"]
				detected_inputs.append(DetectedFormInput(
					polygon=[],
					input_label=pending_field["label"],
					input_description=pending_field["description"],
					input_type="searchable_select",
					coordinates=coords.copy(),
				))
				# Draw label at dropdown position
				draw_label(
					coords["dropdown"]["x"], coords["dropdown"]["y"],
					pending_field["label"], pending_field["description"],
					"searchable_select",
					f"dropdown→input→result"
				)
				pending_field["active"] = False
				update_status()
			else:
				update_status_searchable()
		elif pending_field["type"] == "checkbox_group":
			# Ask for option label for this checkbox
			option_label = simpledialog.askstring("Option Label", "Enter label for this checkbox option:", parent=root) or ""
			pending_field["options"].append({"option_label": option_label, "x": x, "y": y})
			draw_label(x, y, pending_field["label"], "", "checkbox", f"{option_label} ({x}, {y})")
			update_status_checkbox_group()
		else:
			# Single click for text
			detected_inputs.append(DetectedFormInput(
				polygon=[Position(x, y)],
				input_label=pending_field["label"],
				input_description=pending_field["description"],
				input_type=pending_field["type"],
			))
			draw_label(x, y, pending_field["label"], pending_field["description"], pending_field["type"], f"({x}, {y})")
			pending_field["active"] = False
			update_status()

	def save_to_json():
		filename = simpledialog.askstring("Save", "Enter filename (without .json):", parent=root)
		if not filename:
			return None
		form_description = simpledialog.askstring("Description", "Enter form description:", parent=root) or ""

		form_fields = []
		for field in detected_inputs:
			if field.input_type == "searchable_select":
				form_fields.append({
					"field_type": field.input_type,
					"label": field.input_label,
					"description": field.input_description,
					"coordinates": field.coordinates,
				})
			elif field.input_type == "checkbox_group":
				form_fields.append({
					"field_type": field.input_type,
					"label": field.input_label,
					"description": field.input_description,
					"options": field.coordinates.get("options", []),
				})
			else:
				# Use single point (text input)
				x = field.polygon[0].x if field.polygon else 0
				y = field.polygon[0].y if field.polygon else 0
				form_fields.append({
					"field_type": field.input_type,
					"label": field.input_label,
					"description": field.input_description,
					"x": x,
					"y": y,
				})

		schema = {
			"description": form_description,
			"form_fields": form_fields,
		}

		forms_schema_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "forms_schema")
		os.makedirs(forms_schema_dir, exist_ok=True)
		filepath = os.path.join(forms_schema_dir, f"{filename}.json")

		with open(filepath, "w", encoding="utf-8") as f:
			json.dump(schema, f, indent=2, ensure_ascii=False)

		print(f"Saved to {filepath}")
		return filepath

	def finish_checkbox_group():
		if pending_field["options"]:
			detected_inputs.append(DetectedFormInput(
				polygon=[],
				input_label=pending_field["label"],
				input_description=pending_field["description"],
				input_type="checkbox_group",
				coordinates={"options": pending_field["options"].copy()},
			))
		pending_field["active"] = False
		pending_field["options"] = []
		update_status()

	def on_key(event):
		if event.char == "q":
			save_to_json()
			root.destroy()
			# Switch back to previous desktop (Windows: Win+Ctrl+Left)
			pyautogui.hotkey('win', 'ctrl', 'left')
		elif event.char == "d" and pending_field["active"] and pending_field["type"] == "checkbox_group":
			finish_checkbox_group()
		elif event.char == "n" and not pending_field["active"]:
			start_new_field()

	canvas.bind("<Button-1>", on_click)
	root.bind("<Key>", on_key)
	update_status()
	root.mainloop()

	return detected_inputs


if __name__ == "__main__":
	run_labeler()
