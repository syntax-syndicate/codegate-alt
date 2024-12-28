from codegate.utils.package_extractor import PackageExtractor


def test_extractor_javascript():
    js_code = """
    import { createApp } from '@vue/compat';
    import React from 'react';
    import { useState } from 'react';
    import lodash from 'lodash';
    import express from 'express';
    import { Router } from 'express';
    import somethingElse from '@something/somethingelse';
    """
    packages = PackageExtractor.extract_packages(js_code, "javascript")

    assert sorted(packages) == [
        "@something/somethingelse",
        "@vue/compat",
        "express",
        "lodash",
        "react",
    ]


def test_extractor_go():
    go_code = """
    package main

    import (
        "testing"
        "github.com/stretchr/testify/assert"
        "github.com/your/module/types"
    )
    """
    packages = PackageExtractor.extract_packages(go_code, "go")
    assert sorted(packages) == [
        "github.com/stretchr/testify/assert",
        "github.com/your/module/types",
        "testing",
    ]


def test_extractor_python():
    python_code = """
    import pandas
    from codegate.utils import test
    import numpy as np
    """
    packages = PackageExtractor.extract_packages(python_code, "python")
    assert sorted(packages) == ["codegate", "numpy", "pandas"]


def test_extractor_java():
    java_code = """
    import java.util.List;
    import java.io.File;
    import com.example.project.MyClass;
    """
    packages = PackageExtractor.extract_packages(java_code, "java")
    assert sorted(packages) == ["com.example.project.MyClass", "java.io.File", "java.util.List"]


def test_extractor_rust():
    rust_code = """
    use rust_decimal_macros::dec;
    use rust_decimal::prelude::*;
    use inner::foo as bar;
    """
    packages = PackageExtractor.extract_packages(rust_code, "rust")
    assert sorted(packages) == ["inner", "rust_decimal", "rust_decimal_macros"]
