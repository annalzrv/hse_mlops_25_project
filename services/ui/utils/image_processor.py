import torch
import numpy as np
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from typing import List, Optional
import io

class ImageProcessor:
    def __init__(self):
        self.device = self._get_device()
        self.model = None
        self.processor = None
        self._load_model()

    def _get_device(self) -> str:
        if torch.backends.mps.is_available():
            return "mps"
        elif torch.cuda.is_available():
            return "cuda"
        else:
            return "cpu"

    def _load_model(self):
        try:
            self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            self.model = self.model.to(self.device)
            self.model.eval()
        except Exception as e:
            self.model = None
            self.processor = None
            raise Exception(f"Failed to load CLIP model: {str(e)}")

    def resize_image(self, image: Image.Image, max_size: int = 224) -> Image.Image:
        image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        return image

    def process_images(self, image_files: List[bytes]) -> Optional[np.ndarray]:
        if not self.model or not self.processor:
            return None

        if not image_files:
            return np.zeros(512, dtype=np.float32)

        embeddings_list = []

        for img_bytes in image_files:
            try:
                image = Image.open(io.BytesIO(img_bytes))
                if image.mode != 'RGB':
                    image = image.convert('RGB')

                resized_image = self.resize_image(image)
                inputs = self.processor(images=resized_image, return_tensors="pt")
                inputs = {k: v.to(self.device) for k, v in inputs.items()}

                with torch.no_grad():
                    image_features = self.model.get_image_features(**inputs)
                    image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                    embeddings_list.append(image_features)

            except Exception:
                continue

        if not embeddings_list:
            return np.zeros(512, dtype=np.float32)

        if len(embeddings_list) == 1:
            aggregated = embeddings_list[0]
        else:
            stacked = torch.cat(embeddings_list, dim=0)
            aggregated = torch.mean(stacked, dim=0)

        result = aggregated.cpu().numpy().flatten().astype(np.float32)
        return result
