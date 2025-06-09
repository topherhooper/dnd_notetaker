#!/usr/bin/env python3
"""
Process only the transcript step with cost estimation
"""
import sys
import os
import json
import argparse
import tiktoken

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.dnd_notetaker.transcript_processor_v2 import ImprovedTranscriptProcessor
from src.dnd_notetaker.utils import setup_logging

def estimate_cost(text, model="gpt-3.5-turbo"):
    """Estimate API cost for processing text"""
    encoding = tiktoken.encoding_for_model(model)
    tokens = len(encoding.encode(text))
    
    # Rough cost estimates (as of 2024)
    costs = {
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},  # per 1K tokens
        "gpt-4o": {"input": 0.005, "output": 0.015}  # per 1K tokens
    }
    
    # Estimate output tokens as ~50% of input for cleaning, 30% for summary
    estimated_output = tokens * 0.8
    
    if model in costs:
        input_cost = (tokens / 1000) * costs[model]["input"]
        output_cost = (estimated_output / 1000) * costs[model]["output"]
        total_cost = input_cost + output_cost
        return tokens, estimated_output, total_cost
    
    return tokens, estimated_output, 0

def main():
    parser = argparse.ArgumentParser(description='Process transcript with cost estimation')
    parser.add_argument('--transcript', '-t', required=True, help='Path to transcript file')
    parser.add_argument('--output', '-o', help='Output directory', default='output/processed')
    parser.add_argument('--config', '-c', help='Config file', default='.credentials/config.json')
    parser.add_argument('--preview', action='store_true', help='Preview costs without processing')
    parser.add_argument('--max-cost', type=float, default=1.0, help='Maximum cost in USD (default: $1.00)')
    
    args = parser.parse_args()
    logger = setup_logging('ProcessTranscript')
    
    # Load config
    try:
        with open(args.config, 'r') as f:
            config = json.load(f)
        api_key = config['openai_api_key']
    except Exception as e:
        logger.error(f"Failed to load config: {str(e)}")
        return
    
    # Read transcript
    with open(args.transcript, 'r', encoding='utf-8') as f:
        content = f.read()
    
    logger.info(f"Transcript size: {len(content)} characters")
    
    # Estimate costs
    logger.info("\nCost Estimation:")
    logger.info("="*50)
    
    # Estimate for cleaning (multiple chunks with GPT-3.5)
    chunks = len(content) // 15000 + 1  # Rough chunk estimate
    clean_tokens, clean_output, clean_cost = estimate_cost(content, "gpt-3.5-turbo")
    clean_cost = clean_cost * 1.2  # Add 20% buffer for multiple operations
    
    logger.info(f"Cleaning Phase (GPT-3.5-turbo):")
    logger.info(f"  - Estimated chunks: {chunks}")
    logger.info(f"  - Input tokens: ~{clean_tokens:,}")
    logger.info(f"  - Estimated cost: ${clean_cost:.3f}")
    
    # Estimate for final processing (GPT-4)
    # Assume cleaned text is 80% of original
    final_text_size = int(len(content) * 0.8)
    final_tokens, final_output, final_cost = estimate_cost(content[:final_text_size], "gpt-4o")
    
    logger.info(f"\nFinal Processing (GPT-4o):")
    logger.info(f"  - Input tokens: ~{final_tokens:,}")
    logger.info(f"  - Estimated cost: ${final_cost:.3f}")
    
    total_cost = clean_cost + final_cost
    logger.info(f"\nTOTAL ESTIMATED COST: ${total_cost:.2f}")
    logger.info("="*50)
    
    if total_cost > args.max_cost:
        logger.warning(f"\nWARNING: Estimated cost (${total_cost:.2f}) exceeds maximum (${args.max_cost:.2f})")
        if args.preview:
            logger.info("Preview mode - not processing")
            return
        
        response = input("\nDo you want to continue? (yes/no): ")
        if response.lower() != 'yes':
            logger.info("Processing cancelled")
            return
    
    if args.preview:
        logger.info("\nPreview mode - not processing")
        # Show what would be done
        processor = ImprovedTranscriptProcessor(api_key)
        
        # Just show the cleaning preview
        logger.info("\nCleaning preview:")
        cleaned = processor.detect_and_remove_garbled_text(content[:2000])
        logger.info(f"First 500 chars after cleaning:\n{cleaned[:500]}...")
        
        chunks = processor.chunk_transcript(content)
        logger.info(f"\nWould create {len(chunks)} chunks for processing")
        
        return
    
    # Process for real
    logger.info("\nStarting processing...")
    os.makedirs(args.output, exist_ok=True)
    
    processor = ImprovedTranscriptProcessor(api_key)
    
    try:
        notes, filepath = processor.process_transcript(args.transcript, args.output)
        logger.info(f"\nProcessing complete!")
        logger.info(f"Notes saved to: {filepath}")
        
        # Show summary of what was created
        output_files = os.listdir(args.output)
        logger.info(f"\nCreated files:")
        for file in output_files:
            file_path = os.path.join(args.output, file)
            size = os.path.getsize(file_path) / 1024  # KB
            logger.info(f"  - {file} ({size:.1f} KB)")
            
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")

if __name__ == "__main__":
    main()