import os
import tempfile
from typing import Optional, Dict, Any

import fitz  # PyMuPDF

from services.image_to_json import ImageExtractorGenerator
from utils.images import s3_urls_from_images


def convert_pdf_to_images(pdf_path: str) -> list[str]:
	"""Convert each page of a PDF to an image file. Returns list of image paths."""
	doc = fitz.open(pdf_path)
	image_paths = []
	
	for page_num in range(len(doc)):
		page = doc[page_num]
		# Render page to image with good resolution (2x zoom)
		mat = fitz.Matrix(2, 2)
		pix = page.get_pixmap(matrix=mat)
		
		# Save to temp file
		tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_page{page_num + 1}.png")
		pix.save(tmp.name)
		image_paths.append(tmp.name)
	
	doc.close()
	return image_paths


class PDFExtractorGenerator:
	def __init__(self):
		self.image_extractor = ImageExtractorGenerator()

	def __call__(self, pdf_path: str, json_schema: Optional[Dict[str, Any]] = None):
		# Convert PDF pages to images
		image_paths = convert_pdf_to_images(pdf_path)
		
		try:
			# Upload first page image to S3 and get URL
			# For now, process first page only (can be extended to merge results from all pages)
			image_url = s3_urls_from_images(image_paths)[0]
			
			# Use existing image extractor
			result = self.image_extractor(
				image_url=image_url,
				json_schema=json_schema
			)
			return result
		finally:
			# Clean up temp image files
			for path in image_paths:
				if os.path.exists(path):
					os.unlink(path)
