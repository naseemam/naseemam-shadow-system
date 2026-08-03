from .base import AgentContext, AgentOutput, BaseAgent


class RecoveryAgent(BaseAgent):
    name = "recovery_agent"
    capabilities = ["استعادة المسار", "fallback", "استقرار الجلسة"]
    primary_sources = ["01_docs/", "03_architecture/", "04_memory/"]

    def execute(self, context: AgentContext) -> AgentOutput:
        return AgentOutput(
            agent=self.name,
            confidence=0.5,
            reply_draft=(
                "حدث خلل داخلي أثناء معالجة الطلب، وتم تفعيل مسار الاستعادة الآمن. "
                "سأعطيك إجابة محافظة لحين اكتمال المعالجة في طبقة Executive Brain."
            ),
            sources=self.primary_sources,
            actions=["recover_runtime_path"],
            message="تم تفعيل Recovery Agent لضمان عدم انهيار المسار.",
        )
