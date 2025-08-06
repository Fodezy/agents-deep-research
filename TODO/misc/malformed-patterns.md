# Malformed JSON Patterns - Failure Analysis

## Executive Summary
Local models produce structurally invalid JSON despite explicit instructions. Patterns fall into 5 categories: field corruption, syntax errors, value substitution, structural violations, and formatting issues.

## Pattern Categories

### 1. Field Name Corruption
**Pattern**: Field names broken across lines or with invalid characters
```json
// Example 1: Newlines in field names (actual observed case)
{
  "schema_v

on": 1,
  "research_complete": false,
  "outstanding_gaps": [
    "Develop an understanding of the experiments confirming quantum entanglement"
  ]
}

// Example 2: Non-alphanumeric substitution  
"schema_version": χ

// Example 3: Typos
"schema_tag": 1  // should be "schema_version"
```

### 2. Syntax Errors
**Pattern**: Missing punctuation, quotes, or delimiters
```json
// Example 1: Missing comma between objects
{
  "gap": "research gap",
  "agent": "WebSearchAgent"
}
{  // <- Missing comma here
  "gap": "another gap"
}

// Example 2: Unquoted URLs
"entity_website": https://example.com  // Missing quotes

// Example 3: Mixed quote types
'tasks': [  // Single quotes instead of double
  {
    "gap": "test"
  }
]
```

### 3. Value Substitution
**Pattern**: Wrong data types or values in required fields
```json
// Example 1: Wrong schema version
"schema_version": 2  // Only version 1 supported

// Example 2: Greek letters instead of numbers
"schema_version": χ
```

### 4. Structural Violations
**Pattern**: Invalid JSON structure that breaks parsing
```json
// Example 1: Comments in JSON
{
  "gap": "research area",
  "agent": "SiteCrawlerAgent",
  --(https://physicsworld.com/article)  // <- Invalid comment syntax
  "query": "search term"
}

// Example 2: Incomplete objects
{
  "tasks": [
    {
      "gap": "incomplete  // <- String never closed
```

### 5. Formatting Issues
**Pattern**: Valid JSON but with problematic formatting
```json
// Example 1: Markdown fences
```json
{
  "schema_version": 1
}
```

// Example 2: Excessive whitespace/newlines
{

  "schema_version": 1,

  "tasks": [

    {

      "gap": "test"

    }

  ]

}
```

## Impact Analysis

- **Frequency**: ~40-60% of local model responses contain at least one pattern
- **Severity**: Complete pipeline failure requiring manual intervention
- **Cost**: Each failure requires retry or manual parsing
- **User Impact**: Research queries fail with `OutputParserError`

## Root Causes

1. **Local model limitations**: Unlike cloud models, local models struggle with strict formatting
2. **Instruction drift**: Models "interpret" JSON requirements creatively
3. **Context bleeding**: Previous responses influence formatting choices
4. **Lack of structured constraints**: Text-based instructions are insufficient

## Recommendations

1. **Outlines integration**: Constrain generation at token level
2. **ValidationWrapper**: Single retry with specific error feedback
3. **Schema versioning**: Explicit version control for backward compatibility
4. **Metrics collection**: Track pattern frequency for optimization