"""Multi-Agent Collaborative Discussion orchestrator.

This module reuses the SAME agent_framework primitives as the original
a2a/ solution but implements a NEW orchestration pattern: each sub-agent
(Product, Marketing, Ranker) takes individual turns sharing the full
conversation transcript so they can build on each other's contributions.

The Manager agent decides between rounds whether the discussion has reached
consensus (terminate) or should continue (pick the next speaker), with a
hard safety cap of MAX_ROUNDS turns.

This file is intentionally self-contained and does NOT import from src/a2a/.
"""
import json
import logging
import os
from collections.abc import AsyncIterable
from typing import Annotated, Any, Literal

import httpx
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
from pydantic import BaseModel, Field, ValidationError

from agent_framework import Agent, AgentSession, tool
from agent_framework.openai import OpenAIChatClient, OpenAIChatOptions

logger = logging.getLogger(__name__)
load_dotenv()


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MAX_ROUNDS = 8  # Hard safety cap on agent-to-agent turns
MIN_ROUNDS = 4  # Manager cannot conclude before this many turns


# ---------------------------------------------------------------------------
# Chat client (Azure OpenAI with Managed Identity)
# ---------------------------------------------------------------------------

def get_chat_client() -> OpenAIChatClient:
    """Return Azure OpenAI chat client using managed identity."""
    endpoint = os.getenv("gpt_endpoint")
    deployment_name = os.getenv("gpt_deployment")

    if not endpoint:
        raise ValueError("gpt_endpoint env var is required")
    if not deployment_name:
        raise ValueError("gpt_deployment env var is required")

    credential = DefaultAzureCredential()

    async_client = AsyncAzureOpenAI(
        azure_endpoint=endpoint,
        azure_deployment=deployment_name,
        azure_ad_token_provider=lambda: credential.get_token(
            "https://cognitiveservices.azure.com/.default"
        ).token,
        api_version="2025-03-01-preview",
        timeout=httpx.Timeout(120.0, connect=30.0),
        max_retries=2,
    )

    return OpenAIChatClient(model=deployment_name, async_client=async_client)


# ---------------------------------------------------------------------------
# Product catalog tool (used by ProductAgent)
# ---------------------------------------------------------------------------

@tool(
    name="get_products",
    description="Retrieves Zava products based on a natural language query.",
)
def get_products(
    question: Annotated[str, "Natural language query about products"],
) -> list[dict[str, Any]]:
    """Hardcoded sample catalog (same data as the original a2a solution)."""
    return [
        {
            "id": "1",
            "name": "Eco-Friendly Paint Roller",
            "type": "Paint Roller",
            "description": "A high-quality, eco-friendly paint roller for smooth finishes.",
            "punchLine": "Roll with the best, paint with the rest!",
            "price": 15.99,
        },
        {
            "id": "2",
            "name": "Standard Paint Roller",
            "type": "Paint Roller",
            "description": "A reliable everyday paint roller for general home painting projects.",
            "punchLine": "Smooth, simple, dependable.",
            "price": 8.49,
        },
        {
            "id": "3",
            "name": "Premium Paint Brush Set",
            "type": "Paint Brush",
            "description": "A set of premium paint brushes for detailed work and fine finishes.",
            "punchLine": "Brush up your skills with our premium set!",
            "price": 25.49,
        },
        {
            "id": "4",
            "name": "All-Purpose Paint Tray",
            "type": "Paint Tray",
            "description": "A durable paint tray suitable for all types of rollers and brushes.",
            "punchLine": "Tray it, paint it, love it!",
            "price": 9.99,
        },
        {
            "id": "5",
            "name": "Pale Meadow Eco Paint",
            "type": "Eco Paint",
            "description": "Low-VOC, plant-based paint in a soft, earthy green.",
            "punchLine": "Nature's touch inside your home.",
            "price": 29.99,
        },
    ]


# ---------------------------------------------------------------------------
# Structured response models
# ---------------------------------------------------------------------------

class ManagerDecision(BaseModel):
    """Manager decides between rounds whether to continue or conclude."""
    decision: Literal["continue", "conclude"] = Field(
        ..., description="Whether to continue the discussion or conclude with consensus."
    )
    next_agent: str | None = Field(
        None, description="Which agent should speak next: product, marketing, or ranker (only if decision=continue)."
    )
    reason: str = Field(..., description="Brief reason for the decision.")
    summary: str | None = Field(
        None, description="Final consensus summary (only if decision=conclude)."
    )


