import re
with open("backend/app/search/research_engine.py", "r") as f:
    text = f.read()

text = text.replace(
    'await db.execute(\n                """\n                INSERT INTO research_reports (id, conversation_id, topic, markdown_path, pdf_path, docx_path, report_content, facts_json)\n                VALUES (?, ?, ?, ?, ?, ?, ?, ?)\n                """,\n                (report_id, conversation_id, topic, rel_md, rel_pdf, rel_docx, report_md, facts_json)\n            )',
    'await db.db.research_reports.insert_one({"id": report_id, "conversation_id": conversation_id, "topic": topic, "markdown_path": rel_md, "pdf_path": rel_pdf, "docx_path": rel_docx, "report_content": report_md, "facts_json": facts_json, "created_at": datetime.utcnow().isoformat()})'
)

with open("backend/app/search/research_engine.py", "w") as f:
    f.write(text)
