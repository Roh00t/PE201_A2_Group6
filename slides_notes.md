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