# ---------------------------------------------------------------------------
# Discussion orchestrator
# ---------------------------------------------------------------------------

class CollaborativeDiscussionAgent:
    """Orchestrates multi-round agent-to-agent collaborative discussions."""

    def __init__(self) -> None:
        client = get_chat_client()

        self.product_agent = Agent(
            client=client,
            name="ProductAgent",
            instructions=(
                "You are the ProductAgent in a team discussion. "
                "Your expertise is product catalog data, specifications, prices, and descriptions. "
                "You MUST use the get_products tool to fetch real product data — never invent products. "
                "You are the voice of ACCURACY and HONESTY. You believe products should be marketed "
                "based on their REAL specs — not hype. If MarketingAgent exaggerates or oversells, "
                "you MUST push back with specific data points. If RankerAgent ignores price-to-value ratio, "
                "correct them. Say things like 'I disagree because the data shows...' or 'That's misleading — "
                "the actual specs are...' Be concise (2-4 sentences). Always cite real catalog data."
            ),
            tools=get_products,
        )

        self.marketing_agent = Agent(
            client=client,
            name="MarketingAgent",
            instructions=(
                "You are the MarketingAgent in a team discussion. "
                "Your expertise is product positioning, branding, sales copy, and revenue growth. "
                "You are the voice of BOLDNESS and SALES. You believe perception matters more than specs. "
                "You advocate for premium positioning, higher prices, and emotional marketing. "
                "If ProductAgent is too conservative or literal, challenge them — say things like "
                "'I respectfully disagree — customers buy stories, not spec sheets' or 'Playing it safe "
                "won't grow revenue.' If RankerAgent picks the cheap option, argue for the premium one. "
                "Be concise (2-4 sentences). Propose bold marketing angles even if teammates resist."
            ),
        )

        self.ranker_agent = Agent(
            client=client,
            name="RankerAgent",
            instructions=(
                "You are the RankerAgent in a team discussion. "
                "Your expertise is comparing options, ranking by customer value, and spotting bad deals. "
                "You are the voice of the CUSTOMER. You prioritize value-for-money and honest recommendations. "
                "If MarketingAgent pushes premium pricing on a basic product, call it out — say 'Customers "
                "will see through that' or 'This would damage trust.' If ProductAgent is too data-heavy "
                "and ignores customer perception, point that out too. "
                "Be concise (2-4 sentences). Back up your rankings with specific comparisons."
            ),
        )

        self.manager_agent = Agent(
            client=client,
            name="ManagerAgent",
            instructions=(
                "You are the Manager facilitating a discussion among three agents: "
                "ProductAgent, MarketingAgent, and RankerAgent.\n\n"
                "RULES:\n"
                "- You MUST respond with valid JSON matching the ManagerDecision schema.\n"
                "- If fewer than 3 agents have spoken, you MUST set decision='continue'.\n"
                "- If agents DISAGREE with each other, you MUST set decision='continue' to let them "
                "  debate further. Do NOT force premature consensus.\n"
                "- Only set decision='conclude' when agents have found a compromise or when the "
                "  disagreement has been fully explored (both sides stated clearly).\n"
                "- When continuing, pick the agent who was most directly challenged or disagreed with, "
                "  so they can respond.\n"
                "- When you conclude, write a summary that acknowledges any remaining disagreements "
                "  and states the compromise or majority position.\n"
            ),
        )

        self._agents_by_id = {
            "product": self.product_agent,
            "marketing": self.marketing_agent,
            "ranker": self.ranker_agent,
        }

        self._agent_names = {
            "product": "ProductAgent",
            "marketing": "MarketingAgent",
            "ranker": "RankerAgent",
        }

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------

    @staticmethod
    def _format_transcript(transcript: list[dict[str, str]]) -> str:
        """Format the running transcript so agents see what others said."""
        if not transcript:
            return "(no prior discussion — you are speaking first)"
        lines = []
        for i, turn in enumerate(transcript, 1):
            lines.append(f"Turn {i} [{turn['agent_name']}]: {turn['message']}")
        return "\n\n".join(lines)

    async def _run_sub_agent(
        self, agent_id: str, scenario_prompt: str, transcript: list[dict[str, str]],
        session: AgentSession,
    ) -> str:
        """Run a sub-agent for one turn with the full transcript as context."""
        agent = self._agents_by_id[agent_id]
        transcript_text = self._format_transcript(transcript)
        user_message = (
            f"=== SCENARIO ===\n{scenario_prompt}\n\n"
            f"=== DISCUSSION SO FAR ===\n{transcript_text}\n\n"
            f"=== YOUR TURN ===\n"
            f"You are {agent.name}. Reply in 1-2 SHORT sentences. "
            f"If you disagree with someone, say so directly and why. "
            f"Do NOT repeat what was already said."
        )
        logger.info("Running sub-agent %s …", agent_id)
        response = await agent.run(messages=user_message, session=session)
        text = response.text or ""
        # Strip leading "[AgentName]:" if the model echoed it
        for prefix in (f"[{agent.name}]:", f"{agent.name}:"):
            if text.lstrip().startswith(prefix):
                text = text.lstrip()[len(prefix):].strip()
                break
        logger.info("Sub-agent %s responded: %s", agent_id, text[:120])
        return text.strip()

    async def _ask_manager(
        self,
        scenario_prompt: str,
        transcript: list[dict[str, str]],
        round_num: int,
        last_speaker: str | None,
        session: AgentSession,
    ) -> ManagerDecision:
        """Ask the manager whether to continue and who speaks next."""
        transcript_text = self._format_transcript(transcript)
        agents_spoken = set(t["agent_id"] for t in transcript)
        agents_not_spoken = [a for a in ("product", "marketing", "ranker") if a not in agents_spoken]

        user_message = (
            f"=== SCENARIO ===\n{scenario_prompt}\n\n"
            f"=== DISCUSSION TRANSCRIPT ({len(transcript)} turns so far, max {MAX_ROUNDS}) ===\n"
            f"{transcript_text}\n\n"
            f"=== STATUS ===\n"
            f"Total turns so far: {len(transcript)}. Minimum required: {MIN_ROUNDS}.\n"
            f"Last speaker: {last_speaker or 'none'}.\n"
            f"Agents that have spoken: {', '.join(agents_spoken) or 'none'}.\n"
            f"Agents that have NOT spoken yet: {', '.join(agents_not_spoken) or 'all have spoken'}.\n\n"
            f"=== YOUR DECISION ===\n"
            f"REMEMBER: You CANNOT conclude if fewer than {MIN_ROUNDS} turns have happened. "
            f"Currently {len(transcript)} turns. "
            f"If any agent disagreed with another and hasn't replied yet, you MUST continue. "
            f"Respond as JSON."
        )
        logger.info("Asking Manager for decision (round %d) …", round_num)
        try:
            response = await self.manager_agent.run(
                messages=user_message,
                session=session,
                options=OpenAIChatOptions(response_format=ManagerDecision),
            )
            raw = response.text or ""
            logger.info("Manager raw response: %s", raw[:300])
            decision = ManagerDecision.model_validate_json(raw)
            # Validate next_agent value
            if decision.decision == "continue" and decision.next_agent not in self._agents_by_id:
                # Pick someone who hasn't spoken, or anyone except last speaker
                fallback = agents_not_spoken[0] if agents_not_spoken else \
                    [a for a in ("product", "marketing", "ranker") if a != last_speaker][0]
                decision.next_agent = fallback
            return decision
        except (ValidationError, Exception) as e:
            logger.warning("Manager decision parse failed: %s", e, exc_info=True)
            # Instead of concluding, force continue if not all agents spoke
            if agents_not_spoken:
                return ManagerDecision(
                    decision="continue",
                    next_agent=agents_not_spoken[0],
                    reason=f"Parse error fallback — letting {agents_not_spoken[0]} speak next.",
                    summary=None,
                )
            return ManagerDecision(
                decision="conclude",
                next_agent=None,
                reason="All agents spoke and Manager could not parse decision.",
                summary="The team has discussed the topic from product, marketing, and ranking perspectives.",
            )

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------

    async def discuss(self, scenario_prompt: str) -> AsyncIterable[dict[str, Any]]:
        """Run a multi-round collaborative discussion.

        Round 1 is always ProductAgent (to fetch catalog data).
        From round 2 onward, Manager picks who speaks next and decides
        when to conclude. Manager cannot conclude before MIN_ROUNDS turns.
        """
        transcript: list[dict[str, str]] = []
        session = AgentSession()

        # ── Round 1: ProductAgent always goes first (gets real data) ──
        yield {"type": "round_start", "round": 1}
        try:
            message = await self._run_sub_agent("product", scenario_prompt, transcript, session)
        except Exception as e:
            logger.exception("ProductAgent failed")
            yield {"type": "error", "message": f"ProductAgent failed: {e}"}
            return

        transcript.append({"agent_id": "product", "agent_name": "ProductAgent", "message": message})
        yield {"type": "agent_turn", "agent": "product", "agent_name": "ProductAgent", "message": message, "round": 1}

        last_speaker = "product"

        # ── Rounds 2+: Manager-driven ──
        for round_num in range(2, MAX_ROUNDS + 1):
            # Force continue if below MIN_ROUNDS
            if len(transcript) < MIN_ROUNDS:
                agents_spoken = set(t["agent_id"] for t in transcript)
                not_spoken = [a for a in ("marketing", "ranker", "product") if a not in agents_spoken]
                # Pick someone who hasn't spoken, else pick someone other than last speaker
                if not_spoken:
                    next_agent_id = not_spoken[0]
                    reason = f"{self._agent_names[next_agent_id]} hasn't spoken yet."
                else:
                    candidates = [a for a in ("product", "marketing", "ranker") if a != last_speaker]
                    next_agent_id = candidates[0]
                    reason = f"Need more discussion (turn {len(transcript)+1} of min {MIN_ROUNDS})."

                yield {
                    "type": "manager_decision", "decision": "continue",
                    "next_agent": next_agent_id, "reason": reason, "round": round_num - 1,
                }
            else:
                # Let Manager decide
                decision = await self._ask_manager(
                    scenario_prompt, transcript, round_num, last_speaker, session
                )

                # Safety: override conclude if below MIN_ROUNDS
                if decision.decision == "conclude" and len(transcript) < MIN_ROUNDS:
                    decision.decision = "continue"
                    decision.next_agent = [a for a in ("product", "marketing", "ranker") if a != last_speaker][0]
                    decision.reason = "Not enough discussion yet — continuing."

                yield {
                    "type": "manager_decision", "decision": decision.decision,
                    "next_agent": decision.next_agent, "reason": decision.reason,
                    "round": round_num - 1,
                }

                if decision.decision == "conclude":
                    summary = decision.summary or "The team has reached a resolution."
                    yield {"type": "consensus", "summary": summary, "rounds": len(transcript)}
                    return

                next_agent_id = decision.next_agent
                if not next_agent_id or next_agent_id not in self._agents_by_id:
                    yield {"type": "consensus", "summary": "Discussion complete.", "rounds": len(transcript)}
                    return

            # Run the selected agent
            yield {"type": "round_start", "round": round_num}
            agent_name = self._agent_names[next_agent_id]
            try:
                message = await self._run_sub_agent(next_agent_id, scenario_prompt, transcript, session)
            except Exception as e:
                logger.exception("Sub-agent %s failed", next_agent_id)
                yield {"type": "error", "message": f"{agent_name} failed: {e}"}
                return

            transcript.append({"agent_id": next_agent_id, "agent_name": agent_name, "message": message})
            last_speaker = next_agent_id
            yield {
                "type": "agent_turn", "agent": next_agent_id,
                "agent_name": agent_name, "message": message, "round": round_num,
            }

        # Hit MAX_ROUNDS — force conclusion
        final = await self._ask_manager(scenario_prompt, transcript, MAX_ROUNDS + 1, last_speaker, session)
        summary = final.summary or "Maximum rounds reached. Here is the team's position."
        yield {"type": "manager_decision", "decision": "conclude", "next_agent": None,
               "reason": f"Reached max {MAX_ROUNDS} rounds.", "round": MAX_ROUNDS}
        yield {"type": "consensus", "summary": summary, "rounds": len(transcript)}


# Singleton — created on first import
discussion_agent = CollaborativeDiscussionAgent()
