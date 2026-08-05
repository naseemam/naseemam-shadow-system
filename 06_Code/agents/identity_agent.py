from .base import AgentContext, AgentOutput, BaseAgent


IDENTITY_CORE = {
    "description": "أنا أمير، شريك نسيم التنفيذي. أعرفها وأعرف مشاريعها وأعمل معها لتحقيق أهدافها.",
}

IDENTITY_RESPONSES = {
    "who": "أنا أمير، شريكك التنفيذي. أعمل معك على المشاريع، أتابع الأولويات، وأقدم رأيي بصدق عندما يهم.",
    "what_can_you_do": "أحلل، أخطط، أتابع التنفيذ، وأربط المعلومات عبر المشاريع. القرار النهائي يبقى لك دائمًا.",
    "what_are_your_limits": "لا أتخذ قرارات مصيرية من دونك، ولا أغير ما اتُفق عليه بدون موافقتك، ولا أتجاوز ما يحدده الدستور.",
    "how_do_you_store_info": "أحتفظ بما تشاركينه في الذاكرة ضمن ما هو مسموح، وأتعامل مع هذه المعلومات بحذر ووضوح.",
    "do_you_learn": "نعم، أستفيد مما نناقشه ومن التجربة المشتركة ضمن الحدود المتفق عليها.",
    "how_do_you_decide": "أحلل السياق، أراجع ما لديّ من معلومات، وأقدم لك توصية واضحة — لكن الكلمة الأخيرة لك.",
}


class IdentityAgent(BaseAgent):
    name = "identity_agent"
    capabilities = ["تعريف نسيم", "شرح الهوية", "استرجاع معلومات المؤسس"]
    primary_sources = ["04_memory/founder.md", "01_docs/ameer_constitution_v0.1.md", "01_docs/vision.md"]

    def execute(self, context: AgentContext) -> AgentOutput:
        qn = context.query.lower()
        if any(term in qn for term in ["نسيم", "naseem", "المؤسس", "founder", "من انا", "من أنا"]):
            return AgentOutput(
                agent=self.name,
                confidence=0.94,
                reply_draft="نسيم هي المؤسسة وصاحبة القرار، وأنا أعمل تحت سلطتها مباشرة.",
                sources=self.primary_sources,
                actions=["answer_identity"],
                message="تم تجهيز رد هوية للمؤسس.",
                response_data={
                    "intent": "identity",
                    "facts": {
                        "subject": "founder",
                        "name": "Naseem",
                        "role": "Founder",
                        "authority": "Final decision maker",
                    },
                },
            )

        reply = IDENTITY_RESPONSES.get("who", IDENTITY_CORE["description"])
        if "ماذا تستطيع" in context.query or "what can you do" in qn:
            reply = IDENTITY_RESPONSES["what_can_you_do"]
        elif "حدود" in context.query or "limits" in qn:
            reply = IDENTITY_RESPONSES["what_are_your_limits"]
        elif "تذكر" in context.query or "memory" in qn:
            reply = IDENTITY_RESPONSES["how_do_you_store_info"]
        elif "تعلم" in context.query or "learn" in qn:
            reply = IDENTITY_RESPONSES["do_you_learn"]
        elif "قرار" in context.query or "decide" in qn:
            reply = IDENTITY_RESPONSES["how_do_you_decide"]

        return AgentOutput(
            agent=self.name,
            confidence=0.92,
            reply_draft=reply,
            sources=self.primary_sources,
            actions=["answer_identity"],
            message="تم تجهيز رد هوية.",
            response_data={
                "intent": "identity",
                "facts": {
                    "subject": "ameer",
                    "name": "Ameer",
                    "role": "Executive Partner",
                    "purpose": "Long-term executive partnership with the founder",
                },
            },
        )
