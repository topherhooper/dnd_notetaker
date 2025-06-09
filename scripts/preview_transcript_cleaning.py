#!/usr/bin/env python3
"""
Preview transcript cleaning without API calls
"""
import sys
import os
import re
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def detect_language_sections(text):
    """Detect and mark different language sections"""
    lines = text.split('\n')
    sections = []
    current_section = []
    current_lang = None
    
    # Common Welsh words
    welsh_indicators = ['mae', 'yn', 'dweud', 'cyfrinwyr', 'gwahanol', 'rhaid', 'fawr', 'iawn']
    # Common English words
    english_indicators = ['the', 'and', 'is', 'to', 'of', 'a', 'in', 'that', 'it', 'for', 'you', 'have']
    
    for line in lines:
        words = line.lower().split()
        if len(words) < 3:
            current_section.append(line)
            continue
            
        # Count indicators
        welsh_count = sum(1 for word in words[:20] if word in welsh_indicators)
        english_count = sum(1 for word in words[:20] if word in english_indicators)
        
        # Determine language
        if welsh_count > english_count and welsh_count > 2:
            detected_lang = 'welsh'
        elif english_count > 0:
            detected_lang = 'english'
        else:
            detected_lang = 'unknown'
        
        # Check if language changed
        if current_lang and current_lang != detected_lang:
            sections.append((current_lang, '\n'.join(current_section)))
            current_section = [line]
            current_lang = detected_lang
        else:
            current_section.append(line)
            if not current_lang:
                current_lang = detected_lang
    
    # Add final section
    if current_section:
        sections.append((current_lang, '\n'.join(current_section)))
    
    return sections

def clean_repetitive_text(text):
    """Remove obviously repetitive patterns"""
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Skip lines that are mostly the same word repeated
        words = line.split()
        if len(words) > 5:
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            max_count = max(word_counts.values()) if word_counts else 0
            if max_count > len(words) * 0.5:
                cleaned_lines.append(f"[REMOVED: Repetitive line with '{max(word_counts, key=word_counts.get)}' repeated {max_count} times]")
                continue
        
        # Check for patterns like "Mae Mae Mae Mae..."
        if re.search(r'(\b\w+\b)(?:\s+\1){4,}', line):
            cleaned_lines.append("[REMOVED: Line with excessive word repetition]")
            continue
            
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def add_line_breaks(text):
    """Add line breaks at sensible points"""
    # Add breaks after sentences
    text = re.sub(r'([.!?])\s+([A-Z])', r'\1\n\n\2', text)
    
    # Add breaks before obvious speaker changes
    text = re.sub(r'(\w)\s+(Hi!|Hello|Hey)', r'\1\n\n\2', text)
    
    # Add breaks before questions
    text = re.sub(r'(\w)\s+([A-Z]\w+\?)', r'\1\n\n\2', text)
    
    return text

def identify_potential_speakers(text):
    """Try to identify potential speaker patterns"""
    # Look for patterns like "Name:" or "Name says" or quoted speech after names
    speaker_pattern = re.compile(r'^([A-Z]\w+)(?:\s*:|\s+says?|\s+asked?)', re.MULTILINE)
    potential_speakers = set()
    
    for match in speaker_pattern.finditer(text):
        name = match.group(1)
        # Filter out common words that might match
        if name not in ['The', 'This', 'That', 'What', 'When', 'Where', 'Why', 'How']:
            potential_speakers.add(name)
    
    return list(potential_speakers)

def preview_cleaning(transcript_path, output_path=None):
    """Preview cleaning operations without API calls"""
    print(f"Reading transcript from: {transcript_path}")
    
    with open(transcript_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"\nOriginal: {len(content)} characters, {len(content.split())} words, {len(content.split(chr(10)))} lines")
    
    # Step 1: Detect language sections
    print("\n" + "="*60)
    print("STEP 1: Language Detection")
    print("="*60)
    sections = detect_language_sections(content)
    
    for i, (lang, text) in enumerate(sections):
        word_count = len(text.split())
        print(f"\nSection {i+1}: {lang.upper()} ({word_count} words)")
        if lang == 'welsh':
            print("  Preview: " + text[:200] + "...")
            print("  [Would be removed or translated]")
        else:
            print("  Preview: " + text[:200] + "...")
    
    # Keep only English sections
    english_content = '\n\n'.join([text for lang, text in sections if lang == 'english'])
    
    # Step 2: Clean repetitive text
    print("\n" + "="*60)
    print("STEP 2: Removing Repetitive Text")
    print("="*60)
    cleaned_content = clean_repetitive_text(english_content)
    
    # Count removals
    removed_count = cleaned_content.count('[REMOVED:')
    print(f"Removed {removed_count} repetitive lines")
    
    # Step 3: Add line breaks
    print("\n" + "="*60)
    print("STEP 3: Adding Line Breaks")
    print("="*60)
    formatted_content = add_line_breaks(cleaned_content)
    
    new_lines = len(formatted_content.split('\n'))
    print(f"Increased from {len(english_content.split(chr(10)))} to {new_lines} lines")
    
    # Step 4: Identify speakers
    print("\n" + "="*60)
    print("STEP 4: Potential Speakers")
    print("="*60)
    speakers = identify_potential_speakers(formatted_content)
    print(f"Found {len(speakers)} potential speakers: {', '.join(speakers[:10])}")
    if len(speakers) > 10:
        print(f"  ... and {len(speakers) - 10} more")
    
    # Final stats
    print("\n" + "="*60)
    print("CLEANING SUMMARY")
    print("="*60)
    print(f"Original: {len(content)} chars, {len(content.split())} words")
    print(f"After language filter: {len(english_content)} chars, {len(english_content.split())} words")
    print(f"After cleaning: {len(formatted_content)} chars, {len(formatted_content.split())} words")
    print(f"Reduction: {(1 - len(formatted_content)/len(content))*100:.1f}%")
    
    # Save preview if requested
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("="*60 + "\n")
            f.write("CLEANED TRANSCRIPT PREVIEW\n")
            f.write("="*60 + "\n\n")
            f.write(formatted_content)
        print(f"\nPreview saved to: {output_path}")
    
    # Show sample of cleaned content
    print("\n" + "="*60)
    print("SAMPLE OF CLEANED CONTENT")
    print("="*60)
    sample = formatted_content[:1000]
    print(sample)
    print("\n... (preview truncated)")
    
    return formatted_content

def main():
    parser = argparse.ArgumentParser(description='Preview transcript cleaning')
    parser.add_argument('transcript', help='Path to transcript file')
    parser.add_argument('--output', '-o', help='Save preview to file')
    
    args = parser.parse_args()
    
    preview_cleaning(args.transcript, args.output)

if __name__ == "__main__":
    main()