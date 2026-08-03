from .base import AgentContext, AgentOutput, BaseAgent


class MemoryAgent(BaseAgent):
    name = "memory_agent"
    capabilities = ["استرجاع قرارات", "استدعاء سياق", "تلخيص الذاكرة"]
    primary_sources = ["04_memory/"]

    def execute(self, context: AgentContext) -> AgentOutput:
        if context.results:
            path, excerpt = self._top_result(context.results)
            return AgentOutput(
                agent=self.name,
                confidence=0.9,
                reply_draft=(
                    "وجدت سجلات ذاكرة مرتبطة بطلبك:\n"
                    f"- {path}\n"
                    f"{excerpt}"
                ),
                sources=[str(item.get("path")) for item in context.results if item.get("path")],
                actions=["recall_memory"],
                message="تم تجهيز رد ذاكرة من المصادر المتاحة.",
            )

        return AgentOutput(
            agent=self.name,
            confidence=0.55,
            reply_draft="لا توجد سجلات ذاكرة مطابقة بشكل واضح لهذا الطلب.",
            sources=self.primary_sources,
            actions=["memory_not_found"],
            message="تم إنهاء مسار الذاكرة بدون نتائج.",
        )
