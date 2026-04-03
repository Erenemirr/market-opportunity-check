import os
import json
from groq import Groq
from models.output_models import MarketAnalysisResult
from prompts.market_analysis_prompt import ANALYSIS_SYSTEM_PROMPT

def run_market_analysis(idea: str, country: str, city: str, audience: str, 
                        trends_data: dict, serper_data: dict, reddit_data: dict) -> MarketAnalysisResult:

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or api_key.startswith("your_"):
        raise ValueError("Missing or invalid GROQ_API_KEY string in .env file!")
        
    client = Groq(api_key=api_key)
    
    schema_json = MarketAnalysisResult.model_json_schema()
    system_prompt = ANALYSIS_SYSTEM_PROMPT + f"\n\nCRITICAL DO NOT OUTPUT TEXT. You MUST output ONLY raw valid JSON exactly matching this JSON Schema:\n{json.dumps(schema_json)}"
    
    user_payload = f"""
    IDEA: {idea}
    LOCATION: {city}, {country}
    TARGET AUDIENCE: {audience}
    
    1. TRENDS:\n{json.dumps(trends_data, indent=2)}
    2. WEB & NEWS (SERPER):\n{json.dumps(serper_data, indent=2)}
    3. SOCIAL PAIN POINTS:\n{json.dumps(reddit_data, indent=2)}
    """
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_payload}
            ],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return MarketAnalysisResult.model_validate_json(content)
        
    except Exception as e:
        raise RuntimeError(f"Groq API Call Failed: {str(e)}")


def answer_followup_question(query: str, chat_history: list, report_context: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    client = Groq(api_key=api_key)
    
    messages = [
        {"role": "system", "content": f"You are the VC Agent who just generated this market analysis report:\n\n{report_context}\n\nThe user wants to discuss the report. Reply helpfully, truthfully, and ALWAYS in standard English. Keep it concise."}
    ]
    for msg in chat_history:
        messages.append(msg)
        
    messages.append({"role": "user", "content": query})
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Groq Error: {str(e)}"
