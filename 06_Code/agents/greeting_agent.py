from .base import AgentContext, AgentOutput, BaseAgent


class GreetingAgent(BaseAgent):
    name = "greeting_agent"
    capabilities = ["التحية", "بدء الحوار", "تأكيد الجاهزية"]
    primary_sources = []

    def execute(self, context: AgentContext) -> AgentOutput:
        return AgentOutput(
            agent=self.name,
            confidence=0.97,
            reply_draft="نعم، أنا معك. كيف أساعدك؟",
            sources=self.primary_sources,
            actions=["open_conversation"],
            message="تم تجهيز رد ترحيبي مبدئي.",
        )
