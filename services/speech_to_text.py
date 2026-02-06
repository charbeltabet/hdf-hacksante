import requests
import json
import sys
from utils.clients import DEEPGRAM_API_KEY, DEEPGRAM_BASE_URL

def transcribe_audio(audio_url: str, language: str = "en", model: str = "nova-3") -> str:
	url = f"{DEEPGRAM_BASE_URL}/listen?smart_format=true&language={language}&model={model}"

	payload = json.dumps({
		"url": audio_url
	})

	headers = {
		'Authorization': f'Token {DEEPGRAM_API_KEY}',
		'Content-Type': 'application/json'
	}

	response = requests.request("POST", url, headers=headers, data=payload)
	result = response.json()
	return result["results"]["channels"][0]["alternatives"][0]["transcript"]


if __name__ == "__main__":
	transcript = transcribe_audio(sys.argv[1])
	print(transcript)
