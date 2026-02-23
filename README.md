# Overcomplicating An Assignment? Break It Down Into Steps 🧠

*Feeling overwhelmed by an assignment? Upload it and let AI turn it into a clear, actionable plan — one step at a time.*

**[Try the app live →](https://ai-assignment-planner-for-pdai-a1.streamlit.app)** 

**Note:** *This project serves as a second iteration and another retry shot at solving the challenge of prototyping digital products with AI.*

## Features
- **3-Step Wizard Flow**: Clean, guided onboarding experience without clunky sidebars.
- **Multi-Model Support**: Connects to OpenAI (GPT-4o), Anthropic (Claude 3.5), and Google (Gemini 1.5/2.0).
- **In-App API Verification**: instantly tests your API key before you begin.
- **Smart Parsing**: Upload up to 25,000 characters of a PDF grading rubric or assignment brief.
- **Actionable Steps**: The AI breaks down the task into concrete, trackable checkboxes with time estimates and procrastination warnings. 

## Architecture
This project adheres to separation of concerns by splitting the user interface and prediction logic:
- `app.py`: The Streamlit frontend, managing state, UI layout, and the wizard flow.
- `ai_pipeline.py`: The backend prediction logic, containing the system prompts, JSON parsing, API authentication, and model routing.

## Setup and Installation

1. Create a virtual environment and activate it:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python3 -m streamlit run app.py
   ```

## Usage
1. Open the local Network URL provided by Streamlit (usually `http://localhost:8501`).
2. Complete **Step 1** by selecting a provider and entering your API key (or switch on Demo Mode). Test the connection.
3. Complete **Step 2** by uploading your assignment PDF and setting your available time.
4. View your results in **Step 3** and start checking off tasks!
