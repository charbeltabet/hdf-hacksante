from typing import Optional, Dict, Any
from utils.clients import OPENROUTER_API_KEY

import dspy

class ImageExtractor(dspy.Signature):
	"""Analyze images and provide a json satisfying a schema."""

	image: dspy.Image = dspy.InputField(desc="Input image to be analyzed")
	json_schema = dspy.InputField(desc="JSON schema that the  output should satisfy")
	json_result = dspy.OutputField(
		desc="JSON parsable content with detailed analysis of the image that doesn't start with ```json or ```",
	)

class ImageExtractorGenerator(dspy.Module):
	def __init__(self, model_name: str = "openrouter/google/gemini-2.5-pro:nitro"):
		self.lm = dspy.LM(
			model_name,
			api_key=OPENROUTER_API_KEY,
		)
	
	def forward(self, image_url: str, json_schema: Optional[Dict[str, Any]] = None) -> str:
		with dspy.context(lm=self.lm, adapter=dspy.ChatAdapter()):
			img = dspy.Image.from_url(image_url)

			describe = dspy.ChainOfThought(ImageExtractor)
			result = describe(
				image=img,
				json_schema=json_schema
			)
			return result
