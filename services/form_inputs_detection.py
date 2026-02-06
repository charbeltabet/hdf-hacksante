class Position:
	def __init__(self, x, y):
		self.x = x
		self.y = y

class DetectedFormInput:
	def __init__(self, polygon: list[Position], label: str, description: str):
		self.polygon = polygon
		self.label = label
		self.description = description
	