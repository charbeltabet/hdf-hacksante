class Position:
	def __init__(self, x, y):
		self.x = x
		self.y = y

class DetectedFormInput:
	def __init__(self, polygon: list[Position], input_label: str, input_description: str, input_type: str):
		self.polygon = polygon
		self.input_label = input_label
		self.input_description = input_description
		self.input_type = input_type
	