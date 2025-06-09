import argparse
import json
import logging
import os
import re
from typing import Dict, List, Tuple

import openai
import tiktoken

from .utils import save_text_output, setup_logging


class ImprovedTranscriptProcessor:
    def __init__(self, api_key):
        self.logger = setup_logging("ImprovedTranscriptProcessor")
        self.client = openai.OpenAI(api_key=api_key)
        self.cleaning_model = "gpt-3.5-turbo"  # Cheaper model for initial cleaning
        self.processing_model = "gpt-4o"  # Better model for final processing
        self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        self.max_tokens_per_chunk = 3000  # Safe chunk size

    def detect_and_remove_garbled_text(self, text: str) -> str:
        """Remove obviously garbled or repetitive text patterns"""
        # Remove lines with excessive repetition (like "Mae Mae Mae...")
        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            # Skip lines that are mostly repetitive words
            words = line.split()
            if len(words) > 5:
                # Check if more than 50% of words are the same
                word_counts = {}
                for word in words:
                    word_counts[word] = word_counts.get(word, 0) + 1
                max_count = max(word_counts.values()) if word_counts else 0
                if max_count > len(words) * 0.5:
                    self.logger.debug(f"Skipping repetitive line: {line[:50]}...")
                    continue

            # Skip lines that appear to be in a foreign language (non-English)
            # Simple heuristic: check for common English words
            english_indicators = [
                "the",
                "and",
                "is",
                "to",
                "of",
                "a",
                "in",
                "that",
                "it",
                "for",
            ]
            has_english = any(word.lower() in english_indicators for word in words[:20])

            # If line is long and has no English indicators, might be foreign
            if len(words) > 10 and not has_english:
                # Additional check for Welsh/Celtic patterns
                welsh_patterns = [
                    "mae",
                    "yn",
                    "dweud",
                    "cyfrinwyr",
                    "gwahanol",
                    "rhaid",
                ]
                if any(pattern in line.lower() for pattern in welsh_patterns):
                    self.logger.debug(f"Skipping non-English line: {line[:50]}...")
                    continue

            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def chunk_transcript(self, text: str) -> List[str]:
        """Split transcript into manageable chunks for processing"""
        # First, try to split by natural breaks (empty lines, scene changes)
        sections = text.split("\n\n")
        chunks = []
        current_chunk = ""
        current_tokens = 0

        for section in sections:
            section_tokens = len(self.encoding.encode(section))

            # If adding this section would exceed limit, save current chunk
            if (
                current_tokens + section_tokens > self.max_tokens_per_chunk
                and current_chunk
            ):
                chunks.append(current_chunk.strip())
                current_chunk = section
                current_tokens = section_tokens
            else:
                if current_chunk:
                    current_chunk += "\n\n" + section
                else:
                    current_chunk = section
                current_tokens += section_tokens

        # Don't forget the last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        self.logger.info(f"Split transcript into {len(chunks)} chunks")
        return chunks

    def clean_chunk(self, chunk: str) -> str:
        """Clean individual chunk using cheaper model"""
        try:
            response = self.client.chat.completions.create(
                model=self.cleaning_model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are cleaning up a D&D session transcript. Your job is to:
                        1. Fix obvious transcription errors
                        2. Remove filler words and false starts
                        3. Add punctuation and paragraph breaks where appropriate
                        4. Identify speakers where possible (use format "Speaker: dialogue")
                        5. Remove technical interruptions or connection issues
                        6. Keep all game-relevant content
                        
                        Do NOT summarize or remove content, just clean it up.""",
                    },
                    {
                        "role": "user",
                        "content": f"Clean up this transcript chunk:\n\n{chunk}",
                    },
                ],
                temperature=0.3,
                max_tokens=4000,
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Error cleaning chunk: {str(e)}")
            return chunk  # Return original if cleaning fails

    def identify_speakers_and_characters(
        self, cleaned_chunks: List[str]
    ) -> Dict[str, str]:
        """Analyze chunks to identify speakers and their characters"""
        # Take samples from different parts of the transcript
        samples = []
        if len(cleaned_chunks) >= 3:
            samples = [
                cleaned_chunks[0][:1000],
                cleaned_chunks[len(cleaned_chunks) // 2][:1000],
                cleaned_chunks[-1][:1000],
            ]
        else:
            samples = [chunk[:1000] for chunk in cleaned_chunks]

        sample_text = "\n\n---\n\n".join(samples)

        try:
            response = self.client.chat.completions.create(
                model=self.processing_model,
                messages=[
                    {
                        "role": "system",
                        "content": "Analyze these D&D transcript samples to identify players and characters.",
                    },
                    {
                        "role": "user",
                        "content": f"""Based on these samples, identify:
                        1. The DM/GM
                        2. Each player and their character name
                        3. Any recurring NPCs
                        
                        Return as JSON format:
                        {{
                            "dm": "name",
                            "players": {{"player_name": "character_name", ...}},
                            "npcs": ["npc1", "npc2", ...]
                        }}
                        
                        Samples:
                        {sample_text}""",
                    },
                ],
                temperature=0.3,
            )

            return json.loads(response.choices[0].message.content)
        except Exception as e:
            self.logger.error(f"Error identifying speakers: {str(e)}")
            return {"dm": "DM", "players": {}, "npcs": []}

    def create_session_summary(
        self, cleaned_chunks: List[str], speaker_info: Dict
    ) -> str:
        """Create a comprehensive session summary from cleaned chunks"""
        # Join chunks for final processing
        full_text = "\n\n".join(cleaned_chunks)

        # Estimate token count and potentially summarize if still too long
        token_count = len(self.encoding.encode(full_text))

        if token_count > 10000:
            # If still too long, process in sections and combine
            self.logger.info(
                f"Transcript still large ({token_count} tokens), processing in sections"
            )
            return self.process_in_sections(cleaned_chunks, speaker_info)

        try:
            player_list = "\n".join(
                [
                    f"- {player} plays {char}"
                    for player, char in speaker_info.get("players", {}).items()
                ]
            )

            response = self.client.chat.completions.create(
                model=self.processing_model,
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are creating structured D&D session notes. 
                        
                        Known participants:
                        DM: {speaker_info.get('dm', 'Unknown')}
                        Players:
                        {player_list}
                        
                        Create organized session notes with:
                        1. Session recap/summary at the start
                        2. Major story beats and encounters
                        3. Character moments and roleplay highlights
                        4. Combat encounters (if any)
                        5. Important decisions made
                        6. Treasure/items gained
                        7. Plot hooks and unresolved threads
                        8. Memorable quotes
                        
                        Use clear headings and maintain narrative flow.""",
                    },
                    {
                        "role": "user",
                        "content": f"Create session notes from this transcript:\n\n{full_text}",
                    },
                ],
                temperature=0.5,
                max_tokens=4000,
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Error creating summary: {str(e)}")
            raise

    def process_in_sections(self, cleaned_chunks: List[str], speaker_info: Dict) -> str:
        """Process very long transcripts in sections and combine"""
        section_summaries = []

        # Process every 3-4 chunks together
        section_size = 3
        for i in range(0, len(cleaned_chunks), section_size):
            section = cleaned_chunks[i : i + section_size]
            section_text = "\n\n".join(section)

            try:
                response = self.client.chat.completions.create(
                    model=self.processing_model,
                    messages=[
                        {
                            "role": "system",
                            "content": f"""Summarize this section of a D&D session. Include:
                            - Key events and encounters
                            - Important dialogue and decisions
                            - Combat outcomes
                            - Character moments
                            Keep the narrative flow.""",
                        },
                        {"role": "user", "content": section_text},
                    ],
                    temperature=0.5,
                    max_tokens=1500,
                )
                section_summaries.append(response.choices[0].message.content)
            except Exception as e:
                self.logger.error(f"Error processing section {i}: {str(e)}")
                section_summaries.append(f"[Error processing section {i}]")

        # Combine section summaries into final notes
        combined_summary = "\n\n---\n\n".join(section_summaries)

        # Final pass to organize
        try:
            response = self.client.chat.completions.create(
                model=self.processing_model,
                messages=[
                    {
                        "role": "system",
                        "content": """Combine these section summaries into cohesive session notes.
                        Organize with clear headings and maintain chronological flow.
                        Remove any redundancy between sections.""",
                    },
                    {"role": "user", "content": combined_summary},
                ],
                temperature=0.3,
                max_tokens=4000,
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Error in final organization: {str(e)}")
            return combined_summary

    def process_transcript(
        self, transcript_path: str, output_dir: str = None
    ) -> Tuple[str, str]:
        """Main processing pipeline"""
        self.logger.info(f"Processing transcript: {transcript_path}")

        try:
            # Read transcript
            with open(transcript_path, "r", encoding="utf-8") as f:
                raw_transcript = f.read()

            self.logger.info(f"Read transcript: {len(raw_transcript)} characters")

            # Step 1: Remove obviously garbled text
            self.logger.info("Removing garbled text...")
            cleaned_transcript = self.detect_and_remove_garbled_text(raw_transcript)

            # Step 2: Chunk the transcript
            self.logger.info("Chunking transcript...")
            chunks = self.chunk_transcript(cleaned_transcript)

            # Step 3: Clean each chunk
            self.logger.info("Cleaning chunks...")
            cleaned_chunks = []
            for i, chunk in enumerate(chunks):
                self.logger.debug(f"Cleaning chunk {i+1}/{len(chunks)}")
                cleaned_chunk = self.clean_chunk(chunk)
                cleaned_chunks.append(cleaned_chunk)

            # Step 4: Identify speakers
            self.logger.info("Identifying speakers...")
            speaker_info = self.identify_speakers_and_characters(cleaned_chunks)
            self.logger.info(f"Identified speakers: {speaker_info}")

            # Step 5: Create final session notes
            self.logger.info("Creating session summary...")
            session_notes = self.create_session_summary(cleaned_chunks, speaker_info)

            # Save output
            if output_dir:
                # Save the cleaned transcript
                cleaned_path = save_text_output(
                    "\n\n".join(cleaned_chunks), "cleaned_transcript", output_dir
                )
                self.logger.info(f"Saved cleaned transcript to: {cleaned_path}")

                # Save the session notes
                notes_path = save_text_output(
                    session_notes, "processed_notes", output_dir
                )
                self.logger.info(f"Saved session notes to: {notes_path}")

                # Save speaker info
                speaker_path = save_text_output(
                    json.dumps(speaker_info, indent=2), "speaker_info", output_dir
                )
                self.logger.info(f"Saved speaker info to: {speaker_path}")

                return session_notes, notes_path

            return session_notes, None

        except Exception as e:
            self.logger.error(f"Error processing transcript: {str(e)}")
            raise
