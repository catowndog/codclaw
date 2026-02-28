import time


class TokenStats:
    def __init__(self, model: str = ""):
        self.model = model
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.api_calls = 0
        self.image_generations = 0
        self.start_time = time.time()
        self.last_report_time = time.time()

    def add(self, input_tokens: int, output_tokens: int):
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.api_calls += 1

    def add_image(self):
        """Track an image generation call."""
        self.image_generations += 1

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

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
        img_part = f" | Images: {self.image_generations}" if self.image_generations > 0 else ""
        return (
            f"Tokens: {self.total_input_tokens:,} in + {self.total_output_tokens:,} out = {self.total_tokens:,} | "
            f"API calls: {self.api_calls}{img_part} | Time: {self.elapsed_minutes:.1f} min"
        )
