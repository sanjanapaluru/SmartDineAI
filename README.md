# SmartDineAI

SmartDineAI is a Python-based intelligent dining assistant that uses an agentic workflow to provide personalized restaurant recommendations. The project is structured as a modular package, leveraging modern dependency management for reproducible environments.

## Core Features

* **Agentic Decision Making:** Uses a centralized agent to process natural language queries and determine the necessary steps to fulfill user requests.
* **Tool-Based Architecture:** Features a decoupled tool system where the agent calls specific functions for searching, filtering, and data processing.
* **Modern Python Tooling:** Utilizes the uv package manager and pyproject.toml for high-performance dependency resolution and environment consistency.
* **Modular Design:** The core logic is isolated within the dinesmartai package, allowing for easier testing and scalability.

## Project Structure

* **dinesmartai/**: The primary package containing the application logic.
    * **agent.py**: Defines the AI agent's behavior and decision-making loop.
    * **tools.py**: Contains the functional tools (API wrappers, search logic) available to the agent.
* **main.py**: The entry point for the application.
* **pyproject.toml**: Defines project metadata and dependencies.
* **uv.lock**: Ensures consistent installations across different environments.

## Technical Workflow

The application follows an iterative execution cycle:
1. **Input Parsing:** The system accepts a user query regarding dining preferences or location.
2. **Task Planning:** The agent evaluates the query and selects the appropriate tool from the toolset.
3. **Action Execution:** The selected tool performs the required data retrieval or processing task.
4. **Response Synthesis:** The agent gathers the tool output and formats it into a final recommendation for the user.

## Installation

This project requires the [uv](https://github.com/astral-sh/uv) package manager.

1. Clone the repository:
   git clone https://github.com/sanjanapaluru/SmartDineAI.git
   cd SmartDineAI

2. Sync the environment:
   uv sync

## Usage

To run the assistant, execute the main script through the uv runner:

```bash
uv run main.py
