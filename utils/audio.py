import io
from utils.clients import CLOUDFLARE_BUCKET, get_s3_client

def s3_urls_from_audios(paths):
	s3_client = get_s3_client()
	urls = []
	for path in paths:
		content = open(path, 'rb').read()
		s3_client.put_object(Bucket=CLOUDFLARE_BUCKET, Key=path, Body=io.BytesIO(content))
		url = s3_client.generate_presigned_url(
			'get_object',
			Params={'Bucket': CLOUDFLARE_BUCKET, 'Key': path},
			ExpiresIn=3600
		)
		urls.append(url)
	return urls
