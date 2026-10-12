"""
The list of image-to-video models the tool can use.

To switch model: change VIDEO_MODEL in your .env file to one of the names below
(for example VIDEO_MODEL=kling-2.1-standard), or run the tool with --model.

To add a new fal.ai model: copy one of the entries, then change
  - "endpoint": the model id shown on the model's fal.ai page
  - "price_per_clip": what fal.ai charges for one 5-second clip (US dollars)
  - "extra_args": any extra settings that model accepts
  - "supports_end_image": True only if the model can take an end photo too
    (needed for --walkthrough). Check the model's fal.ai page for a field like
    "tail_image_url" or "end_image_url", and put that name in "end_image_field".

Prices change from time to time. Check the model's page on fal.ai and update
"price_per_clip" so the cost report stays accurate.
"""

VIDEO_MODELS = {
    # Default. Good quality, smooth motion.
    "kling-2.5-turbo-pro": {
        "endpoint": "fal-ai/kling-video/v2.5-turbo/pro/image-to-video",
        "price_per_clip": 0.35,
        "extra_args": {"duration": "5", "cfg_scale": 0.5},
        "supports_negative_prompt": True,
        "supports_end_image": True,
        "end_image_field": "tail_image_url",
    },
    # Older and cheaper. Useful for test runs.
    "kling-2.1-standard": {
        "endpoint": "fal-ai/kling-video/v2.1/standard/image-to-video",
        "price_per_clip": 0.25,
        "extra_args": {"duration": "5", "cfg_scale": 0.5},
        "supports_negative_prompt": True,
    },
}

DEFAULT_VIDEO_MODEL = "kling-2.5-turbo-pro"

# The instruction sent with every photo. Deliberately short and strict.
CLIP_PROMPT = (
    "Slow, smooth, steady camera push-in toward the center of the scene. "
    "Keep the room exactly as shown: same furniture, layout, colors and lighting. "
    "No people, no animals, no new objects, nothing moves except the camera."
)

# Used with --walkthrough: the camera travels from one photo to the next.
WALKTHROUGH_PROMPT = (
    "Smooth, steady walkthrough: the camera glides at walking pace from the first view "
    "to the final view, like a person walking through the home with a gimbal. "
    "Keep the rooms exactly as shown: same furniture, layout, colors and lighting. "
    "No people, no animals, no new objects, nothing moves except the camera."
)

NEGATIVE_PROMPT = (
    "people, person, animals, new objects, extra furniture, changing room, "
    "morphing, warping, distortion, shaky camera, fast motion, text, watermark, blur"
)
