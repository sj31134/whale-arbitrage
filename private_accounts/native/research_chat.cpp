// Single offline completion. Messages cross stdin as byte-counted UTF-8, answers cross stdout.
#include "llama.h"
#include "ggml-backend.h"

#include <algorithm>
#include <iostream>
#include <string>
#include <vector>

int main(int argc, char **argv) {
    if (argc != 4) return 1;
    const int output_limit = std::stoi(argv[3]);
    if (output_limit < 1 || output_limit > 1024) return 1;
    std::vector<std::string> roles, texts;
    std::string role, line;
    while (std::getline(std::cin, role)) {
        if (role != "system" && role != "user" && role != "assistant") return 2;
        if (!std::getline(std::cin, line)) return 2;
        auto size = std::stoul(line);
        if (size > 250000 || roles.size() >= 16) return 2;
        std::string content(size, '\0');
        if (!std::cin.read(content.data(), size)) return 2;
        roles.push_back(role);
        texts.push_back(std::move(content));
    }
    if (roles.empty()) return 2;
    std::vector<llama_chat_message> messages;
    for (size_t i = 0; i < roles.size(); ++i) {
        messages.push_back({roles[i].c_str(), texts[i].c_str()});
    }

    ggml_backend_load_all_from_path(argv[2]);
    llama_backend_init();
    auto params = llama_model_default_params();
    auto *model = llama_model_load_from_file(argv[1], params);
    if (!model) return 3;
    const char *tmpl = llama_model_chat_template(model, nullptr);
    if (!tmpl) return 3;
    int length = llama_chat_apply_template(tmpl, messages.data(), messages.size(), true, nullptr, 0);
    if (length <= 0) return 3;
    std::string prompt(length + 1, '\0');
    if (llama_chat_apply_template(tmpl, messages.data(), messages.size(), true, prompt.data(), prompt.size()) != length) return 3;
    auto *vocab = llama_model_get_vocab(model);
    int n = -llama_tokenize(vocab, prompt.data(), length, nullptr, 0, true, true);
    if (n < 1 || n + output_limit > 24576) return 4;
    std::vector<llama_token> tokens(n);
    if (llama_tokenize(vocab, prompt.data(), length, tokens.data(), n, true, true) != n) return 4;
    auto ctx_params = llama_context_default_params();
    ctx_params.n_ctx = n + output_limit;
    ctx_params.n_batch = 512;
    auto *ctx = llama_init_from_model(model, ctx_params);
    if (!ctx) return 5;
    // Each invocation starts with an empty KV cache, even when two desks share a model.
    for (int i = 0; i < n; i += 512) {
        if (llama_decode(ctx, llama_batch_get_one(tokens.data() + i, std::min(512, n - i)))) return 5;
    }
    auto *sampler = llama_sampler_init_greedy();
    std::string answer;
    for (int i = 0; i < output_limit; ++i) {
        auto token = llama_sampler_sample(sampler, ctx, -1);
        if (llama_vocab_is_eog(vocab, token)) break;
        char piece[2048];
        int size = llama_token_to_piece(vocab, token, piece, sizeof(piece), 0, false);
        if (size < 0) return 6;
        answer.append(piece, size);
        if (llama_decode(ctx, llama_batch_get_one(&token, 1))) return 5;
    }
    std::cout << answer;
    llama_sampler_free(sampler);
    llama_free(ctx);
    llama_model_free(model);
    llama_backend_free();
}
