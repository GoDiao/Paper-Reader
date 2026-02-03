from agents.hierarchical_orchestrator import HierarchicalOrchestrator
from rich.console import Console

console = Console()

def test_extraction():
    orchestrator = HierarchicalOrchestrator(api_key="mock")
    
    # Mock content
    content = """
# Title

## 1. Introduction
Intro text.

## 2. Method
Method text.

### 2.1 Submethod
Submethod text.

## 3. Experiments
Experiment text.

### 3.1 Setup
Setup text.

## 4. Conclusion
Conclusion text.

# References
Ref text.

## Appendix
Appendix text.
"""

    print("--- Test 1: Extract 'Method' (should include Submethod) ---")
    extracted = orchestrator._extract_sections(content, ["Method"])
    print(f"DTO: len={len(extracted)}")
    print(f"Preview:\n{extracted}\n")
    
    if "Submethod text" in extracted and "Experiment text" not in extracted:
         print("✅ PASS: Method includes submethod and stops at Experiments")
    else:
         print("❌ FAIL: Method extraction incorrect")

    print("\n--- Test 2: Extract 'Experiments' (should run to end) ---")
    extracted = orchestrator._extract_sections(content, ["Experiments"])
    print(f"Preview:\n{extracted}\n")
    
    if "Experiment text" in extracted and "Conclusion text" in extracted and "Ref text" in extracted and "Appendix text" in extracted:
        print("✅ PASS: Experiments runs to end")
    else:
        print("❌ FAIL: Experiments did not run to end")

if __name__ == "__main__":
    test_extraction()
