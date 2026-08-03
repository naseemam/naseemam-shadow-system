from .base import AgentContext, AgentOutput, BaseAgent


class ResearchAgent(BaseAgent):
    name = "research_agent"
    capabilities = ["بحث عام", "تلخيص مصادر", "توجيه معرفي"]
    primary_sources = ["01_docs/", "03_architecture/", "04_memory/"]

    def execute(self, context: AgentContext) -> AgentOutput:
        if context.conversation_state.get("is_follow_up") and context.active_goal:
            return AgentOutput(
                agent=self.name,
                confidence=0.75,
                reply_draft=(
                    f"سياق الجلسة: {context.active_goal}\n"
                    "أرى أنك تتبع خطوة أو تحوّلًا في الهدف، وسأركز على هذا الاتجاه."
                ),
                sources=self.primary_sources,
                actions=["follow_up_guidance"],
                message="تم تجهيز سياق متابعة الجلسة.",
            )

        if context.conversation_state.get("plan_shifted") and context.active_goal:
            return AgentOutput(
                agent=self.name,
                confidence=0.78,
                reply_draft=(
                    f"تم تغيير الاتجاه بناءً على التحول في الهدف إلى: {context.active_goal}\n"
                    "سأعالج هذا التغيير كتحول رئيسي في الخطة."
                ),
                sources=self.primary_sources,
                actions=["plan_shift_guidance"],
                message="تم تجهيز إشارة التحول في الخطة.",
            )

        if context.results:
            path, excerpt = self._top_result(context.results)
            return AgentOutput(
                agent=self.name,
                confidence=0.72,
                reply_draft=(
                    f"الخطة: {context.execution_plan['goal']}\n"
                    "الإجراء: " + " → ".join(context.execution_plan["steps"][:3]) + "\n\n"
                    "ملخص تنسيقي للمصدر الأعلى صلة:\n"
                    f"- {path}\n"
                    f"{excerpt}"
                ).strip(),
                sources=[str(item.get("path")) for item in context.results if item.get("path")],
                actions=["synthesize_workspace_knowledge"],
                message="تم تجهيز مسودة رد منسقة اعتمادًا على الاسترجاع.",
            )

        return AgentOutput(
            agent=self.name,
            confidence=0.55,
            reply_draft="لا توجد نتائج كافية، يلزم توليد رد توضيحي من Executive Brain.",
            sources=self.primary_sources,
            actions=["request_clarification"],
            message="تم إنهاء التنسيق بدون نتائج كافية.",
        )
