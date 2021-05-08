# Development Guide

## Getting Started

```
% pyenv virtualenv 3.9.4 marks_manager
% pyenv activate marks_manager
% pip install --upgrade pip setuptools wheel pip-tools
% pip-compile --generate-hashes requirements.in
% pip-compile --generate-hashes requirements.dev.in
% pip-sync requirements.*txt
```
