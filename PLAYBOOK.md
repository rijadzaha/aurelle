# Aurelle video playbook

How every Aurelle walkthrough video is made. Read this first in any new session.

## Working with Rijad

- Very short, simple sentences. One step at a time.
- No guessing. Say what is checked and what is not.
- Ask before spending any credits. Say the cost first.
- Never print or ask for the API keys (`AURELLE_ANTHROPIC_KEY`, `FAL_KEY`).
- Private business info (agencies, leads, prices, contacts) lives in the private
  "Aurelle Books" artifact, not in this public repo.

## Tools and settings

- Video model: Higgsfield **Kling 4.0** (`kling4_0`), image-to-video, 1080p,
  3.25 credits per second (a 10 s clip = 32.5 credits). Output is 1760x1176 even
  when 9:16 is asked; the vertical version is a centre crop in the edit.
- Start photo + end photo only when the path between them is real.
- Photo fixes (people, reflections): crop the area, AI-edit only that patch
  (gpt_image), paste back with a soft mask.
- Edit: trim near-still frames at clip ends, even out speed, motion-interpolate,
  output **30 frames per second**, blend clips while both are moving.
- Exports: vertical 9:16 (1080x1920) and horizontal 16:9 (1920x1080).

## Rules for walking through a home

- **No home is the same.** Plan the route, highlights and mood for this home only.
- Walk through it **naturally**: eye height, calm steady pace, the real path a
  visitor would take, a short slow-down at highlights.
- Connecting rooms, in this order:
  1. a real walk between two photos that truly connect;
  2. walk as far as the photos go, then blend while still moving;
  3. a soft fade, only as a last resort.
- **Never invent a path, a door or a window just to avoid a fade.** A fake room
  costs the agent's trust.
- Upper-floor apartments: never walk from the street door straight into the flat.
- No drone shot unless there is a real aerial photo.
- Keep similar rooms (two bathrooms) far apart in the video.

## Checklist

### 0. Understand this home
- [ ] Read the listing text and the floor plan.
- [ ] Find what makes this home special; ask the agent if unclear.
- [ ] Note floor level, number of bathrooms, balconies, garden, garage.

### 1. Before spending credits
- [ ] Get all photos, the floor plan, the address, the agent's name and end screen.
- [ ] Number the photos and look at every one.
- [ ] Check for people, including reflections in mirrors, windows and glass,
      and things that turn into people (shoes, coats). Patch them out first.

### 2. Plan the route
- [ ] Outside (real photos only) → entrance → open spaces as one walk →
      private rooms → end screen.
- [ ] Give each clip a different motion (push in, turn, slide, rise).
- [ ] Use short, gentle moves where a big move would make the AI invent things.
- [ ] Tell Rijad the plan and the cost; wait for "go".

### 3. Make the clips
- [ ] Prompt: slow smooth gimbal shot, no bobbing, no people or reflections,
      keep everything exactly as in the photos, add nothing, only the camera moves.
- [ ] Doors open in the photo stay open.

### 4. Check each clip
- [ ] A frame every second; zoom on mirrors, glass and windows.
- [ ] Compare with the real photos: invented windows, curtains, doors, double
      door handles, new buildings outside, furniture changing shape, scrambled text.
- [ ] Cut bad parts and blend over them (free) before paying for a redo.

### 5. Edit
- [ ] The camera never stops; trim still frames at every join.
- [ ] Short views (balcony) get at least 3 seconds.
- [ ] Bedrooms and bathrooms: blend in while moving.

### 6. Text and ending
- [ ] Address in the centre, no band behind it, then it glides to a corner and stays.
- [ ] Room names as each room appears, definite form (Stofan, Eldhúsið,
      Litla baðherbergið). Long names shrink to fit the phone.
- [ ] The agent's own end screen last, unchanged.

### 7. Final check
- [ ] Watch the whole video, vertical and horizontal.
- [ ] No people, no invented windows or doors, no stops, names and address right.
- [ ] Share links: "Anyone with the link", tested in a private window.

## Asking agents for better photos

To make one continuous walk, ask for 5–10 extra "walking photos": one at each
doorway looking in, one in the hallway toward each door, one leaving each room.
