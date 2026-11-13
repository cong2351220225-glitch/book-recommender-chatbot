import os
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))
print("Các mô hình AI bạn được phép dùng là:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)
