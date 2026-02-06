import os

from PIL import Image
from services.form_fields_coordinates_extraction import FormField
from utils.clients import get_moondream_client
from utils.images import annotate_image_with_text
from utils.paths import PROJECT_ROOT

def parse_form_sc(image_path, queries, annotated_output_path = ''):
	moondream_client = get_moondream_client()
	image = Image.open(image_path)

	if isinstance(queries, str):
		queries = [queries]

	all_annotations = []
	for i, query in enumerate(queries):
		result = moondream_client.point(image, query)
		query_annotations = []
		for point in result['points']:
			annotation = (point['x'], point['y'], query)
			all_annotations.append(annotation)
			query_annotations.append(annotation)

		if annotated_output_path and query_annotations:
			base, ext = os.path.splitext(annotated_output_path)
			output = f"{base}_{i}{ext}"
			annotate_image_with_text(query_annotations, image_path, output)

	return all_annotations

if __name__ == "__main__":
	image_path = os.path.join(
		PROJECT_ROOT,
		'test',
		'files',
		'observation_clinique.png'
	)
	form_fields = [FormField(label="Motif d'hospitalisation", description='Indicate the reason for hospitalization.', field_type='form_input'), FormField(label='Histoire de la maladie', description='Provide the history of the disease.', field_type='form_input'), FormField(label='Traitement habituel', description='Regular medication treatment.', field_type='form_input'), FormField(label='Prise médicamementeluse particulière', description='Specify particular medical treatments.', field_type='checkbox'), FormField(label="Examens d'imagerie apportés par le Patient", description='Indicate imaging examinations brought by the patient.', field_type='checkbox'), FormField(label='Documents apportés par le Patient', description='Documents brought by the patient.', field_type='checkbox')]
	queries = [
    	f"form input with label: #{field.label} and type: #{field.field_type}" for field in form_fields
    ]
	parse_form_sc(image_path, queries, 'annotated_output.png')
