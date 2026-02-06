import requests
from utils.clients import GOOGLE_VISION_API_KEY, GOOGLE_VISION_BASE_URL

def transcribe_image(image_url: str) -> str:
	url = f"{GOOGLE_VISION_BASE_URL}/images:annotate?key={GOOGLE_VISION_API_KEY}"

	payload = {
		"requests": [
			{
				"image": {"source": {"imageUri": image_url}},
				"features": [{"type": "TEXT_DETECTION"}]
			}
		]
	}

	response = requests.post(url, json=payload)
	result = response.json()
	import pdb; pdb.set_trace()
	return result["responses"][0]["textAnnotations"][0]["description"]


if __name__ == "__main__":
	url = "https://2acb0887bdda787de8d4e2eb02b2b9ea.r2.cloudflarestorage.com/hdf-hackathon-bucket//Users/shtb/src/hsante/test/files/observation_clinique.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e305c346d9b9120cf4b1a34630b9b2ef%2F20260206%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20260206T184109Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=ea71bf54ee58c0e14cc4c7e96cab7646bf1573c13807cb212ba6cd8f85fa5d9f"
	text = transcribe_image(url)
	print(text)
