import torch
from transformers import CLIPProcessor, CLIPModel

device = "cpu"
clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

inputs = clip_processor(text=["hello"], return_tensors="pt", padding=True).to(device)
with torch.no_grad():
    text_features = clip_model.get_text_features(**inputs)
    
print("type:", type(text_features))
if hasattr(text_features, "shape"):
    print("shape:", text_features.shape)
else:
    print("attributes:", dir(text_features))
    if hasattr(text_features, "pooler_output"):
        print("pooler shape:", text_features.pooler_output.shape)
