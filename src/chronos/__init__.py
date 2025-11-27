"""
Chronos - Autonomous Scheduling Agent
======================================

A production-grade autonomous agent for intelligent scheduling and calendar management,
powered by LangGraph, Llama 3, and DPO (Direct Preference Optimization).

Features:
---------
- Multi-agent orchestration with LangGraph
- Advanced reasoning with Llama 3
- Gmail/Google Calendar integration
- DPO-optimized for user preferences
- Real-time scheduling optimization
- Conflict resolution and smart rescheduling
- Natural language understanding for calendar requests

Author: Sneha Maurya
License: MIT
"""

__version__ = "1.0.0"
__author__ = "Sneha Maurya"

from src.chronos.config import Config
from src.chronos.models.llama import LlamaModel
from src.chronos.graph.workflow import ChronosWorkflow

__all__ = [
    "Config",
    "LlamaModel",
    "ChronosWorkflow",
]

