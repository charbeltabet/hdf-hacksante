import os

from services.image_to_json import ImageExtractorGenerator
from services.pdf_to_json import PDFExtractorGenerator
from services.spreadsheet_to_json import SpreadsheetExtractorGenerator
from services.speech_to_text import transcribe_audio
from services.text_to_json import TextExtractorGenerator
from utils.audio import s3_urls_from_audios
from utils.images import s3_urls_from_images
from utils.paths import PROJECT_ROOT

def parse_context(path_or_text, context_type, result_schema):
	if context_type == "image":
		return parse_image(path_or_text, result_schema)
	elif context_type == "text":
		return parse_text(path_or_text, result_schema)
	elif context_type == "audio":
		return parse_audio(path_or_text, result_schema)
	elif context_type == "pdf":
		return parse_pdf(path_or_text, result_schema)
	elif context_type == "spreadsheet":
		return parse_spreadsheet(path_or_text, result_schema)
	elif context_type == "json":
		return parse_json_file(path_or_text, result_schema)
	else:
		raise ValueError(f"Unsupported context type: {context_type}")

def parse_image(image_path, result_schema):
	image_url = s3_urls_from_images([image_path])[0]
	extraction_program = ImageExtractorGenerator()

	result = extraction_program(
		image_url=image_url,
		json_schema=result_schema
	)

	return result

def parse_text(text, result_schema):
	extraction_program = TextExtractorGenerator()	
	result = extraction_program(
		text=text,
		json_schema=result_schema
	)

	return result

def parse_audio(audio_path, result_schema):
	audio_url = s3_urls_from_audios([audio_path])[0]
	text = transcribe_audio(audio_url)

	return parse_text(text, result_schema)

def parse_pdf(pdf_path, result_schema):
	extraction_program = PDFExtractorGenerator()

	result = extraction_program(
		pdf_path=pdf_path,
		json_schema=result_schema
	)

	return result

def parse_spreadsheet(file_path, result_schema):
	extraction_program = SpreadsheetExtractorGenerator()

	result = extraction_program(
		file_path=file_path,
		json_schema=result_schema
	)

	return result

def parse_json_file(file_path, result_schema):
	# Read JSON file as text and pass to text parser
	with open(file_path, 'r') as f:
		json_text = f.read()
	return parse_text(json_text, result_schema)

if __name__ == "__main__":
	schema_path = os.path.join(
		PROJECT_ROOT,
		"forms_schema",
		"questionaire_schema.json"
	)
	result_schema = open(schema_path).read()

	context_array = [
		{
			"context_type": "image",
			"path_or_text": os.path.join(
				PROJECT_ROOT,
				'test',
				'files',
				'form_context',
				'observation',
				'handwritten_note.png'
			)
		},
		{
			"context_type": "audio",
			"path_or_text": os.path.join(
				PROJECT_ROOT,
				'test',
				'files',
				'form_context',
				'observation',
				'conversation_recording.m4a'
			)
		},
		{
			"context_type": "spreadsheet",
			"path_or_text": os.path.join(
				PROJECT_ROOT,
				'test',
				'files',
				'form_context',
				'observation',
				'csv_prescription.csv'
			)
		},
		{
			"context_type": "spreadsheet",
			"path_or_text": os.path.join(
				PROJECT_ROOT,
				'test',
				'files',
				'form_context',
				'observation',
				'csv_prescription.xlsx'
			)	
		},
		{
			"context_type": "pdf",
			"path_or_text": os.path.join(
				PROJECT_ROOT,
				'test',
				'files',
				'form_context',
				'observation',
				'discharge_summary.pdf'
			)
		},
		{
			"context_type": "text",
			"path_or_text": "Patient's head is hurting.."
		},
	]

	context_index = 3
	parsed_context = parse_context(
		path_or_text=context_array[context_index]["path_or_text"],
		context_type=context_array[context_index]["context_type"],
		result_schema=result_schema
	)

	print(parsed_context.json_result)
	