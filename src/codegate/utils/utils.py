def generate_vector_string(package) -> str:
    vector_str = f"{package['name']}"
    package_url = ""
    type_map = {
        "pypi": "Python package available on PyPI",
        "npm": "JavaScript package available on NPM",
        "go": "Go package",
        "crates": "Rust package available on Crates",
        "java": "Java package",
    }
    status_messages = {
        "archived": "However, this package is found to be archived and no longer maintained.",
        "deprecated": "However, this package is found to be deprecated and no longer "
        "recommended for use.",
        "malicious": "However, this package is found to be malicious and must not be used.",
    }
    vector_str += f" is a {type_map.get(package['type'], 'package of unknown type')}. "
    package_url = f"https://trustypkg.dev/{package['type']}/{package['name']}"

    # Add extra status
    status_suffix = status_messages.get(package["status"], "")
    if status_suffix:
        vector_str += f" {status_suffix} For additional information refer to {package_url}"

    # add description
    vector_str += f" - Package offers this functionality: {package['description']}"
    return vector_str
