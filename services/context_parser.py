import os

from services.image_to_json import ImageExtractorGenerator
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
			"context_type": "text",
			"path_or_text": "Patient's head is hurting.."
		}
	]

	context_index = 0
	parsed_context = parse_context(
		path_or_text=context_array[context_index]["path_or_text"],
		context_type=context_array[context_index]["context_type"],
		result_schema=result_schema
	)

	print(parsed_context.json_result)
	