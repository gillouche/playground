def _platform_transition_impl(settings, attr):
    return {"//command_line_option:platforms": str(attr.platform)}

_platform_transition = transition(
    implementation = _platform_transition_impl,
    inputs = [],
    outputs = ["//command_line_option:platforms"],
)

def _transition_rule_impl(ctx):
    return [DefaultInfo(files = depset(ctx.files.actual))]

transition_rule = rule(
    implementation = _transition_rule_impl,
    attrs = {
        "actual": attr.label(cfg = _platform_transition),
        "platform": attr.label(default = "//tools/platforms:linux_arm64"),
        "_allowlist_function_transition": attr.label(
            default = "@bazel_tools//tools/allowlists/function_transition_allowlist",
        ),
    },
)
