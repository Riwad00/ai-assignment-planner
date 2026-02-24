import json
import re
import time
import hashlib
from datetime import datetime


def verify_api_key(provider, model, api_key):
    """Send a tiny test prompt to verify the API key works. Returns a dict."""
    if not api_key:
        return {"ok": False, "message": "API key is empty."}
    try:
        t0 = time.perf_counter()

        if provider == "OpenAI (GPT)":
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model=model,
                max_tokens=8,
                temperature=0,
                messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            )
            reply = (resp.choices[0].message.content or "").strip()

        elif provider == "Anthropic (Claude)":
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model=model,
                max_tokens=8,
                messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            )
            reply = (msg.content[0].text or "").strip()

        elif provider == "Cohere":
            import cohere
            client = cohere.ClientV2(api_key=api_key)
            resp = client.chat(
                model=model,
                messages=[{"role": "user", "content": "Reply with exactly: OK"}],
                max_tokens=8,
                temperature=0,
            )
            # Chat V2 returns a message object with content list; first item is text
            reply = (resp.message.content[0].text or "").strip()

        else:  # Google Gemini
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            m = genai.GenerativeModel(model)
            resp = m.generate_content(
                "Reply with exactly: OK",
                generation_config={"max_output_tokens": 8},
            )
            reply = (resp.text or "").strip()

        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "ok": True,
            "message": reply,
            "latency_ms": elapsed_ms,
            "provider": provider,
            "model": model,
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "key_fp": hashlib.sha256(api_key.encode()).hexdigest()[:12],
        }
    except Exception as e:
        return {
            "ok": False,
            "message": str(e),
            "provider": provider,
            "model": model,
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "key_fp": hashlib.sha256(api_key.encode()).hexdigest()[:12] if api_key else "",
        }

SYSTEM_PROMPT = """You are a focused academic and project coach. Your job is to read the uploaded document carefully and produce a step-by-step plan that tells the user exactly HOW to complete the work — not just what the assignment asks them to do.

THE MOST IMPORTANT RULE — READ THIS FIRST:
A step like "Complete exercises 1–11" or "Work through the notebook tasks" is USELESS. The user already knows the assignment exists. Your job is to tell them what to actually DO inside each task — the technique, the code pattern, the approach, the thing they need to produce. Every step must be something the user could act on immediately without re-reading the assignment.

CRITICAL RULES:
1. NEVER write a step that just restates or paraphrases the assignment. "Do exercise 3", "Complete the reflection section", "Work through the tasks" are all forbidden. Instead, explain WHAT the user needs to write, code, produce, or decide for that specific exercise or section — in enough detail that they could start immediately.
2. If the document lists numbered exercises, problems, or tasks, each one (or a small group of closely related ones) gets its own step. Describe what that exercise is actually testing and what the user needs to produce.
3. "what_to_do" must answer: what specific thing do I write, code, or decide right now? It must mention the actual content — the concept being applied, the code structure needed, the argument to make, the format to follow.
4. "why_it_matters" must reference grading criteria, mark allocations, or specific requirements from the document. Not generic stakes — actual stakes from this assignment.
5. "specific_notes" must contain technical or subject-specific guidance a tutor would give: common mistakes for this type of task, the exact variable names or formats required, the concept the exercise is testing, a hint about approach.
6. "calm_intro" must name the assignment and acknowledge what specifically makes it feel complex. No generic reassurance.
7. "first_move" must be a concrete, immediate action — not "start working" but e.g. "Open the notebook, read Exercise 1's instruction cell, and write the one line of code it asks for."

Return ONLY valid JSON — no markdown fences, no explanation outside the JSON. Use this exact structure:
{
  "assignment_snapshot": {
    "title": "Short name for this assignment or task",
    "core_goal": "One sentence: what must ultimately be produced or demonstrated",
    "hard_requirements": ["requirement extracted from the document"],
    "submission_format": "How it must be submitted (file type, length, platform) or null",
    "deadline_note": "Deadline info if present in the document, or null",
    "grading_weights": ["e.g. 40% literature review — only if rubric present, else empty array"]
  },
  "complexity_verdict": "You're overcomplicating this" or "This is about right" or "This is genuinely complex",
  "complexity_reason": "One sentence tied to the specific document or task",
  "calm_intro": "2-3 sentences. Name the assignment, acknowledge what makes it feel heavy, and reassure the user the steps below will make it manageable.",
  "steps": [
    {
      "step": 1,
      "title": "Short action title that describes what you produce, not just what you do",
      "what_to_do": "What specifically to write, code, or produce for this step. If this is an exercise, explain what it is asking the user to do technically — the concept, the expected output, the approach. Specific enough to start immediately.",
      "why_it_matters": "One sentence: the actual stake — mark weight, rubric criterion, or consequence of skipping this",
      "specific_notes": "Technical or subject-specific guidance: common mistakes, required formats, the concept being tested, a concrete hint about approach or output",
      "time_minutes": 30,
      "procrastination_risk": true,
      "procrastination_reason": "Why students stall here — only include this field when procrastination_risk is true"
    }
  ],
  "total_time_minutes": 90,
  "what_to_cut": "Specific things the user can safely skip or defer without hurting their grade",
  "first_move": "The single most concrete first action — specific enough to do in the next 2 minutes"
}

Step count: If the document has numbered exercises or sub-tasks, each one (or small group) should be its own step. Return as many steps as needed to cover the real work — up to 12. Never collapse distinct exercises into a single vague step."""


