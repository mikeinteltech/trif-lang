#pragma once

#include <optional>
#include <string>

#include "ast.hpp"

namespace trif::compiler {

struct CompileOptions {
    std::string target = "python";
    bool aggressive_errors = false;
};

struct CompileResult {
    ast::ModulePtr module;
    std::optional<std::string> output_text;
};

class Compiler {
   public:
    CompileResult compile_source(const std::string& source, const CompileOptions& options = {});
    CompileResult compile_file(const std::string& path, const CompileOptions& options = {});
};

}  // namespace trif::compiler
