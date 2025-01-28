import os
from typing import List, Dict
from utils import cache_to_file, load_config
from openai import OpenAI
import openai

PARTY = {
    "Ali": "Elspeth Cooper",
    "Justin": "Felonias Bru",
    "Luke": "Helisanna Doomfall",
    "Ellis Martha": "Retired Detective Olivia Cooper",
    "Taylor": "Silas Fairbanks",
    "Zack": "Thurnok 'Red' Skyhammer",
    "Topher": "Dunegon Master"
}

CACHE_DIRECTORY = "output/transcript_processor"
FINAL_OUTPUT_PROCESSED_TRANSCRIPT = "output/transcript_processor.txt"
# get the API key from the json file
CONFIG = load_config(".credentials/config.json")
client = OpenAI(api_key=CONFIG['openai_api_key'])
openai._base_client.log.setLevel("INFO")


def load_transcripts(directory: str) -> str:
    transcript_files = sorted([
        os.path.join(directory, file) for file in os.listdir(directory)
        if file.endswith('.txt')
    ])
    consolidated_text = ""
    for file_path in transcript_files:
        with open(file_path, 'r', encoding='utf-8') as file:
            print(f"Loading {file_path}...")
            consolidated_text += file.read() + " "
    return consolidated_text.strip()


@cache_to_file(CACHE_DIRECTORY+"/extract_entities_with_llm.txt")
def extract_entities_with_llm(raw_transcripts: str) -> str:
    messages: List[Dict[str, str]] = [
        {"role": "user", "content": f"""You are an assistant that extracts entities from narrative text.

        Please identify:
        - Characters (people, creatures)
        - Locations (places, settings)
        - Items (objects, artifacts)
        
        Example expected format:
        {{"Characters": ["Player1", "Olivia"], "Locations": ["Tavern"], "Items": ["Sword"]}}
        
        Known party members: {PARTY},
        
        Transcript to refine:
        {raw_transcripts}"""}
    ]

    response = client.chat.completions.create(
        model="o1-mini",
        messages=messages,  # type: ignore[arg-type]
    )

    result = response.choices[0].message.content
    if not result:
        raise ValueError("Empty response received")
    return result.strip()


@cache_to_file(FINAL_OUTPUT_PROCESSED_TRANSCRIPT)
def final_writer(raw_transcripts: str, entities: str) -> str:
    content = (
        "Write in the style of Hemingway. Use the following extracted entities and Transcript from a DnD session to write a single detailed and engaging chapter fantasy narrative suitable for a novel. The beginning of the transcript will include a recap of the prior session. Assume that the session has picked up from a prior session and will have a session to follow. This means that we do not need to write and introduction or exposition - just the action! Remove the content that is out of session. Center the story around the players, their characters, and their decisions. Focus on their decisions and create more vivid descriptions of their heoric deeds. The response should have no formatting and be straight prose.\n\n")
    messages: List[Dict[str, str]] = [
        {"role": "user", "content": f"""{content}\n\n
        players and their characters or roles: {PARTY},\n\nEntities:\n{entities}\n\nTranscript:\n
        {raw_transcripts}"""}
    ]

    response = client.chat.completions.create(
        model="o1-mini",
        messages=messages,  # type: ignore[arg-type]
    )

    result = response.choices[0].message.content
    if not result:
        raise ValueError("Empty response received")
    return result


def process_transcript(directory: str) -> str:
    # Load and clean transcripts
    raw_transcripts = load_transcripts(directory)
    # Extract entities
    entities = extract_entities_with_llm(raw_transcripts)
    # Enhance transitions
    enhanced_narrative = final_writer(raw_transcripts, entities)
    return enhanced_narrative
