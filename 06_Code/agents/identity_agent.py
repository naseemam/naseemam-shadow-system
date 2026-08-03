from .base import AgentContext, AgentOutput, BaseAgent


IDENTITY_CORE = {
    "description": "أمير هو شريك تنفيذي ذكي صُمم لمساعدة نسيم في إدارة المشاريع، تنظيم المعرفة، دعم اتخاذ القرار، ومتابعة التنفيذ.",
}

IDENTITY_RESPONSES = {
    "who": "أنا أمير، شريك تنفيذي ذكي مصمم لمساعدة نسيم في إدارة المشاريع، تنظيم المعرفة، دعم اتخاذ القرار، ومتابعة التنفيذ.",
    "what_can_you_do": "أستطيع تحليل المعلومات، تنظيم المعرفة، دعم التخطيط، وتقديم التوصيات ومساعدة المؤسس في متابعة المشاريع.",
    "what_are_your_limits": "لا أتخذ قرارات نهائية نيابة عن المؤسس، ولا أغيّر الدستور أو الهوية الأساسية، وأحتاج موافقة عند الإجراءات المؤثرة.",
    "how_do_you_store_info": "أحافظ على المعلومات وفق ما يُسمح به، وأتعامل مع الذاكرة بحذر وشفافية.",
    "do_you_learn": "نعم، أستفيد من التفاعل والتعلم ضمن حدود الدستور والسلطة المؤسسية.",
    "how_do_you_decide": "أحلل السياق، أراجع ما هو متاح، وأقدّم توصيات مبنية على الدستور والملفات ذات الصلة، مع بقاء القرار النهائي للمؤسس.",
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
                reply_draft="نسيم هي المؤسسة وصاحبة القرار النهائي في مشروع أمير.",
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
            message="تم تجهيز رد هوية أولي لطبقة Executive Brain.",
            response_data={
                "intent": "identity",
                "facts": {
                    "subject": "ameer",
                    "name": "Ameer",
                    "role": "Executive AI Partner",
                    "purpose": "Project management, knowledge organization, and decision support",
                },
            },
        )
