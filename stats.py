import time

PRICING = {
    "claude-opus-4-6": {"input": 15.0, "output": 75.0},
    "claude-opus-4-5": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.0},
}
DEFAULT_PRICING = {"input": 15.0, "output": 75.0}


class TokenStats:
    def __init__(self, model: str = "claude-opus-4-6"):
        self.model = model
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.api_calls = 0
        self.image_generations = 0
        self.image_cost = 0.0
        self.start_time = time.time()
        self.last_report_time = time.time()
        self._pricing = DEFAULT_PRICING
        for key, price in PRICING.items():
            if key in model:
                self._pricing = price
                break

    def add(self, input_tokens: int, output_tokens: int):
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.api_calls += 1

    def add_image(self, cost: float = 0.0):
        """Track an image generation call and its cost."""
        self.image_generations += 1
        self.image_cost += cost

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    @property
    def input_cost(self) -> float:
        return (self.total_input_tokens / 1_000_000) * self._pricing["input"]

    @property
    def output_cost(self) -> float:
        return (self.total_output_tokens / 1_000_000) * self._pricing["output"]

    @property
    def total_cost(self) -> float:
        return self.input_cost + self.output_cost + self.image_cost

    @property
    def elapsed_minutes(self) -> float:
        return (time.time() - self.start_time) / 60

    def should_report(self, interval_seconds: int = 300) -> bool:
        now = time.time()
        if now - self.last_report_time >= interval_seconds:
            self.last_report_time = now
            return True
        return False

    def format_summary(self) -> str:
        img_part = f" | Images: {self.image_generations} (${self.image_cost:.4f})" if self.image_generations > 0 else ""
        return (
            f"Tokens: {self.total_input_tokens:,} in + {self.total_output_tokens:,} out = {self.total_tokens:,} | "
            f"Cost: ${self.total_cost:.4f} | API calls: {self.api_calls}{img_part} | Time: {self.elapsed_minutes:.1f} min"
        )
