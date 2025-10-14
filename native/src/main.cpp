#include <filesystem>
#include <fstream>
#include <iostream>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "trif/compiler.hpp"

namespace {

struct Arguments {
    std::optional<std::string> input;
    std::optional<std::string> output;
    std::string target = "python";
    bool aggressive_errors = false;
};

Arguments parse_arguments(int argc, char** argv) {
    Arguments args;
    for (int i = 1; i < argc; ++i) {
        std::string_view value(argv[i]);
        if (value == "--target" && i + 1 < argc) {
            args.target = argv[++i];
        } else if (value == "--output" && i + 1 < argc) {
            args.output = argv[++i];
        } else if (value == "--aggressive-errors") {
            args.aggressive_errors = true;
        } else if (!args.input) {
            args.input = std::string(value);
        } else {
            throw std::runtime_error("Unrecognized argument: " + std::string(value));
        }
    }
    return args;
}

void write_output(const std::optional<std::string>& path, const std::string& content) {
    if (!path) {
        std::cout << content << std::endl;
        return;
    }
    std::ofstream stream(*path);
    if (!stream) {
        throw std::runtime_error("Unable to write to output path: " + *path);
    }
    stream << content;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        auto args = parse_arguments(argc, argv);
        if (!args.input) {
            throw std::runtime_error("No input file provided");
        }
        trif::compiler::Compiler compiler;
        trif::compiler::CompileOptions options;
        options.target = args.target;
        options.aggressive_errors = args.aggressive_errors;
        auto result = compiler.compile_file(*args.input, options);
        if (result.output_text) {
            write_output(args.output, *result.output_text);
        }
    } catch (const std::exception& exc) {
        std::cerr << "trifc: " << exc.what() << std::endl;
        return 1;
    }
    return 0;
}
