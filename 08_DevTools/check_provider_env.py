import importlib.util
import os
import sys
print('python', sys.executable)
print('openai_module', bool(importlib.util.find_spec('openai')))
print('OPENAI_API_KEY_SET', bool(os.getenv('OPENAI_API_KEY')))
print('AMEER_MODEL', os.getenv('AMEER_MODEL', 'gpt-4o-mini'))
