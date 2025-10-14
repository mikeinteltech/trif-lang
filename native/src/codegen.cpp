#include "trif/codegen.hpp"

#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "trif/ast.hpp"

namespace trif::codegen {

namespace {

using namespace trif::ast;

class IndentedEmitter {
   public:
    void emit(const std::string& line) { stream_ << std::string(indent_ * 4, ' ') << line << '\n'; }
    void indent() { ++indent_; }
    void dedent() {
        if (indent_ == 0) {
            throw std::runtime_error("Indentation underflow");
        }
        --indent_;
    }
    std::string str() const { return stream_.str(); }

   private:
    std::ostringstream stream_;
    int indent_ = 0;
};

class PythonVisitor {
   public:
    std::string generate(const ModulePtr& module) {
        emitter_.emit("import pathlib");
        emitter_.emit("import sys");
        emitter_.emit("_trif_origin = pathlib.Path(__file__).resolve().parent if '__file__' in globals() else pathlib.Path.cwd()");
        emitter_.emit("for _candidate in (_trif_origin, _trif_origin.parent):");
        emitter_.indent();
        emitter_.emit("candidate_pkg = _candidate / 'trif_lang'");
        emitter_.emit("if candidate_pkg.exists():");
        emitter_.indent();
        emitter_.emit("if str(_candidate) not in sys.path:");
        emitter_.indent();
        emitter_.emit("sys.path.insert(0, str(_candidate))");
        emitter_.dedent();
        emitter_.emit("break");
        emitter_.dedent();
        emitter_.dedent();
        emitter_.emit("from trif_lang.runtime import runtime");
        emitter_.emit("__trif_exports__ = {}");
        emitter_.emit("__trif_default_export__ = None");
        emitter_.emit("");
        for (const auto& stmt : module->body) {
            visit(stmt);
        }
        emitter_.emit("");
        emitter_.emit("runtime.register_module_exports(__name__, __trif_exports__, __trif_default_export__)");
        emitter_.emit("");
        emitter_.emit("if __name__ == '__main__':");
        emitter_.indent();
        emitter_.emit("runtime.default_entry_point(locals())");
        emitter_.dedent();
        return emitter_.str();
    }

   private:
    IndentedEmitter emitter_;
    int temp_index_ = 0;

    std::string temp(const std::string& prefix) { return "__trif_" + prefix + "_" + std::to_string(temp_index_++); }

    void visit(const NodePtr& node) {
        switch (node->kind) {
            case NodeKind::Import:
                visit_import(std::static_pointer_cast<Import>(node));
                break;
            case NodeKind::ImportFrom:
                visit_import_from(std::static_pointer_cast<ImportFrom>(node));
                break;
            case NodeKind::Let:
                visit_let(std::static_pointer_cast<Let>(node));
                break;
            case NodeKind::Assign:
                visit_assign(std::static_pointer_cast<Assign>(node));
                break;
            case NodeKind::FunctionDef:
                visit_function_def(std::static_pointer_cast<FunctionDef>(node));
                break;
            case NodeKind::Return:
                visit_return(std::static_pointer_cast<Return>(node));
                break;
            case NodeKind::ExportNames:
                visit_export_names(std::static_pointer_cast<ExportNames>(node));
                break;
            case NodeKind::ExportDefault:
                visit_export_default(std::static_pointer_cast<ExportDefault>(node));
                break;
            case NodeKind::If:
                visit_if(std::static_pointer_cast<If>(node));
                break;
            case NodeKind::While:
                visit_while(std::static_pointer_cast<While>(node));
                break;
            case NodeKind::For:
                visit_for(std::static_pointer_cast<For>(node));
                break;
            case NodeKind::Spawn:
                visit_spawn(std::static_pointer_cast<Spawn>(node));
                break;
            default:
                if (std::dynamic_pointer_cast<Expression>(node)) {
                    emitter_.emit(render_expression(std::static_pointer_cast<Expression>(node)));
                } else {
                    throw std::runtime_error("Unsupported node in Python generator");
                }
        }
    }

    void visit_import(const std::shared_ptr<Import>& node) {
        std::string target = node->alias.value_or(node->module);
        for (auto& ch : target) {
            if (ch == '.' || ch == '-') {
                ch = '_';
            }
        }
        emitter_.emit(target + " = runtime.import_module('" + node->module + "')");
    }

