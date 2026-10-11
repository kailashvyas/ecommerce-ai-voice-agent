import os
import sys
from pathlib import Path

# Include sys.path addition for voice-agent/ directory so tools import succeeds
VOICE_AGENT_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = VOICE_AGENT_DIR.parent

for path_str in [str(VOICE_AGENT_DIR), str(PROJECT_ROOT)]:
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

try:
    from dotenv import load_dotenv
    for env_file in [VOICE_AGENT_DIR / ".env", PROJECT_ROOT / ".env"]:
        if env_file.exists():
            load_dotenv(env_file)
except ImportError:
    pass

try:
    from tools import search_catalog, place_order
except ImportError:
    from voice_agent.tools import search_catalog, place_order

try:
    from google.adk import Agent
except ImportError:
    try:
        from google.adk.agents import Agent
    except ImportError:
        try:
            from google.genai.agent import Agent
        except ImportError:
            class Agent:
                """Fallback ADK Agent class if google-adk is not installed."""
                def __init__(
                    self,
                    name: str = "voice_catalog_concierge",
                    model: str = "gemini-live-2.5-flash-native-audio",
                    instruction: str = "",
                    instructions: str = "",
                    system_instruction: str = "",
                    tools: list = None,
                    **kwargs
                ):
                    self.name = name
                    self.model = model
                    self.instruction = instruction or instructions or system_instruction
                    self.system_instruction = self.instruction
                    self.tools = tools or []

SYSTEM_INSTRUCTION = (
    "You are an upbeat voice shopping assistant for our e-commerce store. "
    "Answer questions about catalog products concisely. "
    "When a customer wants to buy, use place_order to record the transaction "
    "and state the confirmation details clearly."
)

try:
    voice_catalog_concierge = Agent(
        name="voice_catalog_concierge",
        model="gemini-live-2.5-flash-native-audio",
        instruction=SYSTEM_INSTRUCTION,
        tools=[search_catalog, place_order]
    )
except TypeError:
    try:
        voice_catalog_concierge = Agent(
            name="voice_catalog_concierge",
            model="gemini-live-2.5-flash-native-audio",
            system_instruction=SYSTEM_INSTRUCTION,
            tools=[search_catalog, place_order]
        )
    except TypeError:
        voice_catalog_concierge = Agent(
            name="voice_catalog_concierge",
            model="gemini-live-2.5-flash-native-audio",
            instructions=SYSTEM_INSTRUCTION,
            tools=[search_catalog, place_order]
        )

if not hasattr(voice_catalog_concierge, "system_instruction"):
    try:
        object.__setattr__(voice_catalog_concierge, "system_instruction", SYSTEM_INSTRUCTION)
    except Exception:
        pass

agent = voice_catalog_concierge
root_agent = voice_catalog_concierge
