# D&D Notetaker Processing Options

## Overview

The D&D Notetaker now offers three different transcript processing approaches, each with different costs and benefits:

1. **Standard Improved Processing** - Balanced approach
2. **Multi-Persona Processing** - Rich, multi-perspective analysis
3. **Quick Multi-Persona** - Cost-effective specialized analysis

## 1. Standard Improved Processing (Default)

**Cost**: ~$0.55 per session
**Time**: ~5-10 minutes

This is the default processor that:
- Removes non-English sections and repetitive text
- Chunks large transcripts intelligently
- Uses GPT-3.5 for cleaning, GPT-4o for final processing
- Identifies speakers and creates structured notes

### Usage:
```bash
# Full pipeline
make process-dir DIR=output/session_directory

# Just transcript processing
python scripts/process_transcript_only.py \
  --transcript path/to/transcript.txt \
  --output output_directory
```

### Output:
- `cleaned_transcript_*.txt` - Cleaned and formatted transcript
- `speaker_info_*.txt` - Identified speakers and characters
- `processed_notes_*.txt` - Final session notes

## 2. Multi-Persona Processing

**Cost**: ~$1.70 per session
**Time**: ~10-15 minutes

Uses 6 specialized AI personas to analyze the session from different perspectives:

### The Personas:

1. **The Narrator** (GPT-4o)
   - Story progression and narrative flow
   - Dramatic moments and atmosphere
   - Scene transitions

2. **The Rules Lawyer** (GPT-3.5-turbo)
   - All dice rolls and mechanics
   - Spells cast and effects
   - Rules clarifications

3. **The Character Chronicler** (GPT-4o)
   - Character development and growth
   - Relationships and dynamics
   - Memorable quotes

4. **The Lorekeeper** (GPT-3.5-turbo)
   - Locations and world-building
   - NPCs and factions
   - Historical lore

5. **The Combat Analyst** (GPT-3.5-turbo)
   - Detailed combat breakdowns
   - Tactical analysis
   - Damage tracking

6. **The Session Chronicler** (GPT-4o)
   - Comprehensive summary
   - Progress tracking
   - Next session hooks

### Usage:
```bash
# Full multi-persona analysis
python scripts/test_multipersona.py \
  --transcript path/to/transcript.txt \
  --output output_directory

# Specific personas only
python scripts/test_multipersona.py \
  --transcript path/to/transcript.txt \
  --personas narrator character_chronicler \
  --output output_directory
```

### Output:
- Individual analysis files for each persona
- `session_notes_multipersona_*.txt` - Combined comprehensive notes
- All standard outputs (cleaned transcript, speaker info)

## 3. Quick Multi-Persona (Budget Option)

**Cost**: ~$0.36 per session
**Time**: ~5-8 minutes

Uses only the cheaper personas (Rules Lawyer, Lorekeeper, Combat Analyst) for focused mechanical and world-building analysis.

### Usage:
```bash
python scripts/test_multipersona.py \
  --transcript path/to/transcript.txt \
  --quick \
  --output output_directory
```

## Choosing the Right Option

### Use Standard Processing when:
- You want a good balance of cost and quality
- You need general session notes
- Processing time is a concern

### Use Full Multi-Persona when:
- You want the richest possible analysis
- Multiple players need different perspectives
- You're willing to pay more for comprehensive notes
- You want to catch details that might be missed

### Use Quick Multi-Persona when:
- Budget is tight
- You mainly care about mechanics and lore
- You don't need deep character analysis

## Cost Comparison

For a typical 3-hour session (~140K characters):

| Method | Cost | Personas | Output Quality |
|--------|------|----------|----------------|
| Standard | $0.55 | N/A | Good general notes |
| Quick Multi | $0.36 | 3 cheap | Focused on mechanics/lore |
| Full Multi | $1.70 | All 6 | Comprehensive analysis |

## Preview Before Processing

Always preview costs before processing:

```bash
# Preview standard processing
python scripts/process_transcript_only.py \
  --transcript path/to/transcript.txt \
  --preview

# Preview multi-persona
python scripts/test_multipersona.py \
  --transcript path/to/transcript.txt \
  --preview

# Preview quick multi-persona
python scripts/test_multipersona.py \
  --transcript path/to/transcript.txt \
  --preview --quick
```

## Integration with Main Pipeline

To use multi-persona processing in the main pipeline, update the main processor:

```python
# In main.py, after transcript is generated:
from .transcript_processor_multipersona import MultiPersonaTranscriptProcessor

# Replace standard processing with:
if use_multipersona:
    processor = MultiPersonaTranscriptProcessor(api_key)
    notes, path = processor.process_transcript_multipersona(transcript_path, output_dir)
```

## Benefits of Multi-Persona Approach

1. **Comprehensive Coverage**: Different personas catch different details
2. **Parallel Processing**: Analyses run concurrently for speed
3. **Specialized Focus**: Each persona is optimized for their domain
4. **Richer Output**: Multiple perspectives create more complete notes
5. **Flexibility**: Choose which personas to use based on needs

## Example Outputs

### Standard Processing:
```
Session Summary: The party encountered...
Key Events: Combat with goblins...
Important NPCs: Shopkeeper named...
```

### Multi-Persona:
```
## The Narrator's Tale
The session opened with tension as...

## Rules & Mechanics
- Initiative: Olivia 18, Red 15...
- Spells Cast: Bless (Olivia, Level 1)...

## Character Moments
Silas showed growth when...
Notable quote: "That was supposed to be funny!"

## World Lore
New Location: The Rocket Ship...
NPC: Jasper (ally, fighter)...

[etc...]
```