#include "trif/parser.hpp"

#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

namespace trif::parser {

using lexer::Token;
using lexer::TokenStream;
using namespace trif::ast;

namespace {

class Parser {
   public:
    explicit Parser(const TokenStream& tokens) : tokens_(tokens) {}

    ModulePtr parse() {
        auto module = make_module();
        while (current().type != "EOF") {
            if (current().type == "NEWLINE" || current().type == "SEMICOLON") {
                consume();
                continue;
            }
            module->body.push_back(parse_statement());
        }
        return module;
    }

   private:
    const TokenStream& tokens_;
    std::size_t index_ = 0;

    const Token& current() const { return tokens_[index_]; }

    const Token& peek(int offset = 1) const { return tokens_[index_ + offset]; }

    const Token& consume(const std::string& expected = {}) {
        const Token& token = current();
        if (!expected.empty() && token.type != expected) {
            throw std::runtime_error("Expected " + expected + " but got " + token.type + " at line " +
                                     std::to_string(token.line));
        }
        ++index_;
        return token;
    }

    bool match(std::initializer_list<std::string> types) {
        for (const auto& type : types) {
            if (current().type == type) {
                ++index_;
                return true;
            }
        }
        return false;
    }

    bool match(const std::string& type) {
        if (current().type == type) {
            ++index_;
            return true;
        }
        return false;
    }

    std::string parse_dotted_name() {
        std::string name = consume("NAME").value;
        std::string result = name;
        while (current().type == "DOT") {
            consume("DOT");
            result += "." + consume("NAME").value;
        }
        return result;
    }

    NodePtr parse_statement() {
        const auto& tok = current();
        if (tok.type == "IMPORT") {
            auto stmt = parse_import_statement();
            optional_newline();
            return stmt;
        }
        if (tok.type == "EXPORT") {
            auto stmt = parse_export_statement();
            optional_newline();
            return stmt;
        }
        if (tok.type == "LET" || tok.type == "CONST") {
            bool is_mutable = tok.type == "LET";
            consume();
            auto stmt = parse_variable_statement(is_mutable, false, false);
            optional_newline();
            return stmt;
        }
        if (tok.type == "FN" || tok.type == "FUNCTION") {
            auto stmt = parse_function_statement(false, false);
            optional_newline();
            return stmt;
        }
        if (tok.type == "RETURN") {
            consume();
            auto node = std::make_shared<Return>();
            if (current().type != "NEWLINE" && current().type != "RBRACE" && current().type != "EOF") {
                node->value = parse_expression();
            }
            optional_newline();
            return node;
        }
        if (tok.type == "IF") {
            consume();
            auto node = std::make_shared<If>();
            node->test = parse_expression();
            node->body = parse_block();
            if (match("ELSE")) {
                node->orelse = parse_block();
            }
            optional_newline();
            return node;
        }
        if (tok.type == "WHILE") {
            consume();
            auto node = std::make_shared<While>();
            node->test = parse_expression();
            node->body = parse_block();
            optional_newline();
            return node;
        }
        if (tok.type == "FOR") {
            consume();
            auto node = std::make_shared<For>();
            node->target = consume("NAME").value;
            consume("IN");
            node->iterator = parse_expression();
            node->body = parse_block();
            optional_newline();
            return node;
        }
        if (tok.type == "SPAWN") {
            consume();
            auto call_expr = parse_expression();
            if (call_expr->kind != NodeKind::Call) {
                throw std::runtime_error("spawn expects a function call");
            }
            auto node = std::make_shared<Spawn>();
            node->call = std::static_pointer_cast<Expression>(call_expr);
            optional_newline();
            return node;
        }
        auto expr = parse_expression();
        if (expr->kind == NodeKind::Name || expr->kind == NodeKind::Attribute) {
            if (current().type == "OP" && current().value == "=") {
                consume("OP");
                auto assign = std::make_shared<Assign>();
                assign->target = expr;
                assign->value = parse_expression();
                optional_newline();
                return assign;
            }
        }
        optional_newline();
        return expr;
    }

    NodePtr parse_import_statement() {
        consume("IMPORT");
        std::optional<std::string> default_target;
        std::vector<std::pair<std::string, std::string>> names;
        std::optional<std::string> namespace_name;

        if (current().type == "STRING") {
            std::string module_name = consume("STRING").value;
            std::optional<std::string> alias;
            if (match("AS")) {
                alias = consume("NAME").value;
            }
            auto node = std::make_shared<Import>();
            node->module = module_name;
            node->alias = alias;
            return node;
        }

        if (current().type == "NAME" && peek().type == "COMMA") {
            default_target = consume("NAME").value;
            consume("COMMA");
            if (current().type == "LBRACE") {
                names = parse_import_specifiers();
            } else {
                throw std::runtime_error("Expected named import list after comma");
            }
        } else if (current().type == "NAME" && peek().type == "FROM") {
            default_target = consume("NAME").value;
        } else if (current().type == "LBRACE") {
            names = parse_import_specifiers();
        } else if (current().type == "OP" && current().value == "*") {
            consume("OP");
            consume("AS");
            namespace_name = consume("NAME").value;
        }

        if (default_target || !names.empty() || namespace_name) {
            consume("FROM");
            std::string module_name = parse_module_specifier();
            auto node = std::make_shared<ImportFrom>();
            node->module = module_name;
            node->names = names;
            node->default_name = default_target;
            node->namespace_name = namespace_name;
            return node;
        }

        std::string module_name = parse_module_specifier();
        std::optional<std::string> alias;
        if (match("AS")) {
            alias = consume("NAME").value;
        }
        auto node = std::make_shared<Import>();
        node->module = module_name;
        node->alias = alias;
        return node;
    }

