"""
Prompt Templates for Paper Analysis Agents.

Contains prompts for:
1. Architect Agent - Global paper structure analysis
2. Math Deriver Agent - Formula derivation and explanation
"""

# =============================================================================
# Architect Agent Prompt
# =============================================================================

ARCHITECT_PROMPT = """You are a senior research scientist with expertise in analyzing academic papers.
Your task is to thoroughly analyze the following paper and extract structured information.

## Instructions

Please analyze the paper and provide a comprehensive breakdown in the following structure:

### 1. 📚 Background & Motivation (背景与动机)
- What is the broader research area?
- Why is this problem important?
- What are the key challenges in this area?

### 2. 🎯 Research Problem (研究问题)
- What specific problem does this paper address?
- What gaps in existing work does it aim to fill?
- What are the research questions or hypotheses?

### 3. 🔬 Proposed Method (提出的方法)
- Provide a high-level overview of the proposed approach
- What is the key innovation or contribution?
- How does the method work at a conceptual level?
- **IMPORTANT**: Identify all key equations and their equation numbers (e.g., Eq.(1), Eq.(5))
- Mark which figures are most relevant to explaining the method

### 4. 📊 Experiments & Results (实验与结果)
- What datasets or benchmarks were used?
- What are the main experimental settings?
- Summarize the key results and findings
- How does it compare to baselines?
- Which figures/tables show the main results?

### 5. 💡 Conclusions & Implications (结论与启示)
- What are the main takeaways?
- What are the limitations acknowledged by the authors?
- What future work is suggested?

## Output Format

Use Markdown formatting. For figures, use placeholders like:
`<INSERT_FIGURE: Figure 1 - description>`

For equations you want detailed derivation, mark them like:
`<DERIVE: Eq.(X) - brief description>`

---

## Paper Content:

{content}
"""

# =============================================================================
# Math Deriver Agent Prompt
# =============================================================================

MATH_DERIVER_PROMPT = """You are a mathematical expert and researcher specializing in {domain}.
Your task is to provide detailed derivations and explanations for the mathematical content in this paper.

## Instructions

For each equation or mathematical expression:

1. **Variable Definitions**: Define every variable and symbol used
2. **Step-by-Step Derivation**: Show intermediate steps that may be skipped in the paper
3. **Physical/Mathematical Intuition**: Explain WHY this equation makes sense
4. **Connections**: Link to standard algorithms or well-known results if applicable

## Formatting Guidelines

- Use LaTeX for all mathematical expressions: $inline$ or $$block$$
- Number your derivation steps clearly
- Use clear section headers for each equation

## Mathematical Content to Analyze:

{equations}

## Context from Paper:

{context}

---

Please provide detailed derivations now:
"""

# =============================================================================
# Image Description Prompt (for GPT-4V)
# =============================================================================

IMAGE_CAPTION_PROMPT = """Analyze this figure from an academic paper.

Provide:
1. A concise description of what the figure shows (1-2 sentences)
2. Key insights or findings illustrated by this figure
3. Any important numerical values or trends visible

Keep your response brief and focused on the scientific content.
"""

# =============================================================================
# Summary Synthesis Prompt
# =============================================================================

SYNTHESIS_PROMPT = """You are assembling a comprehensive paper analysis report.

Combine the following analysis sections into a cohesive, well-structured Markdown document:

## Global Analysis:
{architect_output}

## Mathematical Derivations:
{math_output}

## Guidelines:
1. Maintain clear section structure with proper headers
2. Integrate the mathematical derivations into the relevant method sections
3. Keep figure placeholders for later replacement
4. Ensure smooth transitions between sections
5. Add a brief "TL;DR" summary at the beginning
6. Format all LaTeX properly

Generate the final comprehensive paper analysis:
"""

# =============================================================================
# Domain Detection Prompt
# =============================================================================

DOMAIN_DETECTION_PROMPT = """Based on the following paper content, identify the primary research domain.

Paper excerpt:
{excerpt}

Choose from these domains or specify a more appropriate one:
- Computer Vision
- Natural Language Processing
- Reinforcement Learning
- Signal Processing
- Optimization
- Deep Learning / Neural Networks
- Robotics
- Other: [specify]

Respond with just the domain name.
"""
