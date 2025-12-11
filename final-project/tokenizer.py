#!/usr/bin/env python

import re

def tokenize(source_code):
    """Tokenize source code into tokens"""
    # Define token patterns
    patterns = [
        (r'\s+', None),  # Whitespace (ignored)
        (r'//[^\n]*', None),  # Comments (ignored)
        (r'\b(true|false)\b', lambda m: ('boolean', m.group() == 'true')),
        (r'\bnull\b', 'null'),
        (r'\b(and|or|not)\b', lambda m: ('&&' if m.group() == 'and' else 
                                        '||' if m.group() == 'or' else 
                                        '!' if m.group() == 'not' else m.group())),
        (r'\b(function|return|extern|if|else|while|for|break|continue|print|import|exit|assert)\b', lambda m: m.group()),
        (r'\d*\.\d+|\d+\.\d*|\d+', lambda m: ('number', float(m.group()) if '.' in m.group() else int(m.group()))),
        (r'"[^"\\]*(?:\\.[^"\\]*)*"', lambda m: ('string', m.group()[1:-1].replace('\\"', '"').replace('\\\\', '\\'))),
        (r'[a-zA-Z_][a-zA-Z0-9_]*', 'identifier'),
        (r'==|!=|<=|>=|&&|\|\|', lambda m: m.group()),
        (r'[+\-*/%=<>!&|(),{}\[\].,:;]', lambda m: m.group()),
        (r'.', 'error')
    ]
    
    tokens = []
    position = 0
    line = 1
    line_start = 0
    
    while position < len(source_code):
        matched = False
        for pattern, handler in patterns:
            regex = re.compile(pattern)
            match = regex.match(source_code, position)
            if match:
                matched = True
                text = match.group()
                start_pos = position
                position = match.end()
                
                # Update line count
                newlines = text.count('\n')
                if newlines > 0:
                    line += newlines
                    line_start = position - len(text) + text.rfind('\n') + 1
                
                # Skip whitespace and comments
                if handler is None:
                    break
                
                # Handle the token
                if callable(handler):
                    result = handler(match)
                    if isinstance(result, tuple):
                        tag, value = result
                        col = start_pos - line_start + 1
                        tokens.append({
                            "tag": tag,
                            "value": value,
                            "position": start_pos,
                            "line": line,
                            "column": col
                        })
                    else:
                        col = start_pos - line_start + 1
                        tokens.append({
                            "tag": result,
                            "value": result,
                            "position": start_pos,
                            "line": line,
                            "column": col
                        })
                elif handler == 'identifier':
                    col = start_pos - line_start + 1
                    tokens.append({
                        "tag": "identifier",
                        "value": text,
                        "position": start_pos,
                        "line": line,
                        "column": col
                    })
                elif handler == 'null':
                    col = start_pos - line_start + 1
                    tokens.append({
                        "tag": "null",
                        "position": start_pos,
                        "line": line,
                        "column": col
                    })
                elif handler == 'error':
                    raise SyntaxError(f"Unexpected character '{text}' at line {line}, column {col}")
                break
        
        if not matched:
            raise SyntaxError(f"Failed to tokenize at position {position}")
    
    # Add EOF marker
    tokens.append({"tag": None, "position": position, "line": line})
    return tokens

if __name__ == "__main__":
    # Test the tokenizer
    test_code = 'x = 5 + 3; print "hello"'
    print("Testing tokenizer...")
    tokens = tokenize(test_code)
    for token in tokens:
        print(token)