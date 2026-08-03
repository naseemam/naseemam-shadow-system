from .base import AgentContext, AgentOutput, BaseAgent


class ProjectAgent(BaseAgent):
    name = "project_agent"
    capabilities = ["شرح الهدف", "متابعة الخطة", "تحليل التقدم"]
    primary_sources = ["01_docs/master_plan.md", "01_docs/vision.md", "01_docs/roadmap.md"]

    def execute(self, context: AgentContext) -> AgentOutput:
        if context.results:
            path, excerpt = self._top_result(context.results)
            reply = (
                f"الخطة: {context.execution_plan['goal']}\n"
                "الإجراء: " + " → ".join(context.execution_plan["steps"][:3]) + "\n\n"
                "ملخص تنسيقي للمصدر الأعلى صلة:\n"
                f"- {path}\n"
                f"{excerpt}"
            ).strip()
            return AgentOutput(
                agent=self.name,
                confidence=0.9,
                reply_draft=reply,
                sources=[str(item.get("path")) for item in context.results if item.get("path")],
                actions=["summarize_project_context"],
                message="تم تجهيز مسودة رد منسقة اعتمادًا على الاسترجاع.",
                response_data={
                    "intent": "project",
                    "facts": {
                        "goal": context.execution_plan.get("goal", ""),
                        "steps": context.execution_plan.get("steps", []),
                        "top_source": path,
                        "top_excerpt": excerpt,
                    },
                },
            )

        return AgentOutput(
            agent=self.name,
            confidence=0.6,
            reply_draft="لا توجد نتائج كافية حول المشروع في المصادر المتاحة حاليًا.",
            sources=self.primary_sources,
            actions=["request_more_project_context"],
            message="تم إنهاء التنسيق بدون نتائج كافية.",
            response_data={
                "intent": "project",
                "facts": {
                    "status": "not_found",
                },
            },
        )
