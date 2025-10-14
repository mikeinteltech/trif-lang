#include "trif/lexer.hpp"

#include <algorithm>
#include <cctype>
#include <regex>
#include <stdexcept>
#include <string_view>
#include <unordered_map>
#include <unordered_set>

namespace trif::lexer {

namespace {

struct Pattern {
    std::string name;
    std::regex regex;
};

const std::vector<Pattern>& token_patterns() {
    static const std::vector<Pattern> patterns = {
        {"NUMBER", std::regex(R"(\d+(?:\.\d+)?)", std::regex::ECMAScript)},
        {"STRING", std::regex(R"(("([^"\\]|\\.)*")|('([^'\\]|\\.)*'))", std::regex::ECMAScript)},
        {"COMMENT", std::regex(R"(//[^\n]*)", std::regex::ECMAScript)},
        {"NAME", std::regex(R"([A-Za-z_][A-Za-z0-9_]*)", std::regex::ECMAScript)},
        {"OP", std::regex(R"(==|!=|<=|>=|=>|&&|\|\||[+\-*/%=<>!])", std::regex::ECMAScript)},
        {"NEWLINE", std::regex(R"(\n)", std::regex::ECMAScript)},
        {"SKIP", std::regex(R"([ \t]+)", std::regex::ECMAScript)},
        {"LPAREN", std::regex(R"(\()", std::regex::ECMAScript)},
        {"RPAREN", std::regex(R"(\))", std::regex::ECMAScript)},
        {"LBRACE", std::regex(R"(\{)", std::regex::ECMAScript)},
        {"RBRACE", std::regex(R"(\})", std::regex::ECMAScript)},
        {"LBRACKET", std::regex(R"(\[)", std::regex::ECMAScript)},
        {"RBRACKET", std::regex(R"(\])", std::regex::ECMAScript)},
        {"COMMA", std::regex(R"(,)", std::regex::ECMAScript)},
        {"COLON", std::regex(R"(:)", std::regex::ECMAScript)},
        {"DOT", std::regex(R"(\.)", std::regex::ECMAScript)},
        {"SEMICOLON", std::regex(R"(;)", std::regex::ECMAScript)},
    };
    return patterns;
}

const std::unordered_set<std::string> kKeywords = {
    "let",      "fn",      "function", "return",  "if",     "else",    "while",
    "for",      "in",      "true",     "false",   "null",   "import",  "as",
    "from",     "const",   "export",   "default", "spawn",
};

std::string uppercase(const std::string& value) {
    std::string result;
    result.reserve(value.size());
    for (char c : value) {
        result.push_back(static_cast<char>(std::toupper(static_cast<unsigned char>(c))));
    }
    return result;
}

std::string decode_string_literal(const std::string& raw) {
    if (raw.size() < 2) {
        return raw;
    }
    std::string content = raw.substr(1, raw.size() - 2);
    std::string result;
    result.reserve(content.size());
    for (std::size_t i = 0; i < content.size(); ++i) {
        char c = content[i];
        if (c == '\\' && i + 1 < content.size()) {
            char next = content[i + 1];
            switch (next) {
                case 'n':
                    result.push_back('\n');
                    break;
                case 't':
                    result.push_back('\t');
                    break;
                case 'r':
                    result.push_back('\r');
                    break;
                case '\\':
                    result.push_back('\\');
                    break;
                case '"':
                    result.push_back('"');
                    break;
                case '\'':
                    result.push_back('\'');
                    break;
                default:
                    result.push_back(next);
                    break;
            }
            ++i;
        } else {
            result.push_back(c);
        }
    }
    return result;
}

}  // namespace

bool is_keyword(const std::string& value) {
    return kKeywords.contains(value);
}

TokenStream tokenize(const std::string& source) {
    TokenStream tokens;
    std::size_t index = 0;
    int line = 1;
    int column = 1;
    while (index < source.size()) {
        std::string_view remaining(source.c_str() + index, source.size() - index);
        if (remaining.substr(0, 2) == "/*") {
            std::size_t end = remaining.find("*/");
            if (end == std::string_view::npos) {
                throw std::runtime_error("Unterminated block comment at line " + std::to_string(line));
            }
            std::string value = std::string(remaining.substr(0, end + 2));
            int newline_count = static_cast<int>(std::count(value.begin(), value.end(), '\n'));
            line += newline_count;
            if (newline_count > 0) {
                auto pos = value.find_last_of('\n');
                column = static_cast<int>(value.size() - pos);
            } else {
                column += static_cast<int>(value.size());
            }
            index += value.size();
            continue;
        }
        std::cmatch match;
        std::string kind;
        for (const auto& pattern : token_patterns()) {
            if (std::regex_search(remaining.begin(), remaining.end(), match, pattern.regex,
                                   std::regex_constants::match_continuous)) {
                kind = pattern.name;
                break;
            }
        }
        if (!match.ready() || kind.empty()) {
            throw std::runtime_error("Unexpected character '" + std::string(1, source[index]) + "' at line " +
                                     std::to_string(line) + " column " + std::to_string(column));
        }
        std::string value = match.str();
        if (kind == "NEWLINE") {
            tokens.push_back({kind, value, line, column});
            ++line;
            column = 1;
        } else if (kind == "SKIP" || kind == "COMMENT") {
            column += static_cast<int>(value.size());
        } else {
            if (kind == "NAME" && is_keyword(value)) {
                kind = uppercase(value);
            }
            if (kind == "STRING") {
                value = decode_string_literal(value);
            }
            tokens.push_back({kind, value, line, column});
            column += static_cast<int>(match.length());
        }
        index += match.length();
    }
    tokens.push_back({"EOF", "", line, column});
    return tokens;
}

}  // namespace trif::lexer
