import json
from openai import OpenAI


def grok_analyze(texts, api_key):
    if isinstance(texts, str):
        texts = [texts]
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.x.ai/v1",
    )
    
    try:
        completion = client.chat.completions.create(
            model="grok-2-latest",
            messages=[
                {"role": "system", "content": "Process these {count} tweets separately. For each tweet, create a clear, concise headline that summarizes the main point. Return JSON array with each entry containing: relevant, headline, sentiment, score, impact, direction, assets.".replace('{count}', str(len(texts)))},
                {"role": "user", "content": '\n\n'.join([f'Tweet {i+1}: {t}' for i, t in enumerate(texts)])}
            ],
            response_format={"type": "json_object"}
        )
        
        analyses = json.loads(completion.choices[0].message.content)
        return [
            {
                'relevant': a.get('relevant', False),
                'headline': a.get('headline', t[:140]),
                'direction': a.get('direction', 'neutral').capitalize(),
                'sentiment': a.get('sentiment', 'neutral').capitalize(),
                'score': a.get('score', 5),
                'impact': a.get('impact', 5),
                'assets': a.get('assets', [])
            } for a, t in zip(analyses, texts)
        ]
    except Exception as e:
        return [
            {
                'relevant': False,
                'headline': 'Analysis Failed',
                'sentiment': 'Neutral',
                'score': 5,
                'impact': 5,
                'direction': 'Neutral',
                'assets': []
            } for _ in texts
        ]