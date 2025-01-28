import logging
from typing import List
import openai
import json
import argparse
import os

import tiktoken
from utils import setup_logging, save_text_output
from tenacity import retry, wait_exponential, retry_if_exception_type, stop_after_attempt
import time

class TranscriptProcessor:
    def __init__(self, api_key):
        self.logger = setup_logging('TranscriptProcessor')
        self.client = openai.OpenAI(api_key=api_key)
        self.model = "o1-mini"
        self.encoding = tiktoken.get_encoding("cl100k_base")  # Fixed encoding
        self.rate_limit_reset = time.time() + 60  # Initial 1 minute window
        self.tokens_used = 0
        self.rate_limit = 30000  # Default TPM limit

    def analyze_speakers(self, transcript_path):
        """
        Analyze the transcript to identify and label different speakers
        Returns a dictionary mapping speaker labels to likely player/character names
        """
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript = f.read()

            prompt = """Analyze this D&D session transcript and identify:
            1. Who is the DM
            2. Player names and their character names
            3. Any recurring NPCs that speak
            
            Return the information in a clear format."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "developer", "content": "You are analyzing D&D session transcripts to identify speakers."},
                    {"role": "user", "content": f"{prompt}\n\nTranscript:\n{transcript}"}
                ],
                temperature=0.3
            )

            return response.choices[0].message.content

        except Exception as e:
            self.logger.error(f"Error analyzing speakers: {str(e)}")
            raise

    def extract_mechanics(self, transcript_path):
        """
        Extract and organize game mechanics information (rolls, saves, etc.)
        Returns a structured summary of mechanical events
        """
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript = f.read()

            prompt = """Analyze this D&D session transcript and extract:
            1. Important dice rolls and their outcomes
            2. Combat encounters and initiative order
            3. Skill checks and saving throws
            4. Spell usage and effects
            5. Any house rules or mechanical decisions made
            
            Organize this information in a clear format."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "developer", "content": "You are analyzing D&D session transcripts to extract game mechanics information."},
                    {"role": "user", "content": f"{prompt}\n\nTranscript:\n{transcript}"}
                ],
                temperature=0.3
            )

            return response.choices[0].message.content

        except Exception as e:
            self.logger.error(f"Error extracting mechanics: {str(e)}")
            raise

    def process_transcript(self, transcript_files: List[str], output_file: str):
        """
        Post-process raw transcripts from multiple files to clean and structure them
        """
        self.logger.info(
            f"Processing {len(transcript_files)} transcript files")

        try:
            raw_transcript = self._read_transcript_files(transcript_files)
            assert raw_transcript, "Transcript content is empty"
            system_message = self._get_system_message()
            max_context_tokens = self._get_model_context_size()

            # Calculate available tokens with proper buffer
            available_tokens = self._calculate_available_tokens(
                system_message, max_context_tokens
            )

            transcript_chunks = self._chunk_transcript(
                raw_transcript, available_tokens)
            processed_transcript = self._process_chunks(
                transcript_chunks, system_message)

            return self._save_and_return(processed_transcript, output_file)

        except Exception as e:
            self.logger.error(f"Error processing transcript: {str(e)}")
            raise

    def _read_transcript_files(self, transcript_files):
        """Read and concatenate multiple transcript files"""
        raw_transcript = []
        for path in transcript_files:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Transcript file not found: {path}")
            with open(path, 'r', encoding='utf-8') as f:
                raw_transcript.append(f.read())
        return "\n".join(raw_transcript)

    def _get_system_message(self):
        """More specific processing instructions"""
        return """You are a D&D transcript processing expert. For EVERY chunk you receive:

    2. Add speaker labels (DM, Player#) when missing
    3. Mark game mechanics with [ROLL], [SAVE], [COMBAT] tags
    4. Separate OOC discussions into {OOC} blocks
    5. Maintain exact dialogue text
    7. Add scene markers when location changes
    8. Preserve voice/style quirks

    Formatting rules:
    - One speaker per line
    - Actions in parentheses
    - Mechanics in square brackets
    - OOC in curly braces
    - Never use markdown"""

    def _get_model_context_size(self):
        """Updated context sizes for modern models"""
        model_context = {
            "gpt-o1": 128000,
            "gpt-4o": 128000,
            "gpt-4-turbo": 128000,
            "gpt-4-32k": 32768,
            "gpt-4": 8192,
            "gpt-3.5-turbo": 16385  # Updated for newer 16k context
        }
        return next((v for k, v in model_context.items() if k in self.model), 8192)

    def _calculate_available_tokens(self, system_message, max_context_tokens):
        """Improved token calculation with response buffer"""
        system_tokens = self.encoding.encode(system_message)
        response_buffer = 2000  # Increased buffer for longer responses
        return max_context_tokens - len(system_tokens) - response_buffer

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception_type(openai.RateLimitError),
        stop=stop_after_attempt(5)
    )
    def _process_chunk_with_retry(self, messages):
        """Process chunk with rate limit handling"""
        # Check rate limits
        if time.time() < self.rate_limit_reset and self.tokens_used >= self.rate_limit:
            sleep_time = self.rate_limit_reset - time.time() + 5
            self.logger.warning(f"Rate limit reached. Sleeping {sleep_time:.1f} seconds")
            time.sleep(max(sleep_time, 0))
            self.tokens_used = 0  # Reset counter after sleep
        # set logging level to info
        openai._base_client.log.setLevel(logging.INFO)
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",  # Use a smaller model for chunk processing
            messages=messages,
            temperature=0.3,
            max_tokens=3500,  # Reduced from 4000
        )

        # Update rate limit tracking
        self.tokens_used += response.usage.total_tokens
        if self.tokens_used >= self.rate_limit * 0.9:  # 90% threshold
            self.rate_limit_reset = time.time() + 60  # Reset window
            self.tokens_used = 0

        return response
    
    def _process_chunks(self, chunks, system_message):
        """Modified processing with rate control"""
        processed_parts = []
        previous_context = ""
        
        for i, chunk in enumerate(chunks, 1):
            if not chunk.strip():
                continue

            # Create optimized prompt
            user_content = f"""Process this transcript chunk:
            {chunk}
            
            [Previous Context Summary]
            {previous_context[-500:]}
            
            Follow format rules strictly. Use minimal tokens for processing."""

            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_content}
            ]

            try:
                response = self._process_chunk_with_retry(messages)
                result = response.choices[0].message.content
                # write response to a file
                directory = "output/processed_transcripts"
                os.makedirs(directory, exist_ok=True)
                save_text_output(result, f"output/processed_transcripts/chunk_{i}.txt")
                processed_parts.append(result)
                
                # Update context with compressed version
                previous_context = self._compress_context(result, previous_context)
                
                # Add safety delay between chunks
                time.sleep(2)  # Add 2-second delay between requests

            except openai.RateLimitError as e:
                self.logger.error("Persistent rate limit error. Try:")
                self.logger.error("1. Reduce chunk sizes further")
                self.logger.error("2. Upgrade your API tier")
                self.logger.error("3. Use gpt-3.5-turbo for initial processing")
                raise

        return self._integrate_chunks(processed_parts, system_message)

    def _compress_context(self, new_content, existing_context):
        """Compress context to preserve tokens"""
        # Keep only key elements from context
        keeper_phrases = ["DM:", "Player", "[COMBAT]", "{OOC}", "Scene:"]
        compressed = "\n".join(
            line for line in existing_context.split('\n') 
            if any(phrase in line for phrase in keeper_phrases)
        )
        return f"{compressed[-1000:]}\n{new_content}"[:2000]  # Keep under 2000 chars
    
    def _chunk_transcript(self, transcript, available_tokens):
        """More conservative chunking"""
        tokens = self.encoding.encode(transcript)
        chunk_size = int(available_tokens * 0.7)  # 70% of available tokens

        if len(tokens) == 0:
            raise ValueError("Transcript contains no encodable content")

        if len(tokens) <= available_tokens:
            return [transcript]

        chunks = []
        # More conservative chunk size
        chunk_size = int(available_tokens * 0.8)
        overlap = int(chunk_size * 0.15)  # 15% overlap

        for i in range(0, len(tokens), chunk_size - overlap):
            chunk_tokens = tokens[i:i + chunk_size]

            # Ensure minimum chunk size
            if len(chunk_tokens) < 100:
                if chunks:  # Add to last chunk
                    chunks[-1] = self.encoding.decode(
                        self.encoding.encode(chunks[-1]) + chunk_tokens)
                else:  # Handle tiny transcript case
                    chunks.append(self.encoding.decode(chunk_tokens))
                continue

            chunk_text = self.encoding.decode(chunk_tokens)

            # Ensure chunk contains valid content
            if chunk_text.strip():
                chunks.append(chunk_text)
            else:
                self.logger.warning(f"Skipping empty chunk at position {i}")

        return chunks

    def _integrate_chunks(self, processed_parts, system_message):
        """Improved integration with hierarchical merging"""
        while len(processed_parts) > 1:
            new_parts = []
            for i in range(0, len(processed_parts), 2):
                pair = processed_parts[i:i+2]
                if len(pair) == 1:
                    new_parts.append(pair[0])
                    continue

                merged = self._merge_pair(pair[0], pair[1], system_message)
                new_parts.append(merged)
            processed_parts = new_parts

        return processed_parts[0]

    def _merge_pair(self, part1, part2, system_message):
        """Merge two processed chunks while preserving context"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "developer", "content": system_message},
                {"role": "user", "content": f"Merge these two processed chunks while maintaining all important details:\n\nCHUNK 1:\n{part1}\n\nCHUNK 2:\n{part2}"}
            ],
            temperature=0.2,
            max_tokens=6000
        )
        return response.choices[0].message.content

    def _summary_integration(self, processed_parts, system_message):
        """Handle very large combined results with summary integration"""
        summary_parts = []
        for part in processed_parts:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "developer", "content": system_message},
                    {"role": "user", "content": f"Create a summary version of this processed chunk:\n{part}"}
                ],
                temperature=0.3
            )
            summary_parts.append(response.choices[0].message.content)

        combined_summaries = "\n\n".join(summary_parts)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "developer", "content": system_message},
                {"role": "user", "content": f"Create a final integrated transcript from these summaries:\n{combined_summaries}"}
            ],
            temperature=0.2
        )
        return response.choices[0].message.content

    def _save_and_return(self, processed_transcript, output_file):
        """Handle saving and returning the final result"""
        self.logger.info("Successfully processed transcript")
        if output_file:
            filepath = save_text_output(processed_transcript, output_file)
            return processed_transcript, filepath
        return processed_transcript, None


def main():
    """Main function for testing transcript processor independently"""
    logger = setup_logging('TranscriptProcessorMain')

    parser = argparse.ArgumentParser(
        description='Process D&D session transcript')
    parser.add_argument('--input', '-i', required=True,
                        help='Path to the input transcript file')
    parser.add_argument(
        '--output', '-o', help='Output directory', default='output')
    parser.add_argument('--config', help='Path to config file',
                        default='.credentials/config.json')
    parser.add_argument('--analyze-speakers', action='store_true',
                        help='Analyze and identify speakers')
    parser.add_argument('--extract-mechanics', action='store_true',
                        help='Extract game mechanics information')

    args = parser.parse_args()
    logger.debug(f"Arguments parsed: {args}")

    try:
        # Load config for API key
        with open(args.config, 'r') as f:
            config = json.load(f)
        logger.debug("Config loaded successfully")

        # Create output directory
        os.makedirs(args.output, exist_ok=True)

        processor = TranscriptProcessor(config['openai_api_key'])

        if args.analyze_speakers:
            speaker_analysis = processor.analyze_speakers(args.input)
            filepath = save_text_output(
                speaker_analysis, "speaker_analysis", args.output)
            logger.info(f"Speaker analysis saved to: {filepath}")
            print("\nSpeaker Analysis:")
            print(speaker_analysis)

        elif args.extract_mechanics:
            mechanics_info = processor.extract_mechanics(args.input)
            filepath = save_text_output(
                mechanics_info, "mechanics_info", args.output)
            logger.info(f"Mechanics information saved to: {filepath}")
            print("\nMechanics Information:")
            print(mechanics_info)

        else:
            _, filepath = processor.process_transcript(args.input, args.output)
            logger.info(f"Processed transcript saved to: {filepath}")

    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()
