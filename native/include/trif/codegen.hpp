#pragma once

#include <string>

#include "ast.hpp"

namespace trif::codegen {

class Generator {
   public:
    virtual ~Generator() = default;
    virtual std::string generate(const ast::ModulePtr& module) = 0;
};

class PythonGenerator : public Generator {
   public:
    std::string generate(const ast::ModulePtr& module) override;
};

class JavaScriptGenerator : public Generator {
   public:
    std::string generate(const ast::ModulePtr& module) override;
};

}  // namespace trif::codegen
