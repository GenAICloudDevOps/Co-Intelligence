"""
Quick test script for Agentic Barista
Run: python test_barista.py
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from apps.agentic_barista.agents.coordinator import BaristaCoordinator

async def test_barista():
    print("🧪 Testing Agentic Barista\n")
    
    coordinator = BaristaCoordinator()
    session_id = "test_session"
    cart = {}
    
    # Test 1: Show menu
    print("Test 1: Show menu")
    result = await coordinator.process_message("show me the menu", session_id, cart)
    print(f"Agent: {result['agent']}")
    print(f"Response: {result['response'][:200]}...\n")
    cart = result['cart']
    
    # Test 2: Add items
    print("Test 2: Add items to cart")
    result = await coordinator.process_message("add 2 lattes and 1 croissant", session_id, cart)
    print(f"Agent: {result['agent']}")
    print(f"Response: {result['response']}")
    print(f"Cart: {result['cart']}\n")
    cart = result['cart']
    
    # Test 3: Show cart
    print("Test 3: Show cart")
    result = await coordinator.process_message("show my cart", session_id, cart)
    print(f"Agent: {result['agent']}")
    print(f"Response: {result['response']}")
    print(f"Total: ${result['total_amount']:.2f}\n")
    
    print("✅ All tests passed!")

if __name__ == "__main__":
    asyncio.run(test_barista())
