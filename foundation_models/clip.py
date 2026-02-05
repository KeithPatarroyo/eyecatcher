# import os
# os.environ["TOKENIZERS_PARALLELISM"] = "false"

"""
CLIP model integration for image embedding.
Based on: https://github.com/SakanaAI/asal/blob/main/foundation_models/clip.py
"""
import jax
import jax.numpy as jnp
from einops import rearrange
from transformers import AutoProcessor, FlaxCLIPModel


class CLIP:
    def __init__(self, clip_model="clip-vit-base-patch32"):
        self.processor = AutoProcessor.from_pretrained(f"openai/{clip_model}")
        self.clip_model = FlaxCLIPModel.from_pretrained(f"openai/{clip_model}")

        self.img_mean = jnp.array(self.processor.image_processor.image_mean)
        self.img_std = jnp.array(self.processor.image_processor.image_std)

    def embed_img(self, img):
        """
        img shape (H W C) and values in [0, 1].
        returns shape (D)
        """
        H, W, C = img.shape
        if H != 224 or W != 224:
            img = jax.image.resize(img, (224, 224, C), method='bilinear')
        img = rearrange((img - self.img_mean) / self.img_std, "H W C -> 1 C H W")
        z_img = self.clip_model.get_image_features(img)[0]
        return z_img / jnp.linalg.norm(z_img, axis=-1, keepdims=True)

    def embed_txt(self, prompts):
        """
        prompts is list of strings
        returns shape (B D)
        """
        inputs = self.processor(text=prompts, return_tensors="jax", padding=True)
        z_text = self.clip_model.get_text_features(
            input_ids=inputs['input_ids'],
            attention_mask=inputs['attention_mask']
        )
        return z_text / jnp.linalg.norm(z_text, axis=-1, keepdims=True)


# Wrapper class for compatibility with our evolution code
class CLIPEmbedder:
    """
    Wrapper around CLIP class for compatibility with vlm_evolution.
    """

    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        # Extract model name (e.g., "clip-vit-base-patch32" from "openai/clip-vit-base-patch32")
        if "/" in model_name:
            model_name = model_name.split("/")[-1]
        self._clip = None
        self._model_name = model_name

    def _load_model(self):
        if self._clip is None:
            self._clip = CLIP(clip_model=self._model_name)

    def embed_image(self, image):
        """
        Embed a single image.

        Parameters
        ----------
        image : np.ndarray or jnp.ndarray
            Image of shape (H, W, C) with values in [0, 255] or [0, 1].

        Returns
        -------
        jnp.ndarray
            L2-normalized embedding of shape (D,).
        """
        self._load_model()
        import numpy as np

        # Convert to JAX array if needed
        if isinstance(image, np.ndarray):
            image = jnp.array(image)

        # Normalize to [0, 1] if in [0, 255]
        if image.max() > 1.0:
            image = image / 255.0

        return self._clip.embed_img(image)

    def embed_images(self, images):
        """
        Embed multiple images.

        Parameters
        ----------
        images : list
            List of images (np.ndarray or jnp.ndarray), each of shape (H, W, C).

        Returns
        -------
        jnp.ndarray
            L2-normalized embeddings of shape (N, D).
        """
        self._load_model()
        import numpy as np

        embeddings = []
        for img in images:
            # Convert to JAX array if needed
            if isinstance(img, np.ndarray):
                img = jnp.array(img)

            # Normalize to [0, 1] if in [0, 255]
            if img.max() > 1.0:
                img = img / 255.0

            emb = self._clip.embed_img(img)
            embeddings.append(emb)

        return jnp.stack(embeddings)

    def embed_text(self, text):
        """
        Embed a single text string.

        Parameters
        ----------
        text : str
            Text to embed.

        Returns
        -------
        jnp.ndarray
            L2-normalized embedding of shape (D,).
        """
        self._load_model()
        return self._clip.embed_txt([text])[0]

    def embed_texts(self, texts):
        """
        Embed multiple text strings.

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
        return self._clip.embed_txt(texts)
