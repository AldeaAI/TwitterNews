# TwitterNews & InstagramNews

## Overview
This project automates the process of finding, analyzing, and posting news about Colombian real estate to Twitter and Instagram.

- **Twitter:** Generates and posts a concise tweet with a link to the article.
- **Instagram:** Uses the same text (excluding the link) to generate an image post with a background and Roboto font. The link is placed in the Instagram post description or comments. Optionally, the post can be published automatically to Instagram.

## Instagram Posting Workflow
1. After generating the tweet text, the same text (minus the link) is rendered onto an image using `InstagramNews/Backgrounds/InstagramBackground_1.png` and the Roboto font.
2. The link is extracted from the tweet and used as the Instagram caption/description.
3. The image is saved to `InstagramNews/generated_instagram_post.png`.
4. If Instagram credentials are provided, the image and caption are posted automatically using the [instagrapi](https://github.com/adw0rd/instagrapi) library.
5. If credentials are not provided, the image and caption are generated for manual upload.

## Usage
- Ensure you have the required dependencies:
  - `Pillow` for image generation
  - `instagrapi` for Instagram posting (optional, only if you want to auto-post)
- Place the Roboto font file (`Roboto-Regular.ttf`) in the project root or update the path in `main.py`.
- Instagram credentials can be set in `main.py` or via environment variables.

## Example
After running the pipeline, you will see output indicating the location of the generated Instagram image and the caption to use. If credentials are set, the post will be published automatically.

## File Structure
- `main.py`: Orchestrates the pipeline and now calls the Instagram post generator.
- `InstagramNews/instagram_post.py`: Contains functions for generating and posting Instagram images.
- `InstagramNews/Backgrounds/InstagramBackground_1.png`: Background image for Instagram posts.

## Configuration
- Twitter and Perplexity API keys are managed via `config.toml` or environment variables.
- Instagram credentials (optional) can be set as environment variables or directly in `main.py`.

## Dependencies
```
pip install Pillow instagrapi
```

## Notes
- The Instagram auto-post feature is optional. If you do not provide credentials, you can upload the generated image and caption manually.
- The Roboto font file must be available for best results.
