"""Token usage logger for real-time debugging.

Captures and displays exact token usage from LLM responses.
"""
from typing import Any, Dict, Optional
from datetime import datetime


class TokenLogger:
    """Logs token usage with detailed breakdown."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cached_tokens = 0
        self.call_count = 0

    def log_usage(self, response: Any, context: str = "LLM Call") -> None:
        """Log token usage from LLM response.

        Args:
            response: LLM response object (AIMessage or similar)
            context: Description of the call (e.g., "Agent Node", "Tool Call")
        """
        if not self.enabled:
            return

        self.call_count += 1

        # Extract usage metadata
        usage = self._extract_usage(response)

        if not usage:
            print(f"\n⚠️  [{context}] No usage metadata available")
            return

        # Update totals
        input_tokens = usage.get('input_tokens', 0)
        output_tokens = usage.get('output_tokens', 0)
        total_tokens = usage.get('total_tokens', 0)

        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

        # Print detailed breakdown
        print("\n" + "="*70)
        print(f"🔍 TOKEN USAGE DEBUG - Call #{self.call_count}")
        print(f"📍 Context: {context}")
        print(f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}")
        print("-"*70)

        # Basic tokens
        print(f"📥 Input tokens:  {input_tokens:,}")
        print(f"📤 Output tokens: {output_tokens:,}")
        print(f"📊 Total tokens:  {total_tokens:,}")

        # Cached tokens (OpenAI/Anthropic specific)
        cached_input = usage.get('input_token_details', {}).get('cached_tokens', 0)
        if cached_input > 0:
            self.total_cached_tokens += cached_input
            print(f"⚡ Cache hits:    {cached_input:,} tokens (SAVED!)")
            actual_cost = input_tokens - cached_input
            print(f"💰 Actual cost:   {actual_cost:,} tokens (after cache)")

        # Anthropic-specific cache tokens
        cache_creation = usage.get('cache_creation_input_tokens', 0)
        cache_read = usage.get('cache_read_input_tokens', 0)
        if cache_creation > 0 or cache_read > 0:
            print(f"🔧 Cache created: {cache_creation:,} tokens")
            print(f"⚡ Cache read:    {cache_read:,} tokens")
            self.total_cached_tokens += cache_read

        # Reasoning tokens (o1 models)
        reasoning = usage.get('output_token_details', {}).get('reasoning_tokens', 0)
        if reasoning > 0:
            print(f"🧠 Reasoning:     {reasoning:,} tokens")

        # Session totals
        print("-"*70)
        print(f"📈 SESSION TOTALS (all {self.call_count} calls):")
        print(f"   Input:  {self.total_input_tokens:,} tokens")
        print(f"   Output: {self.total_output_tokens:,} tokens")
        if self.total_cached_tokens > 0:
            print(f"   Cached: {self.total_cached_tokens:,} tokens (saved)")
        print(f"   TOTAL:  {self.total_input_tokens + self.total_output_tokens:,} tokens")

        # Cost estimate (gpt-4o-mini pricing)
        self._print_cost_estimate()

        print("="*70 + "\n")

    def _extract_usage(self, response: Any) -> Optional[Dict[str, Any]]:
        """Extract usage metadata from various response formats."""
        # Try usage_metadata attribute (LangChain format)
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            return response.usage_metadata

        # Try response_metadata.token_usage (alternative format)
        if hasattr(response, 'response_metadata'):
            metadata = response.response_metadata
            if isinstance(metadata, dict) and 'token_usage' in metadata:
                return metadata['token_usage']

        # Try direct usage attribute (OpenAI format)
        if hasattr(response, 'usage'):
            usage = response.usage
            # Convert to dict if it's an object
            if hasattr(usage, 'model_dump'):
                return usage.model_dump()
            elif hasattr(usage, '__dict__'):
                return usage.__dict__

        return None

    def _print_cost_estimate(self) -> None:
        """Print cost estimate for gpt-4o-mini."""
        # gpt-4o-mini pricing (as of 2025)
        # $0.150 per 1M input tokens
        # $0.600 per 1M output tokens
        # Cached: $0.075 per 1M tokens (50% discount)

        input_cost = (self.total_input_tokens / 1_000_000) * 0.150
        output_cost = (self.total_output_tokens / 1_000_000) * 0.600

        # Calculate savings from cache
        cache_savings = 0
        if self.total_cached_tokens > 0:
            cache_savings = (self.total_cached_tokens / 1_000_000) * 0.075

        total_cost = input_cost + output_cost - cache_savings

        print(f"💵 COST ESTIMATE (gpt-4o-mini):")
        print(f"   Input:  ${input_cost:.6f}")
        print(f"   Output: ${output_cost:.6f}")
        if cache_savings > 0:
            print(f"   Savings: -${cache_savings:.6f} (cache)")
        print(f"   TOTAL:  ${total_cost:.6f}")

    def reset(self) -> None:
        """Reset session counters."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cached_tokens = 0
        self.call_count = 0
        print("🔄 Token logger reset\n")


# Global instance
_token_logger = TokenLogger(enabled=True)


def log_tokens(response: Any, context: str = "LLM Call") -> None:
    """Convenience function to log tokens using global logger."""
    _token_logger.log_usage(response, context)


def get_logger() -> TokenLogger:
    """Get the global token logger instance."""
    return _token_logger


def enable_token_logging(enabled: bool = True) -> None:
    """Enable or disable token logging."""
    _token_logger.enabled = enabled
    status = "enabled" if enabled else "disabled"
    print(f"🔍 Token logging {status}\n")


def reset_token_tracking() -> None:
    """Reset token tracking counters."""
    _token_logger.reset()
