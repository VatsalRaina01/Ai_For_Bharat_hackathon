"""Local development server — run without AWS."""
import uvicorn
from dotenv import load_dotenv

load_dotenv()  # loads .env automatically

if __name__ == "__main__":
    print("🏛️ LokSarthi — Starting local dev server...")
    print("📍 API: http://localhost:8000")
    print("📍 Docs: http://localhost:8000/docs")
    print("📍 Open frontend/index.html in browser")
    print("---")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
