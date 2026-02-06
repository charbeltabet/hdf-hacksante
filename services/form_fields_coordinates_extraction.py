import os
import dspy
from utils.clients import DEFAULT_MODEL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL, PROVIDER, get_openai_client
from utils.paths import PROJECT_ROOT
from typing import List, Literal
from pydantic import BaseModel

FieldType = Literal["form_input", "searchable_select", "checkbox"]

class FormField(BaseModel):
    label: str
    description: str
    field_type: FieldType

class FormExtractionSignature(dspy.Signature):
    """Extract form fields from an image with normalized coordinates (0-1 range)."""
    
    image: dspy.Image = dspy.InputField(desc="Form image to analyze")
    form_inputs: List[FormField] = dspy.OutputField(
        desc="Extracted form input fields"
    )

def parse_form_sc(image_url: str):
    # Configure DSPy with OpenAI
    lm = dspy.LM(
        model=f"{PROVIDER}/{DEFAULT_MODEL}",
        api_key=OPENROUTER_API_KEY,
        api_base=OPENROUTER_BASE_URL
    )
    dspy.configure(lm=lm)
    
    # Create predictor
    extractor = dspy.Predict(FormExtractionSignature)
    
    # Create dspy.Image from URL
    image = dspy.Image(image_url)
    
    # Run extraction
    result = extractor(image=image)
    
    return result.form_inputs

if __name__ == "__main__":
	image_path = os.path.join(
    	PROJECT_ROOT,
		'test',
		'files',
    	'patient_intake_form.png'
    )
	url = "https://2acb0887bdda787de8d4e2eb02b2b9ea.r2.cloudflarestorage.com/hdf-hackathon-bucket//Users/shtb/src/hsante/test/files/observation_clinique.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e305c346d9b9120cf4b1a34630b9b2ef%2F20260206%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20260206T132354Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=b516c48118f0af83f114555c1f382a866cdd76cd687af45f2ec10d29d004728a"
	result = parse_form_sc(url)
	print(result)
