import toml
import openai
from openai import OpenAI

token = toml.load(".streamlit/secrets.toml")["GITHUB_TOKEN"]
client = OpenAI(base_url="https://models.github.ai/inference", api_key=token)

print("openai version:", openai.__version__)
print("URL:", client.base_url)
raw = client.chat.completions.with_raw_response.create(
    model="openai/gpt-4o",
    messages=[{"role": "user", "content": "Say hi"}],
)
print("Status:", raw.http_response.status_code)
print("Body:", raw.http_response.text[:300])