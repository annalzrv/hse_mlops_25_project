import torch
import numpy as np
from PIL import Image
from typing import List
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

    def process_listing_images(self, image_paths: List[str], aggregation: str = "mean_max_std") -> np.ndarray:
        """
        Process all images for a listing and return aggregated embedding.
        All operations (extraction, normalization, aggregation) happen on MPS for optimal performance.
        Only final conversion to numpy happens on CPU.

        Args:
            image_paths: List of paths to images
            aggregation: Aggregation method - "mean" (512d), "mean_max_std" (1536d)

        Returns:
            Aggregated embedding vector (1536d for mean_max_std, 512d for mean)
        """
        output_dim = 1536 if aggregation == "mean_max_std" else 512

        if not image_paths:
            logger.warning("No images provided, returning zero vector")
            return np.zeros(output_dim, dtype=np.float32)

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
            return np.zeros(output_dim, dtype=np.float32)

        # Aggregation on MPS
        if len(embeddings_tensor_list) == 1:
            # Single image: use as mean, zeros for max/std variation
            single_emb = embeddings_tensor_list[0].squeeze(0)
            if aggregation == "mean_max_std":
                aggregated = torch.cat([single_emb, single_emb, torch.zeros_like(single_emb)], dim=0)
            else:
                aggregated = single_emb
        else:
            stacked = torch.cat(embeddings_tensor_list, dim=0)  # [N, 512]

            if aggregation == "mean_max_std":
                # Mean + Max + Std aggregation (1536 dims)
                mean_emb = torch.mean(stacked, dim=0)              # [512]
                max_emb = torch.max(stacked, dim=0).values         # [512]
                std_emb = torch.std(stacked, dim=0)                # [512]
                aggregated = torch.cat([mean_emb, max_emb, std_emb], dim=0)  # [1536]
            else:
                # Original mean pooling (512 dims)
                aggregated = torch.mean(stacked, dim=0)

        # Convert to numpy only at the end
        result = aggregated.cpu().numpy().flatten().astype(np.float32)
        logger.info(f"Processed {len(embeddings_tensor_list)}/{len(image_paths)} images on {self.device} ({aggregation}: {len(result)}d)")
        return result

