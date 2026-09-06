These slides serve as the opening section (C0) for Class 4 of PE6201: Emerging AI Technologies. They bridge previous lessons on AI models with the current session's focus on building and evaluating AI agents.

**Course Recap (Classes 1–3)**

* **Classes 1 & 2:** Covered the taxonomy of AI, the "jagged frontier" of capabilities, the AI tech stack (from compute to evals), build-vs-buy decisions, and hands-on work building a RAG pipeline end-to-end.
* **Class 3:** Focused on steering the model via prompt engineering (chain-of-thought, structured JSON), understanding transformers/tokens, and using eval-driven iteration.

**AI in the News**

* **Agents in the Wild:** Highlights a recent security intrusion where a multi-agent system bypassed model guardrails, alongside Google's Agent2Agent moving under the Linux Foundation to standardize agent communication.
* **Agent Economics:** Notes the massive ~$40bn valuation of Cognition (makers of Devin) contrasted with low actual production rates of agentic AI (only ~9–14% of firms), setting up a discussion on the cost, reliability, and trust gap.
* **Fine-Tuning:** Uses the Harvey Legal Agent Benchmark to show that fine-tuning models for specific tasks improves performance at roughly the same cost per task.

**Class 4 Objectives & Agenda**

* **Focus:** Understanding agents and tool use, agentic patterns (like ReAct), agent failure modes, and agent economics.
* **C1:** What is an agent? (Lecture and discussion).
* **C2:** Tools, failure modes, and evals, including a live demo where you will build and intentionally break a loop.
* **C3:** Agent economics and a case discussion on Anthropic.

The graph in **Screenshot 2026-08-25 at 18.51.57.jpg** plots the performance of various AI models on the August 2026 Harvey Legal Agent Benchmark, measuring their task success rate against their actual operating costs.

**Specialization Over Scale**

* The vertical arrow from Kimi K3 to Harvey highlights the performance jump achieved by fine-tuning a strong general model specifically for legal work.
* This post-training specialization roughly doubled the model's all-pass rate—from approximately 11% to 20%—while maintaining broadly the same cost per task.

**Pricing the Task, Not the Token**

* The horizontal axis evaluates the cache-aware cost in dollars per completed task, rather than the raw price per million tokens.
* This metric is used because models with cheaper tokens might require more retries, conversational turns, and re-sent context, which can ultimately cost more per completed task.

**Frontier Model Landscape**

* Frontier models like Opus 5, Fable 5, and Opus 4.8 cluster on the high-cost side (left), requiring $10 to $25+ per task to achieve pass rates between 5% and 12%.
* Muse Spark 1.1 stands out in the top right quadrant as a high-efficiency outlier, reaching a 20% pass rate for under $1 per task.
* Models positioned on the far right, such as Haiku 4.5 and GPT-5.6 Luna, represent the lowest cost per task (under $0.50) but yield near-zero all-pass rates on this strict evaluation standard.

The **PE6201 Class 4 (Capsule C1)** slide deck, titled *"What is an agent?"*, provides a comprehensive framework for defining, structuring, evaluating, and deciding when to deploy AI agents.

### Slide-by-Slide Overview

**Slide 1: Title & Objective**

* **Focus:** Introduces Capsule C1 (~45 mins) covering agent loops, memory, architectural patterns, and anti-patterns.


* **Learning Goal:** Differentiate agents from static prompts, deterministic workflows, and RAG pipelines, while understanding the cost and operational implications of each.



**Slide 2: Definition of an Agent**

* **Core Definition:** Cites Anthropic's definition where a model dynamically directs its own process and tool usage at runtime.


* **Two Non-Negotiable Conditions:** (1) Steps are not fixed in advance (chosen dynamically at runtime); (2) Ground truth (tool execution results) feeds back into the model to correct its path.


* **Contrast:** Removing condition 1 yields a fixed workflow; removing condition 2 yields an unvalidated monologue.



**Slide 3: You Have Already Used One**

* **Everyday Examples:** Highlights real-world agent implementations like Deep Research, AI coding assistants running test suites, Google's Gemini Spark, and automated customer support rebooking agents.


* **Takeaway:** Agents are already mainstream patterns embedded in daily enterprise tools.



**Slide 4: From One Call to a Loop**

* **Architecture:** Breaks down an agent system into 6 core components: Model, Tools, Memory, Control Loop (orchestration code), Stop Condition (budget/step cap), and System Orchestration.


* **Takeaway:** The developer builds and controls the loop around the model; the model only produces action requests.



**Slide 5: The Loop, as Text (Mechanism)**

* **ReAct Trajectory:** Illustrates the `Thought` $\rightarrow$ `Action` $\rightarrow$ `Observation` execution trace based on Yao et al. (2022).


* **Key Insight:** Observations from external tools are the model's only touchpoint with reality. Because observations append to the transcript and resend on every turn, they drive accuracy as well as token costs.



**Slide 6: What Counts as a Tool?**

* **5 Tool Categories:** Classifies tools by side-effects into Retrieve (read-only), Compute (deterministic execution), Act on System (write/update), Communicate (messaging), and Sense (OCR/sensing).


* **Governance Boundary:** Systems that only read (Retrieve/Compute/Sense) are research tools; systems that write or communicate carry non-reversible real-world impact.



**Slide 7: Memory — What It Holds, and What It Keeps**

* **Working Memory:** The active running transcript. Highly temporary, resent on each call, and susceptible to "context rot" as tokens grow.


* **Persistent Memory:** External storage (databases, notes, vector stores) loaded at initialization and saved upon exit.



**Slide 8: Who Decides the Control Flow?**

* **Workflow vs. Agent:**
* *Workflows:* Pre-defined code paths, fixed step counts, fully testable paths, predictable costs.


* *Agents:* Runtime-determined paths, variable step counts, outcome-based testing, unpredictable costs.





**Slide 9: The Chooser — Seven Rungs, Cheapest First**

* **Taxonomy Ladder:** Maps system complexity across 7 rungs: (1) Single call, (2) Prompt chain, (3) Routing, (4) Parallelisation, (5) Orchestrator–workers, (6) Evaluator–optimiser, and (7) Full Agent.


* **Takeaway:** Rungs 1–6 are deterministic workflows. Developers should only escalate to Rung 7 when step sequences genuinely cannot be pre-determined.



**Slide 10: Three Agent Patterns**

