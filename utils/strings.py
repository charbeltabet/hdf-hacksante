import json

def safe_json_parse(json_string):
	try:
		return json.loads(json_string)
	except json.JSONDecodeError:
		return None