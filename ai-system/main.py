from fastapi import FastAPI
from pydantic import BaseModel

from crewai import Agent, Task, Crew
from langchain_ollama import OllamaLLM

app = FastAPI()

# =========================
# 🧠 MODELS (LOCAL OLLAMA)
# =========================

llama = OllamaLLM(model="llama3:8b")
qwen = OllamaLLM(model="qwen3-coder:30b")
gemma = OllamaLLM(model="gemma4:31b")
gptoss = OllamaLLM(model="gpt-oss:20b")

# =========================
# 🤖 AGENTS
# =========================

planner = Agent(
    role="System Architect",
    goal="Design system architecture from user request",
    backstory="Expert software architect specializing in scalable systems and clean design.",
    llm=llama
)

coder = Agent(
    role="Senior Developer",
    goal="Implement high-quality production code",
    backstory="Expert full-stack developer specialized in MERN and backend systems.",
    llm=qwen
)

reviewer = Agent(
    role="Code Reviewer",
    goal="Find bugs and improve code quality",
    backstory="Senior software engineer focused on correctness, security, and best practices.",
    llm=gemma
)

optimizer = Agent(
    role="Performance Optimizer",
    goal="Optimize performance and structure of final solution",
    backstory="Expert in system optimization and efficiency improvements.",
    llm=gptoss
)

# =========================
# 📦 REQUEST MODEL
# =========================

class PromptRequest(BaseModel):
    prompt: str

# =========================
# 🚀 API ENDPOINT
# =========================

@app.post("/run")
def run_agents(request: PromptRequest):

    # 🧠 STEP 1: Planning
    task1 = Task(
        description=f"""
        Create a full system architecture and step-by-step plan for:

        {request.prompt}
        """,
        agent=planner
    )

    # 💻 STEP 2: Implementation
    task2 = Task(
        description="""
        Using the architecture plan, implement the full solution in clean code.
        """,
        agent=coder,
        context=[task1]
    )

    # 🔍 STEP 3: Review
    task3 = Task(
        description="""
        Review the implementation, fix bugs, and improve structure and security.
        """,
        agent=reviewer,
        context=[task2]
    )

    # ⚡ STEP 4: Optimization
    task4 = Task(
        description="""
        Optimize the final output for performance, readability, and best practices.
        """,
        agent=optimizer,
        context=[task3]
    )

    # 👥 CREW SETUP
    crew = Crew(
        agents=[planner, coder, reviewer, optimizer],
        tasks=[task1, task2, task3, task4],
        verbose=True
    )

    # 🚀 RUN
    result = crew.kickoff()

    return {
        "result": result
    }