    void visit_import_from(const std::shared_ptr<ImportFrom>& node) {
        std::string temp_name = temp("import");
        emitter_.emit(temp_name + " = runtime.import_module('" + node->module + "')");
        if (node->namespace_name) {
            emitter_.emit(*node->namespace_name + " = " + temp_name);
        }
        if (node->default_name) {
            emitter_.emit(*node->default_name + " = runtime.extract_default(" + temp_name + ")");
        }
        for (const auto& [source, alias] : node->names) {
            emitter_.emit(alias + " = runtime.extract_export(" + temp_name + ", '" + source + "')");
        }
    }

    void visit_let(const std::shared_ptr<Let>& node) {
        std::string assignment = node->name + " = " + render_expression(node->value);
        if (!node->mutable_flag) {
            assignment += "  # const";
        }
        emitter_.emit(assignment);
        if (node->exported) {
            emitter_.emit("__trif_exports__['" + node->name + "'] = " + node->name);
        }
        if (node->is_default) {
            emitter_.emit("__trif_default_export__ = " + node->name);
        }
    }

    void visit_assign(const std::shared_ptr<Assign>& node) {
        emitter_.emit(render_expression(node->target) + " = " + render_expression(node->value));
    }

    void visit_function_def(const std::shared_ptr<FunctionDef>& node) {
        emitter_.emit("def " + node->name + "(" + join(node->params, ", ") + "):");
        emitter_.indent();
        if (node->body.empty()) {
            emitter_.emit("return None");
        } else {
            for (const auto& stmt : node->body) {
                visit(stmt);
            }
            if (node->body.empty() || node->body.back()->kind != NodeKind::Return) {
                emitter_.emit("return None");
            }
        }
        emitter_.dedent();
        if (node->exported) {
            emitter_.emit("__trif_exports__['" + node->name + "'] = " + node->name);
        }
        if (node->is_default) {
            emitter_.emit("__trif_default_export__ = " + node->name);
        }
        emitter_.emit("");
    }

    void visit_return(const std::shared_ptr<Return>& node) {
        if (!node->value) {
            emitter_.emit("return None");
        } else {
            emitter_.emit("return " + render_expression(*node->value));
        }
    }

    void visit_export_names(const std::shared_ptr<ExportNames>& node) {
        if (node->source) {
            std::string temp_name = temp("export");
            emitter_.emit(temp_name + " = runtime.import_module('" + *node->source + "')");
            for (const auto& [source, alias] : node->names) {
                emitter_.emit("__trif_exports__['" + alias + "'] = runtime.extract_export(" + temp_name + ", '" + source + "')");
            }
        } else {
            for (const auto& [local, alias] : node->names) {
                emitter_.emit("__trif_exports__['" + alias + "'] = " + local);
            }
        }
    }

    void visit_export_default(const std::shared_ptr<ExportDefault>& node) {
        emitter_.emit("__trif_default_export__ = " + render_expression(node->value));
    }

    void visit_if(const std::shared_ptr<If>& node) {
        emitter_.emit("if " + render_expression(node->test) + ":");
        emitter_.indent();
        for (const auto& stmt : node->body) {
            visit(stmt);
        }
        emitter_.dedent();
        if (!node->orelse.empty()) {
            emitter_.emit("else:");
            emitter_.indent();
            for (const auto& stmt : node->orelse) {
                visit(stmt);
            }
            emitter_.dedent();
        }
    }

    void visit_while(const std::shared_ptr<While>& node) {
        emitter_.emit("while " + render_expression(node->test) + ":");
        emitter_.indent();
        for (const auto& stmt : node->body) {
            visit(stmt);
        }
        emitter_.dedent();
    }

    void visit_for(const std::shared_ptr<For>& node) {
        emitter_.emit("for " + node->target + " in " + render_expression(node->iterator) + ":");
        emitter_.indent();
        for (const auto& stmt : node->body) {
            visit(stmt);
        }
        emitter_.dedent();
    }

    void visit_spawn(const std::shared_ptr<Spawn>& node) {
        emitter_.emit("runtime.spawn(" + render_expression(node->call) + ")");
    }

