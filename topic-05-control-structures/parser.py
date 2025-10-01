from tokenizer import tokenize

"""
parser.py -- implement parser for simple expressions

Accept a string of tokens, return an AST expressed as stack of dictionaries
"""

ebnf = """

    factor = <number> | <identifier> | "(" expression ")" | "!" factor | "-" factor
    term = factor { "*"|"/" factor }
    arithmetic_expression = term { "+"|"-" term }
    relational_expression = arithmetic_expression { ("<" | ">" | "<=" | ">=" | "==" | "!=") arithmetic_expression } ;
    logical_factor = relational_expression
    logical_term = logical_factor { "&&" logical_factor }
    logical_expression = logical_term { "||" logical_term }
    expression = logical_expression

    statement_block = "{" statement { ";" statement } "}"

    if_statement = "if" "(" expression ")" statement_block [ "else" statement_block ]

    statement = <print> expression | expression { "=" expression } | statement_block | if _statement 
    program = expression { ";" expression }
"""


def parse_factor(tokens):
    """
    factor = <number> | <identifier> | "(" expression ")" | "!" factor | "-" factor
    """
    token = tokens[0]
    if token["tag"] == "number":
        return {
            "tag":"number",
            "value": token["value"]
        }, tokens[1:]
    if token["tag"] == "identifier":
        return {
            "tag":"identifier",
            "value": token["value"]
        }, tokens[1:]
    if token["tag"] == "(":
        ast, tokens = parse_expression(tokens[1:])
        assert tokens[0]["tag"] == ")"
        return ast, tokens[1:]
    if token["tag"] == "-":
        ast, tokens = parse_factor(tokens[1:])
        return {
            "tag": "negate",
            "value": ast,
        }, tokens
    if token["tag"] == "!":
        ast, tokens = parse_factor(tokens[1:])
        return {
            "tag": "not",
            "value": ast,
        }, tokens
    raise Exception(f"Unexpected token '{token['tag']}' at position {token['position']}.")

def test_parse_factor():
    """
    factor = <number> | <identifier> | "(" expression ")" | "!" factor | "-" factor
    """
    print("testing parse_factor()")
    for s in ["1","22","333"]:
        tokens = tokenize(s)
        ast, tokens = parse_factor(tokens)
        assert ast=={'tag': 'number', 'value': int(s)}
        assert tokens[0]['tag'] == None 
    for s in ["(1)","(22)"]:
        tokens = tokenize(s)
        ast, tokens = parse_factor(tokens)
        s_n = s.replace("(","").replace(")","")
        assert ast=={'tag': 'number', 'value': int(s_n)}
        assert tokens[0]['tag'] == None 
    tokens = tokenize("(2+3)")
    ast, tokens = parse_factor(tokens)
    assert ast == {'tag': '+', 'left': {'tag': 'number', 'value': 2}, 'right': {'tag': 'number', 'value': 3}}
    tokens = tokenize("x+y+z")
    ast, tokens = parse_factor(tokens)
    assert ast == {'tag': 'identifier', 'value': 'x'}
    assert tokens == [{'tag': '+', 'position': 1, 'value': '+'}, {'tag': 'identifier', 'position': 2, 'value': 'y'}, {'tag': '+', 'position': 3, 'value': '+'}, {'tag': 'identifier', 'position': 4, 'value': 'z'}, {'tag': None, 'value': None, 'position': 5}]
    tokens = tokenize("-3")
    ast, tokens = parse_factor(tokens)
    assert ast == {'tag': 'negate', 'value': {'tag': 'number', 'value': 3}}
    tokens = tokenize("-3+2")
    ast, tokens = parse_factor(tokens)


def parse_term(tokens):
    """
    term = factor { "*"|"/" factor }
    """
    node, tokens = parse_factor(tokens)
    while tokens[0]["tag"] in ["*","/"]:
        tag = tokens[0]["tag"]
        right_node, tokens = parse_factor(tokens[1:])
        node = {"tag":tag, "left":node, "right":right_node}

    return node, tokens

