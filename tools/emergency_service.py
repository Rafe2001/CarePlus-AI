import json
from duckduckgo_search import DDGS

def search_nearest_hospital(location: str) -> str:
    """Uses DuckDuckGo to search for the nearest hospital or emergency room based on location."""
    try:
        ddgs = DDGS()
        query = f"nearest hospital emergency room to {location} with phone number and address"
        
        # Get top 3 search results
        results = list(ddgs.text(query, max_results=3))
        
        if not results:
            return "Could not find specific hospital information online. Please dial 911 immediately."
            
        formatted_results = "Here are the closest emergency rooms I found:\n\n"
        for i, res in enumerate(results):
            formatted_results += f"**{i+1}. {res.get('title', 'Hospital')}**\n"
            formatted_results += f"{res.get('body', '')}\n"
            if res.get('href'):
                formatted_results += f"Website/Directions: {res.get('href')}\n"
            formatted_results += "\n"
            
        return formatted_results
    except Exception as e:
        print(f"Web search error: {e}")
        return "I am having trouble connecting to the search service. Please dial 911 or go to the nearest hospital immediately."
