"""
CLIP model integration for image embedding using JAX/Flax.
Used to convert CPPN-generated images to latent representations
for computing open-endedness scores.
"""
import jax
import jax.numpy as jnp
import numpy as np
from typing import Optional, Union
from PIL import Image


class CLIPEmbedder:
    """
    CLIP image embedder for computing latent representations.

    Uses OpenAI's CLIP model via transformers Flax implementation to embed images
    into a shared latent space where semantic similarity can be computed.
    """

    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        """
        Initialize the CLIP embedder.

        Parameters
        ----------
        model_name : str
            The CLIP model to use. Default is ViT-B/32.
        """
        self.model_name = model_name
        self._model = None
        self._processor = None
        self._params = None

    def _load_model(self):
        """Lazy load the model on first use."""
        if self._model is not None:
            return

        try:
            from transformers import FlaxCLIPModel, CLIPProcessor

            self._model = FlaxCLIPModel.from_pretrained(self.model_name)
            self._processor = CLIPProcessor.from_pretrained(self.model_name)
            self._params = self._model.params
        except ImportError as e:
            raise ImportError(
                "CLIP requires jax, flax and transformers. "
                "Install with: pip install jax jaxlib flax transformers"
            ) from e

    def embed_image(self, image: Union[np.ndarray, Image.Image]) -> jnp.ndarray:
        """
        Embed a single image into CLIP latent space.

        Parameters
        ----------
        image : np.ndarray or PIL.Image
            Image to embed. If numpy array, should be (H, W, C) with values in [0, 255]
            or [0, 1]. Will be converted to PIL Image internally.

        Returns
        -------
        jnp.ndarray
            L2-normalized embedding vector of shape (D,) where D is the embedding dimension
            (512 for ViT-B/32, 768 for ViT-L/14).
        """
        self._load_model()

        # Convert numpy array to PIL Image if needed
        if isinstance(image, np.ndarray):
            # Handle both [0, 1] and [0, 255] ranges
            if image.max() <= 1.0:
                image = (image * 255).astype(np.uint8)
            image = Image.fromarray(image)

        # Process image through CLIP
        inputs = self._processor(images=image, return_tensors="jax")

        # Get image features
        outputs = self._model.get_image_features(
            pixel_values=inputs["pixel_values"],
            params=self._params,
        )

        # L2 normalize
        embedding = outputs.squeeze()
        embedding = embedding / jnp.linalg.norm(embedding)

        return embedding

    def embed_images(self, images: list) -> jnp.ndarray:
        """
        Embed multiple images into CLIP latent space.

        Parameters
        ----------
        images : list
            List of images (np.ndarray or PIL.Image).

        Returns
        -------
        jnp.ndarray
            L2-normalized embeddings of shape (N, D) where N is number of images.
        """
        self._load_model()

        # Convert all images to PIL
        pil_images = []
        for img in images:
            if isinstance(img, np.ndarray):
                if img.max() <= 1.0:
                    img = (img * 255).astype(np.uint8)
                img = Image.fromarray(img)
            pil_images.append(img)

        # Batch process
        inputs = self._processor(images=pil_images, return_tensors="jax")

        # Get image features
        outputs = self._model.get_image_features(
            pixel_values=inputs["pixel_values"],
            params=self._params,
        )

        # L2 normalize
        norms = jnp.linalg.norm(outputs, axis=-1, keepdims=True)
        embeddings = outputs / norms

        return embeddings

    def embed_text(self, text: str) -> jnp.ndarray:
        """
        Embed text into CLIP latent space.

        Parameters
        ----------
        text : str
            Text to embed.

        Returns
        -------
        jnp.ndarray
            L2-normalized embedding vector of shape (D,).
        """
        self._load_model()

        inputs = self._processor(text=[text], return_tensors="jax", padding=True)

        # Get text features
        outputs = self._model.get_text_features(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            params=self._params,
        )

        embedding = outputs.squeeze()
        embedding = embedding / jnp.linalg.norm(embedding)

        return embedding

    def embed_texts(self, texts: list) -> jnp.ndarray:
        """
        Embed multiple texts into CLIP latent space.

        Parameters
        ----------
        texts : list
            List of text strings.

        Returns
        -------
        jnp.ndarray
            L2-normalized embeddings of shape (N, D).
        """
        self._load_model()

        inputs = self._processor(text=texts, return_tensors="jax", padding=True)

        # Get text features
        outputs = self._model.get_text_features(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            params=self._params,
        )

        norms = jnp.linalg.norm(outputs, axis=-1, keepdims=True)
        embeddings = outputs / norms

        return embeddings

    @property
    def embedding_dim(self) -> int:
        """Get the embedding dimension for the loaded model."""
        self._load_model()
        # ViT-B models have 512 dim, ViT-L have 768
        if "vit-l" in self.model_name.lower() or "large" in self.model_name.lower():
            return 768
        return 512
