#pragma once

#include <string>

namespace trif::lexer {

struct Token {
    std::string type;
    std::string value;
    int line;
    int column;
};

}  // namespace trif::lexer
