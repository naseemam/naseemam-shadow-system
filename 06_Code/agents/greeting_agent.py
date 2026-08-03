from .base import AgentContext, AgentOutput, BaseAgent
import re


class GreetingAgent(BaseAgent):
    name = "greeting_agent"
    capabilities = ["التحية", "بدء الحوار", "تأكيد الجاهزية"]
    primary_sources = []

    _assistant_name_forms = {"أمير", "امير", "ameer"}

    def execute(self, context: AgentContext) -> AgentOutput:
        q_words_only = re.sub(r"[^\u0621-\u064Aa-zA-Z0-9]", "", (context.query or "").lower()).strip()
        is_name_call = q_words_only in self._assistant_name_forms
        reply = (
            "نعم، أنا معك. كيف أساعدك؟"
            if is_name_call
            else "مرحبا نسيم، أنا حاضر. كيف تحبين نبدأ الآن؟"
        )
        return AgentOutput(
            agent=self.name,
            confidence=0.97,
            reply_draft=reply,
            sources=self.primary_sources,
            actions=["open_conversation"],
            message="تم تجهيز رد ترحيبي مبدئي.",
        )
