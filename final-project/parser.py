#!/usr/bin/env python

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
    
    def peek(self):
        """Look at next token without consuming it"""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return {"tag": None}
    
    def consume(self, expected_tag=None):
        """Consume current token"""
        if self.pos >= len(self.tokens):
            raise SyntaxError("Unexpected end of input")
        
        token = self.tokens[self.pos]
        
        if expected_tag and token.get("tag") != expected_tag:
            raise SyntaxError(f"Expected {expected_tag}, got {token.get('tag')}")
        
        self.pos += 1
        return token
    
    def parse(self):
        """Parse the entire program"""
        # Wrap in a statement list for compatibility
        eof = self.tokens[-1]
        wrapped_tokens = [{"tag": "{"}] + self.tokens[:-1] + [{"tag": "}"}] + [eof]
        self.tokens = wrapped_tokens
        self.pos = 0
        
        ast = self.parse_statement_list()
        ast["tag"] = "program"
        return ast
    
    def parse_statement_list(self):
        """Parse { statement ; statement ... }"""
        self.consume("{")
        statements = []
        
        while self.peek()["tag"] != "}":
            if self.peek()["tag"] == ";":
                self.consume(";")
                continue
            
            statement = self.parse_statement()
            statements.append(statement)
            
            # Skip semicolon for block statements
            if statement["tag"] in ["if", "while", "function"]:
                continue
            if statement["tag"] == "assign" and statement.get("value", {}).get("tag") == "function":
                continue
            
            if self.peek()["tag"] != "}":
                self.consume(";")
        
        self.consume("}")
        return {"tag": "statement_list", "statements": statements}
    
    def parse_statement(self):
        """Parse a single statement"""
        token = self.peek()
        
        if token["tag"] == "if":
            return self.parse_if()
        elif token["tag"] == "while":
            return self.parse_while()
        elif token["tag"] == "function":
            return self.parse_function_statement()
        elif token["tag"] == "return":
            return self.parse_return()
        elif token["tag"] == "print":
            return self.parse_print()
        elif token["tag"] == "exit":
            return self.parse_exit()
        elif token["tag"] == "import":
            return self.parse_import()
        elif token["tag"] == "break":
            return self.parse_break()
        elif token["tag"] == "continue":
            return self.parse_continue()
        elif token["tag"] == "assert":
            return self.parse_assert()
        else:
            return self.parse_expression()
    
    def parse_if(self):
        """Parse if statement"""
        self.consume("if")
        self.consume("(")
        condition = self.parse_expression()
        self.consume(")")
        then_branch = self.parse_statement_list()
        
        result = {"tag": "if", "condition": condition, "then": then_branch}
        
        if self.peek()["tag"] == "else":
            self.consume("else")
            result["else"] = self.parse_statement_list()
        
        return result
    
    def parse_while(self):
        """Parse while statement"""
        self.consume("while")
        self.consume("(")
        condition = self.parse_expression()
        self.consume(")")
        body = self.parse_statement_list()
        return {"tag": "while", "condition": condition, "do": body}
    
    def parse_function_statement(self):
        """Parse function statement: function name(params) { body }"""
        self.consume("function")
        name_token = self.consume("identifier")
    
        # Always expect parentheses
        self.consume("(")
        parameters = []
    
        if self.peek()["tag"] == "identifier":
            parameters.append(self.consume("identifier"))
            while self.peek()["tag"] == ",":
                self.consume(",")
                parameters.append(self.consume("identifier"))
    
        self.consume(")")
        body = self.parse_statement_list()
    
        # Convert parameters to identifier nodes
        param_nodes = []
        for param in parameters:
            param_nodes.append({"tag": "identifier", "value": param["value"]})
    
        # Return as assignment: name = function(params) { body }
        return {
            "tag": "assign",
            "target": {"tag": "identifier", "value": name_token["value"]},
            "value": {
                "tag": "function",
                "parameters": param_nodes,
                "body": body
            }
        }
    
    def parse_return(self):
        """Parse return statement"""
        self.consume("return")
        
        if self.peek()["tag"] in [";", "}", None]:
            return {"tag": "return"}
        else:
            value = self.parse_expression()
            return {"tag": "return", "value": value}
    
    def parse_print(self):
        """Parse print statement"""
        self.consume("print")
        
        if self.peek()["tag"] in [";", "}", None]:
            return {"tag": "print", "value": None}
        else:
            value = self.parse_expression()
            return {"tag": "print", "value": value}
    
    def parse_exit(self):
        """Parse exit statement"""
        self.consume("exit")
        
        if self.peek()["tag"] in [";", "}", None]:
            return {"tag": "exit", "value": None}
        else:
            value = self.parse_expression()
            return {"tag": "exit", "value": value}
    
    def parse_import(self):
        """Parse import statement"""
        self.consume("import")
        value = self.parse_expression()
        return {"tag": "import", "value": value}
    
    def parse_break(self):
        """Parse break statement"""
        self.consume("break")
        return {"tag": "break"}
    
    def parse_continue(self):
        """Parse continue statement"""
        self.consume("continue")
        return {"tag": "continue"}
    
    def parse_assert(self):
        """Parse assert statement"""
        self.consume("assert")
        condition = self.parse_expression()
        
        if self.peek()["tag"] == ",":
            self.consume(",")
            explanation = self.parse_expression()
            return {"tag": "assert", "condition": condition, "explanation": explanation}
        else:
            return {"tag": "assert", "condition": condition}
    
    def parse_expression(self):
        """Parse an expression"""
        return self.parse_assignment_expression()
    
    def parse_assignment_expression(self):
        """Parse assignment expression: target = value"""
        # Check for extern keyword
        extern = False
        if self.peek()["tag"] == "extern":
            extern = True
            self.consume("extern")
        
        left = self.parse_logical_expression()
        
        if self.peek()["tag"] == "=":
            self.consume("=")
            right = self.parse_assignment_expression()
            
            if extern:
                if left["tag"] != "identifier":
                    raise SyntaxError("extern can only be used with simple identifiers")
                left["extern"] = True
            
            return {"tag": "assign", "target": left, "value": right}
        
        if extern:
            raise SyntaxError("Can't use extern without assignment")
        
        return left
    
    def parse_logical_expression(self):
        """Parse logical expression with ||"""
        node = self.parse_logical_term()
        
        while self.peek()["tag"] == "||":
            self.consume("||")
            right = self.parse_logical_term()
            node = {"tag": "||", "left": node, "right": right}
        
        return node
    
    def parse_logical_term(self):
        """Parse logical term with &&"""
        node = self.parse_logical_factor()
        
        while self.peek()["tag"] == "&&":
            self.consume("&&")
            right = self.parse_logical_factor()
            node = {"tag": "&&", "left": node, "right": right}
        
        return node
    
    def parse_logical_factor(self):
        """Parse logical factor (relational expression)"""
        return self.parse_relational_expression()
    
    def parse_relational_expression(self):
        """Parse relational expression with comparisons"""
        node = self.parse_arithmetic_expression()
        
        while self.peek()["tag"] in ["<", ">", "<=", ">=", "==", "!="]:
            op = self.consume()
            right = self.parse_arithmetic_expression()
            node = {"tag": op["tag"], "left": node, "right": right}
        
        return node
    
    def parse_arithmetic_expression(self):
        """Parse arithmetic expression with + and -"""
        node = self.parse_term()
        
        while self.peek()["tag"] in ["+", "-"]:
            op = self.consume()
            right = self.parse_term()
            node = {"tag": op["tag"], "left": node, "right": right}
        
        return node
    
    def parse_term(self):
        """Parse term with *, /, %"""
        node = self.parse_factor()
        
        while self.peek()["tag"] in ["*", "/", "%"]:
            op = self.consume()
            right = self.parse_factor()
            node = {"tag": op["tag"], "left": node, "right": right}
        
        return node
    
    def parse_factor(self):
        """Parse factor (unary operators or simple expressions)"""
        token = self.peek()
        
        if token["tag"] == "-":
            self.consume("-")
            value = self.parse_factor()
            return {"tag": "negate", "value": value}
        elif token["tag"] == "!":
            self.consume("!")
            value = self.parse_factor()
            return {"tag": "not", "value": value}
        else:
            return self.parse_complex_expression()
    
    def parse_complex_expression(self):
        """Parse complex expression with indexing, calls, etc."""
        node = self.parse_simple_expression()
        
        while True:
            token = self.peek()
            
            if token["tag"] == "[":
                self.consume("[")
                index = self.parse_expression()
                self.consume("]")
                node = {"tag": "complex", "base": node, "index": index}
            elif token["tag"] == ".":
                self.consume(".")
                identifier = self.consume("identifier")
                node = {"tag": "complex", "base": node, "index": {"tag": "string", "value": identifier["value"]}}
            elif token["tag"] == "(":
                self.consume("(")
                arguments = []
                
                if self.peek()["tag"] != ")":
                    arguments.append(self.parse_expression())
                    while self.peek()["tag"] == ",":
                        self.consume(",")
                        arguments.append(self.parse_expression())
                
                self.consume(")")
                node = {"tag": "call", "function": node, "arguments": arguments}
            else:
                break
        
        return node
    
    def parse_simple_expression(self):
        """Parse simple expression: literals, identifiers, parentheses"""
        token = self.peek()
        
        if token["tag"] == "identifier":
            tok = self.consume("identifier")
            return {"tag": "identifier", "value": tok["value"]}
        elif token["tag"] == "number":
            tok = self.consume("number")
            return {"tag": "number", "value": tok["value"]}
        elif token["tag"] == "string":
            tok = self.consume("string")
            return {"tag": "string", "value": tok["value"]}
        elif token["tag"] == "boolean":
            tok = self.consume("boolean")
            return {"tag": "boolean", "value": tok["value"]}
        elif token["tag"] == "null":
            self.consume("null")
            return {"tag": "null"}
        elif token["tag"] == "[":
            return self.parse_list()
        elif token["tag"] == "{":
            return self.parse_object()
        elif token["tag"] == "function":
            return self.parse_function_literal()
        elif token["tag"] == "(":
            self.consume("(")
            expr = self.parse_expression()
            self.consume(")")
            return expr
        else:
            raise SyntaxError(f"Unexpected token: {token['tag']}")
    
    def parse_list(self):
        """Parse list literal: [expr, expr, ...]"""
        self.consume("[")
        items = []
        
        if self.peek()["tag"] != "]":
            items.append(self.parse_expression())
            while self.peek()["tag"] == ",":
                self.consume(",")
                if self.peek()["tag"] == "]":  # Allow trailing comma
                    break
                items.append(self.parse_expression())
        
        self.consume("]")
        return {"tag": "list", "items": items}
    
    def parse_object(self):
        """Parse object literal: {key: value, ...}"""
        self.consume("{")
        items = []
        
        if self.peek()["tag"] != "}":
            key = self.parse_expression()
            self.consume(":")
            value = self.parse_expression()
            items.append({"key": key, "value": value})
            
            while self.peek()["tag"] == ",":
                self.consume(",")
                if self.peek()["tag"] == "}":  # Allow trailing comma
                    break
                key = self.parse_expression()
                self.consume(":")
                value = self.parse_expression()
                items.append({"key": key, "value": value})
        
        self.consume("}")
        return {"tag": "object", "items": items}
    
    def parse_function_literal(self):
        """Parse function literal: function(params) { body }"""
        self.consume("function")
        self.consume("(")
        parameters = []
        
        if self.peek()["tag"] == "identifier":
            parameters.append(self.consume("identifier"))
            while self.peek()["tag"] == ",":
                self.consume(",")
                parameters.append(self.consume("identifier"))
        
        self.consume(")")
        body = self.parse_statement_list()
        
        # Convert parameters to identifier nodes
        param_nodes = []
        for param in parameters:
            param_nodes.append({"tag": "identifier", "value": param["value"]})
        
        return {"tag": "function", "parameters": param_nodes, "body": body}

def parse(tokens):
    """Main parse function"""
    parser = Parser(tokens)
    return parser.parse()

if __name__ == "__main__":
    # Test the parser
    from tokenizer import tokenize
    
    test_code = 'x = 5; print(x + 3)'
    print("Testing parser...")
    tokens = tokenize(test_code)
    ast = parse(tokens)
    import json
    print(json.dumps(ast, indent=2))