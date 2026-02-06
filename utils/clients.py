import os
from PIL import Image
from openai import OpenAI
import boto3
from botocore.config import Config
from utils.paths import DOTENV_PATH, PROJECT_ROOT
import moondream as md

from dotenv import load_dotenv
load_dotenv(DOTENV_PATH)

PROVIDER = "openrouter"
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "openai/gpt-4o-mini:nitro")

def get_openai_client():
    return OpenAI(
		base_url=OPENROUTER_BASE_URL,
		api_key=OPENROUTER_API_KEY
	)

CLOUDFLARE_TOKEN_VALUE = os.getenv("CLOUDFLARE_TOKEN_VALUE")
CLOUDFLARE_ENDPOINT_URL = os.getenv("CLOUDFLARE_ENDPOINT_URL")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_ACCESS_KEY = os.getenv("CLOUDFLARE_ACCESS_KEY")
CLOUDFLARE_ACCESS_KEY_ID = os.getenv("CLOUDFLARE_ACCESS_KEY_ID")
CLOUDFLARE_BUCKET = os.getenv("CLOUDFLARE_BUCKET")

def get_s3_client():
	config = Config(signature_version='s3v4')

	s3 = boto3.client(
		's3',
		endpoint_url=CLOUDFLARE_ENDPOINT_URL,
		aws_access_key_id=CLOUDFLARE_ACCESS_KEY_ID,
		aws_secret_access_key=CLOUDFLARE_ACCESS_KEY,
		config=config
	)

	return s3
    
MOONDREAM_API_KEY = os.getenv("MOONDREAM_API_KEY")
def get_moondream_client():
	return md.vl(api_key=MOONDREAM_API_KEY)
	

if __name__ == "__main__":
	moondream_client = get_moondream_client()
	openai_client = get_openai_client()

	# response = openai_client.chat.completions.create(
	# 	model=DEFAULT_MODEL,
	# 	messages=[
	# 		{"role": "user", "content": "Hello, how are you?"}
	# 	]
	# )
	# print(response.choices[0].message.content)
