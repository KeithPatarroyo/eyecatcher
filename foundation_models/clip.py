"""
CLIP model integration for image embedding.
Used to convert CPPN-generated images to latent representations
for computing open-endedness scores.
"""
import numpy as np
from typing import Optional, Union
from PIL import Image


class CLIPEmbedder:
    """
    CLIP image embedder for computing latent representations.

    Uses OpenAI's CLIP model via transformers library to embed images
    into a shared latent space where semantic similarity can be computed.
    """

    def __init__(self, model_name: str = "openai/clip-vit-base-patch32", device: str = "cpu"):
        """
        Initialize the CLIP embedder.

        Parameters
        ----------
        model_name : str
            The CLIP model to use. Default is ViT-B/32.
        device : str
            Device to run the model on ('cpu' or 'cuda').
        """
        self.model_name = model_name
        self.device = device
        self._model = None
        self._processor = None

    def _load_model(self):
        """Lazy load the model on first use."""
        if self._model is not None:
            return

        try:
            import torch
            from transformers import CLIPModel, CLIPProcessor

            self._model = CLIPModel.from_pretrained(self.model_name)
            self._processor = CLIPProcessor.from_pretrained(self.model_name)
            self._model = self._model.to(self.device)
            self._model.eval()
        except ImportError as e:
            raise ImportError(
                "CLIP requires torch and transformers. "
                "Install with: pip install torch transformers"
            ) from e

    def embed_image(self, image: Union[np.ndarray, Image.Image]) -> np.ndarray:
        """
        Embed a single image into CLIP latent space.

        Parameters
        ----------
        image : np.ndarray or PIL.Image
            Image to embed. If numpy array, should be (H, W, C) with values in [0, 255]
            or [0, 1]. Will be converted to PIL Image internally.

        Returns
        -------
        np.ndarray
            L2-normalized embedding vector of shape (D,) where D is the embedding dimension
            (512 for ViT-B/32, 768 for ViT-L/14).
        """
        self._load_model()
        import torch

        # Convert numpy array to PIL Image if needed
        if isinstance(image, np.ndarray):
            # Handle both [0, 1] and [0, 255] ranges
            if image.max() <= 1.0:
                image = (image * 255).astype(np.uint8)
            image = Image.fromarray(image)

        # Process image through CLIP
        inputs = self._processor(images=image, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._model.get_image_features(**inputs)

        # L2 normalize
        embedding = outputs.cpu().numpy().squeeze()
        embedding = embedding / np.linalg.norm(embedding)

        return embedding

    def embed_images(self, images: list) -> np.ndarray:
        """
        Embed multiple images into CLIP latent space.

        Parameters
        ----------
        images : list
            List of images (np.ndarray or PIL.Image).

        Returns
        -------
        np.ndarray
            L2-normalized embeddings of shape (N, D) where N is number of images.
        """
        self._load_model()
        import torch

        # Convert all images to PIL
        pil_images = []
        for img in images:
            if isinstance(img, np.ndarray):
                if img.max() <= 1.0:
                    img = (img * 255).astype(np.uint8)
                img = Image.fromarray(img)
            pil_images.append(img)

        # Batch process
        inputs = self._processor(images=pil_images, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._model.get_image_features(**inputs)

        # L2 normalize
        embeddings = outputs.cpu().numpy()
        norms = np.linalg.norm(embeddings, axis=-1, keepdims=True)
        embeddings = embeddings / norms

        return embeddings

    def embed_text(self, text: str) -> np.ndarray:
        """
        Embed text into CLIP latent space.

        Parameters
        ----------
        text : str
            Text to embed.

        Returns
        -------
        np.ndarray
            L2-normalized embedding vector of shape (D,).
        """
        self._load_model()
        import torch

        inputs = self._processor(text=[text], return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._model.get_text_features(**inputs)

        embedding = outputs.cpu().numpy().squeeze()
        embedding = embedding / np.linalg.norm(embedding)

        return embedding

    def embed_texts(self, texts: list) -> np.ndarray:
        """
        Embed multiple texts into CLIP latent space.

        Parameters
        ----------
        texts : list
            List of text strings.

        Returns
        -------
        np.ndarray
            L2-normalized embeddings of shape (N, D).
        """
        self._load_model()
        import torch

        inputs = self._processor(text=texts, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._model.get_text_features(**inputs)

        embeddings = outputs.cpu().numpy()
        norms = np.linalg.norm(embeddings, axis=-1, keepdims=True)
        embeddings = embeddings / norms

        return embeddings

    @property
    def embedding_dim(self) -> int:
        """Get the embedding dimension for the loaded model."""
        self._load_model()
        # ViT-B models have 512 dim, ViT-L have 768
        if "vit-l" in self.model_name.lower() or "large" in self.model_name.lower():
            return 768
        return 512
