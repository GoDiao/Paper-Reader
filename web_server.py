#!/usr/bin/env python
"""
Web Server Entry Point for Paper Reader

Run with: python web_server.py
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    import uvicorn
    from backend.app import app
    
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   📚 Paper Reader Web Interface                              ║
║                                                              ║
║   Server running at: http://localhost:{port}                  ║
║                                                              ║
║   Features:                                                  ║
║   • Upload PDF papers                                        ║
║   • AI-powered hierarchical analysis (1+3+1 agents)          ║
║   • Bilingual reports (English + Chinese)                    ║
║   • Export to PDF/DOCX/Markdown                              ║
║   • Chat with AI about the paper                             ║
║   • Full analysis history                                    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    uvicorn.run(
        "backend.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()