    std::string join(const std::vector<std::string>& values, const std::string& sep) {
        std::ostringstream oss;
        for (std::size_t i = 0; i < values.size(); ++i) {
            if (i != 0) {
                oss << sep;
            }
            oss << values[i];
        }
        return oss.str();
    }

    std::string render_expression(const ExpressionPtr& expr) {
        switch (expr->kind) {
            case NodeKind::Name:
                return std::static_pointer_cast<Name>(expr)->id;
            case NodeKind::Number: {
                std::ostringstream oss;
                oss << std::static_pointer_cast<Number>(expr)->value;
                return oss.str();
            }
            case NodeKind::String:
                return repr_string(std::static_pointer_cast<String>(expr)->value);
            case NodeKind::Boolean:
                return std::static_pointer_cast<Boolean>(expr)->value ? "True" : "False";
            case NodeKind::Null:
                return "None";
            case NodeKind::BinaryOp: {
                auto node = std::static_pointer_cast<BinaryOp>(expr);
                return render_expression(node->left) + " " + node->op + " " + render_expression(node->right);
            }
            case NodeKind::UnaryOp: {
                auto node = std::static_pointer_cast<UnaryOp>(expr);
                return node->op + render_expression(node->operand);
            }
            case NodeKind::Call: {
                auto node = std::static_pointer_cast<Call>(expr);
                std::vector<std::string> args;
                for (const auto& arg : node->args) {
                    args.push_back(render_expression(arg));
                }
                return render_expression(node->func) + "(" + join(args, ", ") + ")";
            }
            case NodeKind::Attribute: {
                auto node = std::static_pointer_cast<Attribute>(expr);
                return render_expression(node->value) + "." + node->attr;
            }
            case NodeKind::ListLiteral: {
                auto node = std::static_pointer_cast<ListLiteral>(expr);
                std::vector<std::string> values;
                for (const auto& element : node->elements) {
                    values.push_back(render_expression(element));
                }
                return "[" + join(values, ", ") + "]";
            }
            case NodeKind::DictLiteral: {
                auto node = std::static_pointer_cast<DictLiteral>(expr);
                std::vector<std::string> pairs;
                for (const auto& [key, value] : node->pairs) {
                    pairs.push_back(render_expression(key) + ": " + render_expression(value));
                }
                return "{" + join(pairs, ", ") + "}";
            }
            default:
                throw std::runtime_error("Unsupported expression in Python generator");
        }
    }

    std::string repr_string(const std::string& value) {
        std::ostringstream oss;
        oss << '"';
        for (char c : value) {
            switch (c) {
                case '\\':
                    oss << "\\\\";
                    break;
                case '"':
                    oss << "\\\"";
                    break;
                case '\n':
                    oss << "\\n";
                    break;
                case '\t':
                    oss << "\\t";
                    break;
                case '\r':
                    oss << "\\r";
                    break;
                default:
                    oss << c;
                    break;
            }
        }
        oss << '"';
        return oss.str();
    }
};

class JavaScriptVisitor {
   public:
    std::string generate(const ModulePtr& module) {
        emitter_.emit("import { runtime } from '@trif/lang/runtime.js'");
        emitter_.emit("const __trif_exports__ = new Map();");
        emitter_.emit("let __trif_default_export__ = null;");
        emitter_.emit("");
        for (const auto& stmt : module->body) {
            visit(stmt);
        }
        emitter_.emit("");
        emitter_.emit("export default __trif_default_export__;");
        emitter_.emit("export const exports = __trif_exports__;");
        return emitter_.str();
    }

   private:
    IndentedEmitter emitter_;

