# Shared Libraries (`libs/`)

This directory will contain shared code libraries and packages that are used across multiple applications or tools within the monorepo.

## Usage Patterns

1.  **Create a new package:**
    `libs/my-utils/`

2.  **Add build configuration:**
    `BUILD.bazel` file to define the library target (e.g., `py_library`, `go_library`).

    ```python
    # libs/my-utils/BUILD.bazel
    load("@rules_python//python:defs.bzl", "py_library")

    py_library(
        name = "my_utils",
        srcs = ["utils.py"],
        visibility = ["//visibility:public"],
    )
    ```

3.  **Link:**
    `BUILD.bazel`

    ```python
    # apps/my-app/BUILD.bazel
    py_binary(
        name = "main",
        srcs = ["main.py"],
        deps = ["//libs/my-utils"],
    )
    ```

## Structure

- organization by domain? language?
