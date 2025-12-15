# Customer Support Multi Agentic System

A multi-agent customer support system built with LangGraph, Python, and LLMs. This project utilizes a Supervisor-Worker architecture enabling dynamic routing, retrieval-augmented generation (RAG), and seamless Human-in-the-Loop (HITL) interactions.

A central "Brain" (Supervisor Node) analyzes user intent before delegating tasks. It can answer general queries directly or route complex tasks to specialist agents (Billing, Returns, Troubleshoot). The agents don't just call tools; they analyze the output.
If a tool fails or returns data that needs further processing, the agent recursively calls the LLM to decide the next step until the task is marked completed.

Conversation history mentained in Mongodb (identifiers hardoded as of now)

<img width="2528" height="4544" alt="image" src="https://github.com/user-attachments/assets/8cb32f3b-76c7-47d6-9197-fed945273e9b" />


## 🛠️ Installation & Setup
This project uses uv for extremely fast package management and execution.

1. Prerequisites
- Python 3.10+

- uv installed (pip install uv or via your system package manager)

2. Configure Environment
The system relies on a configuration file for API keys and environment settings.

Copy the example configuration:

```Bash

cp config.example.yaml config.yaml
```
Open config.yaml and fill in your credentials:

```YAML

llm:
  provider: "openai" # or "anthropic"
  api_key: "sk-..."
  model: "gpt-4o"

database:
  # ... database configs if applicable
```

3. Install Dependencies
Sync your virtual environment with uv:

```Bash

uv sync
```

🚀 Usage
To start the main application loop (which initializes the LangGraph and waits for input):

```Bash

uv run python main.py

```