def build_user_msg(pdf_text, task, hours, overwhelm, context):
    parts = []
    if pdf_text and pdf_text.strip():
        parts.append(f"""Assignment document (this is the authoritative source — base all requirements, steps, and notes on this):

---
{pdf_text[:25000]}
---""")
    if (task or "").strip():
        if pdf_text:
            parts.append(f"Additional task description from student: {task.strip()}")
        else:
            parts.append(f"Task: {task.strip()}")
    if not parts:
        parts.append("Task: (No document or task provided — give a general planning guide.)")

    parts.append(f"""Available time: {hours} hours
How overwhelming it feels: {overwhelm}
Context: {context if context else 'none'}

Produce a step-by-step plan where every step tells the user what to actually write, code, or produce — not just what the assignment says to do. If the document has numbered exercises or tasks, give each one its own step describing what it specifically involves. Never write a step that just says "complete exercise N" or "work through the tasks" — that is not useful. Each step must be actionable immediately.""")
    return "\n\n".join(parts)


def parse_json(raw):
    raw = re.sub(r"^```json|^```|```$", "", raw, flags=re.MULTILINE).strip()
    if not raw:
        raise json.JSONDecodeError("Empty response", raw, 0)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw[start:end + 1])
        raise


def demo_result():
    return {
        "assignment_snapshot": {
            "title": "PDAI Assignment 1 – Reflective Report",
            "core_goal": "Produce a 1500-word reflective report analysing how AI tools affected your learning during the module, supported by at least four academic references.",
            "hard_requirements": [
                "Minimum 1500 words, maximum 2000 words",
                "At least 4 peer-reviewed academic references (APA 7th edition)",
                "Must include: Introduction, Reflection section using Gibbs' Reflective Cycle (6 stages), Conclusion",
                "Submitted as a PDF via the Moodle portal by the stated deadline",
                "AI tool use must be declared in an appendix",
            ],
            "submission_format": "PDF upload via Moodle, single document",
            "deadline_note": "Week 10 Friday, 11:59 PM",
            "grading_weights": [
                "40% — Depth of reflection and critical thinking",
                "30% — Evidence of wider reading and referencing",
                "20% — Structure and academic writing quality",
                "10% — AI use declaration and appendix",
            ],
        },
        "complexity_verdict": "You're overcomplicating this",
        "complexity_reason": "The rubric is explicit and Gibbs' Cycle gives you a ready-made skeleton — once you map your experience to the six stages, the structure writes itself.",
        "calm_intro": "This is a structured reflection report with a tight 2000-word ceiling, which means you literally cannot over-write even if you wanted to. Gibbs' Reflective Cycle is your scaffold — six stages, each needing one or two honest paragraphs drawn from your own experience with AI tools. You are not doing original research here; you are describing what happened and what you learned from it.",
        "steps": [
            {
                "step": 1,
                "title": "Build your document skeleton in 10 minutes",
                "what_to_do": "Create a blank document with these exact headings in order: Introduction, Description (Gibbs Stage 1), Feelings (Stage 2), Evaluation (Stage 3), Analysis (Stage 4), Conclusion (Stage 5), Action Plan (Stage 6), Reference List, Appendix: AI Use Declaration.",
                "why_it_matters": "Structure accounts for 20% of the grade and the rubric explicitly names required headings — a missing section heading loses marks regardless of writing quality.",
                "specific_notes": "All six Gibbs stages must be visible as separate paragraphs or subheadings. Budget roughly 200 words per stage, 150 for the Introduction, and 150 for the Conclusion — that lands you cleanly in the 1500–2000 word window.",
                "time_minutes": 10,
                "procrastination_risk": False,
            },
            {
                "step": 2,
                "title": "Brain-dump your AI experiences under each Gibbs stage",
                "what_to_do": "Set a 12-minute timer. Under each of the six stage headings, write rough notes — not sentences — about what happened with AI tools in this module. What did you use? What went wrong? How did it feel? What surprised you? What would you do differently?",
                "why_it_matters": "Depth of reflection is worth 40% of the grade. Raw, specific memory from your own experience is the input — no amount of referencing covers a superficial or generic reflection.",
                "specific_notes": "The rubric rewards 'critical thinking' specifically — generic statements like 'AI helped me write faster' score in the lowest band. Aim for a specific moment: a prompt that failed, a result you had to correct, a decision you made because of (or despite) AI output.",
                "time_minutes": 15,
                "procrastination_risk": True,
                "procrastination_reason": "Starting to write feels like committing to something imperfect. Brain-dumping reframes this as rough notes, not prose — that makes it much easier to begin.",
            },
            {
                "step": 3,
                "title": "Find and save your 4 peer-reviewed references",
                "what_to_do": "Go to Google Scholar or your institution library portal. Search for peer-reviewed papers on AI in education, reflective practice, or the specific tool you used. Save 4–5 papers. Skim abstracts to confirm they connect to your actual reflection, not just the general topic.",
                "why_it_matters": "References are worth 30% of the grade and must be peer-reviewed — blog posts, vendor pages, and Wikipedia do not count toward the minimum four.",
                "specific_notes": "The rubric requires APA 7th edition. For a journal article: Author, A. A. (Year). Title of article. Journal Name, volume(issue), pages. https://doi.org/xxxxx — set this up in a reference manager (Zotero is free) now so you are not reformatting citations at midnight.",
                "time_minutes": 30,
                "procrastination_risk": True,
                "procrastination_reason": "Reference hunting can expand infinitely. Cap it at 30 minutes — 4 solid papers is enough. You can add a fifth later if a gap appears.",
            },
            {
                "step": 4,
                "title": "Write the reflection body — one Gibbs stage at a time",
                "what_to_do": "Using your brain-dump notes, convert each stage into 1–2 readable paragraphs (~200 words per stage). Work through all six stages in order. In Stage 4 (Analysis), integrate at least two of your references to connect your experience to theory. Do not edit while writing — just complete each stage and move to the next.",
                "why_it_matters": "This is the core deliverable. The Analysis stage is where your references belong, and it is the section markers read most carefully for critical thinking (40% of the grade).",
                "specific_notes": "References fit naturally in Stage 4 (Analysis) and optionally Stage 5 (Conclusion). Avoid dropping citations into Stages 1-2 (Description, Feelings) — it feels forced and the rubric does not reward it there. If you feel stuck on any stage, write one sentence and move on; you can return to it.",
                "time_minutes": 60,
                "procrastination_risk": True,
                "procrastination_reason": "This is the longest block and it has no clear stopping point. Break it into six 10-minute sub-tasks — one per Gibbs stage — and treat each as a separate small win.",
            },
            {
                "step": 5,
                "title": "Write the Introduction and Conclusion",
                "what_to_do": "Write a 150-word Introduction stating the purpose of the report and briefly naming the AI tools you used. Write a 150-word Conclusion summarising what you learned and what you would do differently. Do not introduce new information in the Conclusion.",
                "why_it_matters": "These sections frame the report and contribute to the 20% structure mark. A weak or missing introduction signals poor academic writing regardless of content quality.",
                "specific_notes": "Write these after the body, not before — it is much easier to introduce a report you have already written. The Conclusion should echo your Action Plan (Gibbs Stage 6) rather than repeat it word-for-word.",
                "time_minutes": 20,
                "procrastination_risk": False,
            },
            {
                "step": 6,
                "title": "Write the AI Use Declaration appendix",
                "what_to_do": "Add a section titled 'Appendix: AI Use Declaration'. List each AI tool you used, describe what task you used it for, and explain how you checked or adapted its output. One short paragraph per tool is enough.",
                "why_it_matters": "The AI declaration is worth 10% of the grade and is a mandatory submission component — it cannot be skipped even if your AI use was minimal.",
                "specific_notes": "The rubric does not penalise AI use — it rewards honest and reflective disclosure. If you used no AI tools at all, state that clearly. Undisclosed AI use is treated as academic misconduct.",
                "time_minutes": 10,
                "procrastination_risk": False,
            },
            {
                "step": 7,
                "title": "Word count, formatting check, and PDF submission",
                "what_to_do": "Check your word count (target: 1500–2000 words, excluding references and appendix). Confirm all six Gibbs stage headings are present. Export as PDF. Log in to Moodle and complete the upload before the deadline.",
                "why_it_matters": "Submissions outside the word count window are penalised. A PDF that fails to upload costs you the deadline regardless of how good the content is.",
                "specific_notes": "Test the Moodle upload before the deadline — do not wait until 11:58 PM. Moodle can reject certain PDF versions or fail under load. After uploading, download your submission receipt as proof.",
                "time_minutes": 15,
                "procrastination_risk": True,
                "procrastination_reason": "The urge to keep editing at this stage is strong. If your word count is in range and all headings are present, submit. Done is better than perfect.",
            },
        ],
        "total_time_minutes": 160,
        "what_to_cut": "You do not need an abstract, table of contents, diagrams, or extra frameworks alongside Gibbs. The rubric does not ask for any of these and adding them will push you over the 2000-word limit.",
        "first_move": "Open the assignment brief PDF right now, find the list of required section headings, and paste them as a skeleton into a blank document — this takes 5 minutes and immediately makes the report feel finite.",
    }