    NodePtr parse_export_statement() {
        consume("EXPORT");
        if (current().type == "DEFAULT") {
            consume("DEFAULT");
            if (current().type == "FN" || current().type == "FUNCTION") {
                return parse_function_statement(true, true);
            }
            if (current().type == "LET" || current().type == "CONST") {
                bool mut = current().type == "LET";
                consume();
                return parse_variable_statement(mut, true, true);
            }
            auto node = std::make_shared<ExportDefault>();
            node->value = parse_expression();
            return node;
        }
        if (current().type == "FN" || current().type == "FUNCTION") {
            return parse_function_statement(true, false);
        }
        if (current().type == "LET" || current().type == "CONST") {
            bool mut = current().type == "LET";
            consume();
            return parse_variable_statement(mut, true, false);
        }
        if (current().type == "LBRACE") {
            auto node = std::make_shared<ExportNames>();
            node->names = parse_export_specifiers();
            if (match("FROM")) {
                node->source = parse_module_specifier();
            }
            return node;
        }
        throw std::runtime_error("Unsupported export statement");
    }

    std::vector<std::pair<std::string, std::string>> parse_import_specifiers() {
        consume("LBRACE");
        std::vector<std::pair<std::string, std::string>> names;
        while (current().type != "RBRACE") {
            std::string imported = consume("NAME").value;
            std::string alias = imported;
            if (match("AS")) {
                alias = consume("NAME").value;
            }
            names.emplace_back(imported, alias);
            if (!match("COMMA")) {
                break;
            }
        }
        consume("RBRACE");
        return names;
    }

    std::vector<std::pair<std::string, std::string>> parse_export_specifiers() {
        consume("LBRACE");
        std::vector<std::pair<std::string, std::string>> names;
        while (current().type != "RBRACE") {
            std::string local = consume("NAME").value;
            std::string exported = local;
            if (match("AS")) {
                exported = consume("NAME").value;
            }
            names.emplace_back(local, exported);
            if (!match("COMMA")) {
                break;
            }
        }
        consume("RBRACE");
        return names;
    }

    std::string parse_module_specifier() {
        if (current().type == "STRING") {
            return consume("STRING").value;
        }
        return parse_dotted_name();
    }

    NodePtr parse_variable_statement(bool mutable_flag, bool exported, bool is_default) {
        std::string name = consume("NAME").value;
        if (current().type != "OP" || current().value != "=") {
            throw std::runtime_error("Expected '=' in variable declaration");
        }
        consume("OP");
        auto let = std::make_shared<Let>();
        let->name = name;
        let->value = parse_expression();
        let->mutable_flag = mutable_flag;
        let->exported = exported;
        let->is_default = is_default;
        return let;
    }

    NodePtr parse_function_statement(bool exported, bool is_default) {
        consume();
        std::string name;
        if (current().type == "NAME") {
            name = consume("NAME").value;
        } else if (is_default) {
            name = "_default_export";
        } else {
            throw std::runtime_error("Function declaration requires a name");
        }
        consume("LPAREN");
        std::vector<std::string> params;
        if (current().type != "RPAREN") {
            while (true) {
                params.push_back(consume("NAME").value);
                if (!match("COMMA")) {
                    break;
                }
            }
        }
        consume("RPAREN");
        auto node = std::make_shared<FunctionDef>();
        node->name = name;
        node->params = params;
        node->body = parse_block();
        node->exported = exported;
        node->is_default = is_default;
        return node;
    }

    void optional_newline() {
        while (current().type == "NEWLINE" || current().type == "SEMICOLON") {
            consume();
        }
    }

    std::vector<NodePtr> parse_block() {
        consume("LBRACE");
        std::vector<NodePtr> body;
        while (current().type != "RBRACE") {
            if (current().type == "NEWLINE" || current().type == "SEMICOLON") {
                consume();
                continue;
            }
            body.push_back(parse_statement());
        }
        consume("RBRACE");
        return body;
    }

    ExpressionPtr parse_expression() { return parse_or(); }

    ExpressionPtr parse_or() {
        auto expr = parse_and();
        while (current().type == "OP" && current().value == "||") {
            auto node = std::make_shared<BinaryOp>();
            node->left = expr;
            node->op = consume("OP").value;
            node->right = parse_and();
            expr = node;
        }
        return expr;
    }

