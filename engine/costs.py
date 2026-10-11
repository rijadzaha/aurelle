"""
Keeps a running total of what this run cost.

Claude is charged per "token" (roughly, per piece of text or image it reads and
writes). fal.ai is charged per finished clip. Prices are in US dollars.
"""

# Claude prices per 1 million tokens: (input, output).
CLAUDE_PRICES = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
    # Models Claude may hand over to in the rare case it declines a request.
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-4-8": (5.00, 25.00),
}


class CostTracker:
    def __init__(self):
        self.claude_cost = 0.0
        self.claude_input_tokens = 0
        self.claude_output_tokens = 0
        self.clips_made = 0
        self.clips_reused = 0
        self.clip_cost = 0.0
        self.warnings = []

    def add_claude(self, model, usage):
        if model not in CLAUDE_PRICES:
            self.warnings.append(
                f"No price on file for Claude model '{model}', so its cost is not counted. "
                "Add it to CLAUDE_PRICES in engine/costs.py."
            )
            return
        in_price, out_price = CLAUDE_PRICES[model]
        input_tokens = (
            usage.input_tokens
            + (getattr(usage, "cache_creation_input_tokens", 0) or 0)
            + (getattr(usage, "cache_read_input_tokens", 0) or 0)
        )
        self.claude_input_tokens += input_tokens
        self.claude_output_tokens += usage.output_tokens
        self.claude_cost += (input_tokens * in_price + usage.output_tokens * out_price) / 1_000_000

    def add_clip(self, price):
        self.clips_made += 1
        self.clip_cost += price

    @property
    def total(self):
        return self.claude_cost + self.clip_cost

    def report(self):
        lines = [
            "",
            "=" * 52,
            "  COST OF THIS RUN (US dollars)",
            "=" * 52,
            f"  Claude (photo labeling):  ${self.claude_cost:8.4f}"
            f"   ({self.claude_input_tokens:,} in / {self.claude_output_tokens:,} out tokens)",
            f"  fal.ai (video clips):     ${self.clip_cost:8.4f}   ({self.clips_made} new clips)",
        ]
        if self.clips_reused:
            lines.append(f"  Clips reused from an earlier run (free this time): {self.clips_reused}")
        lines += [
            "-" * 52,
            f"  TOTAL:                    ${self.total:8.4f}",
            "=" * 52,
            "  fal.ai cost is based on the price per clip in engine/video_models.py.",
        ]
        for w in self.warnings:
            lines.append(f"  NOTE: {w}")
        return "\n".join(lines)
