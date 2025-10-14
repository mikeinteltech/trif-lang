#pragma once

#include <memory>
#include <optional>
#include <string>
#include <utility>
#include <variant>
#include <vector>

namespace trif::ast {

enum class NodeKind {
    Module,
    ImportFrom,
    Import,
    Let,
    Assign,
    FunctionDef,
    ExportNames,
    ExportDefault,
    Return,
    If,
    While,
    For,
    Spawn,
    Name,
    Number,
    String,
    Boolean,
    Null,
    BinaryOp,
    UnaryOp,
    Call,
    Attribute,
    ListLiteral,
    DictLiteral
};

struct Node {
    explicit Node(NodeKind kind) : kind(kind) {}
    virtual ~Node() = default;
    NodeKind kind;
};

using NodePtr = std::shared_ptr<Node>;

struct Expression : Node {
    explicit Expression(NodeKind kind) : Node(kind) {}
};

using ExpressionPtr = std::shared_ptr<Expression>;

struct Module : Node {
    Module() : Node(NodeKind::Module) {}
    std::vector<NodePtr> body;
};
using ModulePtr = std::shared_ptr<Module>;

struct ImportFrom : Node {
    ImportFrom() : Node(NodeKind::ImportFrom) {}
    std::string module;
    std::vector<std::pair<std::string, std::string>> names;
    std::optional<std::string> default_name;
    std::optional<std::string> namespace_name;
};

struct Import : Node {
    Import() : Node(NodeKind::Import) {}
    std::string module;
    std::optional<std::string> alias;
};

struct Let : Node {
    Let() : Node(NodeKind::Let) {}
    std::string name;
    ExpressionPtr value;
    bool mutable_flag = true;
    bool exported = false;
    bool is_default = false;
};

struct Assign : Node {
    Assign() : Node(NodeKind::Assign) {}
    ExpressionPtr target;
    ExpressionPtr value;
};

struct FunctionDef : Node {
    FunctionDef() : Node(NodeKind::FunctionDef) {}
    std::string name;
    std::vector<std::string> params;
    std::vector<NodePtr> body;
    bool exported = false;
    bool is_default = false;
};

struct ExportNames : Node {
    ExportNames() : Node(NodeKind::ExportNames) {}
    std::vector<std::pair<std::string, std::string>> names;
    std::optional<std::string> source;
};

struct ExportDefault : Node {
    ExportDefault() : Node(NodeKind::ExportDefault) {}
    ExpressionPtr value;
};

struct Return : Node {
    Return() : Node(NodeKind::Return) {}
    std::optional<ExpressionPtr> value;
};

struct If : Node {
    If() : Node(NodeKind::If) {}
    ExpressionPtr test;
    std::vector<NodePtr> body;
    std::vector<NodePtr> orelse;
};

struct While : Node {
    While() : Node(NodeKind::While) {}
    ExpressionPtr test;
    std::vector<NodePtr> body;
};

struct For : Node {
    For() : Node(NodeKind::For) {}
    std::string target;
    ExpressionPtr iterator;
    std::vector<NodePtr> body;
};

struct Spawn : Node {
    Spawn() : Node(NodeKind::Spawn) {}
    ExpressionPtr call;
};

struct Name : Expression {
    Name() : Expression(NodeKind::Name) {}
    std::string id;
};

struct Number : Expression {
    Number() : Expression(NodeKind::Number) {}
    double value = 0.0;
};

struct String : Expression {
    String() : Expression(NodeKind::String) {}
    std::string value;
};

struct Boolean : Expression {
    Boolean() : Expression(NodeKind::Boolean) {}
    bool value = false;
};

struct Null : Expression {
    Null() : Expression(NodeKind::Null) {}
};

struct BinaryOp : Expression {
    BinaryOp() : Expression(NodeKind::BinaryOp) {}
    ExpressionPtr left;
    std::string op;
    ExpressionPtr right;
};

struct UnaryOp : Expression {
    UnaryOp() : Expression(NodeKind::UnaryOp) {}
    std::string op;
    ExpressionPtr operand;
};

struct Call : Expression {
    Call() : Expression(NodeKind::Call) {}
    ExpressionPtr func;
    std::vector<ExpressionPtr> args;
};

struct Attribute : Expression {
    Attribute() : Expression(NodeKind::Attribute) {}
    ExpressionPtr value;
    std::string attr;
};

struct ListLiteral : Expression {
    ListLiteral() : Expression(NodeKind::ListLiteral) {}
    std::vector<ExpressionPtr> elements;
};

struct DictLiteral : Expression {
    DictLiteral() : Expression(NodeKind::DictLiteral) {}
    std::vector<std::pair<ExpressionPtr, ExpressionPtr>> pairs;
};

inline ModulePtr make_module() {
    return std::make_shared<Module>();
}

template <typename T, typename... Args>
std::shared_ptr<T> make_node(Args&&... args) {
    auto node = std::make_shared<T>();
    if constexpr (sizeof...(Args) > 0) {
        *node = T{std::forward<Args>(args)...};
    }
    return node;
}

}  // namespace trif::ast
