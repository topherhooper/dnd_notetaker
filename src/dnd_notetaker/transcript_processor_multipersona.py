import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple

import openai

from .transcript_processor_v2 import ImprovedTranscriptProcessor
from .utils import save_text_output, setup_logging


class MultiPersonaTranscriptProcessor(ImprovedTranscriptProcessor):
    """
    Enhanced transcript processor that uses multiple AI personas to extract
    different types of information from D&D sessions
    """

    def __init__(self, api_key):
        super().__init__(api_key)
        self.logger = setup_logging("MultiPersonaProcessor")

        # Define personas with their specialized prompts
        self.personas = {
            "narrator": {
                "name": "The Narrator",
                "model": "gpt-4o",
                "system_prompt": """You are an expert storyteller analyzing a D&D session transcript.
                Focus on:
                - Story progression and narrative flow
                - Scene transitions and pacing
                - Dramatic moments and plot twists
                - Emotional beats and character reactions
                - Setting descriptions and atmosphere
                
                Create a narrative summary that reads like a story, not just notes.""",
                "focus_areas": ["story", "narrative", "plot", "scenes", "atmosphere"],
            },
            "rules_lawyer": {
                "name": "The Rules Lawyer",
                "model": "gpt-3.5-turbo",  # Cheaper for mechanical extraction
                "system_prompt": """You are a D&D rules expert analyzing game mechanics in a session.
                Extract and organize:
                - All dice rolls with context (attack rolls, saves, checks)
                - Spells cast with effects
                - Combat encounters with initiative order
                - Rules clarifications or house rules mentioned
                - Mechanical character abilities used
                - Items/equipment gained or used
                
                Format as structured data when possible.""",
                "focus_areas": ["mechanics", "rolls", "combat", "spells", "rules"],
            },
            "character_chronicler": {
                "name": "The Character Chronicler",
                "model": "gpt-4o",
                "system_prompt": """You are focused on character development and roleplay in this D&D session.
                Track:
                - Character growth moments and revelations
                - Inter-character relationships and dynamics
                - In-character dialogue and memorable quotes
                - Character decisions and their motivations
                - Backstory reveals or hints
                - Character goals established or pursued
                
                Organize by character with subheadings.""",
                "focus_areas": [
                    "characters",
                    "roleplay",
                    "relationships",
                    "dialogue",
                    "development",
                ],
            },
            "lorekeeper": {
                "name": "The Lorekeeper",
                "model": "gpt-3.5-turbo",
                "system_prompt": """You are a loremaster documenting world-building elements from this D&D session.
                Catalog:
                - Locations visited or mentioned
                - NPCs encountered (names, descriptions, roles)
                - Organizations, factions, or groups
                - Historical events or lore revealed
                - Magic items or artifacts
                - Cultural details or customs
                - Maps or geographical information
                
                Create an organized reference document.""",
                "focus_areas": [
                    "worldbuilding",
                    "NPCs",
                    "locations",
                    "lore",
                    "factions",
                ],
            },
            "combat_analyst": {
                "name": "The Combat Analyst",
                "model": "gpt-3.5-turbo",
                "system_prompt": """You are a tactical expert analyzing combat encounters in this D&D session.
                Detail:
                - Combat encounter summaries (enemies, environment, stakes)
                - Turn-by-turn significant actions
                - Tactical decisions and their outcomes
                - Damage dealt/taken by parties
                - Combat MVP moments
                - Near-death experiences or dramatic saves
                - Combat duration and resource usage
                
                Format as encounter reports.""",
                "focus_areas": [
                    "combat",
                    "tactics",
                    "encounters",
                    "damage",
                    "strategy",
                ],
            },
            "session_chronicler": {
                "name": "The Session Chronicler",
                "model": "gpt-4o",
                "system_prompt": """You are creating a comprehensive session summary that future players can reference.
                Include:
                - Session recap (what happened previously)
                - Major accomplishments this session
                - Unresolved plot threads
                - Party inventory changes
                - Level ups or character changes
                - Next session hooks
                - Time/date tracking in-game
                
                Write as a formal session log.""",
                "focus_areas": [
                    "summary",
                    "recap",
                    "progress",
                    "logistics",
                    "continuity",
                ],
            },
        }

    def analyze_with_persona(self, transcript: str, persona_key: str) -> str:
        """Analyze transcript from a specific persona's perspective"""
        persona = self.personas[persona_key]
        self.logger.info(f"Analyzing with {persona['name']}...")

        try:
            response = self.client.chat.completions.create(
                model=persona["model"],
                messages=[
                    {"role": "system", "content": persona["system_prompt"]},
                    {
                        "role": "user",
                        "content": f"Analyze this D&D session transcript:\n\n{transcript}",
                    },
                ],
                temperature=0.5,
                max_tokens=3000,
            )

            return response.choices[0].message.content

        except Exception as e:
            self.logger.error(f"Error with {persona['name']}: {str(e)}")
            return f"[Error analyzing with {persona['name']}]"

    def parallel_persona_analysis(
        self, transcript: str, selected_personas: List[str] = None
    ) -> Dict[str, str]:
        """Run multiple persona analyses in parallel"""
        if selected_personas is None:
            selected_personas = list(self.personas.keys())

        results = {}

        # Use thread pool for parallel API calls
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all persona analyses
            future_to_persona = {
                executor.submit(
                    self.analyze_with_persona, transcript, persona_key
                ): persona_key
                for persona_key in selected_personas
            }

            # Collect results as they complete
            for future in as_completed(future_to_persona):
                persona_key = future_to_persona[future]
                try:
                    result = future.result()
                    results[persona_key] = result
                    self.logger.info(
                        f"Completed analysis: {self.personas[persona_key]['name']}"
                    )
                except Exception as e:
                    self.logger.error(f"Failed {persona_key}: {str(e)}")
                    results[persona_key] = f"[Analysis failed: {str(e)}]"

        return results

    def combine_persona_insights(
        self, persona_results: Dict[str, str], speaker_info: Dict
    ) -> str:
        """Combine insights from all personas into comprehensive session notes"""
        self.logger.info("Combining persona insights...")

        # Create a structured prompt with all insights
        combined_prompt = f"""You are creating the final, comprehensive D&D session notes by combining insights from multiple specialized analyses.

Speaker Information:
DM: {speaker_info.get('dm', 'Unknown')}
Players: {json.dumps(speaker_info.get('players', {}), indent=2)}

Combine these specialized analyses into well-organized, comprehensive session notes:

"""

        for persona_key, analysis in persona_results.items():
            persona_name = self.personas[persona_key]["name"]
            combined_prompt += f"\n\n### {persona_name} Analysis ###\n{analysis}\n"

        combined_prompt += """

Create a final document that:
1. Starts with a session summary
2. Includes all important information from each analysis
3. Eliminates redundancy while preserving unique insights
4. Uses clear section headings
5. Maintains chronological flow where appropriate
6. Highlights critical information for players to remember

Format the output as comprehensive session notes suitable for players to reference."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are combining multiple analytical perspectives into comprehensive D&D session notes.",
                    },
                    {"role": "user", "content": combined_prompt},
                ],
                temperature=0.3,
                max_tokens=4000,
            )

            return response.choices[0].message.content

        except Exception as e:
            self.logger.error(f"Error combining insights: {str(e)}")
            # Fallback: just concatenate the analyses
            fallback = "# D&D Session Notes\n\n"
            for persona_key, analysis in persona_results.items():
                persona_name = self.personas[persona_key]["name"]
                fallback += f"\n## {persona_name}\n\n{analysis}\n\n"
            return fallback

    def process_transcript_multipersona(
        self,
        transcript_path: str,
        output_dir: str = None,
        selected_personas: List[str] = None,
    ) -> Tuple[str, str]:
        """
        Process transcript using multiple personas for richer analysis
        """
        self.logger.info(
            f"Processing transcript with multiple personas: {transcript_path}"
        )

        # First, do the standard cleaning and chunking
        with open(transcript_path, "r", encoding="utf-8") as f:
            raw_transcript = f.read()

        # Clean and prepare transcript
        self.logger.info("Preparing transcript...")
        cleaned_transcript = self.detect_and_remove_garbled_text(raw_transcript)
        chunks = self.chunk_transcript(cleaned_transcript)

        # Clean chunks (reuse from parent class)
        self.logger.info("Cleaning chunks...")
        cleaned_chunks = []
        for i, chunk in enumerate(chunks):
            self.logger.debug(f"Cleaning chunk {i+1}/{len(chunks)}")
            cleaned_chunk = self.clean_chunk(chunk)
            cleaned_chunks.append(cleaned_chunk)

        # Get speaker info
        self.logger.info("Identifying speakers...")
        speaker_info = self.identify_speakers_and_characters(cleaned_chunks)

        # For very long transcripts, we might need to sample or summarize first
        full_cleaned_text = "\n\n".join(cleaned_chunks)

        # Check if we need to condense for persona analysis
        if len(full_cleaned_text) > 50000:  # ~12k tokens
            self.logger.info(
                "Transcript too long, creating condensed version for persona analysis..."
            )
            # Take beginning, middle, and end sections
            section_size = 15000
            condensed = (
                full_cleaned_text[:section_size]
                + "\n\n[... middle section ...]\n\n"
                + full_cleaned_text[
                    len(full_cleaned_text) // 2
                    - section_size // 2 : len(full_cleaned_text) // 2
                    + section_size // 2
                ]
                + "\n\n[... final section ...]\n\n"
                + full_cleaned_text[-section_size:]
            )
            analysis_text = condensed
        else:
            analysis_text = full_cleaned_text

        # Run persona analyses in parallel
        self.logger.info("Running multi-persona analysis...")
        persona_results = self.parallel_persona_analysis(
            analysis_text, selected_personas
        )

        # Combine insights
        self.logger.info("Combining insights...")
        final_notes = self.combine_persona_insights(persona_results, speaker_info)

        # Save outputs if directory provided
        if output_dir:
            # Save individual persona analyses
            for persona_key, analysis in persona_results.items():
                persona_name = (
                    self.personas[persona_key]["name"].lower().replace(" ", "_")
                )
                save_text_output(analysis, f"analysis_{persona_name}", output_dir)

            # Save cleaned transcript
            cleaned_path = save_text_output(
                full_cleaned_text, "cleaned_transcript", output_dir
            )

            # Save speaker info
            speaker_path = save_text_output(
                json.dumps(speaker_info, indent=2), "speaker_info", output_dir
            )

            # Save final notes
            notes_path = save_text_output(
                final_notes, "session_notes_multipersona", output_dir
            )

            self.logger.info(f"Saved all outputs to {output_dir}")
            return final_notes, notes_path

        return final_notes, None

    def get_quick_insights(
        self, transcript_path: str, output_dir: str = None
    ) -> Tuple[str, str]:
        """
        Get quick insights using only the cheaper models (Rules Lawyer, Lorekeeper, Combat Analyst)
        Useful for testing or when cost is a concern
        """
        cheap_personas = ["rules_lawyer", "lorekeeper", "combat_analyst"]
        return self.process_transcript_multipersona(
            transcript_path, output_dir, cheap_personas
        )
