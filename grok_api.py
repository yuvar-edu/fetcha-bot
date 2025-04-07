import json
from openai import OpenAI


def grok_analyze(text, api_key):
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.x.ai/v1",
    )
    
    try:
        completion = client.chat.completions.create(
            model="grok-2-latest",
            messages=[
                {"role": "system", "content": "Generate a headline and analyze this financial tweet for market implications. Return JSON format with: relevant (boolean), headline, sentiment, score (1-10), impact (1-10), direction (bullish/bearish/neutral), assets (list)."},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"}
        )
        
        analysis = json.loads(completion.choices[0].message.content)
        return {
            'relevant': analysis.get('relevant', False),
            'headline': analysis.get('headline', text[:140]),
            'direction': analysis.get('direction', 'neutral').capitalize(),
            'sentiment': analysis.get('sentiment', 'neutral').capitalize(),
            'score': analysis.get('score', 5),
            'impact': analysis.get('impact', 5),
            'assets': analysis.get('assets', [])
        }
    except Exception as e:
        return {
            'relevant': False,
            'summary': f'Grok analysis failed: {str(e)}',
            'sentiment': 'Neutral',
            'score': 5,
            'impact': 5,
            'assets': []
        }