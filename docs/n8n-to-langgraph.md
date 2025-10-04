

## Step 1: Prompt to convert n8n workflow to requirements (use Claude opus)

* Paste (*ctrl+shift+v* and not *ctrl+v*) the following prompt in Claude Opus 4.1 chat interface followed by n8n workflow  
* Create new Cursor project folder: `<appropriate project folder name>`  
* Create `docs/` folder inside this project folder  
* Save Claude's output as `docs/prd.md`

```
You are an expert n8n developer and system analyst. Your task is to analyze the provided n8n workflow JSON and create a detailed technical specification for building and debugging an equivalent Express.js application. Separate platform features (capabilities to implement) from workflow configuration (business-specific values).IMPORTANT: Always describe configurations in plain language. Do not use n8n expressions directly - instead, explain the logic in plain English.

Global Workflow Summary

Objective: Concisely state the workflow’s main purpose and business goal.

Workflow Settings: List any workflow-level configurations found in the JSON (e.g., error workflow reference, timezone, save execution progress).

Triggers: List all entry points (e.g., webhook method/path, cron schedule) and when responses are sent (immediate vs after execution). Include any trigger-specific configurations.

Execution Rules: Concurrency limits, batching rules, retry/backoff strategy, and timeout settings (global and per-node)
Security: Inbound auth (method, scopes, CORS/CSRF, body limits) and outbound auth (type, token handling, secret source).

Error Handling: How the workflow handles failures globally (stop, skip, error node).

Per Node Specification

For each node (use the name or type as the heading):
- Functionality: Plain-English description of what the node does and any external services used.
- Built-in Parameters to Replicate: List the n8n node's native capabilities and configuration options that define HOW the node operates. Features such as authentication modes, execution mode (per-item/per-batch), retries, timeouts, continue-on-fail, output format, pagination, rate limits, and error output handling.
- Workflow-Specific Configuration: Actual business values like API endpoints, database names/tables, query params, field mappings, or constants—describe in plain language.
- Data Mapping: How input data is transformed to output data, including defaults and conditions.
- Success Path: Which node(s) run next and under what conditions.
- Error Path: Behavior if the node fails (stop, skip, or route to error handler).- If the node is a **custom node** (e.g., Function, Lambda, or not part of the standard n8n library), generate a stub specification:
  - Clearly mark it as **custom**.
  - Describe any visible inputs/outputs in plain English if possible.
  - Add a note: "Implementation for this node lives in `/req-for-custom-nodes/<node-name>.md`."
  - Do not invent internal logic — just reference the external file.


Based on the workflow analysis, note any additional requirements for the Express.js implementation: - Required middleware (body parsing, CORS, authentication) - External service dependencies - Rate limiting or throttling needs - Error handling strategy - Data validation requirements

n8n JSON Code:
[PASTE YOUR N8N JSON CODE]
```

### Step 2: Requirement generation for custom nodes

* Save all custom nodes code at `/req-for-custom-nodes/<node-name>.md` in Cursor project folder. 

```
You are a Python code analyst. Analyze the provided Python code from n8n custom nodes and create technical requirements:

For each Python function/class:
1. **Purpose**: What does this code accomplish?
2. **Inputs**: Expected parameters, data types, and validation
3. **Processing Logic**: Step-by-step description of the transformation
4. **Outputs**: Return data structure and format
5. **Dependencies**: External libraries and their purpose
6. **Error Handling**: Exception types and handling strategy
7. **Node.js Equivalent Strategy**: Suggest equivalent npm packages

Python Code:
[PASTE PYTHON CODE HERE]
```

### 

### Step 3: Code Generation (n8n Workflow to Langgraph Python)

* Paste the following prompt in Cursor. 

````
## Task Overview
Convert the provided n8n JSON workflow into a LangGraph implementation where each n8n node becomes a corresponding LangGraph node. Maintain the original workflow logic, data flow, and functionality while leveraging LangGraph's capabilities.

