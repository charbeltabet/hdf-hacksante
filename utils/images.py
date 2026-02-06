import base64
import io
import os
from utils.clients import CLOUDFLARE_BUCKET, get_s3_client
from utils.paths import PROJECT_ROOT
from PIL import Image, ImageDraw, ImageFont

def base64_urls_from_images(paths):
	base64_urls = []
	for image_path in paths:
		with open(image_path, "rb") as image_file:
			base64_string = base64.b64encode(image_file.read()).decode('utf-8')
			base64_url = f"data:image/{image_path.split('.')[-1]};base64,{base64_string}"
			base64_urls.append(base64_url)
	return base64_urls

def s3_urls_from_images(paths):
	s3_client = get_s3_client()
	urls = []
	for path in paths:
		content = open(path, 'rb').read()
		response = s3_client.put_object(Bucket=CLOUDFLARE_BUCKET, Key=path, Body=io.BytesIO(content))
		url = s3_client.generate_presigned_url(
			'get_object',
			Params={'Bucket': CLOUDFLARE_BUCKET, 'Key': path},
			ExpiresIn=3600
		)
		urls.append(url)
	return urls

def annotate_image_with_text(annotations: list[tuple[float, float, str]], image_path: str, output_path: str):
	img = Image.open(image_path)
	draw = ImageDraw.Draw(img)
	w, h = img.size
	font_size = max(16, int(min(w, h) * 0.03))
	font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
	for x, y, text in annotations:
		cx = int(x * w)
		cy = int(y * h)
		draw.text((cx, cy), text, fill='red', anchor='mm', font=font)

	img.save(output_path)

if __name__ == "__main__":
	image_path = os.path.join(
		PROJECT_ROOT,
		'test',
		'files',
		'observation_clinique.png'
	)
	urls = s3_urls_from_images([image_path])
	print(urls)
