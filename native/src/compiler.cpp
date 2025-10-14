#include "trif/compiler.hpp"

#include <fstream>
#include <sstream>
#include <stdexcept>

#include "trif/codegen.hpp"
#include "trif/lexer.hpp"
#include "trif/parser.hpp"

namespace trif::compiler {

namespace {

std::string generate_cpp_stub(const ast::ModulePtr& module) {
    std::ostringstream oss;
    oss << "#include <trif/runtime.hpp>\n";
    oss << "#include <utility>\n";
    oss << "\n";
    oss << "int main(int argc, char** argv) {\n";
    oss << "    trif::runtime::Runtime runtime;\n";
    oss << "    auto exports = runtime.create_module();\n";
    oss << "    auto default_export = runtime.null_value();\n";
    oss << "    runtime.bootstrap(argv[0]);\n";
    oss << "    // TODO: Generated body\n";
    oss << "    runtime.register_module(exports, default_export);\n";
    oss << "    return 0;\n";
    oss << "}\n";
    (void)module;
    return oss.str();
}

}  // namespace

CompileResult Compiler::compile_source(const std::string& source, const CompileOptions& options) {
    try {
        auto tokens = lexer::tokenize(source);
        auto module = parser::parse(tokens);
        CompileResult result{module, std::nullopt};
        if (options.target == "python") {
            codegen::PythonGenerator generator;
            result.output_text = generator.generate(module);
        } else if (options.target == "javascript" || options.target == "js") {
            codegen::JavaScriptGenerator generator;
            result.output_text = generator.generate(module);
        } else if (options.target == "cpp" || options.target == "c++") {
            result.output_text = generate_cpp_stub(module);
        } else {
            throw std::runtime_error("Unknown target: " + options.target);
        }
        return result;
    } catch (const std::exception& exc) {
        if (options.aggressive_errors) {
            throw;
        }
        throw std::runtime_error(std::string("Compilation failed: ") + exc.what());
    }
}

CompileResult Compiler::compile_file(const std::string& path, const CompileOptions& options) {
    std::ifstream stream(path);
    if (!stream) {
        throw std::runtime_error("Unable to open file: " + path);
    }
    std::ostringstream buffer;
    buffer << stream.rdbuf();
    return compile_source(buffer.str(), options);
}

}  // namespace trif::compiler