def test_parse_term():
    """
    term = factor { "*"|"/" factor }
    """
    print("testing parse_term()")
    for s in ["1","22","333"]:
        tokens = tokenize(s)
        ast, tokens = parse_term(tokens)
        assert ast=={'tag': 'number', 'value': int(s)}
        assert tokens[0]['tag'] == None 
    tokens = tokenize("2*4")
    ast, tokens = parse_term(tokens)
    assert ast == {'tag': '*', 'left': {'tag': 'number', 'value': 2}, 'right': {'tag': 'number', 'value': 4}}
    tokens = tokenize("2*4/6")
    ast, tokens = parse_term(tokens)
    assert ast == {'tag': '/', 'left': {'tag': '*', 'left': {'tag': 'number', 'value': 2}, 'right': {'tag': 'number', 'value': 4}}, 'right': {'tag': 'number', 'value': 6}}

def parse_arithmetic_expression(tokens):
    """
    arithmetic_expression = term { "+"|"-" term }
    """
    node, tokens = parse_term(tokens)
    while tokens[0]["tag"] in ["+","-"]:
        tag = tokens[0]["tag"]
        right_node, tokens = parse_term(tokens[1:])
        node = {"tag":tag, "left":node, "right":right_node}

    return node, tokens

def test_parse_arithmetic_expression():
    """
    expression = term { "+"|"-" term }
    """
    print("testing parse_arithmetic_expression()")
    for s in ["1","22","333"]:
        tokens = tokenize(s)
        ast, tokens = parse_expression(tokens)
        assert ast=={'tag': 'number', 'value': int(s)}
        assert tokens[0]['tag'] == None 
    tokens = tokenize("2*4")
    ast, tokens = parse_expression(tokens)
    assert ast == {'tag': '*', 'left': {'tag': 'number', 'value': 2}, 'right': {'tag': 'number', 'value': 4}}
    tokens = tokenize("1+2*4")
    ast, tokens = parse_expression(tokens)
    assert ast == {'tag': '+', 'left': {'tag': 'number', 'value': 1}, 'right': {'tag': '*', 'left': {'tag': 'number', 'value': 2}, 'right': {'tag': 'number', 'value': 4}}}
    tokens = tokenize("1+(2+3)*4")
    ast, tokens = parse_expression(tokens)
    assert ast == {'tag': '+', 'left': {'tag': 'number', 'value': 1}, 'right': {'tag': '*', 'left': {'tag': '+', 'left': {'tag': 'number', 'value': 2}, 'right': {'tag': 'number', 'value': 3}}, 'right': {'tag': 'number', 'value': 4}}}

def parse_relational_expression(tokens):
    """
    relational_expression = arithmetic_expression { ("<" | ">" | "<=" | ">=" | "==" | "!=") arithmetic_expression } ;
    """
    node, tokens = parse_arithmetic_expression(tokens)
    while tokens[0]["tag"] in [ "<" , ">" , "<=" , ">=" , "==" , "!=" ]:
        tag = tokens[0]["tag"]
        right_node, tokens = parse_arithmetic_expression(tokens[1:])
        node = {"tag":tag, "left":node, "right":right_node}

    return node, tokens

def test_parse_relational_expression():
    """
    relational_expression = arithmetic_expression { ("<" | ">" | "<=" | ">=" | "==" | "!=") arithmetic_expression } ;
    """
    print("testing parse_relational_expression()")
    for op in [ "<" , ">" , "<=" , ">=" , "==" , "!=" ]:
        tokens = tokenize(f"1{op}2")
        ast, tokens = parse_relational_expression(tokens)
        assert ast == {'tag': op, 'left': {'tag': 'number', 'value': 1}, 'right': {'tag': 'number', 'value': 2}}


# LOGICAL EXPRESSIONS


def parse_logical_factor(tokens):
    """
    logical_factor = relational_expression
    """
    return parse_relational_expression(tokens)


