import asyncio
import os

from agents import function_tool
from agents.realtime import RealtimeAgent, RealtimeRunner


@function_tool
def get_weather(city: str) -> str:
    """Get current weather for a city."""
    return f"The weather in {city} is sunny and 72°F."


@function_tool
def get_time() -> str:
    """Get the current time."""
    from datetime import datetime

    return f"The current time is {datetime.now().strftime('%I:%M %p')}."


agent = RealtimeAgent(
    name="Assistant",
    instructions=(
        "You are a helpful voice assistant. "
        "Keep your responses brief and conversational. "
        "You can help users with weather information and telling the time."
    ),
    tools=[get_weather, get_time],
)


async def main():
    runner = RealtimeRunner(
        starting_agent=agent,
        config={
            "model_settings": {
                "model_name": "gpt-realtime",
                "voice": "ash",
                "modalities": ["audio", "text"],
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {"model": "gpt-4o-mini-transcribe"},
                "turn_detection": {"type": "semantic_vad", "interrupt_response": True},
            }
        },
    )

    print("Starting realtime session...")
    print("Press Ctrl+C to exit.\n")

    session = await runner.run()
    async with session:
        print("Session started! Listening for events...\n")

        async for event in session:
            if event.type == "agent_start":
                print(f"[Agent] Started: {event.agent.name}")
            elif event.type == "agent_end":
                print(f"[Agent] Ended: {event.agent.name}")
            elif event.type == "tool_start":
                print(f"[Tool] Calling: {event.tool.name}")
            elif event.type == "tool_end":
                print(f"[Tool] Result: {event.output}")
            elif event.type == "audio":
                print(".", end="", flush=True)
            elif event.type == "audio_end":
                print("\n[Audio] Finished speaking")
            elif event.type == "audio_interrupted":
                print("\n[Audio] Interrupted by user")
            elif event.type == "error":
                print(f"[Error] {event.error}")
            elif event.type == "transcript":
                if hasattr(event, "text"):
                    print(f"[Transcript] {event.text}")


if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable is not set")
        exit(1)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSession ended.")
