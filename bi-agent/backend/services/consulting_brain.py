"""
services/consulting_brain.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  DEPRECATED — merged into story_builder.py

This file is kept ONLY for backward compatibility.
All imports from here now route to story_builder.py.

Why:
  consulting_brain was a separate AI call doing 90% the same work as story_builder.
  Merged = 1 fewer AI call per deck = ~$0.08 saved per deck.

Migration:
  OLD: from services.consulting_brain import build_consulting_story
  NEW: from services.story_builder    import build_consulting_story  ← same API
"""

from services.story_builder import (
    build_consulting_story,
    build_story,
    StoryDeck,
    SlideStory,
    generate_executive_title,
)

__all__ = ["build_consulting_story", "build_story", "StoryDeck", "SlideStory"]