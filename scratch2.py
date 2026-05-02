import torch
from transformers import CLIPProcessor, CLIPModel

device = "cpu"
clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

inputs = clip_processor(text=["hello"], return_tensors="pt", padding=True).to(device)
with torch.no_grad():
    text_features = clip_model.get_text_features(**inputs)

print("get_text_features returns:", type(text_features))

with torch.no_grad():
    outputs = clip_model(**inputs)

print("model(**inputs) text_embeds:", type(outputs.text_embeds))
print("model(**inputs) text_embeds shape:", outputs.text_embeds.shape)
