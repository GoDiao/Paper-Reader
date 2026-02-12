from generators.report_generator import ReportGenerator

def test_fallback():
    generator = ReportGenerator()
    
    # Mock image map with internal keys (fig_X) and paths
    image_map = {
        "fig_1": "path/to/Figure_1.jpg",
        "fig_2": "path/to/Figure_2.jpg"
    }
    
    # Text with mismatched ID (Figure 2 instead of fig_2)
    text = "Here is <INSERT_FIGURE: Figure 2>"
    
    result = generator._embed_images(text, image_map)
    
    print(f"Input: {text}")
    print(f"Output: {result}")
    
    if "Figure_2.jpg" in result:
        print("SUCCESS: Fallback worked!")
    else:
        print("FAILURE: Fallback failed.")

if __name__ == "__main__":
    test_fallback()