    void visit(const NodePtr& node) {
        switch (node->kind) {
            case NodeKind::Import:
                visit_import(std::static_pointer_cast<Import>(node));
                break;
            case NodeKind::ImportFrom:
                visit_import_from(std::static_pointer_cast<ImportFrom>(node));
                break;
            case NodeKind::Let:
                visit_let(std::static_pointer_cast<Let>(node));
                break;
            case NodeKind::Assign:
                visit_assign(std::static_pointer_cast<Assign>(node));
                break;
            case NodeKind::FunctionDef:
                visit_function_def(std::static_pointer_cast<FunctionDef>(node));
                break;
            case NodeKind::Return:
                visit_return(std::static_pointer_cast<Return>(node));
                break;
            case NodeKind::ExportNames:
                visit_export_names(std::static_pointer_cast<ExportNames>(node));
                break;
            case NodeKind::ExportDefault:
                visit_export_default(std::static_pointer_cast<ExportDefault>(node));
                break;
            case NodeKind::If:
                visit_if(std::static_pointer_cast<If>(node));
                break;
            case NodeKind::While:
                visit_while(std::static_pointer_cast<While>(node));
                break;
            case NodeKind::For:
                visit_for(std::static_pointer_cast<For>(node));
                break;
            case NodeKind::Spawn:
                visit_spawn(std::static_pointer_cast<Spawn>(node));
                break;
            default:
                if (std::dynamic_pointer_cast<Expression>(node)) {
                    emitter_.emit(render_expression(std::static_pointer_cast<Expression>(node)) + ';');
                } else {
                    throw std::runtime_error("Unsupported node in JS generator");
                }
        }
    }

    void visit_import(const std::shared_ptr<Import>& node) {
        std::string target = node->alias.value_or(node->module);
        emitter_.emit("const " + target + " = await runtime.importModule('" + node->module + "');");
    }

    void visit_import_from(const std::shared_ptr<ImportFrom>& node) {
        emitter_.emit("const __mod = await runtime.importModule('" + node->module + "');");
        if (node->namespace_name) {
            emitter_.emit("const " + *node->namespace_name + " = __mod;");
        }
        if (node->default_name) {
            emitter_.emit("const " + *node->default_name + " = runtime.extractDefault(__mod);");
        }
        for (const auto& [source, alias] : node->names) {
            emitter_.emit("const " + alias + " = runtime.extractExport(__mod, '" + source + "');");
        }
    }

    void visit_let(const std::shared_ptr<Let>& node) {
        std::string keyword = node->mutable_flag ? "let" : "const";
        emitter_.emit(keyword + " " + node->name + " = " + render_expression(node->value) + ";");
        if (node->exported) {
            emitter_.emit("__trif_exports__.set('" + node->name + "', " + node->name + ");");
        }
        if (node->is_default) {
            emitter_.emit("__trif_default_export__ = " + node->name + ";");
        }
    }

    void visit_assign(const std::shared_ptr<Assign>& node) {
        emitter_.emit(render_expression(node->target) + " = " + render_expression(node->value) + ";");
    }

    void visit_function_def(const std::shared_ptr<FunctionDef>& node) {
        emitter_.emit("function " + node->name + "(" + join(node->params, ", ") + ") {");
        emitter_.indent();
        if (node->body.empty()) {
            emitter_.emit("return null;");
        } else {
            for (const auto& stmt : node->body) {
                visit(stmt);
            }
            emitter_.emit("return null;");
        }
        emitter_.dedent();
        emitter_.emit("}");
        if (node->exported) {
            emitter_.emit("__trif_exports__.set('" + node->name + "', " + node->name + ");");
        }
        if (node->is_default) {
            emitter_.emit("__trif_default_export__ = " + node->name + ";");
        }
        emitter_.emit("");
    }

    void visit_return(const std::shared_ptr<Return>& node) {
        if (!node->value) {
            emitter_.emit("return null;");
        } else {
            emitter_.emit("return " + render_expression(*node->value) + ";");
        }
    }

    void visit_export_names(const std::shared_ptr<ExportNames>& node) {
        if (node->source) {
            emitter_.emit("const __mod = await runtime.importModule('" + *node->source + "');");
            for (const auto& [source, alias] : node->names) {
                emitter_.emit("__trif_exports__.set('" + alias + "', runtime.extractExport(__mod, '" + source + "'));");
            }
        } else {
            for (const auto& [local, alias] : node->names) {
                emitter_.emit("__trif_exports__.set('" + alias + "', " + local + ");");
            }
        }
    }

    void visit_export_default(const std::shared_ptr<ExportDefault>& node) {
        emitter_.emit("__trif_default_export__ = " + render_expression(node->value) + ";");
    }

    void visit_if(const std::shared_ptr<If>& node) {
        emitter_.emit("if (" + render_expression(node->test) + ") {");
        emitter_.indent();
        for (const auto& stmt : node->body) {
            visit(stmt);
        }
        emitter_.dedent();
        if (!node->orelse.empty()) {
            emitter_.emit("} else {");
            emitter_.indent();
            for (const auto& stmt : node->orelse) {
                visit(stmt);
            }
            emitter_.dedent();
        }
        emitter_.emit("}");
    }

