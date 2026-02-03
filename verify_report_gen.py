import sys
from pathlib import Path
from generators import ReportGenerator

def test_report_generator():
    print("Testing ReportGenerator...")
    
    # 1. Setup
    generator = ReportGenerator()
    output_path = Path("test_output/report.md")
    images_dir = Path("test_output/images")
    
    # Mock data
    image_map = {
        "Figure_1": str(images_dir / "fig1.png"),
        "Figure_2": str(images_dir / "fig2.png")
    }
    
    # Input content
    analysis_report = """
# Test Report

This is a test.

<INSERT_FIGURE: Figure_1 - Shows the architecture>

Here is another figure:

<INSERT_FIGURE: Figure_2>

End of report.
"""

    expected_output_snippet_1 = "![Figure_1](images/fig1.png)"
    expected_output_snippet_2 = "![Figure_2](images/fig2.png)"
    
    # 2. Execution
    final_md = generator.generate(
        analysis_report=analysis_report,
        image_map=image_map,
        title="Test Report",
        output_path=output_path,
        images_output_dir=images_dir
    )
    
    # 3. Verification
    print("\n--- Final Markdown ---")
    print(final_md)
    print("----------------------\n")
    
    if expected_output_snippet_1 in final_md and expected_output_snippet_2 in final_md:
        print("✅ SUCCESS: Images embedded correctly.")
    else:
        print("❌ FAILURE: Images not embedded as expected.")
        if expected_output_snippet_1 not in final_md:
            print(f"Missing: {expected_output_snippet_1}")
        if expected_output_snippet_2 not in final_md:
            print(f"Missing: {expected_output_snippet_2}")

if __name__ == "__main__":
    test_report_generator()
