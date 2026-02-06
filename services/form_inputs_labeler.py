import tkinter as tk
from tkinter import simpledialog
from PIL import ImageTk
import pyautogui
from services.form_inputs_detection import Position, DetectedFormInput

def run_labeler():
	screenshot = pyautogui.screenshot()
	screen_w, screen_h = screenshot.size

	detected_inputs: list[DetectedFormInput] = []
	current_points: list[Position] = []

	root = tk.Tk()
	root.title("Form Input Labeler - Click 4 points per field, then enter label")
	root.attributes("-fullscreen", True)

	canvas = tk.Canvas(root, width=screen_w, height=screen_h)
	canvas.pack()

	tk_image = ImageTk.PhotoImage(screenshot)
	canvas.create_image(0, 0, anchor=tk.NW, image=tk_image)

	status_text = canvas.create_text(
		screen_w // 2, 30,
		text="Click 4 corners of a form field (0/4) | Press 'q' to finish",
		fill="yellow", font=("Helvetica", 18, "bold"),
	)

	def update_status():
		count = len(current_points)
		total = len(detected_inputs)
		canvas.itemconfig(
			status_text,
			text=f"Click 4 corners of a form field ({count}/4) | {total} field(s) labeled | Press 'q' to finish",
		)

	def draw_point(x, y):
		r = 5
		canvas.create_oval(x - r, y - r, x + r, y + r, fill="red", outline="red")

	def draw_polygon(points: list[Position]):
		coords = []
		for p in points:
			coords.extend([p.x, p.y])
		coords.extend([points[0].x, points[0].y])
		canvas.create_line(coords, fill="lime", width=2)

	def on_click(event):
		x, y = event.x, event.y
		current_points.append(Position(x, y))
		draw_point(x, y)

		if len(current_points) >= 2:
			p1 = current_points[-2]
			p2 = current_points[-1]
			canvas.create_line(p1.x, p1.y, p2.x, p2.y, fill="lime", width=2)

		if len(current_points) == 4:
			draw_polygon(current_points)
			label = simpledialog.askstring("Label", "Enter field label:", parent=root) or ""
			description = simpledialog.askstring("Description", "Enter field description:", parent=root) or ""
			detected_inputs.append(DetectedFormInput(
				polygon=list(current_points),
				label=label,
				description=description,
			))
			current_points.clear()

		update_status()

	def on_key(event):
		if event.char == "q":
			root.destroy()

	canvas.bind("<Button-1>", on_click)
	root.bind("<Key>", on_key)
	update_status()
	root.mainloop()

	print(f"\n{'='*60}")
	print(f"Detected {len(detected_inputs)} form input(s):")
	print(f"{'='*60}")
	for i, field in enumerate(detected_inputs):
		corners = [(p.x, p.y) for p in field.polygon]
		print(f"\n[{i}] label: {field.label!r}")
		print(f"    description: {field.description!r}")
		print(f"    polygon: {corners}")
	print()

	return detected_inputs


if __name__ == "__main__":
	run_labeler()
