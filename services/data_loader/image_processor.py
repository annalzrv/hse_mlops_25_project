import os
import torch
import numpy as np
from PIL import Image
from pathlib import Path
from typing import List, Optional
from transformers import CLIPProcessor, CLIPModel
from logger import setup_logger

logger = setup_logger(__name__)

class ImageProcessor:
    def __init__(self):
        device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.device = torch.device(device)
        logger.info(f"Using device: {device}")
        
        logger.info("Loading CLIP model...")
        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.model.to(self.device)
        self.model.eval()
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        logger.info("CLIP model loaded successfully")
        
    def resize_image(self, image_path: str, size: tuple = (224, 224)) -> Image.Image:
        try:
            image = Image.open(image_path).convert("RGB")
            image.thumbnail(size, Image.Resampling.LANCZOS)
            
            new_image = Image.new("RGB", size, (0, 0, 0))
            paste_x = (size[0] - image.width) // 2
            paste_y = (size[1] - image.height) // 2
            new_image.paste(image, (paste_x, paste_y))
            
            return new_image
        except Exception as e:
            logger.error(f"Error resizing image {image_path}: {e}")
            raise
    
    def process_listing_images(self, image_paths: List[str]) -> np.ndarray:
        """
        Process all images for a listing and return aggregated embedding.
        All operations (extraction, normalization, aggregation) happen on MPS for optimal performance.
        Only final conversion to numpy happens on CPU.
        """
        if not image_paths:
            logger.warning("No images provided, returning zero vector")
            return np.zeros(512, dtype=np.float32)
        
        embeddings_tensor_list = []
        
        for image_path in image_paths:
            try:
                resized_image = self.resize_image(image_path)
                inputs = self.processor(images=resized_image, return_tensors="pt")
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                with torch.no_grad():
                    image_features = self.model.get_image_features(**inputs)
                    # normalization on MPS
                    image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                    embeddings_tensor_list.append(image_features)
                    
            except Exception as e:
                logger.warning(f"Failed to process image {image_path}: {e}")
                continue
        
        if not embeddings_tensor_list:
            logger.warning("No embeddings extracted, returning zero vector")
            return np.zeros(512, dtype=np.float32)
        
        # aggregation on MPS (mean pooling without transferring to CPU)
        if len(embeddings_tensor_list) == 1:
            aggregated = embeddings_tensor_list[0]
        else:
            stacked = torch.cat(embeddings_tensor_list, dim=0)
            aggregated = torch.mean(stacked, dim=0, keepdim=True)
        
        # convert to numpy only at the end
        result = aggregated.cpu().numpy().flatten().astype(np.float32)
        logger.info(f"Processed {len(embeddings_tensor_list)}/{len(image_paths)} images on {self.device}")
        return result

