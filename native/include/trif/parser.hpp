#pragma once

#include <memory>
#include <vector>

#include "ast.hpp"
#include "lexer.hpp"

namespace trif::parser {

using ast::ModulePtr;

ModulePtr parse(const lexer::TokenStream& tokens);

}  // namespace trif::parser