def test_parse_logical_factor():
    """
    logical_factor = relational_expression
    """
    print("testing parse_logical_factor...")
    assert parse_logical_factor(tokenize("x"))[0] == {"tag": "identifier", "value": "x"}
    assert parse_logical_factor(tokenize("!x"))[0] == {
        "tag": "not",
        "value": {"tag": "identifier", "value": "x"},
    }


def parse_logical_term(tokens):
    """
    logical_term = logical_factor { "&&" logical_factor }
    """
    node, tokens = parse_logical_factor(tokens)
    while tokens[0]["tag"] == "&&":
        tag = tokens[0]["tag"]
        next_node, tokens = parse_logical_factor(tokens[1:])
        node = {"tag": tag, "left": node, "right": next_node}
    return node, tokens


def test_parse_logical_term():
    """
    logical_term = logical_factor { "&&" logical_factor }
    """
    print("testing parse_logical_term...")
    assert parse_logical_term(tokenize("x"))[0] == {"tag": "identifier", "value": "x"}
    assert parse_logical_term(tokenize("x&&y"))[0] == {
        "tag": "&&",
        "left": {"tag": "identifier", "value": "x"},
        "right": {"tag": "identifier", "value": "y"},
    }
    assert parse_logical_term(tokenize("x&&y&&z"))[0] == {
        "tag": "&&",
        "left": {
            "tag": "&&",
            "left": {"tag": "identifier", "value": "x"},
            "right": {"tag": "identifier", "value": "y"},
        },
        "right": {"tag": "identifier", "value": "z"},
    }


def parse_logical_expression(tokens):
    """
    logical_expression = logical_term { "||" logical_term }
    """
    node, tokens = parse_logical_term(tokens)
    while tokens[0]["tag"] == "||":
        tag = tokens[0]["tag"]
        next_node, tokens = parse_logical_term(tokens[1:])
        node = {"tag": tag, "left": node, "right": next_node}
    return node, tokens


def test_parse_logical_expression():
    """
    logical_expression = logical_term { "||" logical_term }
    """
    print("testing parse_logical_expression...")

    assert parse_logical_expression(tokenize("x"))[0] == {
        "tag": "identifier",
        "value": "x",
    }
    assert parse_logical_expression(tokenize("x||y"))[0] == {
        "tag": "||",
        "left": {"tag": "identifier", "value": "x"},
        "right": {"tag": "identifier", "value": "y"},
    }
    assert parse_logical_expression(tokenize("x||y&&z"))[0] == {
        "tag": "||",
        "left": {"tag": "identifier", "value": "x"},
        "right": {
            "tag": "&&",
            "left": {"tag": "identifier", "value": "y"},
            "right": {"tag": "identifier", "value": "z"},
        },
    }


def parse_expression(tokens):
    return parse_logical_expression(tokens)

def test_parse_expression():
    print("testing parse_expression()")
    ast1, _ = parse_expression(tokenize("1+1"))
    ast2, _ = parse_logical_expression(tokenize("1+1"))
    assert ast1 == ast2

def parse_statement_block(tokens):
    """
    statement_block = "{" statement { ";" statement } "}"
    """ 
    ast = {"tag": "block", "statements": []}
    assert tokens[0]["tag"] == "{"
    tokens = tokens[1:]
    if tokens[0]["tag"] != "}":
        statement, tokens = parse_statement(tokens) 
        ast["statements"].append(statement) 
    while tokens[0]["tag"] == ";":
        statement, tokens = parse_statement(tokens[1:])  
        ast["statements"].append(statement) 
    assert tokens[0]["tag"] == "}"
    return ast, tokens[1:]

