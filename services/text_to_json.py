from typing import Optional, Dict, Any
from utils.clients import OPENROUTER_API_KEY

import dspy

class TextExtractor(dspy.Signature):
	"""Extract structured data from text and provide a json satisfying a schema."""

	text: str = dspy.InputField(desc="Input text to extract data from")
	json_schema = dspy.InputField(desc="JSON schema that the output should satisfy")
	json_result = dspy.OutputField(
		desc="JSON parsable content with data extracted from the text that doesn't start with ```json or ```",
	)

class TextExtractorGenerator(dspy.Module):
	def __init__(self, model_name: str = "openrouter/openai/gpt-oss-120b:nitro"):
		self.lm = dspy.LM(
			model_name,
			api_key=OPENROUTER_API_KEY,
		)

	def forward(self, text: str, json_schema: Optional[Dict[str, Any]] = None) -> str:
		with dspy.context(lm=self.lm, adapter=dspy.ChatAdapter()):
			extract = dspy.ChainOfThought(TextExtractor)
			result = extract(
				text=text,
				json_schema=json_schema
			)
			return result
