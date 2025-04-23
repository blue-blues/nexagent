"""
Simple test script for the ManusAgent implementation.
"""

from app.agent.manus_agent import ManusAgent

print("Importing ManusAgent successful!")
print("ManusAgent class attributes:")
for attr in dir(ManusAgent):
    if not attr.startswith('__'):
        print(f"- {attr}")