def test_parse_statement_block():
    """
    statement_block = "{" statement { ";" statement } "}"
    """ 
    print("testing parse_statement_block()...")
    ast = parse_statement_block(tokenize("{}"))[0]
    assert ast == {'tag': 'block', 'statements': []}
    ast = parse_statement_block(tokenize("{i=2}"))[0]
    assert ast == {'tag': 'block', 'statements': [{'tag': 'assign', 'target': {'tag': 'identifier', 'value': 'i'}, 'value': {'tag': 'number', 'value': 2}}]}
    ast = parse_statement_block(tokenize("{i=2;k=3}"))[0]
    assert ast == {'tag': 'block', 
        'statements': [
            {'tag': 'assign', 'target': {'tag': 'identifier', 'value': 'i'}, 'value': {'tag': 'number', 'value': 2}}, 
            {'tag': 'assign', 'target': {'tag': 'identifier', 'value': 'k'}, 'value': {'tag': 'number', 'value': 3}}
            ]}


def parse_if_statement(tokens):
    """
    if_statement = "if" "(" expression ")" statement_block [ "else" statement_block ]
    """
    assert tokens[0]["tag"] == "if"
    tokens = tokens[1:]
    assert tokens[0]["tag"] == "("
    tokens = tokens[1:]
    condition, tokens = parse_expression(tokens)
    assert tokens[0]["tag"] == ")"
    tokens = tokens[1:]
    then_statement, tokens = parse_statement_block(tokens)
    else_statement = None
    if tokens[0]["tag"] == "else":
        tokens = tokens[1:]
        else_statement, tokens = parse_statement_block(tokens)
    ast = {
        "tag":"if",
        "condition":condition,
        "then":then_statement,
        "else":else_statement,
    }
    return ast, tokens

def test_parse_if_statement():
    """
    if_statement = "if" "(" expression ")" statement_block [ "else" statement_block ]
    """
    print("testing parse_if_statement")
    ast , _= parse_if_statement(tokenize("if(1){print(2)}"))
    assert ast == {
        'tag': 'if', 
            'condition': {'tag': 'number', 'value': 1}, 
        'then': 
            {'tag': 'block', 'statements': [
                {'tag': 'print', 'value': {'tag': 'number', 'value': 2}}]}, 
        'else': None
    }    
    ast , _= parse_if_statement(
            tokenize("if(1){print(2)}else{print(3)}")
        )
    assert ast == {'tag': 'if', 'condition': {'tag': 'number', 'value': 1}, 'then': {'tag': 'block', 'statements': [{'tag': 'print', 'value': {'tag': 'number', 'value': 2}}]}, 'else': {'tag': 'block', 'statements': [{'tag': 'print', 'value': {'tag': 'number', 'value': 3}}]}}

def parse_while_statement(tokens):
    """
    while_statement = "while" "(" expression ")" statement_block 
    """
    assert tokens[0]["tag"] == "while"
    tokens = tokens[1:]
    assert tokens[0]["tag"] == "("
    tokens = tokens[1:]
    condition, tokens = parse_expression(tokens)
    assert tokens[0]["tag"] == ")"
    tokens = tokens[1:]
    do_statement, tokens = parse_statement_block(tokens)
    ast = {
        "tag":"while",
        "condition":condition,
        "do":do_statement,
    }
    return ast, tokens

def test_parse_while_statement():
    """
    while_statement = "while" "(" expression ")" statement_block 
    """
    print("testing parse_while_statement")
    ast , _= parse_while_statement(tokenize("while(1){print(2)}"))
    assert ast == {
        'tag': 'while', 
            'condition': {'tag': 'number', 'value': 1}, 
        'do': 
            {'tag': 'block', 'statements': [
                {'tag': 'print', 'value': {'tag': 'number', 'value': 2}}]}
    }    

