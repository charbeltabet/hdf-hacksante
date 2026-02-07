import json
from utils.clients import get_openai_client, DEFAULT_MODEL


PATIENT_SYSTEM_PROMPT = """You are a friendly medical intake assistant having a conversation with a PATIENT to collect their information.

You must gather data to populate the following JSON schema:
{schema}

RULES:
- Ask about ONE or TWO related fields at a time, in a natural conversational way.
- Keep questions short, clear, and use simple non-medical language the patient can understand.
- If the patient provides information about multiple fields at once, acknowledge all of it.
- Be warm, empathetic, and reassuring.
- If the patient says something unrelated, gently redirect to the intake questions.
- Do NOT provide a summary unless explicitly asked.
- When asking about fields that have predefined options (array type with enum values), present ALL available options as a markdown bullet list so the patient can pick. Use **bold** for the option names.
- You may use markdown formatting (bold, bullet lists, numbered lists) to make your messages clearer and easier to read.

IMPORTANT — At the END of every response, you MUST include a status block on a new line in exactly this format:
<!--STATUS::{"collected":["field1","field2"],"missing":["field3","field4"]}-->
where "collected" lists schema field names for which you have gathered sufficient info, and "missing" lists those still needed.
This block MUST always be present, even in your very first message. Do not explain it to the user.
"""

DOCTOR_SYSTEM_PROMPT = """You are a medical intake assistant having a conversation with a DOCTOR or healthcare professional to collect patient information.

You must gather data to populate the following JSON schema:
{schema}

RULES:
- Ask about ONE or TWO related fields at a time in a concise, professional manner.
- You can use medical terminology freely — the user is a healthcare professional.
- If the doctor provides information about multiple fields at once, acknowledge all of it.
- Be efficient and to the point.
- If the doctor says something unrelated, redirect to the remaining fields.
- Do NOT provide a summary unless explicitly asked.
- When asking about fields that have predefined options (array type with enum values), present ALL available options as a markdown bullet list so the doctor can select. Use **bold** for the option names.
- You may use markdown formatting (bold, bullet lists, numbered lists) to make your messages clearer.

IMPORTANT — At the END of every response, you MUST include a status block on a new line in exactly this format:
<!--STATUS::{"collected":["field1","field2"],"missing":["field3","field4"]}-->
where "collected" lists schema field names for which you have gathered sufficient info, and "missing" lists those still needed.
This block MUST always be present, even in your very first message. Do not explain it to the user.
"""

SUMMARY_PROMPT = """Based on the conversation so far, provide a comprehensive text summary of ALL patient information collected.
Format it as a clear, readable medical intake note. Include all details mentioned.
Start your response directly with the summary content — no preamble.
Do NOT include a STATUS block in this response."""


def create_chat_session(schema_str, role="patient"):
    schema = json.loads(schema_str)
    template = PATIENT_SYSTEM_PROMPT if role == "patient" else DOCTOR_SYSTEM_PROMPT
    system_message = template.replace("{schema}", json.dumps(schema, indent=2))
    return [{"role": "system", "content": system_message}]


def chat_message_stream(messages, user_message):
    client = get_openai_client()
    messages.append({"role": "user", "content": user_message})

    stream = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=messages,
        stream=True,
    )

    return stream, messages


def finalize_stream(messages, full_reply):
    messages.append({"role": "assistant", "content": full_reply})
    return messages


def parse_status_from_reply(full_reply):
    import re
    match = re.search(r'<!--STATUS::(.*?)-->', full_reply, re.DOTALL)
    if match:
        raw = match.group(1).strip()
        # Strip double braces if the LLM wrapped with {{ }}
        if raw.startswith("{{") and raw.endswith("}}"):
            raw = raw[1:-1]
        try:
            status = json.loads(raw)
            visible_text = full_reply[:match.start()].rstrip()
            return visible_text, status
        except json.JSONDecodeError:
            pass
    return full_reply, None


def request_summary_stream(messages):
    client = get_openai_client()
    messages.append({"role": "user", "content": SUMMARY_PROMPT})

    stream = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=messages,
        stream=True,
    )

    return stream, messages
