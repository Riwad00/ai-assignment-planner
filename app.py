import streamlit as st

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Overcomplicating An Assignment?",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="collapsed",
)

from ai_pipeline import demo_result, call_step_help, call_ai, verify_api_key

# ── Session state defaults ────────────────────────────────────────────────────
for key, default in [
    ("current_step", 1),
    ("result", None),
    ("done_steps", set()),
    ("api_key", ""),
    ("provider", "OpenAI (GPT)"),
    ("demo_mode", False),
    ("api_verified", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🧠 Overcomplicating An Assignment? Break It Down Into Steps")
st.markdown(
    "*Feeling overwhelmed by an assignment? Upload it and let AI turn it "
    "into a clear, actionable plan — one step at a time.*"
)
st.divider()

# ── STEP INDICATOR ────────────────────────────────────────────────────────────
current = st.session_state.current_step
step_labels = ["Setup", "Upload", "Results"]
step_icons  = ["⚙️", "📄", "✨"]

def _stepper_html(current_step, labels, icons):
    circles = ""
    for i, (label, icon) in enumerate(zip(labels, icons)):
        num = i + 1
        if num < current_step:
            state = "completed"
            display = "✓"
        elif num == current_step:
            state = "active"
            display = icon
        else:
            state = "upcoming"
            display = icon
        connector = ""
        if i < len(labels) - 1:
            bar_class = "completed" if num < current_step else "upcoming"
            connector = f'<div class="step-connector {bar_class}"></div>'
        circles += f"""
        <div class="step-item">
            <div class="step-circle {state}">{display}</div>
            <div class="step-label {state}">{label}</div>
        </div>
        {connector}
        """
    return f"""
    <style>
        .step-container {{
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1rem 0;
        }}
        .step-item {{
            display: flex;
            flex-direction: column;
            align-items: center;
            min-width: 80px;
        }}
        .step-circle {{
            width: 48px;
            height: 48px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            font-weight: 600;
            transition: all 0.3s ease;
        }}
        .step-circle.completed {{
            background: linear-gradient(135deg, #34d399, #10b981);
            color: white;
            box-shadow: 0 2px 8px rgba(16, 185, 129, 0.35);
        }}
        .step-circle.active {{
            background: linear-gradient(135deg, #60a5fa, #3b82f6);
            color: white;
            box-shadow: 0 2px 12px rgba(59, 130, 246, 0.4);
            animation: pulse 2s ease-in-out infinite;
        }}
        .step-circle.upcoming {{
            background: #f1f5f9;
            color: #94a3b8;
            border: 2px solid #e2e8f0;
        }}
        .step-label {{
            margin-top: 8px;
            font-size: 0.85rem;
            font-weight: 500;
        }}
        .step-label.completed {{ color: #10b981; }}
        .step-label.active {{ color: #3b82f6; font-weight: 700; }}
        .step-label.upcoming {{ color: #94a3b8; }}
        .step-connector {{
            height: 3px;
            width: 80px;
            margin: 0 8px;
            margin-bottom: 28px;
            border-radius: 2px;
        }}
        .step-connector.completed {{
            background: linear-gradient(90deg, #34d399, #10b981);
        }}
        .step-connector.upcoming {{
            background: #e2e8f0;
        }}
        @keyframes pulse {{
            0%, 100% {{ box-shadow: 0 2px 12px rgba(59, 130, 246, 0.4); }}
            50% {{ box-shadow: 0 2px 20px rgba(59, 130, 246, 0.6); }}
        }}
    </style>
    <div class="step-container">{circles}</div>
    """

st.html(_stepper_html(current, step_labels, step_icons))

# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — SETUP
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.current_step == 1:
    st.markdown("### ⚙️ Step 1: Choose how to connect")
    st.caption("Pick an AI provider and enter your key, **or** just enable Demo Mode to try the app instantly.")

    demo_mode = st.toggle(
        "🧪 Demo mode — skip API setup & try a sample response",
        value=st.session_state.demo_mode,
        key="demo_toggle",
    )
    st.session_state.demo_mode = demo_mode

    if not demo_mode:
        provider_options = ["OpenAI (GPT)", "Anthropic (Claude)", "Google Gemini", "Cohere"]
        # Ensure the saved provider is always a valid option
        if st.session_state.provider not in provider_options:
            st.session_state.provider = "OpenAI (GPT)"

        provider = st.radio(
            "AI Provider",
            provider_options,
            index=provider_options.index(st.session_state.provider),
            horizontal=True,
        )
        st.session_state.provider = provider

        if provider == "OpenAI (GPT)":
            api_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
            model_choice = st.selectbox(
                "Model",
                ["gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-4o", "gpt-4o-mini", "o3", "o3-mini"],
            )
        elif provider == "Anthropic (Claude)":
            api_key = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...")
            model_choice = st.selectbox(
                "Model",
                ["claude-sonnet-4-6", "claude-haiku-4-5-20251001", "claude-opus-4-6"],
            )
        elif provider == "Google Gemini":
            api_key = st.text_input("Google API Key", type="password", placeholder="AIza...")
            model_choice = st.selectbox(
                "Model",
                ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash", "gemini-2.0-pro"],
            )
        else:  # Cohere
            api_key = st.text_input("Cohere API Key", type="password", placeholder="coh-...")
            model_choice = st.selectbox(
                "Model",
                [
                    "command-a-03-2025",
                    "command-r-plus-08-2024",
                    "command-r-08-2024",
                ],
            )
        st.session_state.api_key = api_key
        st.session_state.model_choice = model_choice

        # Reset verification if key or provider changed
        if (api_key != st.session_state.get("_last_verified_key", "") or
                provider != st.session_state.get("_last_verified_provider", "")):
            st.session_state.api_verified = False

        # ── Test API Key button ───────────────────────────────────────────
        if api_key:
            if st.button("🔑 Test API Key", use_container_width=True):
                with st.spinner("Testing connection…"):
                    result = verify_api_key(provider, model_choice, api_key)
                if result["ok"]:
                    st.session_state.api_verified = True
                    st.session_state["_last_verified_key"] = api_key
                    st.session_state["_last_verified_provider"] = provider
                    st.success(
                        f"✅ Connected! Model replied: **{result['message']}** "
                        f"({result['latency_ms']} ms, key `{result['key_fp']}`)"
                    )
                else:
                    st.session_state.api_verified = False
                    st.error(f"❌ Failed: {result['message']}")
            elif st.session_state.api_verified:
                st.success("✅ API key verified — you're good to go!")
    else:
        st.info("Demo mode is on — no API key needed. You'll see a sample plan.")

    # Next button
    can_proceed = demo_mode or st.session_state.api_verified
    if st.button("Next → Upload your assignment", use_container_width=True, type="primary", disabled=not can_proceed):
        st.session_state.current_step = 2
        st.rerun()

    if not can_proceed and not demo_mode:
        st.caption("Please test your API key before continuing.")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — UPLOAD & CONFIGURE
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.current_step == 2:
    st.markdown("### 📄 Step 2: Tell us about your assignment")

    uploaded_pdf = st.file_uploader("Upload PDF", type=["pdf"], label_visibility="collapsed")
    pdf_text = None
    if uploaded_pdf is not None:
        try:
            from pypdf import PdfReader
            reader = PdfReader(uploaded_pdf)
            pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
            if pdf_text:
                with st.expander("Preview extracted text", expanded=False):
                    st.text(pdf_text[:3000] + ("…" if len(pdf_text) > 3000 else ""))
            else:
                st.caption("No text could be extracted (might be scanned / image-based).")
        except Exception as e:
            st.warning(f"Could not read PDF: {e}")
            pdf_text = None

    task_input = st.text_input(
        "Or describe your task in a line *(if no PDF)*",
        placeholder="e.g. 'Write a 10-page report on climate change with bibliography'",
    )

    col1, col2 = st.columns(2)
    with col1:
        available_time = st.slider(
            "⏱️ Time available (hours)",
            min_value=0.5, max_value=8.0, value=2.0, step=0.5,
        )
    with col2:
        complexity_feel = st.select_slider(
            "😅 How overwhelming does this feel?",
            options=["Meh", "A bit", "Quite a lot", "Send help"],
            value="Quite a lot",
        )

    context_note = st.text_input(
        "📌 Any context? *(optional)*",
        placeholder="e.g. 'Due tomorrow', 'First time doing this'",
    )

    st.divider()

    # Navigation
    bcol1, bcol2 = st.columns(2)
    with bcol1:
        if st.button("← Back to Setup", use_container_width=True):
            st.session_state.current_step = 1
            st.rerun()

    has_input = (pdf_text and pdf_text.strip()) or (task_input or "").strip()
    with bcol2:
        if st.button("✨ Simplify it", use_container_width=True, type="primary", disabled=not has_input):
            with st.spinner("Reading your assignment…"):
                try:
                    if st.session_state.demo_mode:
                        result = demo_result()
                    else:
                        provider = st.session_state.provider
                        api_key = st.session_state.api_key
                        model_choice = st.session_state.get("model_choice", "gpt-4.1")
                        result = call_ai(
                            pdf_text, task_input or "", available_time, complexity_feel,
                            context_note, provider, api_key, model_choice,
                        )
                    st.session_state["result"] = result
                    st.session_state["pdf_text"] = pdf_text
                    st.session_state["available_time"] = available_time
                    st.session_state.current_step = 3
                    st.rerun()
                except Exception as e:
                    st.error(f"Something went wrong: {e}")

    if not has_input:
        st.caption("Upload a PDF or describe your task to continue.")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — RESULTS
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.current_step == 3:
    result = st.session_state.get("result")
    if not result:
        st.warning("No results yet — going back to upload.")
        st.session_state.current_step = 2
        st.rerun()

    # Back button
    if st.button("← Start over with a new assignment"):
        st.session_state.current_step = 2
        st.session_state["result"] = None
        st.rerun()

    # ── Assignment snapshot ────────────────────────────────────────────────
    snapshot = result.get("assignment_snapshot", {})
    if snapshot:
        st.markdown(f"### 📋 {snapshot.get('title', 'Assignment overview')}")
        if snapshot.get("core_goal"):
            st.caption(snapshot["core_goal"])
        meta = []
        if snapshot.get("submission_format"):
            meta.append(f"📁 {snapshot['submission_format']}")
        if snapshot.get("deadline_note"):
            meta.append(f"⏰ {snapshot['deadline_note']}")
        if meta:
            st.caption(" · ".join(meta))

        reqs = snapshot.get("hard_requirements", [])
        weights = snapshot.get("grading_weights", [])
        if reqs and weights:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Requirements**")
                for r in reqs:
                    st.markdown(f"- {r}")
            with c2:
                st.markdown("**Grading weights**")
                for w in weights:
                    st.markdown(f"- {w}")
        elif reqs:
            st.markdown("**Requirements**")
            for r in reqs:
                st.markdown(f"- {r}")
        st.divider()

    # ── Calm intro ────────────────────────────────────────────────────────
    calm_intro = result.get("calm_intro", "")
    if calm_intro:
        st.info(calm_intro)

    # ── Verdict ───────────────────────────────────────────────────────────
    verdict = result.get("complexity_verdict", "")
    reason = result.get("complexity_reason", "")
    if verdict:
        if "overcomplicating" in verdict.lower():
            icon = "🟠"
        elif "right" in verdict.lower():
            icon = "🟢"
        else:
            icon = "🔵"
        st.markdown(f"{icon} **{verdict}** — {reason}")

    # ── First move ────────────────────────────────────────────────────────
    first_move = result.get("first_move", "")
    if first_move:
        st.success(f"⚡ **Start right now:** {first_move}")

    # ── Steps ─────────────────────────────────────────────────────────────
    steps = result.get("steps", [])
    total_proc = 0

    st.markdown("### 📍 Your step-by-step plan")
    if steps:
        completed_count = len(
            st.session_state["done_steps"].intersection(
                {str(s.get("step", "")) for s in steps}
            )
        )
        st.progress(completed_count / len(steps))
        st.caption(f"{completed_count} of {len(steps)} steps completed")

    def make_step_toggle(sid):
        def toggle():
            wk = f"step_done_{sid}"
            if st.session_state.get(wk):
                st.session_state["done_steps"].add(sid)
            else:
                st.session_state["done_steps"].discard(sid)
        return toggle

    pdf_text = st.session_state.get("pdf_text")

    for s in steps:
        step_id = s.get("step", "")
        step_title = s.get("title", "")
        what_to_do = s.get("what_to_do", "") or s.get("description", "")
        why = s.get("why_it_matters", "")
        notes = s.get("specific_notes", "")
        step_time = s.get("time_minutes", "?")
        is_trap = s.get("procrastination_risk", False)
        trap_reason = s.get("procrastination_reason", "")
        sid = str(step_id)

        if is_trap:
            total_proc += 1

        st.markdown(f"#### Step {step_id}: {step_title} `~{step_time} min`")
        st.write(what_to_do)
        if why:
            st.info(f"**Why it matters:** {why}")
        if notes:
            st.success(f"📘 **Tutor note:** {notes}")
        if is_trap and trap_reason:
            st.warning(f"⚠️ **Stall risk:** {trap_reason}")

        wk = f"step_done_{sid}"
        if wk not in st.session_state:
            st.session_state[wk] = sid in st.session_state["done_steps"]
        st.checkbox("Mark as done", key=wk, on_change=make_step_toggle(sid))

        with st.expander("Stuck on this step? Ask for help"):
            issue_key = f"issue_{step_id}"
            response_key = f"help_response_{step_id}"
            issue_text = st.text_area("What's the issue?", key=issue_key, height=80)
            if st.button("Get help", key=f"ask_{step_id}"):
                if st.session_state.demo_mode:
                    st.session_state[response_key] = (
                        "- Focus on the smallest next action.\n"
                        "- Ignore polish; just create a rough version.\n"
                        "- If stuck, write a placeholder and move on."
                    )
                else:
                    try:
                        st.session_state[response_key] = call_step_help(
                            issue_text, step_title, what_to_do,
                            st.session_state.provider,
                            st.session_state.api_key,
                            st.session_state.get("model_choice", "gpt-4.1"),
                            pdf_text=pdf_text,
                        )
                    except Exception as e:
                        st.session_state[response_key] = f"Error: {e}"
            if response_key in st.session_state:
                st.markdown("**AI help**")
                st.write(st.session_state[response_key])

        st.divider()

    # ── Metrics ───────────────────────────────────────────────────────────
    m1, m2, m3 = st.columns(3)
    total_min = result.get("total_time_minutes", 0)
    if not total_min and steps:
        total_min = sum(int(s.get("time_minutes", 0)) for s in steps)
    available_time = st.session_state.get("available_time", 2.0)
    m1.metric("⏱️ Real time needed", f"{total_min} min")
    m2.metric("🪤 Stall-risk steps", f"{total_proc} step{'s' if total_proc != 1 else ''}")
    slack = round(available_time * 60 - total_min)
    m3.metric(
        "🧘 Slack time", f"{max(0, slack)} min",
        delta="buffer" if slack > 0 else "overbooked",
        delta_color="normal" if slack > 0 else "inverse",
    )
    budget_min = int(available_time * 60)
    if budget_min > 0 and total_min > 0:
        ratio = min(1.0, total_min / budget_min)
        st.progress(ratio)
        st.caption(f"Using {total_min} of {budget_min} min available")

    # ── What to cut ───────────────────────────────────────────────────────
    what_to_cut = result.get("what_to_cut", "")
    if what_to_cut:
        st.markdown("**✂️ What you can skip**")
        st.write(what_to_cut)

    # ── Copy steps ────────────────────────────────────────────────────────
    with st.expander("📋 Copy steps as plain text"):
        lines = []
        for s in steps:
            trap = " [⚠️ STALL RISK]" if s.get("procrastination_risk") else ""
            what = s.get("what_to_do", "") or s.get("description", "")
            why_text = s.get("why_it_matters", "")
            notes_text = s.get("specific_notes", "")
            block = f"Step {s['step']}: {s['title']}{trap} (~{s.get('time_minutes', '?')} min)\n  → {what}"
            if why_text:
                block += f"\n  Why: {why_text}"
            if notes_text:
                block += f"\n  Note: {notes_text}"
            lines.append(block)
        st.code("\n\n".join(lines), language=None)
