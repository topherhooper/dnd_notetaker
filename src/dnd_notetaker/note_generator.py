"""Generate natural prose-style meeting notes from transcripts"""

import logging
import openai
from typing import List
import textwrap

logger = logging.getLogger(__name__)


class NoteGenerator:
    """Generate narrative-style notes from meeting transcripts"""
    
    def __init__(self, api_key: str, config=None):
        self.config = config
        if not config or not config.dry_run:
            self.client = openai.OpenAI(api_key=api_key)
        else:
            self.client = None
        self.model = "o4-mini"
        
    def generate(self, transcript: str) -> str:
        """Generate prose-style notes from transcript
        
        Args:
            transcript: Raw meeting transcript text
            
        Returns:
            Natural language prose summary
        """
        if self.config and self.config.dry_run:
            # Dry run mode - just show what would happen
            print(f"[DRY RUN] Would generate notes using OpenAI GPT:")
            print(f"  Model: {self.model}")
            print(f"  Transcript length: {len(transcript)} characters")
            print(f"  Estimated tokens: ~{len(transcript) // 4}")
            return "[DRY RUN - No actual notes generated]"
            
        # Split transcript into chunks if it's too long
        chunks = self._split_transcript(transcript)
        
        if len(chunks) == 1:
            # Process single chunk
            return self._generate_notes(chunks[0])
        else:
            # Process multiple chunks and combine
            logger.info(f"Processing {len(chunks)} transcript chunks...")
            chunk_summaries = []
            
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{len(chunks)}...")
                summary = self._generate_chunk_summary(chunk, i+1, len(chunks))
                chunk_summaries.append(summary)
            
            # Combine summaries into final notes
            return self._combine_summaries(chunk_summaries)
    
    def _split_transcript(self, transcript: str, max_tokens: int = 12000) -> List[str]:
        """Split transcript into processable chunks"""
        # Rough estimate: 1 token H 4 characters
        max_chars = max_tokens * 4
        
        if len(transcript) <= max_chars:
            return [transcript]
        
        # Split by sentences to avoid breaking mid-sentence
        sentences = transcript.replace('\n', ' ').split('. ')
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            if current_size + sentence_size > max_chars and current_chunk:
                chunks.append('. '.join(current_chunk) + '.')
                current_chunk = [sentence]
                current_size = sentence_size
            else:
                current_chunk.append(sentence)
                current_size += sentence_size
        
        if current_chunk:
            chunks.append('. '.join(current_chunk) + '.')
        
        return chunks
    
    def _generate_notes(self, transcript: str) -> str:
        """Generate notes for a single transcript"""
        prompt = """You are a skilled meeting notes writer. Your task is to transform this meeting transcript into a flowing, natural narrative summary.

IMPORTANT REQUIREMENTS:
- Write in continuous prose paragraphs (NO bullet points, lists, or headers)
- Use natural storytelling language as if describing the meeting to a colleague
- Follow the chronological flow of the conversation
- Preserve key decisions, action items, and important discussions
- Keep the tone professional but conversational
- Focus on what matters: decisions made, problems discussed, solutions proposed, and next steps

Write the summary as a cohesive narrative that captures the essence of the meeting."""
        
        if not self.client:
            raise RuntimeError("OpenAI client not initialized (check dry_run mode)")
            
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Please summarize this meeting transcript:\n\n{transcript}"}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        return response.choices[0].message.content.strip() if response.choices[0].message.content else ""
            
    
    def _generate_chunk_summary(self, chunk: str, chunk_num: int, total_chunks: int) -> str:
        """Generate summary for a transcript chunk"""
        prompt = f"""You are summarizing part {chunk_num} of {total_chunks} of a meeting transcript.
Write a flowing narrative summary of this portion of the meeting.

IMPORTANT: Write in continuous prose paragraphs with no bullet points or headers.
Focus on the key discussions, decisions, and action items in this segment."""
        
        if not self.client:
            raise RuntimeError("OpenAI client not initialized (check dry_run mode)")
            
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Summarize this meeting segment:\n\n{chunk}"}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        return response.choices[0].message.content.strip() if response.choices[0].message.content else ""
    
    def _combine_summaries(self, summaries: List[str]) -> str:
        """Combine multiple chunk summaries into cohesive notes"""
        combined = "\n\n".join(summaries)
        
        prompt = """You have summaries from different parts of a long meeting. 
Combine these into one cohesive, flowing narrative that reads naturally.

IMPORTANT:
- Maintain chronological flow
- Remove any redundancy
- Write in continuous prose (no bullets or headers)
- Ensure smooth transitions between topics
- Keep all important decisions and action items"""
        
        if not self.client:
            raise RuntimeError("OpenAI client not initialized (check dry_run mode)")
            
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Combine these meeting summaries:\n\n{combined}"}
            ],
            temperature=0.7,
            max_tokens=3000
        )
        
        return response.choices[0].message.content.strip() if response.choices[0].message.content else ""