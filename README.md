# AI Agent Team Demo

### An Experimental AI Software House for .NET Development

**From Requirements to Architecture, Code, Testing, and Delivery.**

AI Agent Team is an experimental multi-agent software development project that explores how specialized AI agents can collaborate across a software engineering workflow.

Instead of relying on a single AI coding assistant, the project organizes AI agents into dedicated engineering roles and coordinates their work through a shared project workspace.

The goal is to explore how AI can assist with the software development lifecycle, from requirements analysis to implementation and quality checks.

> **Project status: Experimental / Early Development**
>
> This project is a work in progress. Features may be incomplete, results require human review, and production readiness has not been established.

## Virtual Office Preview

The project includes a 3D Virtual Office interface that visualizes the AI development team, workflow progress, and activity logs.

<!-- Add a screenshot here after uploading it to the repository -->
<!-- Example: ![AI Agent Team Virtual Office](screenshots/virtual-office.png) -->

## AI Engineering Roles

The current implementation defines seven specialized roles:

| Role | Responsibility |
|---|---|
| System Analyst (SA) | Analyze requirements and prepare software specifications |
| Solution Architect (.NET) | Design the application architecture |
| Senior .NET Backend Developer | Generate backend APIs and business logic |
| Senior Blazor Frontend Developer | Generate the frontend application |
| QA Automation Engineer (.NET) | Create tests and evaluate build/test results |
| Technical Writer & Product Specialist | Prepare user and technical documentation |
| DevOps Engineer | Assist with Git workflows and project delivery tasks |

## Development Workflow

The system is designed to coordinate tasks across a software development pipeline:

1. Submit project requirements.
2. Analyze requirements and prepare specifications.
3. Design the solution architecture.
4. Generate or update backend and frontend code.
5. Run automated build and test checks.
6. Attempt to repair detected issues.
7. Prepare documentation and Git delivery steps.

Actual results depend on the requirement, the target project, the installed tools, and the LLM response. Human review remains necessary.

## Supported Work Modes

- **New Project:** Generate a new .NET solution from requirements.
- **Feature Addition:** Explore and extend an existing project.
- **Scalability Enhancement:** Explore performance and scalability improvements.

## Key Features

- 3D Virtual Office with seven AI role representations
- Requirement input and project configuration
- Support for existing project workspaces
- File read, write, and targeted replacement tools
- .NET CLI and Git CLI integration
- Live workflow status and activity logs
- Automated build/test checks and repair attempts
- Documentation generation workflow

These capabilities are experimental and should not be interpreted as a guarantee of fully autonomous or production-quality delivery.

## Technology Stack

- Python
- CrewAI
- Google Gemini
- Pydantic
- python-dotenv
- HTML and JavaScript
- Three.js
- Tailwind CSS
- .NET CLI and Git CLI

## Getting Started

### Prerequisites

Prepare the following before running the application:

- Python installed on Windows
- Git installed and available on `PATH`
- .NET SDK installed and available on `PATH`
- A Google Gemini API key
- Access to any target repository you intend to use

### 1. Clone the repository

```bash
git clone https://github.com/worawut-boxsolution/ai-agent-team-demo.git
cd ai-agent-team-demo
```

### 2. Create a virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Python dependencies

Install the compatible versions of the packages imported by `main.py`, including CrewAI, Pydantic, and python-dotenv.

Check the current CrewAI documentation for compatible installation requirements.

### 4. Configure your API key

Create a local `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key
```

Use your own API key. Never commit `.env` or other secrets to GitHub.

### 5. Start the application

```bash
python main.py
```

The application is configured to open the Virtual Office at:

`http://localhost:8000/office.html`

### 6. Try a development task

1. Select a work mode.
2. Enter a project name.
3. Configure a local workspace path.
4. Enter a software requirement.
5. Review the workflow and activity logs.
6. Inspect the generated files and run the appropriate tests.

Start with a disposable test project rather than an important production codebase.

> Installation steps and dependency versions may need adjustment as the project evolves. The setup has not been verified across all environments.

## Security Notice

This project is experimental and can execute commands through development tools.

AI agents may read and modify files and invoke Git or .NET CLI commands. Generated commands and code may be incorrect or destructive.

Before running the project:

- Use a dedicated, disposable workspace.
- Review commands before allowing them to execute.
- Never expose the local server directly to the public internet.
- Do not use production credentials or sensitive customer data.
- Review repository URLs and Git operations before execution.
- Use least-privilege credentials.
- Keep API keys in local environment variables.
- Back up important source code before testing.

Additional sandboxing, authentication, authorization, process isolation, and command restrictions are recommended before any production use.

## Current Limitations

- The project is under active experimentation.
- AI-generated code may contain errors or security vulnerabilities.
- Automated tests cannot guarantee correctness.
- Repair attempts may fail or introduce new defects.
- Results and execution time may vary.
- API usage may incur costs.
- Production deployment is not guaranteed.

## Roadmap

Potential areas for future development:

- [ ] Improved agent context sharing
- [ ] Human approval checkpoints
- [ ] Safer command execution and sandboxing
- [ ] More reliable automated testing
- [ ] Git branch and pull request workflows
- [ ] Better error recovery and execution monitoring
- [ ] Usage and token cost tracking
- [ ] Additional LLM provider support

## Feedback and Collaboration

I welcome feedback from developers, software architects, QA engineers, DevOps engineers, and AI researchers interested in multi-agent software engineering.

If you try the demo, feedback on architecture, workflow design, reliability, and safety is welcome through GitHub Issues.

## Author

**Worawut Chaingam**

Software Development · .NET · Software Architecture · AI Agents

GitHub: [@worawut-boxsolution](https://github.com/worawut-boxsolution)

---

**This repository is a public demonstration of an ongoing experiment in AI-assisted software engineering. It is not a production-ready autonomous development platform.**
