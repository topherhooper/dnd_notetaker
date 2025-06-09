#!/usr/bin/env python3
"""
Test the multi-persona transcript processor
"""
import sys
import os
import json
import argparse
import tiktoken
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.dnd_notetaker.transcript_processor_multipersona import MultiPersonaTranscriptProcessor
from src.dnd_notetaker.utils import setup_logging

def estimate_multipersona_cost(text_length: int, selected_personas: list = None):
    """Estimate cost for multi-persona processing"""
    # Token estimation
    tokens = text_length / 3.5  # Rough estimate
    
    # Default to all personas if none selected
    if selected_personas is None:
        selected_personas = ["narrator", "rules_lawyer", "character_chronicler", 
                           "lorekeeper", "combat_analyst", "session_chronicler"]
    
    # Model costs (per 1K tokens)
    costs = {
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "gpt-4o": {"input": 0.005, "output": 0.015}
    }
    
    # Persona model mapping
    persona_models = {
        "narrator": "gpt-4o",
        "rules_lawyer": "gpt-3.5-turbo",
        "character_chronicler": "gpt-4o", 
        "lorekeeper": "gpt-3.5-turbo",
        "combat_analyst": "gpt-3.5-turbo",
        "session_chronicler": "gpt-4o"
    }
    
    total_cost = 0
    cost_breakdown = {}
    
    # Calculate per-persona costs
    for persona in selected_personas:
        model = persona_models.get(persona, "gpt-3.5-turbo")
        
        # Input tokens (analyzing the transcript)
        input_cost = (tokens / 1000) * costs[model]["input"]
        
        # Output tokens (roughly 30% of input for analysis)
        output_tokens = tokens * 0.3
        output_cost = (output_tokens / 1000) * costs[model]["output"]
        
        persona_cost = input_cost + output_cost
        cost_breakdown[persona] = {
            "model": model,
            "cost": persona_cost
        }
        total_cost += persona_cost
    
    # Add combination step (GPT-4o)
    combination_input = len(selected_personas) * output_tokens  # All analyses
    combination_cost = (combination_input / 1000) * costs["gpt-4o"]["input"]
    combination_cost += (4000 / 1000) * costs["gpt-4o"]["output"]  # Final output
    
    cost_breakdown["final_combination"] = {
        "model": "gpt-4o",
        "cost": combination_cost
    }
    total_cost += combination_cost
    
    return total_cost, cost_breakdown

def main():
    parser = argparse.ArgumentParser(description='Test multi-persona transcript processing')
    parser.add_argument('--transcript', '-t', required=True, help='Path to transcript file')
    parser.add_argument('--output', '-o', help='Output directory', default='output/multipersona_test')
    parser.add_argument('--config', '-c', help='Config file', default='.credentials/config.json')
    parser.add_argument('--preview', action='store_true', help='Preview costs without processing')
    parser.add_argument('--quick', action='store_true', help='Use only cheaper personas')
    parser.add_argument('--personas', nargs='+', help='Specific personas to use', 
                      choices=['narrator', 'rules_lawyer', 'character_chronicler', 
                               'lorekeeper', 'combat_analyst', 'session_chronicler'])
    parser.add_argument('--max-cost', type=float, default=2.0, help='Maximum cost in USD')
    
    args = parser.parse_args()
    logger = setup_logging('TestMultiPersona')
    
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
    
    # Determine which personas to use
    if args.quick:
        selected_personas = ["rules_lawyer", "lorekeeper", "combat_analyst"]
        logger.info("Quick mode: Using only cheaper personas")
    elif args.personas:
        selected_personas = args.personas
        logger.info(f"Using specified personas: {', '.join(selected_personas)}")
    else:
        selected_personas = None  # Use all
        logger.info("Using all personas")
    
    # Estimate costs
    total_cost, cost_breakdown = estimate_multipersona_cost(len(content), selected_personas)
    
    logger.info("\nCost Estimation:")
    logger.info("="*60)
    for persona, info in cost_breakdown.items():
        logger.info(f"{persona:20s} ({info['model']:15s}): ${info['cost']:.3f}")
    logger.info("="*60)
    logger.info(f"TOTAL ESTIMATED COST: ${total_cost:.2f}")
    
    if total_cost > args.max_cost:
        logger.warning(f"\nWARNING: Estimated cost (${total_cost:.2f}) exceeds maximum (${args.max_cost:.2f})")
        
    if args.preview:
        logger.info("\nPreview mode - not processing")
        
        # Show what personas would analyze
        processor = MultiPersonaTranscriptProcessor(api_key)
        logger.info("\nPersona Focus Areas:")
        for persona_key, persona_info in processor.personas.items():
            if selected_personas and persona_key not in selected_personas:
                continue
            logger.info(f"\n{persona_info['name']}:")
            logger.info(f"  Focus: {', '.join(persona_info['focus_areas'])}")
            logger.info(f"  Model: {persona_info['model']}")
        
        return
    
    # Get confirmation if cost is high
    if total_cost > args.max_cost / 2:
        response = input(f"\nEstimated cost is ${total_cost:.2f}. Continue? (yes/no): ")
        if response.lower() != 'yes':
            logger.info("Processing cancelled")
            return
    
    # Process
    logger.info("\nStarting multi-persona processing...")
    os.makedirs(args.output, exist_ok=True)
    
    processor = MultiPersonaTranscriptProcessor(api_key)
    
    try:
        start_time = datetime.now()
        
        if args.quick:
            notes, filepath = processor.get_quick_insights(args.transcript, args.output)
        else:
            notes, filepath = processor.process_transcript_multipersona(
                args.transcript, args.output, selected_personas
            )
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"\nProcessing complete in {elapsed:.1f} seconds!")
        logger.info(f"Session notes saved to: {filepath}")
        
        # Show what was created
        output_files = os.listdir(args.output)
        logger.info(f"\nCreated {len(output_files)} files:")
        for file in sorted(output_files):
            file_path = os.path.join(args.output, file)
            size = os.path.getsize(file_path) / 1024  # KB
            logger.info(f"  - {file} ({size:.1f} KB)")
            
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")

if __name__ == "__main__":
    main()