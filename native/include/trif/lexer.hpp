#pragma once

#include <string>
#include <vector>

#include "token.hpp"

namespace trif::lexer {

using TokenStream = std::vector<Token>;

TokenStream tokenize(const std::string& source);

bool is_keyword(const std::string& value);

}  // namespace trif::lexer