## Input Materials
- **n8n JSON Workflow**: ```
[Paste your n8n workflow JSON here]
```
- **Project Requirements**: ```
[Paste your project requirements here]
```

## Critical Custom Node Handling Process

### 1. **MANDATORY: Read Custom Node Requirements FIRST**
**BEFORE generating any code:**
- Scan the n8n workflow JSON for nodes marked as **custom** with placeholders pointing to `/req-for-custom-nodes/<node-name>.md`
- **Read each referenced file `/req-for-custom-nodes/<node-name>.md` completely**
- These files contain the actual implementation requirements for custom business logic
- Do NOT proceed with conversion until all custom node requirement files are analyzed

### 2. **Custom Node Translation Process**
For each custom node found:
1. **Read the requirement file**: `/req-for-custom-nodes/<node-name>.md`
2. **Translate the implementation**: Convert any existing code (Python, etc.) to Python functions suitable for LangGraph
3. **Preserve functionality**: Ensure inputs/outputs match exactly so it integrates seamlessly
4. **Expand specification**: Replace the placeholder in the workflow with full node details (Functionality, Parameters, Data Mapping, Success/Error Paths)
5. **Mark as custom**: Preserve the `**custom**` marker for traceability

### 3. **Integration Strategy**
- Custom nodes become regular LangGraph node functions
- Use the same calling pattern as built-in nodes
- Ensure custom nodes return proper state updates
- Handle custom node errors within the LangGraph error handling framework

## Conversion Requirements

### 1. Node Mapping Strategy
- **First**, analyze project requirements to understand custom functionality needed
- **Then**, create a LangGraph node for each n8n workflow node based on:
  - Standard n8n node functionality
  - **Custom business logic from project requirements**
  - **Domain-specific processing needs**
  - **Integration requirements with external systems**
- Preserve the original node names and functionality
- Maintain the execution order and conditional logic
- Map n8n node types to appropriate LangGraph implementations:
  - HTTP Request nodes → LangGraph tool nodes or custom API clients
  - Code/Function nodes → Custom Python functions implementing project-specific logic
  - Conditional nodes → LangGraph conditional edges with business rule validation
  - Loop nodes → LangGraph loop structures with custom iteration logic
  - Webhook nodes → LangGraph input nodes with custom payload processing
  - Database nodes → Tool nodes with database connections and custom queries
  - **Custom/Function nodes → Implement based on project requirements analysis**

### 2. Project Requirements Integration
After reading custom node files, analyze how they integrate with the overall project:
- Map custom nodes to business requirements
- Understand data flow between custom and standard nodes
- Identify dependencies and external integrations needed
- Plan error handling for custom business logic
- Maintain all data connections between nodes
- Preserve variable passing and data transformation
- Keep the same input/output structure
- Ensure proper state management between nodes

### 3. LangGraph Structure Requirements
- Use proper LangGraph StateGraph initialization
- Implement appropriate state schema using TypedDict or Pydantic
- Create proper node functions with state parameter
- Set up correct edges and conditional routing
- Include proper error handling and logging
- When invoking the compiled graph, set a default recursion limit of 100 (e.g., `app.invoke(initial_state, {"recursion_limit": 100})`). This is crucial for workflows that loop over many items.

### 4. Code Organization
- Structure code with clear imports and dependencies
- Create helper functions for complex logic
- Add proper type hints and documentation
- Include configuration variables at the top
- Organize into logical sections (state, nodes, graph setup)

## Output Requirements

### 1. Complete LangGraph Implementation
```python
# Provide the full, runnable LangGraph code
```

### 2. Comprehensive Node Analysis Documentation
Create detailed documentation showing:

#### A. Complete Node Conversion Table
| n8n Node Name | n8n Node Type | Custom Req File | Functionality Translated | LangGraph Implementation | Dependencies | Notes |
|---------------|---------------|----------------|-------------------------|-------------------------|--------------|-------|
| EmailProcessor | HTTP Request | - | - | Tool node with API call | requests | Standard node |
| BusinessLogic | Function | `/req-for-custom-nodes/business-logic.md` | Python validation rules | Custom function node | pandas, custom-lib | **custom** |
| SendNotification | Webhook | - | - | Tool node with POST | requests | Standard node |

