"""
Step 1 and 2: Claude looks at all the photos at once, labels each one with a
room type, and suggests the order a buyer would walk through the property.
"""

import base64
import json

import anthropic

ROOM_TYPES = ["exterior", "entrance", "living room", "kitchen", "bedroom", "bathroom", "outdoor", "other"]

# Used if Claude's suggested order is unusable for some reason.
ROOM_RANK = {room: i for i, room in enumerate(ROOM_TYPES)}

INSTRUCTIONS = f"""You are planning a property walkthrough video from listing photos.

1. Label every photo with exactly one room type from this list: {", ".join(ROOM_TYPES)}.
   "exterior" = the front of the building seen from outside.
   "outdoor" = garden, yard, patio, balcony, pool or view.
   "other" = anything that fits none of the above (dining room, office, hallway, etc.).
2. Choose a natural tour order, like a buyer walking through: start outside at the
   exterior, go in through the entrance, then living spaces, kitchen, bedrooms,
   bathrooms, and finish outdoors. Keep photos of the same room next to each other.
   If there are several exterior shots, start with the most attractive one.
3. Give each photo a short description (under 15 words).

Every photo number must appear exactly once in tour_order."""

SCHEMA = {
    "type": "object",
    "properties": {
        "photos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "number": {"type": "integer"},
                    "room": {"type": "string", "enum": ROOM_TYPES},
                    "description": {"type": "string"},
                },
                "required": ["number", "room", "description"],
                "additionalProperties": False,
            },
        },
        "tour_order": {"type": "array", "items": {"type": "integer"}},
    },
    "required": ["photos", "tour_order"],
    "additionalProperties": False,
}


class LabelingError(Exception):
    pass


def _image_block(path):
    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}}


def label_and_order(photos, previews, model, costs, api_key):
    """
    photos:   the original photo files
    previews: the shrunk copies to send (same order as photos)
    Returns a list of {"file", "room", "description"} in tour order.
    """
    content = []
    for number, preview in enumerate(previews, start=1):
        content.append({"type": "text", "text": f"Photo {number}:"})
        content.append(_image_block(preview))
    content.append({"type": "text", "text": INSTRUCTIONS})

    # Talk to Anthropic directly, even if ANTHROPIC_BASE_URL points somewhere else.
    client = anthropic.Anthropic(api_key=api_key, base_url="https://api.anthropic.com")
    try:
        response = client.beta.messages.create(
            model=model,
            max_tokens=16000,
            # Labeling photos is a simple job, so low effort keeps it cheap and fast.
            output_config={
                "effort": "low",
                "format": {"type": "json_schema", "schema": SCHEMA},
            },
            # If Claude ever declines, the API retries on another Claude model automatically.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": content}],
        )
    except anthropic.AuthenticationError:
        raise LabelingError("Claude rejected the API key. Check ANTHROPIC_API_KEY in your .env file.")
    except anthropic.PermissionDeniedError:
        raise LabelingError("Your Anthropic key is not allowed to use this model. Check your Anthropic account.")
    except anthropic.NotFoundError:
        raise LabelingError(f"Claude model '{model}' was not found. Check CLAUDE_MODEL in your .env file.")
    except anthropic.BadRequestError as e:
        raise LabelingError(f"Claude could not process the request: {e.message}")
    except anthropic.RateLimitError:
        raise LabelingError("Claude is rate-limiting this key right now. Wait a minute and try again.")
    except anthropic.APIStatusError as e:
        raise LabelingError(f"Claude had a problem (error {e.status_code}). Try again in a few minutes.")
    except anthropic.APIConnectionError:
        raise LabelingError("Could not reach Claude. Check your internet connection.")

    costs.add_claude(response.model, response.usage)

    if response.stop_reason == "refusal":
        raise LabelingError("Claude declined to label these photos.")
    if response.stop_reason == "max_tokens":
        raise LabelingError("Claude's answer was cut off. Try again.")

    text = next((b.text for b in response.content if b.type == "text"), None)
    if text is None:
        raise LabelingError("Claude returned no answer. Try again.")
    data = json.loads(text)

    labels = {}
    for item in data["photos"]:
        if 1 <= item["number"] <= len(photos):
            labels[item["number"]] = item
    missing = [n for n in range(1, len(photos) + 1) if n not in labels]
    if missing:
        raise LabelingError(f"Claude did not label photo(s) {missing}. Try again.")

    order = data["tour_order"]
    if sorted(order) != list(range(1, len(photos) + 1)):
        # Claude's order skipped or repeated a photo; fall back to a simple rule-based order.
        order = sorted(labels, key=lambda n: (ROOM_RANK[labels[n]["room"]], n))

    return [
        {"file": photos[n - 1].name, "room": labels[n]["room"], "description": labels[n]["description"]}
        for n in order
    ]
