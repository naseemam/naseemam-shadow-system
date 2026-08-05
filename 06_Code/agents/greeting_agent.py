from .base import AgentContext, AgentOutput, BaseAgent
import re


class GreetingAgent(BaseAgent):
    name = "greeting_agent"
    capabilities = ["استئناف العمل", "بدء الحوار التنفيذي"]
    primary_sources = []

    _assistant_name_forms = {"أمير", "امير", "ameer"}

    def execute(self, context: AgentContext) -> AgentOutput:
        q_words_only = re.sub(r"[^\u0621-\u064Aa-zA-Z0-9]", "", (context.query or "").lower()).strip()
        is_name_call = q_words_only in self._assistant_name_forms
        reply = (
            "أنا هنا. من أين نبدأ؟"
            if is_name_call
            else "نبدأ من أعلى نقطة أثرًا — ما الذي يحتاج قرارًا أو تقدمًا الآن؟"
        )
        return AgentOutput(
            agent=self.name,
            confidence=0.97,
            reply_draft=reply,
            sources=self.primary_sources,
            actions=["open_conversation"],
            message="استئناف الحوار التنفيذي.",
            response_data={
                "intent": "greeting",
                "facts": {
                    "mode": "name_call" if is_name_call else "standard_greeting",
                },
            },
        )