def parse_statement(tokens):
    """
    statement = <print> expression | statement_block | expression { "=" expression } | if_statement | while_statement
    """
    if tokens[0]["tag"] == "print":
        value_ast, tokens = parse_expression(tokens[1:])
        ast = {
            'tag':'print',
            'value': value_ast
        }
        return ast, tokens
    if tokens[0]["tag"] == "{":
        ast, tokens = parse_statement_block(tokens)
        return ast, tokens
    if tokens[0]["tag"] == "if":
        ast, tokens = parse_if_statement(tokens)
        return ast, tokens
    if tokens[0]["tag"] == "while":
        ast, tokens = parse_while_statement(tokens)
        return ast, tokens
    else:
        ast, tokens = parse_expression(tokens)
        if tokens[0]["tag"] == "=":
            tokens = tokens[1:]
            value_ast, tokens = parse_expression(tokens)
            ast = {
                'tag':'assign',
                'target':ast,
                'value':value_ast
            }
        return ast, tokens

def test_parse_statement():
    """
    statement = <print> expression | expression
    """
    print("testing parse_statement()")
    tokens = tokenize("1+(2+3)*4")
    ast, tokens = parse_statement(tokens)
    assert ast == {'tag': '+', 'left': {'tag': 'number', 'value': 1}, 'right': {'tag': '*', 'left': {'tag': '+', 'left': {'tag': 'number', 'value': 2}, 'right': {'tag': 'number', 'value': 3}}, 'right': {'tag': 'number', 'value': 4}}}
    tokens = tokenize("print 2*4")
    ast, tokens = parse_statement(tokens)
    assert ast == {'tag': 'print', 'value': {'tag': '*', 'left': {'tag': 'number', 'value': 2}, 'right': {'tag': 'number', 'value': 4}}}
    tokens = tokenize("x=3")
    ast, tokens = parse_statement(tokens)
    assert ast == {'tag': 'assign', 'target': {'tag': 'identifier', 'value': 'x'}, 'value': {'tag': 'number', 'value': 3}}
        # statement block
    ast, _ = parse_statement(tokenize("{print 1}"))
    assert ast == {'tag': 'block', 'statements': [{'tag': 'print', 'value': {'tag': 'number', 'value': 1}}]}
    tokens = tokenize("if (x==3) {y=2}")
    ast1, _ = parse_statement(tokens)
    ast2, _ = parse_if_statement(tokens)
    assert ast1 == ast2
    tokens = tokenize("while (x<3) {x=x+1}")
    ast1, _ = parse_statement(tokens)
    ast2, _ = parse_while_statement(tokens)
    assert ast1 == ast2


def parse_program(tokens):
    """
    program = [ statement { ";" statement } ] ;
    """
    statements = []
    if tokens[0]["tag"]:
        statement, tokens = parse_statement(tokens)
        statements.append(statement)
        while tokens[0]["tag"] == ";":
            tokens = tokens[1:]
            statement, tokens = parse_statement(tokens)
            statements.append(statement)
    assert (
        tokens[0]["tag"] == None
    ), f"Expected end of input at position {tokens[0]['position']}, got [{tokens[0]}]"
    return {"tag": "program", "statements": statements}, tokens[1:]

def test_parse_program():
    """program = [ statement { ";" statement } ]"""
    print("testing parse_program...")
    ast, tokens = parse_program(tokenize("print 1; print 2"))
    assert ast == {
        "tag": "program",
        "statements": [
            {"tag": "print", "value": {"tag": "number", "value": 1}},
            {"tag": "print", "value": {"tag": "number", "value": 2}},
        ],
    }

def parse(tokens):
    ast, _ = parse_program(tokens)
    return ast

def test_parse():
    """
        program = expression
    """
    print("testing parse()")
    tokens = tokenize("1+(2+3)*4")
    ast1, _ = parse_program(tokens)
    ast2 = parse(tokens)
    assert ast1 == ast2, "parse() is not evaluating via parse_program()"



if __name__ == "__main__":
    test_parse_factor()
    test_parse_term()
    test_parse_arithmetic_expression()
    test_parse_relational_expression()
    test_parse_logical_factor()
    test_parse_logical_term()
    test_parse_logical_expression()
    test_parse_expression()
    test_parse_statement_block()
    test_parse_if_statement()
    test_parse_while_statement()
    test_parse_statement()
    test_parse_program()
    test_parse()
    print("done.")
