# My agent: Parent & Child Daily School & Health Concierge

One-liner: A conversational agent that monitors ParentSquare and school channels for concise announcement digests, tracks daily school progress and evening activity checklists, generates quarterly trimester improvement plans via vector store docs, and manages child medical records, medicine/doctor follow-ups, annual health checks, and yearly renewal notifications.

Tool coverage:
- Memory: Remembers child profile, grade, bedtime schedule, medical records/allergies, medication dosages/schedules, doctor appointments, and annual checkup dates
- Tools: Monitors ParentSquare announcements, manages daily evening tasks, retrieves school & health records from vector store, schedules medicine/doctor follow-up reminders, and triggers annual checkup notifications
- Catalog/UI: Cards & tables showing urgent announcements, daily school summary, evening activity checklist, quarterly trimester reports, and medical records/appointment logs
- Image gen: Custom reward badges, accomplishment stars, or fun bedtime completion certificates
- Sandbox: Calculates evening time budgets, medication dosage timing intervals, and grade/health metric trends

Core rails (everyone): memory, tools, eval, deploy, frontend
My stretch menu (pick later): RAG / Vector Store (for quarterly academic & medical records), A2UI (announcements, health records & activity cards), Image Gen (reward badges), Sandbox (time & health math)
First eval question: "Summarize today's key school announcements, check pending evening assignments, and list upcoming doctor appointments or medicine follow-ups due this week."