* **Architectural Options:**
* *ReAct:* Single loop (Think $\rightarrow$ Act $\rightarrow$ Observe). Fails via infinite loops or wandering when observations are noisy.


* *Planner–Executor:* Upfront master plan execution. Fails when rigid plans encounter unexpected realities.


* *Multi-Agent:* Specialized sub-agents coordinated by a lead. Fails when agents make contradictory un-reconciled assumptions.





**Slide 11: Multi-Agent, Honestly (The Correction)**

* **Cognition Case Study:** Compares Cognition's shift from [June 2025 ("Don't build multi-agents")](https://cognition.com/blog/dont-build-multi-agents) to [April 2026 ("Multi-agents: what's actually working")](https://cognition.com/blog/multi-agents-working).


* **Rule of Thumb:** "Multiple minds, one hand on the keyboard"—split analysis across specialized agents, but enforce single-threaded state writes.



**Slide 12: RAG, Agentic RAG, or an Agent?**

* **3-Question Matrix:** Differentiates systems based on who selects retrieval parameters, whether query looping is supported, and whether external side-effects (writes/payments) occur.


* **Agentic RAG:** An agent restricted entirely to read-only tool sets.



**Slides 13–15: One Patient, Three Systems (Clinical Example)**

* **RAG:** Single guideline lookup for metformin dosage rules.


* **Agentic RAG:** Dynamically queries guidelines, checks patient lab values ($eGFR = 38$), re-queries adjusted bands, and returns cited recommendations.


* **Agent:** Executes clinical actions—drafting record adjustments, scheduling follow-up lab panels, and notifying pharmacy staff.



**Slide 16: When NOT to Build an Agent**

* **Ground-Truth Test:** Agents require immediate, objective feedback (e.g., code test suite passing vs. delayed subjective user feedback).


* **Compound Probability Arithmetic:** A 20-step process with 95% single-step accuracy yields only $0.95^{20} \approx 36\%$ end-to-end reliability. Reliable agents require heavy recovery machinery rather than just raw model capabilities.



**Slide 17: Same Pattern, Different Industries**

* **Industry Mapping:** Evaluates banking reconciliation, prior-authorization workflows, shipment tracking, and telco outage routing, demonstrating that most real-world enterprise tasks require workflows below Rung 7.



**Slide 18: Think–Pair–Share Exercise**

* **Class Activity:** Interactive exercise asking students to analyze a workplace task across retrieval capabilities, loop requirements, irreversible action boundaries, and appropriate target rungs.



**Slide 19: Capsule 1 Takeaway & References**