def call_step_help(issue_text, step_title, step_description, provider, api_key, model, pdf_text=None):
    if not issue_text.strip():
        return "Please describe the issue you are facing on this step."

    helper_prompt = f"""You are a calm, practical tutor helping a student who is stuck on a specific step.
Give short, direct advice that unblocks them. Keep it to 3-5 bullet points. Be specific to the step and the assignment.

Step: {step_title}
What the step involves: {step_description}
Student's issue: {issue_text}"""

    if pdf_text and pdf_text.strip():
        helper_prompt += f"\n\nAssignment context:\n---\n{pdf_text[:8000]}\n---"

    if provider == "Anthropic (Claude)":
        try:
            import anthropic
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError("Missing dependency: anthropic. Install with `pip install anthropic`.") from exc
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=600,
            system="You are a calm, practical tutor. Respond with concise bullets only.",
            messages=[{"role": "user", "content": helper_prompt}],
        )
        return message.content[0].text.strip()

    if provider == "OpenAI (GPT)":
        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError("Missing dependency: openai. Install with `pip install openai`.") from exc
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            max_tokens=600,
            messages=[
                {"role": "system", "content": "You are a calm, practical tutor. Respond with concise bullets only."},
                {"role": "user", "content": helper_prompt},
            ],
        )
        return response.choices[0].message.content.strip()

    if provider == "Cohere":
        try:
            import cohere
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError("Missing dependency: cohere. Install with `pip install cohere`.") from exc
        client = cohere.ClientV2(api_key=api_key)
        # Put style instructions directly into the user message for simplicity
        response = client.chat(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": "You are a calm, practical tutor. Respond with concise bullets only.\n\n"
                    + helper_prompt,
                }
            ],
            max_tokens=600,
        )
        return response.message.content[0].text.strip()

    try:
        import google.generativeai as genai
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError("Missing dependency: google-generativeai. Install with `pip install google-generativeai`.") from exc
    genai.configure(api_key=api_key)
    model_client = genai.GenerativeModel(model)
    response = model_client.generate_content(
        helper_prompt,
        generation_config={"max_output_tokens": 600},
    )
    return (response.text or "").strip()