    void visit_while(const std::shared_ptr<While>& node) {
        emitter_.emit("while (" + render_expression(node->test) + ") {");
        emitter_.indent();
        for (const auto& stmt : node->body) {
            visit(stmt);
        }
        emitter_.dedent();
        emitter_.emit("}");
    }

    void visit_for(const std::shared_ptr<For>& node) {
        emitter_.emit("for (const " + node->target + " of " + render_expression(node->iterator) + ") {");
        emitter_.indent();
        for (const auto& stmt : node->body) {
            visit(stmt);
        }
        emitter_.dedent();
        emitter_.emit("}");
    }

    void visit_spawn(const std::shared_ptr<Spawn>& node) {
        emitter_.emit("runtime.spawn(" + render_expression(node->call) + ");");
    }

    std::string join(const std::vector<std::string>& values, const std::string& sep) {
        std::ostringstream oss;
        for (std::size_t i = 0; i < values.size(); ++i) {
            if (i != 0) {
                oss << sep;
            }
            oss << values[i];
        }
        return oss.str();
    }

    std::string render_expression(const ExpressionPtr& expr) {
        switch (expr->kind) {
            case NodeKind::Name:
                return std::static_pointer_cast<Name>(expr)->id;
            case NodeKind::Number: {
                std::ostringstream oss;
                oss << std::static_pointer_cast<Number>(expr)->value;
                return oss.str();
            }
            case NodeKind::String:
                return repr_string(std::static_pointer_cast<String>(expr)->value);
            case NodeKind::Boolean:
                return std::static_pointer_cast<Boolean>(expr)->value ? "true" : "false";
            case NodeKind::Null:
                return "null";
            case NodeKind::BinaryOp: {
                auto node = std::static_pointer_cast<BinaryOp>(expr);
                return render_expression(node->left) + " " + node->op + " " + render_expression(node->right);
            }
            case NodeKind::UnaryOp: {
                auto node = std::static_pointer_cast<UnaryOp>(expr);
                return node->op + render_expression(node->operand);
            }
            case NodeKind::Call: {
                auto node = std::static_pointer_cast<Call>(expr);
                std::vector<std::string> args;
                for (const auto& arg : node->args) {
                    args.push_back(render_expression(arg));
                }
                return render_expression(node->func) + "(" + join(args, ", ") + ")";
            }
            case NodeKind::Attribute: {
                auto node = std::static_pointer_cast<Attribute>(expr);
                return render_expression(node->value) + "." + node->attr;
            }
            case NodeKind::ListLiteral: {
                auto node = std::static_pointer_cast<ListLiteral>(expr);
                std::vector<std::string> values;
                for (const auto& element : node->elements) {
                    values.push_back(render_expression(element));
                }
                return "[" + join(values, ", ") + "]";
            }
            case NodeKind::DictLiteral: {
                auto node = std::static_pointer_cast<DictLiteral>(expr);
                std::vector<std::string> pairs;
                for (const auto& [key, value] : node->pairs) {
                    pairs.push_back(render_expression(key) + ": " + render_expression(value));
                }
                return "{" + join(pairs, ", ") + "}";
            }
            default:
                throw std::runtime_error("Unsupported expression in JS generator");
        }
    }

    std::string repr_string(const std::string& value) {
        std::ostringstream oss;
        oss << '"';
        for (char c : value) {
            switch (c) {
                case '\\':
                    oss << "\\\\";
                    break;
                case '"':
                    oss << "\\\"";
                    break;
                case '\n':
                    oss << "\\n";
                    break;
                case '\t':
                    oss << "\\t";
                    break;
                case '\r':
                    oss << "\\r";
                    break;
                default:
                    oss << c;
                    break;
            }
        }
        oss << '"';
        return oss.str();
    }
};

}  // namespace

std::string PythonGenerator::generate(const ModulePtr& module) {
    PythonVisitor visitor;
    return visitor.generate(module);
}

std::string JavaScriptGenerator::generate(const ModulePtr& module) {
    JavaScriptVisitor visitor;
    return visitor.generate(module);
}

}  // namespace trif::codegen
