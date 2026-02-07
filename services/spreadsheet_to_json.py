import json
from typing import Optional, Dict, Any

import pandas as pd

from services.text_to_json import TextExtractorGenerator


def convert_spreadsheet_to_json_string(file_path: str) -> str:
	"""Convert CSV or Excel file to a JSON string representation."""
	# Determine file type and read accordingly
	if file_path.endswith('.csv'):
		df = pd.read_csv(file_path)
	elif file_path.endswith(('.xlsx', '.xls')):
		df = pd.read_excel(file_path)
	else:
		raise ValueError(f"Unsupported spreadsheet format: {file_path}")
	
	# Convert to JSON-serializable format
	# Use records orientation for readable row-by-row data
	records = df.to_dict(orient='records')
	
	# Create a structured representation
	result = {
		"columns": list(df.columns),
		"row_count": len(df),
		"data": records
	}
	
	return json.dumps(result, indent=2, default=str)


class SpreadsheetExtractorGenerator:
	def __init__(self):
		self.text_extractor = TextExtractorGenerator()

	def __call__(self, file_path: str, json_schema: Optional[Dict[str, Any]] = None):
		# Convert spreadsheet to JSON string
		json_string = convert_spreadsheet_to_json_string(file_path)
		
		# Prepend context to help the model understand the data
		text_with_context = f"""The following is data from a spreadsheet file converted to JSON format:

{json_string}

Please extract the relevant information according to the schema."""
		
		# Use existing text extractor
		result = self.text_extractor(
			text=text_with_context,
			json_schema=json_schema
		)
		return result