    ExpressionPtr parse_and() {
        auto expr = parse_equality();
        while (current().type == "OP" && current().value == "&&") {
            auto node = std::make_shared<BinaryOp>();
            node->left = expr;
            node->op = consume("OP").value;
            node->right = parse_equality();
            expr = node;
        }
        return expr;
    }

    ExpressionPtr parse_equality() {
        auto expr = parse_comparison();
        while (current().type == "OP" && (current().value == "==" || current().value == "!=")) {
            auto node = std::make_shared<BinaryOp>();
            node->left = expr;
            node->op = consume("OP").value;
            node->right = parse_comparison();
            expr = node;
        }
        return expr;
    }

    ExpressionPtr parse_comparison() {
        auto expr = parse_term();
        while (current().type == "OP" &&
               (current().value == "<" || current().value == ">" || current().value == "<=" ||
                current().value == ">=")) {
            auto node = std::make_shared<BinaryOp>();
            node->left = expr;
            node->op = consume("OP").value;
            node->right = parse_term();
            expr = node;
        }
        return expr;
    }

    ExpressionPtr parse_term() {
        auto expr = parse_factor();
        while (current().type == "OP" && (current().value == "+" || current().value == "-")) {
            auto node = std::make_shared<BinaryOp>();
            node->left = expr;
            node->op = consume("OP").value;
            node->right = parse_factor();
            expr = node;
        }
        return expr;
    }

    ExpressionPtr parse_factor() {
        auto expr = parse_unary();
        while (current().type == "OP" &&
               (current().value == "*" || current().value == "/" || current().value == "%")) {
            auto node = std::make_shared<BinaryOp>();
            node->left = expr;
            node->op = consume("OP").value;
            node->right = parse_unary();
            expr = node;
        }
        return expr;
    }

    ExpressionPtr parse_unary() {
        if (current().type == "OP" && (current().value == "-" || current().value == "!")) {
            auto node = std::make_shared<UnaryOp>();
            node->op = consume("OP").value;
            node->operand = parse_unary();
            return node;
        }
        return parse_call_expression();
    }

    ExpressionPtr parse_call_expression() {
        auto expr = parse_primary();
        while (true) {
            if (match("LPAREN")) {
                auto call = std::make_shared<Call>();
                call->func = expr;
                if (current().type != "RPAREN") {
                    while (true) {
                        call->args.push_back(parse_expression());
                        if (!match("COMMA")) {
                            break;
                        }
                    }
                }
                consume("RPAREN");
                expr = call;
            } else if (match("DOT")) {
                auto attr = std::make_shared<Attribute>();
                attr->value = expr;
                attr->attr = consume("NAME").value;
                expr = attr;
            } else {
                break;
            }
        }
        return expr;
    }

    ExpressionPtr parse_primary() {
        const auto& tok = current();
        if (tok.type == "NUMBER") {
            consume();
            auto node = std::make_shared<Number>();
            node->value = std::stod(tok.value);
            return node;
        }
        if (tok.type == "STRING") {
            consume();
            auto node = std::make_shared<String>();
            node->value = tok.value;
            return node;
        }
        if (tok.type == "TRUE") {
            consume();
            auto node = std::make_shared<Boolean>();
            node->value = true;
            return node;
        }
        if (tok.type == "FALSE") {
            consume();
            auto node = std::make_shared<Boolean>();
            node->value = false;
            return node;
        }
        if (tok.type == "NULL") {
            consume();
            return std::make_shared<Null>();
        }
        if (tok.type == "NAME") {
            consume();
            auto node = std::make_shared<Name>();
            node->id = tok.value;
            return node;
        }
        if (tok.type == "LPAREN") {
            consume();
            auto expr = parse_expression();
            consume("RPAREN");
            return expr;
        }
        if (tok.type == "LBRACKET") {
            consume();
            auto node = std::make_shared<ListLiteral>();
            if (current().type != "RBRACKET") {
                while (true) {
                    node->elements.push_back(parse_expression());
                    if (!match("COMMA")) {
                        break;
                    }
                }
            }
            consume("RBRACKET");
            return node;
        }
        if (tok.type == "LBRACE") {
            consume();
            auto node = std::make_shared<DictLiteral>();
            if (current().type != "RBRACE") {
                while (true) {
                    auto key = parse_expression();
                    consume("COLON");
                    auto value = parse_expression();
                    node->pairs.emplace_back(key, value);
                    if (!match("COMMA")) {
                        break;
                    }
                }
            }
            consume("RBRACE");
            return node;
        }
        throw std::runtime_error("Unexpected token " + tok.type + " at line " + std::to_string(tok.line));
    }
};

}  // namespace

ModulePtr parse(const TokenStream& tokens) {
    Parser parser(tokens);
    return parser.parse();
}

}  // namespace trif::parser
