import openai
import json
import logging
import argparse
import os
from utils import setup_logging, save_text_output

class TranscriptProcessor:
    def __init__(self, api_key):
        self.logger = setup_logging('TranscriptProcessor')
        self.client = openai.OpenAI(api_key=api_key)
        self.model = "gpt-4o"

    def process_transcript(self, transcript_path, output_dir=None):
        """
        Post-process the raw transcript to clean and structure it
        
        Args:
            transcript_path (str): Path to the raw transcript file
            output_dir (str, optional): Directory to save the processed transcript
            
        Returns:
            tuple: (processed transcript text, path to saved file if output_dir provided)
        """
        self.logger.info(f"Processing transcript: {transcript_path}")
        
        try:
            # Verify transcript file exists
            if not os.path.exists(transcript_path):
                raise FileNotFoundError(f"Transcript file not found: {transcript_path}")
            
            # Read raw transcript
            with open(transcript_path, 'r', encoding='utf-8') as f:
                raw_transcript = f.read()

            # System message for post-processing
            system_message = """You are an expert at processing D&D session transcripts.
            Your task is to clean up and structure raw transcription text to make it more
            readable and suitable for summarization. You should:

            1. Fix any obvious transcription errors
            2. Add speaker labels where possible (DM, Player names)
            3. Separate out-of-character (OOC) discussion
            4. Mark important game mechanics moments (rolls, combat)
            5. Identify the session recap section at the start
            6. Remove irrelevant cross-talk or technical discussions
            7. Preserve memorable quotes and funny moments
            8. Structure the text into clear scenes or segments
            
            Maintain all the important content but make it clearer and more organized."""

            # Process the transcript
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Please process this raw D&D session transcript:\n\n{raw_transcript}"}
                ],
                temperature=0.3  # Lower temperature for more consistent processing
            )
            
            processed_transcript = response.choices[0].message.content
            self.logger.info("Successfully processed transcript")
            
            # Save processed transcript if output directory provided
            if output_dir:
                filepath = save_text_output(processed_transcript, "processed_transcript", output_dir)
                return processed_transcript, filepath
            
            return processed_transcript, None
            
        except Exception as e:
            self.logger.error(f"Error processing transcript: {str(e)}")
            raise

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
                    {"role": "system", "content": "You are analyzing D&D session transcripts to identify speakers."},
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
                    {"role": "system", "content": "You are analyzing D&D session transcripts to extract game mechanics information."},
                    {"role": "user", "content": f"{prompt}\n\nTranscript:\n{transcript}"}
                ],
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Error extracting mechanics: {str(e)}")
            raise

def main():
    """Main function for testing transcript processor independently"""
    logger = setup_logging('TranscriptProcessorMain')
    
    parser = argparse.ArgumentParser(description='Process D&D session transcript')
    parser.add_argument('--input', '-i', required=True, help='Path to the input transcript file')
    parser.add_argument('--output', '-o', help='Output directory', default='output')
    parser.add_argument('--config', help='Path to config file', default='.credentials/config.json')
    parser.add_argument('--analyze-speakers', action='store_true', help='Analyze and identify speakers')
    parser.add_argument('--extract-mechanics', action='store_true', help='Extract game mechanics information')
    
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
            filepath = save_text_output(speaker_analysis, "speaker_analysis", args.output)
            logger.info(f"Speaker analysis saved to: {filepath}")
            print("\nSpeaker Analysis:")
            print(speaker_analysis)
            
        elif args.extract_mechanics:
            mechanics_info = processor.extract_mechanics(args.input)
            filepath = save_text_output(mechanics_info, "mechanics_info", args.output)
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