* **Summary:** Reinforces that an agent is fundamentally a decision loop. Links to foundational engineering resources from [Anthropic's Agent Guide](https://www.anthropic.com/engineering/building-effective-agents) and Cognition.

The **C2: Build it & Harden it** slide deck (~60 mins) focuses on designing robust agent interfaces, breaking and hardening control loops, implementing code-level guardrails, and evaluating multi-step agent trajectories.

**Tool Design & Interface Design**

* **The Agent-Computer Interface (ACI):** Models resolve description ambiguities confidently and wrongly. Tool descriptions serve as the entire manual, requiring strict typing and clear parameters rather than conversational instructions.


* **Poka-Yoke Interface Design:** Replace soft prompt requests with hard code constraints. For instance, use `Literal["SIN-DC1", "KUL-DC2"]` instead of free-text strings, split `draft_email` from `send_email`, and set `dry_run = True` as the default.


* **Prompts vs. Interfaces:** Interface constraints cost zero marginal tokens and permanently eliminate failure modes, whereas prompt instructions re-bill tokens every turn and risk being ignored during model updates.


* **Minimal Tool Sets:** Adding unnecessary tools inflates context cost (+24% across an 8-turn run for 5 extra tools) and degrades tool selection accuracy.



**Failure Mechanisms & Field Evidence**

* **Bad Observations:** Poor tool output derails model reasoning; fixed at the **tool layer** by filtering returned data.


* **Repetitive Loops:** Agent repeats identical actions; fixed at the **loop layer** via step caps, budget limits, and deduplication.


* **Prior Overriding Evidence:** Model relies on pre-trained assumptions over tool outputs; fixed in **code** by verifying claims against observations.


* **Real-World Failures:** Maps real-world coding agent benchmarks (e.g., Devin) to these mechanisms, showing failures like hallucinated capabilities and context rot.



**Deterministic Guardrails & Autonomy**

* **Bounds:** Three lines of non-AI code (step caps, budget ceilings, action deduplication) turn silent token burns into immediate stops, recovering ~75% of wasted spend.


* **Gates:** Enforce an autonomy dial (`suggest` $\rightarrow$ `confirm` $\rightarrow$ `act`) placed strictly in front of non-reversible write/action tools.



**Agent Evaluation & Test Harness**

* **Outcome-Based Evals:** Evaluate trajectories and real-world side effects across multiple isolated trials rather than fixed paths.


* **Negative Test Cases:** The 8-task eval suite includes negative cases (e.g., non-existent orders or unapproved draft policies). Eager agents pass standard tasks but fail negative cases by inventing dates or enforcing draft policies, whereas careful agents know when to refuse.

The **Agent-Computer Interface (ACI)** is the design paradigm stating that tool engineering for AI models is fundamentally interface design. Because an AI agent cannot ask clarifying questions, hover over tooltips, or test code in staging, it relies entirely on a tool's name, type signature, and description to execute actions.

**The Asymmetric Reader**

* Human engineers read documentation, test endpoints, and ask colleagues when ambiguity arises.
* AI models read a name, signature, and single docstring, then immediately execute—resolving any ambiguity confidently, incorrectly, and at scale.

**Four Core Interface Rules**

* **Room to Think:** Provide sufficient token space for the model to reason through its plan before emitting non-retractable action parameters.
* **Familiar Formats:** Use standard formats (e.g., standard JSON, SQL, or tabular data) matching patterns dense in pre-training corpora.
* **No Bookkeeping:** Avoid requiring the model to manage string escaping, manual character counting, or precise indentation.
* **Mistake-Proofing (Poka-Yoke):** Build constraints into code signatures instead of prompt text. Prompts re-bill tokens every turn and can be ignored, whereas type constraints cannot be bypassed.

**ACI Implementation Examples**

* **Constrained Types:** Use `Literal["SIN-DC1", "KUL-DC2"]` instead of `str` to eliminate silent lookup errors from typos.
* **Unambiguous Identifiers:** Pass exact keys like `patient_id: str` rather than ambiguous attributes like `patient_name: str`.
* **Separation of Concerns:** Split single destructive functions into safe two-step interfaces (e.g., `draft_email` and `send_email`).
* **Safe Defaults:** Set non-destructive defaults explicitly (e.g., `dry_run: bool = True`) so missing flags fail safely.
* **Observation Filtering:** Return compact, relevant schema fields (e.g., returning 3 summary records of 8 tokens instead of dumping 246 tokens of unparsed text) to prevent context rot and lower turn costs.

This formula calculates the **total input tokens billed across an $T$-turn agentic loop**, illustrating why agent execution costs scale quadratically ($O(T^2)$) rather than linearly.

**Formula Breakdown**

$$\text{Total Cumulative Tokens} \approx B \cdot T + \frac{D \cdot T^2}{2}$$

* **$B$ (Base Context):** Fixed overhead tokens re-sent on every single turn (system prompt, guidelines, and tool definitions).
* **$D$ (Delta / Turn Growth):** Average number of new tokens added to the working memory transcript on each turn (tool observations, model thoughts, and action calls).
* **$T$ (Turns / Steps):** The number of iterations the agent loop executes.

---

**Derivation**

Because an agent's working memory transcript grows with every turn and is re-sent in full on each subsequent call:

* **Turn 1:** $B + D$ tokens billed
* **Turn 2:** $B + 2D$ tokens billed
* **Turn $T$:** $B + T \cdot D$ tokens billed

Summing across all $T$ turns yields:

$$\sum_{t=1}^{T} (B + t \cdot D) = B \cdot T + D \frac{T(T + 1)}{2} = B \cdot T + \frac{D \cdot T^2}{2} + \frac{D \cdot T}{2} \approx B \cdot T + \frac{D \cdot T^2}{2}$$

---

**Engineering Takeaways**

* **Quadratic Scaling ($T^2$):** Doubling the number of turns quadruples the token cost driven by transcript history. Capping steps or stopping early provides the largest cost reduction.
* **The "Fat Observation" Tax ($D$):** Returning a 200-token tool output instead of an 8-token filtered JSON increases $D$ by $25\times$. That penalty compounds across every subsequent turn in the run.
* **Tool Overhead ($B$):** Every tool added to the prompt inflates $B$, increasing the base baseline cost for every turn, even if that tool is never called.

This slide bridges theoretical AI failure modes with empirical field data by mapping independent evaluation data from the Devin AI coding agent across 20 real-world tasks to the course's three core failure mechanisms.

| Devin's Observed Failure | Evaluator Symptom | Underlying Mechanism & Layer |
| --- | --- | --- |
| **Hallucinated capabilities** | Claimed to use tools or services that did not exist. | **Mechanism 3 (Priors Over Evidence):** The model relied on training priors instead of checking the actual tool list provided in context. |
| **Context blindness** | Missed a constraint stated earlier in the trajectory. | **Mechanism 1 (Bad Observation / Context Rot):** Early constraints were diluted by accumulated transcript tokens. |
| **Tunnel vision** | Each local step seemed reasonable, but the global path was wrong. | **Mechanism 2 (Repetition Sibling):** The control loop lacks an explicit world model or global tracking of progress. |
| **Overcomplexity** | Built far more code or features than requested. | **Lack of Stop Criteria:** No ground-truth definition of "done" was enforced in code. |
| **No confidence signalling** | Reported success on tasks that actually failed. | **Mechanism 1 (Unchecked Output):** Returned observations were bad or unverified by deterministic checks. |

**Key Engineering Takeaways**

* **Symptoms vs. Mechanisms:** Evaluators report symptoms ("tunnel vision" or "hallucinations"), but developers cannot fix a symptom directly. You must fix the underlying layer—filtering tool observations, capping loop iterations, or verifying claims in code.
* **Greenfield vs. Brownfield Gap:** Devin completed **2 of 8 greenfield tasks** but **0 of 8 brownfield tasks**. Autonomous agents struggle significantly when dropped into existing, complex codebases.
* **The Institutional Knowledge Bottleneck:** An agent's effectiveness is strictly capped by how much architectural context and institutional knowledge is explicitly written down. Unwritten conventions lead directly to agent failure.

In **Class 4 (Capsule 3)** of the course, **Agent Economics & The Case** addresses the financial and strategic trade-offs of deploying autonomous AI agents, shifting focus from single-call prompt costs to multi-step loop economics.

**The Quadratic Cost Curve**
Agent execution loops are stateless, meaning the entire history of previous turns and tool observations must be re-sent on every new turn.

* **Input Formula**: For $T$ turns with a base prompt $B$ and added observation tokens $D$ per turn, total input tokens grow quadratically: $\text{Input Tokens} \approx B \cdot T + \frac{D \cdot T^2}{2}$.


* **Impact**: Doubling turns from 8 to 16 does not double costs; it nearly triples input tokens (from 16,400 to 52,000) and cost (from US$0.0612 to US$0.1800).



**Four Cost Optimization Levers**

* **Fewer Turns ($T$)**: Narrowing tasks or providing better tools to remove turns entirely.


* **Thinner Observations ($D$)**: Reducing returned tool data, which pays dividends on every subsequent turn.


* **Prompt Caching**: Discounts the re-sent unchanged prefix (~2.4× savings on an 8-turn run).


* **Context Compaction**: Caps quadratic growth into linear growth via periodic summarization.



**Product Pricing & Subscription Envelopes**

* **Per-Seat vs. Per-Work Pricing**: Agent costs scale with steps executed, making flat per-seat subscriptions risky without usage caps. Usage caps prevent heavy users at the 95th percentile from creating unbounded liabilities.


* **Model Selection**: Multi-step agents prioritize fast, lightweight models because per-step latency and token costs dominate overall task performance.



**The Decision Test & Pricing Equation**
Evaluating whether an agent loop is financially viable requires adjusting for failures:


$$\text{Cost per Useful Output} = \frac{\text{Cost per Run}}{\text{Success Rate}}$$


Because failed runs are billed in full, a 70% success rate increases the effective cost per completed output by over 42%.

**The HBS Strategy Case: Anthropic**
The case study (*"Anthropic's Next Step: From LLM to Agents?"*) examines Anthropic's position in late 2025:

* **Market Position**: Holding a 32% enterprise model share, US$3B ARR, and a US$183B valuation.


* **Strategic Dilemma**: Balancing its Public Benefit Corporation charter and safety-first identity against faster-moving competitors (OpenAI, Google, Microsoft) shipping commercial agent frameworks.

The base prompt ($B$) is directly proportional to the number of tools because an LLM agent requires the complete definition, parameter schema, and description of every available tool to be injected into its baseline context.

* **Tool Schemas Live in $B$**: For an agent to know what actions it can take, the prompt must explicitly list each tool's name, function description, parameter types, and JSON schema.
* **Per-Tool Token Overhead**: Every tool added consumes a fixed token payload (typically 100 to 300+ tokens per schema). If $N$ is the number of tools, $B$ scales linearly as $B \approx B_{\text{system}} + (N \cdot \text{Tokens}_{\text{tool}})$. Loading 50 tools instead of 5 bloats $B$ by thousands of tokens.
* **Multiplicative Cost Across Turns**: In the agent token equation ($\text{Input Tokens} \approx B \cdot T + \frac{D \cdot T^2}{2}$), $B$ is re-sent on every single turn $T$. Carrying 45 unused tool schemas inflates $B$ on turn 1 and multiplies that wasted token cost across all $T$ steps in the loop.

$T$ represents the **number of turns** (the count of loop iterations executed by the agent), not the token count.

* **$T$ (Number of Turns)**: The total number of steps or iterations the agent loop takes (e.g., 1, 2, 4, 8, or 16 turns).
* **$B$ (Base Prompt)**: The baseline size in **tokens** of the initial prompt (system instructions + tool schemas).
* **$D$ (Delta Tokens)**: The **tokens** added per turn from tool observations and intermediate outputs.
* **Input Tokens**: The total combined **tokens** sent across the entire run, calculated as $\text{Input Tokens} \approx B \cdot T + \frac{D \cdot T^2}{2}$.

Because $T$ is squared in the formula ($\frac{D \cdot T^2}{2}$), increasing the number of turns ($T$) causes the total input token count—and therefore the cost—to scale quadratically rather than linearly.

$$\text{Input Tokens} \approx B \cdot T + \frac{D \cdot T^2}{2}$$

This equation governs total input token consumption across a stateless agent loop, where $B$ is the base prompt (system rules and tool schemas), $D$ is the delta observation tokens added per turn, and $T$ is the number of executed turns. Backtracking down the pattern ladder shows how architectural decisions directly manipulate these variables:

**1. Autonomous ReAct Loop (Dynamic Reasoning)**

* **Equation Profile**: High $B$, variable $T$, compounding $D$.
* **Design**: The agent dynamically cycles through Thought $\rightarrow$ Action $\rightarrow$ Observation. Because context is re-sent every turn, every prior observation $D$ is re-billed on all subsequent turns, driving quadratic token growth ($\frac{D \cdot T^2}{2}$).
* **Economics**: Highest cost and failure risk; requires hard step caps on $T$ to prevent unbounded usage.

**2. Evaluator-Optimizer Loop (Iterative Refinement)**

* **Equation Profile**: Strictly capped $T$ (e.g., $T \le 3$), static $B$, moderate $D$.
* **Design**: A generator model creates an output and an evaluator checks it, looping until quality criteria are met.
* **Economics**: Bounds the quadratic term by limiting maximum turns, trading predictable token burn for higher output accuracy.

**3. Orchestrator-Workers (Parallel Sub-Agents)**

* **Equation Profile**: Replaces one large $T$ with $N$ parallel sub-runs ($T_i$), using targeted worker base prompts ($B_i$).
* **Design**: A central router breaks complex tasks into sub-tasks and delegates them to specialized worker prompts.
* **Economics**: Eliminates $T^2$ explosion by isolating loop contexts and shrinking $B_i$ (workers only receive the specific tool schemas they need rather than the full tool suite).

**4. Prompt Chaining & Routing Workflows (Deterministic Sequences)**

* **Equation Profile**: Fixed step count $k$; $D = 0$ across turns; linear cost $\sum_{i=1}^{k} B_i$.
* **Design**: Hardcoded, step-by-step pipelines where the output of step $i$ feeds directly into step $i+1$.
* **Economics**: Removes quadratic growth entirely, yielding deterministic costs and predictable latency.

**5. Single Augmented Call (RAG / Direct Function Call)**

* **Equation Profile**: $T = 1$, $D = 0$, Total Input Tokens $= B$.
* **Design**: A single prompt call with context or basic schema injection.
* **Economics**: Represents the economic floor (1.0× baseline cost) against which any multi-turn agent loop must prove its ROI.

Preserving the seam between the teaching case and the course scaffold is the strongest structural framing choice for your presentation. It prevents your analysis from collapsing into a standard HBS summary by cleanly separating **empirical case observations** (what Anthropic faced in late 2025) from **underlying engineering mechanisms** (why agent loops behave the way they do).

**Structuring the Core Arguments**
Connecting the presentation spine directly to your course readings transforms open-ended strategy questions into a mechanically sound position:

* **Q1: ARR vs. Burn Rate (Financial Mechanics)**: Pair Anthropic's US$3B ARR and cash burn metrics directly with Reading 2’s quadratic input token formula ($\text{Input} \approx B \cdot T + \frac{D \cdot T^2}{2}$) and Reading 4’s Pareto 95th-percentile cost distribution. This proves that compute costs do not merely scale linearly with user acquisition—they compound quadratically as workloads transition from single calls to multi-turn agent loops.
* **Q2: Forecast vs. Friction (Architectural Gaps)**: Use your mapping of the case's five agent components against LeCun’s six modules. Identifying the two structural omissions—the **World Model** and an **Explicit Cost Module**—explains why adoption lags behind enterprise hype: without an internal world model to simulate environment state changes, agents hit a governance cliff where safety requires human confirmation loops.

**Bridging the Data Cutoff to Reality**
Grounding the final section in Anthropic's post-September 2025 moves resolves the case's open closing question. Rather than choosing between a horizontal model platform and vertical specialization, Anthropic executed both. Bringing Stainless in-house captured SDK generation and MCP server infrastructure to control agent connectivity, while standing up an in-house custom silicon team under Amir Salek directly addresses compute cost and supply chain bottlenecks at the hardware layer.

**Audit Rigor in Q&A**
Your audit of third-party responses exposes the exact conceptual flattening the course aims to correct: conflating context-window pressure with latency, or treating Agentic RAG as a parallel alternative to agents rather than a constrained subset. Positioning these distinctions clearly ensures you can defend your technical choices under pushback.

Which specific slide or scenario would you like to stress-test next: defending the $T^2/2$ token compounding against model price drops, or unpacking how the approval step in Exhibit 4 creates a latency bottleneck?

## PE6201 Class 5 (C0): Strategic & Technical Notes

### 1. The Core Pivot: From Technical Feasibility to Business Viability

Class 5 transitions from the mechanics of building an agent (Class 4) to the strategic economics of deploying one.

- **Agentic Mechanics & Cost:** The thought $\rightarrow$ action $\rightarrow$ observation loop means the observation context must be re-sent every turn. Consequently, cost grows faster than the turns, modeled by the formula $B \times T + \frac{1}{2}DT^2$.
- **Compounding Errors:** Because errors compound across steps, the critical business metric is the **cost per *successful* task**, rather than the raw price per token.
- **The Governance Cliff:** Executing the "first write" action changes an agent from a passive reader to an active operational risk requiring strict governance.
- **Data Readiness:** System readiness is entirely dictated by its weakest link, evaluated via five data-readiness tests.
- **The Ultimate Decision:** While Class 4 priced a single agent, Class 5 determines if a specific use case economically justifies building an agent at all.

### 2. Market Dynamics: AI Economics (August 2026)

| **Market Trend** | **Technical Impact** | **Business Impact** |
| --- | --- | --- |
| **Plummeting Frontier Costs** | Grok 4.6 launched in August 2026 at just $\$2$ input / $\$6$ output per million tokens, heavily undercutting standard $\$5$/$\$25$ frontier tiers. | A fixed AI capability gets approximately $10\times$ cheaper per year, making previously expensive architectures economically viable faster than expected. |
| **The Performance Ceiling** | The top-performing model ($\approx \$10$/million tokens) captured only 6% of volume and 11.4% of spend on the Ramp platform post-launch. | Buyers refuse to pay top-tier premiums; claiming "we used the best model" is no longer a strategic advantage, it is purely a cost. |
| **The Enterprise Spend Paradox** | The median US business AI spend per employee is roughly equivalent to a single streaming subscription. | Companies are universally renting the same models but struggling to find high-value, scalable workflows to justify larger investments. |

### 3. Compute as a Tradable Asset vs. Proprietary Moats

- **Fungible Infrastructure (Rentable):** NVIDIA announced a $\$500$ billion financing platform because raw compute is fungible and transferable. It serves as financial collateral because it holds value to other operators.
- **Proprietary Operations (Un-financeable):** Conversely, internal data pipelines, evaluation harnesses, and legacy system integrations hold zero value to external parties. Nobody will lend against them, meaning these custom components remain the true, fixed-cost bottlenecks that dictate your unit economics.

### 4. Integration of Course Pre-Reads

- **Iansiti & Lakhani (Ant Group Case):** Establishes the AI factory, network effects, and the necessary transition to a software-driven operating model.
- **McKinsey & Unit Economics:** Differentiates between raw token costs and the true "cost-to-serve", feeding directly into the Class 5 financial calculator.
- **GraphCast:** Highlights the specific data and architectural prerequisites required to deploy AI in specialized vertical markets before it is even possible.

### 5. Administrative Actions & Re-Routing

- **Guest Lecture Re-Routing:** The scheduled guest speaker canceled, but the six planned practitioner topics (e.g., the kill story, the intake screen, pilot to product, and cost-to-serve) were absorbed directly into the instructor's core lectures rather than being cut.
- **Assignment 2 (A2):** Team declarations are strictly due by **Friday, September 4, 2026 at 23:59 SGT** via a file in the submission folder, not via email.

**Core Objective of AI Implementation**

The primary goal is to determine which AI use cases are actually worth pursuing. A use case's priority must be defended across three pillars:

- **Business ROI:** What the use case actually buys or saves.
- **Technical Data Readiness:** Whether existing data infrastructure can reliably feed the system.
- **Operating Model:** Whether the organization is structurally capable of collecting and utilizing the output.

**The Value Gap (Business Perspective)**

AI adoption is now considered table stakes, but material financial value remains incredibly rare.

- **High Adoption, Low Impact:** While **88% of organizations use AI** (and 79% use Generative AI), only **39% report any EBIT (Earnings Before Interest and Taxes) impact**.
- **The Materiality Ceiling:** Of that 39%, most see less than a 5% impact. Only **~6% of organizations clear a 5% EBIT impact**.
- **The Differentiator:** The strongest predictor of high performance is **Process Redesign**. 55% of high performers fundamentally redesign their workflows to accommodate AI, compared to only 20% of average organizations.

**The Three Implementation Leaks (Technical & Operational Perspective)**

Organizations fail to convert pilot adoption into scalable profit due to three specific failures, which they erroneously try to fix by simply buying more tools:

- **Leak 1: Plumbing (88% adoption → 33% scaling):** Pilots often succeed using highly curated, hand-assembled data extracts. When moved to production, they fail because there is no automated, owned daily data path (pipeline) to sustain the model.
- **Leak 2: Selection (33% scaling → 39% EBIT impact):** The AI system works perfectly from a technical standpoint but fundamentally automates a process that was never expensive to begin with, resulting in negligible financial return.
- **Leak 3: Measurement (39% EBIT → 6% material impact):** The business failed to capture a baseline metric before implementation. Because finance cannot attribute the cost savings or revenue generation to the AI, they cannot officially book the impact.

**Evaluating AI Statistics**

Flashy statistics regarding AI failure rates often lack technical context. For example, a headline claiming "95% of AI pilots return nothing" is fundamentally undermined by the fact that **~80% of the sample never actually piloted a custom system**. Scrutinizing the baseline data and operational reality is required before taking AI failure (or success) metrics at face value.

## PE6201 Class 5 — Capsule 2 (C2): What Does It Actually Cost?

Capsule 2 (C2) shifts the strategic evaluation of AI from **price per token** to **cost per successful task** and **total cost-to-serve (CTS)**. It exposes why raw token price drops do not automatically lower enterprise AI bills and provides the complete mathematical framework to price, evaluate, and defend AI agent architectures.

---

## 1. Business & Strategic Foundations of C2

### The Paradox of Falling Token Prices

- **Market Dynamics:** Token prices for frontier models drop by roughly $10\times$ per year (e.g., Grok 4.6 launched at $\$2.00$ in / $\$6.00$ out per million tokens compared to standard $\$5.00$ / $\$25.00$ tiers).
- **Enterprise Spend Reality:** Despite a $1,000\times$ fall in token prices over three years, enterprise AI bills have **stayed flat or increased**.
- **The Jevons Paradox in AI:** As inference becomes cheaper, organizations increase context window sizes, build multi-turn agentic loops, add tool calls, and run automated retry harnesses. Consumption scales faster than token price declines.
- **Commodity vs. Premium:** High-performing models taking only 6% of token volume prove that using top-tier models for basic tasks is an unrecoverable operational cost rather than a strategy.

### The Bessemer AI Cost-to-Serve (CTS) Stack

Unlike traditional software-as-a-service (SaaS) where marginal delivery cost is near zero, AI unit economics require accounting for four distinct cost layers:

1. **Model Inference Costs:** Compute and API expenses for all input, output, and tool-call tokens.
2. **Human-in-the-Loop (HITL) Support:** Cost of human intervention when the model fails, hallucinates, or falls below confidence thresholds.
3. **Customer Success Overhead:** High-touch onboarding and workflow integration required to maintain active deployment.
4. **Sales Allocation / GTM Time:** Sales engineering and proof-of-concept (PoC) customization costs amortized over customer lifetime.

---

## 2. Technical Mechanics of AI Agent Costs

### Context Accumulation in Agent Loops

In single-call LLM applications, input tokens are fixed. In agentic workflows (Thought $\rightarrow$ Action $\rightarrow$ Observation), **the observation context is re-sent on every subsequent turn**.

```
Turn 1: [System Prompt + User Query]                          --> Output Action 1
Turn 2: [System Prompt + User Query + Action 1 + Obs 1]       --> Output Action 2
Turn 3: [System Prompt + User Query + ... + Obs 2]            --> Output Action 3
```

This structural requirement causes input token volume to grow quadratically ($\mathcal{O}(T^2)$) with the number of turns $T$.

### Compounding Error Cascades

If an agent executes a sequence of $T$ independent steps, each with a step-level success probability $p$:

$$\text{Overall System Success Rate } (S) = p^T$$

As step count $T$ increases, overall reliability drops exponentially, driving up retry frequency and human escalation costs.

---

## 3. Mathematical Framework & Explicit Derivations

### A. Single-Turn Call Token Cost Formula

Let:

- $P_{in}$ = Price per $1,000,000$ input tokens (USD)
- $P_{out}$ = Price per $1,000,000$ output tokens (USD)
- $N_{in}$ = Number of input tokens
- $N_{out}$ = Number of output tokens

$$\text{Cost}_{\text{call}} = \left( N_{in} \times \frac{P_{in}}{1,000,000} \right) + \left( N_{out} \times \frac{P_{out}}{1,000,000} \right)$$

#### Worked Example:

For $N_{in} = 1,500$, $N_{out} = 400$, $P_{in} = \$0.10$, $P_{out} = \$0.40$:

$$\text{Cost}_{\text{call}} = \left( 1,500 \times \frac{0.10}{10^6} \right) + \left( 400 \times \frac{0.40}{10^6} \right) = \$0.00015 + \$0.00016 = \$0.00031 \text{ per task}$$

For $50,000$ monthly tasks: $50,000 \times \$0.00031 = \$15.50 \text{ / month}$.

---

### B. Multi-Turn Context Growth Formula ($B \cdot T + \frac{1}{2} D \cdot T^2$)

Let:

- $T$ = Total number of agent turns
- $B$ = Base input tokens (System prompt + initial user query)
- $D$ = Average new tokens added per turn (Agent thought + tool output + environment observation)

#### Derivation of Total Cumulative Input Tokens ($S_{in}$):

At turn $t$ (where $t = 1, 2, \dots, T$):

$$N_{in}(t) = B + (t - 1) \cdot D$$

Summing across all $T$ turns:

$$S_{in}(T) = \sum_{t=1}^{T} \left[ B + (t - 1) \cdot D \right] = T \cdot B + D \sum_{t=1}^{T} (t - 1)$$

Using the arithmetic series sum $\sum_{k=0}^{T-1} k = \frac{(T - 1) T}{2} = \frac{T^2 - T}{2}$:

$$S_{in}(T) = B \cdot T + \frac{1}{2} D \cdot T^2 - \frac{1}{2} D \cdot T$$

For large $T$ or when $D \cdot T^2 \gg D \cdot T$, this simplifies to the C2 core formula:

$$S_{in}(T) \approx B \cdot T + \frac{1}{2} D \cdot T^2$$

#### Economic Implication:

- Doubling turn count $T$ quadruples the quadratic context term $\frac{1}{2} D \cdot T^2$.
- Controlling agent depth $T$ is mathematically more impactful for cost reduction than optimizing prompt length $B$.

---

### C. Cost per Successful Task ($C_{\text{success}}$) & The Ranking Inversion

A raw LLM call cost ($C_{\text{agent}}$) is meaningless without accounting for model reliability ($S$) and human fallback costs ($C_{\text{human}}$).

Let:

- $S$ = Probability of agent successfully resolving the task without error ($0 < S \le 1$).
- $1 - S$ = Failure / escalation rate.
- $C_{\text{agent}}$ = Direct token inference cost of one agent run.
- $C_{\text{human}}$ = Cost of human labor to review, correct, or execute the failed task.

#### Formula for Total Effective Cost per Completed Task:

$$C_{\text{success}} = C_{\text{agent}} + (1 - S) \cdot C_{\text{human}}$$

#### Mathematical Proof of the Ranking Inversion:

Consider two model options for a 50,000 ticket/month support system where human remediation cost $C_{\text{human}} = \$5.00$ per ticket:

- **Option A (Cheap Tier Model):**
    - Token Cost ($C_{\text{agent, A}}$) = $\$0.002$
    - Success Rate ($S_A$) = $80\%$ ($0.80$)
    - Failure Rate ($1 - S_A$) = $20\%$ ($0.20$)
    - $C_{\text{success, A}} = \$0.002 + (0.20 \times \$5.00) = \$0.002 + \$1.00 = \mathbf{\$1.002 \text{ per task}}$
    - **Total Monthly Cost (50k tasks):** $50,000 \times \$1.002 = \mathbf{\$50,100}$
- **Option B (Frontier Model):**
    - Token Cost ($C_{\text{agent, B}}$) = $\$0.05$ ($25\times$ more expensive token cost)
    - Success Rate ($S_B$) = $98\%$ ($0.98$)
    - Failure Rate ($1 - S_B$) = $2\%$ ($0.02$)
    - $C_{\text{success, B}} = \$0.05 + (0.02 \times \$5.00) = \$0.05 + \$0.10 = \mathbf{\$0.15 \text{ per task}}$
    - **Total Monthly Cost (50k tasks):** $50,000 \times \$0.15 = \mathbf{\$7,500}$

> **Key Takeaway:** Despite Option B having a $2,400\%$ higher token price, **Option B is $85\%$ cheaper overall** because human labor dominates failure costs.
> 

---

### D. Break-Even Success Rate ($S_{\text{break-even}}$)

To determine if deploying an AI agent is financially viable compared to a $100\%$ human execution process ($C_{\text{human}}$):

$$C_{\text{success}} \le C_{\text{human}}$$

$$C_{\text{agent}} + (1 - S) \cdot C_{\text{human}} \le C_{\text{human}}$$

$$C_{\text{agent}} \le S \cdot C_{\text{human}}$$

$$S_{\text{break-even}} = \frac{C_{\text{agent}}}{C_{\text{human}}}$$

If the agent's actual success rate $S < S_{\text{break-even}}$, running the AI assistant combined with human backup is **more expensive than using no AI at all**.

---

## 4. Architectural Comparison Matrix

| **Architectural Design** | **Token Growth Dynamics** | **Cost Driver** | **Best For** | **Failure Risk** |
| --- | --- | --- | --- | --- |
| **v1: Single Call** | Linear: $B_{\text{in}} + N_{\text{out}}$
 | Input/Output token counts | Simple triage, classification, routing | High hallucination on complex tasks |
| **v2: Multi-Turn Chain** | Quadratic: $B \cdot T + \frac{1}{2} D \cdot T^2$
 | Turn depth $T$
 | Multi-step research, API tool invocation | Infinite loops, compounding drift |
| **v3: Router + Model Cascading** | Tiered: $S \cdot C_{\text{cheap}} + (1-S) \cdot C_{\text{frontier}}$ | Router accuracy & tier differential | High-volume mixed-complexity workflows | Router misclassification overhead |
| **v4: Human-in-the-Loop (HITL)** | Mixed: $C_{\text{agent}} + (1-S) \cdot C_{\text{human}}$ | Human hourly wage / intervention time | Mission-critical, high-compliance tasks | Context handoff friction & fatigue |

---

## 5. Practical Application to Course Deliverables

### For Assignment 2 (A2) Applied AI System Calculator:

1. **Never evaluate models on token price alone:** Build a dynamic calculator that takes $P_{in}, P_{out}, B, D, T, S,$ and $C_{\text{human}}$ as inputs.
2. **Model multi-turn context correctly:** Use $B \cdot T + \frac{1}{2} D \cdot T^2$ for any multi-step agent or loop.
3. **Include Human-in-the-Loop cost:** Explicitly factor in the dollar cost of human intervention for the $(1 - S)$ failure fraction.

## PE6201 Class 5 — Capsule 3 (C3): Two Archetypes, AI Strategy, and the Ant Group Case

Capsule 3 (C3) synthesizes technical system architecture with corporate strategy. It addresses a fundamental market question: **When underlying foundational models become commoditized, where does sustainable competitive advantage live?**

---

## 1. The Strategic Taxonomy: Two AI Deployment Archetypes

Organizations pursuing enterprise AI fall into two distinct architectural and economic archetypes:

```
┌─────────────────────────────────────────────────────────────────┐
│                    ARCHETYPE 1: HORIZONTAL                     │
│                  Model Integrator (Rent & Plug)                 │
├─────────────────────────────────────────────────────────────────┤
│ • Rent third-party LLM APIs (OpenAI, Anthropic, xAI)            │
│ • Low upfront CapEx; pure variable OpEx                         │
│ • Moat: Workflow integration, UI/UX, domain prompt context      │
│ • Strategic Vulnerability: Zero model-level differentiation     │
└─────────────────────────────────────────────────────────────────┘
                                vs
┌─────────────────────────────────────────────────────────────────┐
│                     ARCHETYPE 2: VERTICAL                      │
│                  AI Factory Engine (Build & Scale)              │
├─────────────────────────────────────────────────────────────────┤
│ • Custom data pipelines, fine-tuned/proprietary models          │
│ • High upfront CapEx (R&D, infrastructure, eval harnesses)      │
│ • Moat: Data network effects, automated closed-loop operating model│
│ • Strategic Advantage: Near-zero marginal cost of delivery ($MC \to 0$)│
└─────────────────────────────────────────────────────────────────┘
```

### Strategic Comparison

| **Axis** | **Archetype 1: Horizontal (Model Integrator)** | **Archetype 2: Vertical (AI Factory Engine)** |
| --- | --- | --- |
| **Sourcing Strategy** | **Buy / Rent** (API-first) | **Build / Proprietary Architecture** |
| **Cost Structure** | High variable OpEx per API call | High fixed CapEx; near-zero marginal cost per task ($MC \approx \$0$) |
| **Primary Moat** | **Workflow & Judgement:** Deep integration into existing enterprise tools and user habit loop | **Data Network Effects:** Proprietary data feedback loops and specialized algorithms |
| **Operational Scalability** | Scalability bound by API rate limits, token pricing, and context costs | Infinite scale; software decoupled from human headcount constraints |
| **Exemplars** | Enterprise workflow copilots, CRM summarizers | **Ant Group** (Fintech), **GraphCast** (Weather Forecasting) |

> **Key Rule for Strategy:** *"When the model is a commodity, the judgement is the product."* If every competitor rents the exact same LLM API, competitive moat cannot exist within the model itself. It exists entirely in the proprietary data pipeline, evaluation harness, and workflow integration surrounding the model.
> 

---

## 2. Technical Architecture of the AI Factory (Iansiti & Lakhani)

An **AI Factory** is an automated operational engine that replaces traditional human-driven business processes with integrated software components.

```
┌─────────────────────────────────────────────────────────────────┐
│                     THE AI FACTORY ENGINE                       │
│                                                                 │
│  [ Real-Time Data Ingestion ] ──► [ Feature Pipeline & Store ]  │
│                                                 │               │
│                                                 ▼               │
│  [ Automated Decisioning ] ◄─── [ Algorithmic Inference Model ] │
│             │                                                   │
│             ▼                                                   │
│  [ User Outcome / Action ] ────► [ Feedback Loop / Retraining ] │
└─────────────────────────────────────────────────────────────────┘
```

### The Four Core Pillars

1. **Data Pipeline:** Automated, continuous ingestion, cleaning, and transformation of operational data into structured feature stores in real time.
2. **Algorithmic Engine:** Machine learning models that execute core business inferences (e.g., credit risk scoring, fraud detection, supply chain routing) without manual human intervention.
3. **Experimentation Platform (Eval Harness & A/B Testing):** Infrastructure that continuously tests model iterations, prompt strategies, and guardrail thresholds against baseline metrics.
4. **Infrastructure & Guardrail Layer:** Scalable compute, security monitoring, and deterministic policy guardrails to enforce governance before executing actions.

---

## 3. Case Exhibit: Ant Group & The "3-1-0" Operating Model

Ant Group serves as the primary exhibit for the AI Factory framework, illustrating how digitizing the core operating architecture transforms business economics.

### The "3-1-0" Loan Approval Process

- **3 Minutes:** Time required for a user to complete an online loan application.
- **1 Second:** Time required for the AI Factory to evaluate thousands of credit variables and render an approval decision.
- **0 Human Interventions:** Total human manual reviews involved in the approval loop.

### Linear vs. Exponential Operating Decoupling

```
Traditional Operating Model (Human-Centric):
Cost / Headcount ─────────────────────────► Scales Linearly with Loan Volume (Scale Bottleneck)

AI Factory Operating Model (Ant Group):
Cost / Headcount ──────────────┬──────────► Fixed Base Cost
                               └──────────► Loan Volume Scales Exponentially (MC ≈ 0)
```

- **Traditional Banking:** Scaling loan volume requires linear increases in underwriting staff, risk managers, and branch infrastructure ($Cost \propto Volume$).
- **Ant Group AI Factory:** Upfront capital cost is invested in software architecture. Once deployed, serving customer $N+1$ incurs negligible marginal compute cost, completely decoupling business scale from labor headcount.

---

## 4. Mathematical Standpoint & Quantitative Models

### A. Cost Decoupling & Unit Economics Function

Let total operational cost $C(Q)$ be a function of transaction volume $Q$:

- **Traditional Manual Operating Model:**
    
    $$C_{\text{trad}}(Q) = F_{\text{fixed}} + c_{\text{human}} \cdot Q$$
    
    where $c_{\text{human}}$ is the labor cost per manual task evaluation.
    
- **AI Factory Operating Model:**
    
    $$C_{\text{AIFactory}}(Q) = F_{\text{CapEx}} + c_{\text{infer}} \cdot Q$$
    
    where $F_{\text{CapEx}} \gg F_{\text{fixed}}$ (high upfront software/infrastructure development), but $c_{\text{infer}} \ll c_{\text{human}}$ (inference cost per query is pennies or fractions of a cent).
    

#### Average Cost per Unit ($AC(Q)$):

$$AC_{\text{AIFactory}}(Q) = \frac{C_{\text{AIFactory}}(Q)}{Q} = \frac{F_{\text{CapEx}}}{Q} + c_{\text{infer}}$$

$$\lim_{Q \to \infty} AC_{\text{AIFactory}}(Q) = c_{\text{infer}} \approx \$0$$

**Economic Insight:** As volume $Q$ grows large, average unit cost approaches near-zero inference cost $c_{\text{infer}}$, yielding an unassailable pricing and margin advantage over traditional manual competitors.

---

### B. Data Network Effects & Mathematical Feedback Loop

Unlike traditional user network effects (Metcalfe’s Law: $V \propto N^2$), **Data Network Effects** create an algorithmic feedback loop where scale improves product quality:

```
[ More Users ] ──► [ More Data Ingested ] ──► [ Better Model Accuracy ] ──► [ Superior UX / Lower Price ] ──► [ More Users ]
```

#### Formulation:

Let algorithm accuracy $A(D)$ depend on cumulative historical training data $D$:

$$A(D) = A_{\max} \left( 1 - e^{-\alpha D} \right)$$

User acquisition rate $\frac{dU}{dt}$ scales with model performance $A(D)$ and price efficiency:

$$\frac{dU}{dt} = \beta \cdot A(D)^{\gamma}$$

Data growth rate $\frac{dD}{dt}$ is directly proportional to active user volume $U$:

$$\frac{dD}{dt} = \delta \cdot U$$

#### Diminishing Marginal Returns of Raw Data:

Taking the derivative of accuracy $A$ with respect to data $D$:

$$\frac{dA}{dD} = \alpha A_{\max} e^{-\alpha D}$$

$$\lim_{D \to \infty} \frac{dA}{dD} = 0$$

**Strategic Implication:** Raw data volume exhibits **diminishing marginal returns**. Therefore, data velocity (freshness) and proprietary domain context—rather than sheer static dataset size—define long-term defensibility.

---

### C. Systemic Risk & The Governance Cliff

Automating decisions completely ($0$ human intervention) shifts risk profiles from independent human errors to correlated system failure modes.

#### Risk Exposure Formula:

$$\text{Expected Financial Loss } (\mathcal{L}) = Q \cdot P(\text{Failure}) \cdot \text{Severity per Failure}$$

- **Human System:** $P(\text{Failure})$ is moderate, but errors are uncorrelated across individual loan officers. $Q$ is limited by human speed.
- **AI Factory:** $P(\text{Failure})$ is low under standard conditions, but errors are $100\%$ correlated if an unhandled edge case or data drift occurs. Because $Q$ executes at supercomputer speeds ($1$ second per task), an unmitigated error can cause massive financial loss before detection.

> **The Governance Cliff:** The precise point where an agent transitions from passive reading/recommendation to executing active writes/financial commitments. Passing the governance cliff requires hard deterministic guardrails surrounding the probabilistic model.
> 

---

## 5. Practical Integration into Course Deliverables

### For Assignment 2 (A2) Applied AI System (Due Fri 4 Sep team decl. / Sun 13 Sep final)

1. **Explicitly Frame Your Archetype:** Declare whether your system acts as a Horizontal Integration or a specialized Vertical Engine.
2. **Defend Why an Agent is Necessary:** Demonstrate how automating the workflow removes a human labor bottleneck rather than simply adding system complexity.
3. **Map the Governance Cliff & Guardrails:** Design explicit validation checks before your agent calls external APIs or performs database writes.
4. **Build a 30–50 Case Evaluation Set:** Measure model accuracy, failure rates, and loop conditions across a structured test harness.
