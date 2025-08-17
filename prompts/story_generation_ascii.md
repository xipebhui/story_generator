# Story Generation Prompt for ASCII-Only Output

## CRITICAL REQUIREMENT
You MUST generate ALL text using ONLY standard ASCII characters (character codes 0-127).

## Character Rules
1. **Quotation Marks**: Use ONLY straight quotes
   - Use " for double quotes (NOT " or ")  
   - Use ' for single quotes (NOT ' or ')
   
2. **Punctuation**: Use standard ASCII punctuation
   - Use ... for ellipsis (NOT …)
   - Use - for dash (NOT — or –)
   - Use regular spaces (NOT non-breaking spaces)
   
3. **Text Formatting**:
   - NO smart quotes or curly quotes
   - NO em dashes or en dashes
   - NO Unicode ellipsis
   - NO special spaces or invisible characters
   - NO accented characters

## Example Output Format
```
CORRECT: "Hello," she said. "It's a beautiful day..."
WRONG: "Hello," she said. "It's a beautiful day…"

CORRECT: The plan was simple - wait and see.
WRONG: The plan was simple — wait and see.
```

## Story Generation Guidelines
Generate an engaging story while strictly following the ASCII-only requirement. The story should be:
- Emotionally engaging
- Well-structured with clear dialogue
- Using ONLY standard ASCII characters
- Free from any Unicode or special characters

Remember: Every single character must be within ASCII range (0-127). This is absolutely critical for the text-to-speech system to work correctly.