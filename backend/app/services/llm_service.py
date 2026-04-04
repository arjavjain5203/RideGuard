import os

# Try to configure Gemini API. If no key, fallback to mock.
api_key = os.environ.get("GEMINI_API_KEY")
genai = None
if api_key:
    try:
        import google.generativeai as google_genai  # pragma: no cover - optional dependency
    except ImportError:
        google_genai = None

    if google_genai is not None:
        google_genai.configure(api_key=api_key)
        genai = google_genai

def call_gemini(prompt: str) -> str:
    """Helper to call Gemini or return mock response if key is missing."""
    if not api_key or genai is None:
        return f"[MOCK AI RESPONSE]: {prompt[:50]}..."
    
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI Error: {str(e)}"

def explain_claim(trigger_type: str, hours: float, payout: float, urts: int) -> str:
    prompt = f"Write a 1-sentence explanation to a gig worker explaining why they received Rs {payout} due to {trigger_type} for {hours} hours. Their Trust Score is {urts}."
    return call_gemini(prompt)

def explain_risk(zone: str, risk_score: float) -> str:
    prompt = f"Write a 1-sentence explanation of why the risk multiplier for {zone} is {risk_score}."
    return call_gemini(prompt)

def explain_fraud(signals: dict, penalty: int) -> str:
    prompt = f"Write a brief explanation of why the rider's score was penalized by {penalty} points based on these signals: {signals}. Be polite but firm."
    return call_gemini(prompt)

def generate_admin_insights(zone_data: str) -> str:
    prompt = f"Analyze this zone data and provide a 1-sentence insight for the admin: {zone_data}"
    return call_gemini(prompt)
