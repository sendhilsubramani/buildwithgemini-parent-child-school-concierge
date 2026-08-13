# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types


MODEL = "gemini-3.6-flash"


async def generate_memories_callback(callback_context: CallbackContext):
    await callback_context.add_session_to_memory()
    return None


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        city: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from app.a2ui_utils import a2ui_callback
from app.firestore_tools import (
    add_evening_activity,
    add_medical_record,
    check_medical_followup_alerts,
    generate_student_avatar_picture,
    get_evening_activities,
    get_medical_records,
    get_school_announcements,
    mark_activity_completed,
    send_parent_guidance_and_advice,
)
from app.school_email_tools import fetch_cordos_elementary_emails


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are a Parent & Child Daily School & Health Concierge assistant. "
        "You help parents track daily school progress, evening activity checklists, "
        "medical/health records, Cordos Elementary School emails, upcoming follow-ups, "
        "student picture generation/reward avatars with emojis, and parent-child coaching advice."
    ),
    workflow_description=(
        "Use `fetch_cordos_elementary_emails` to read Cordos Elementary School emails, announcements, and teacher updates. "
        "Use `check_medical_followup_alerts` to check upcoming or overdue annual checkups, flu shots, and prescription refills. "
        "Use `generate_student_avatar_picture` to create a student picture, reward avatar, or accomplishment badge using Imagen. "
        "Use `send_parent_guidance_and_advice` when parents want to advise or encourage their child to focus on homework, activities, or chores. "
        "Use your Firestore tools to read and write evening activities, medical records, and school announcements as needed."
    ),
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image. Set the Image url to that exact https link. Never point an "
        "Image at a bare filename or non-http(s) path. If you do not have a public URL, add a short Text line instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[
        get_weather,
        get_current_time,
        fetch_cordos_elementary_emails,
        check_medical_followup_alerts,
        generate_student_avatar_picture,
        send_parent_guidance_and_advice,
        get_evening_activities,
        add_evening_activity,
        mark_activity_completed,
        get_medical_records,
        add_medical_record,
        get_school_announcements,
        PreloadMemoryTool(),
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)