#### B. Custom Node Implementation Details
For each custom node, provide:
- **Source**: Which requirement file it came from
- **Translation**: How the original code was converted to Python/LangGraph
- **Integration**: How it connects to the workflow state
- **Dependencies**: External packages or services required

### 3. Dependencies List
List all required Python packages and versions needed to run the LangGraph workflow.

### 4. Configuration Notes
- Environment variables needed
- API keys or credentials required
- Any setup instructions, including Google OAuth setup:
  - Explain the need for `credentials.json` from Google Cloud Console.
  - Describe the first-run interactive authentication flow: the script will print a URL, the user must visit it, authorize the application, and paste the resulting code back into the terminal.
  - Mention that a `token.json` file will be created to store credentials for subsequent runs.

### 5. Testing Instructions
Provide basic instructions on how to test the converted workflow.

### 6. Graph Flow and Recursion Analysis 
After generating the Python code, you must provide a separate analysis of the graph's control flow. The purpose of this analysis is to formally verify that the implementation is robust and free of common recursion traps or dead-end paths, especially in workflows that iterate over a list of items.

Your analysis must include the following parts:

A. Loop Structure Identification
First, identify and name the key components of the primary loop in the generated graph.

Controller Node: State the name of the single node that manages the iteration (i.e., the one that selects the next item from the list).

Conditional Exit: Identify the conditional edge and the condition that allows the workflow to terminate gracefully (i.e., by routing to END when the list of items is empty).

Processing Entry Point: Name the first node that begins the processing for a single item after it's been selected by the controller.

B. Path Tracing and Verification
Next, trace the execution paths for a single item to verify that all branches loop back correctly.

Success Path Trace: Document the sequence of nodes that execute when an item is processed successfully. You must explicitly state that the final node in this path connects back to the Controller Node.

Example Format: start_processing -> step_2 -> step_3_success -> log_success -> (Loops back to) Controller Node

Failure Path Trace(s): Identify every critical failure or alternative branch in the workflow (e.g., an "if" condition is not met, an API call fails, no data is found). For each distinct failure path, document its node sequence and confirm that it also connects back to the Controller Node.

Example Format (No Data Found): start_processing -> step_2_api_call -> (conditional_no_data) -> log_failure -> (Loops back to) Controller Node

C. Final Verdict
Provide a brief, concluding statement confirming that the graph architecture is sound.

Example Verdict: "The analysis confirms that all success and failure branches for a single item's lifecycle correctly route back to the controller node. No dead-end paths or recursion traps were identified. The workflow will reliably process all items in the initial list."

## Additional Considerations
- Maintain error handling from original workflow
- Preserve any retry logic or timeout settings
- Keep authentication and security configurations
- Ensure scalability and performance characteristics
- Add comments explaining complex conversions
- Include any necessary data validation

## Expected Deliverables
1. **Pre-conversion Analysis**: List of all custom node requirement files found and their purposes
2. **Complete, runnable LangGraph Python code** with custom nodes fully integrated
3. **Enhanced workflow documentation** showing both standard and custom node conversions
4. **Custom node implementation details** with source traceability
5. **Dependencies list** including packages needed for custom nodes
6. **Configuration and setup instructions** for both standard and custom functionality

## Conversion Process
1. **FIRST**: Scan n8n JSON for custom node placeholders
2. **SECOND**: Read all `/req-for-custom-nodes/<node-name>.md` files
3. **THIRD**: Translate custom implementations to Python
4. **FOURTH**: Create integrated LangGraph workflow
5. **FIFTH**: Document all conversions with custom node traceability

Please analyze the provided n8n workflow, read all referenced custom node requirement files, then deliver a fully functional LangGraph implementation that maintains the original workflow's behavior while properly integrating all custom business logic.
````

```

```