def call_ai(pdf_text, task, hours, overwhelm, context, provider, api_key, model):
    user_msg = build_user_msg(pdf_text, task, hours, overwhelm, context)

    if provider == "Anthropic (Claude)":
        try:
            import anthropic
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError("Missing dependency: anthropic. Install with `pip install anthropic`.") from exc
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = message.content[0].text.strip()

    elif provider == "OpenAI (GPT)":
        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError("Missing dependency: openai. Install with `pip install openai`.") from exc
        client = OpenAI(api_key=api_key)
        openai_params = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            "max_tokens": 4000,
        }
        response = client.chat.completions.create(**openai_params)
        raw = response.choices[0].message.content.strip()

    elif provider == "Cohere":
        try:
            import cohere
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError("Missing dependency: cohere. Install with `pip install cohere`.") from exc
        client = cohere.ClientV2(api_key=api_key)
        response = client.chat(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": f"{SYSTEM_PROMPT}\n\n{user_msg}",
                }
            ],
            max_tokens=4000,
        )
        raw = response.message.content[0].text.strip()

    else:  # Gemini
        try:
            import google.generativeai as genai
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError("Missing dependency: google-generativeai. Install with `pip install google-generativeai`.") from exc
        genai.configure(api_key=api_key)
        model_client = genai.GenerativeModel(model)
        response = model_client.generate_content(
            f"{SYSTEM_PROMPT}\n\n{user_msg}",
            generation_config={"max_output_tokens": 4000},
        )
        raw = (response.text or "").strip()

    if not raw:
        raise ValueError("Model returned an empty response. Try again or switch models.")
    try:
        return parse_json(raw)
    except json.JSONDecodeError:
        # One retry with stricter instruction
        retry_msg = user_msg + "\n\nSTRICT: Return only valid JSON, no markdown, no extra text."
        if provider == "Anthropic (Claude)":
            message = client.messages.create(
                model=model,
                max_tokens=4000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": retry_msg}],
            )
            raw = message.content[0].text.strip()
        elif provider == "OpenAI (GPT)":
            openai_params = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": retry_msg},
                ],
                "max_tokens": 4000,
            }
            response = client.chat.completions.create(**openai_params)
            raw = response.choices[0].message.content.strip()
        elif provider == "Cohere":
            response = client.chat(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": f"{SYSTEM_PROMPT}\n\n{retry_msg}",
                    }
                ],
                max_tokens=4000,
            )
            raw = response.message.content[0].text.strip()
        else:
            response = model_client.generate_content(
                f"{SYSTEM_PROMPT}\n\n{retry_msg}",
                generation_config={"max_output_tokens": 4000},
            )
            raw = (response.text or "").strip()
        return parse_json(raw)
