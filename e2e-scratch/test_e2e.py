import random
import uuid
import time
from playwright.sync_api import sync_playwright, expect, Page

FRONTEND_URL = "http://localhost:3000"
DEMO_OTP = "123456"

def register_user(page: Page, display_name: str, username: str) -> str:
    phone = f"+9199{random.randint(10000000, 99999999)}"
    print(f"Registering {display_name} with phone {phone} and username {username}")
    
    page.click("text=Create an account")
    page.fill("input[placeholder='+1234567890']", phone)
    page.click("text=Next")
    
    page.wait_for_selector("text=Enter the 6-digit verification code.")
    inputs = page.locator("input[inputmode='numeric']").all()
    for i, char in enumerate(DEMO_OTP):
        inputs[i].fill(char)
        
    page.click("text=Verify Code")
    
    page.wait_for_selector("text=Profile Setup")
    page.fill("input[placeholder='Display Name (Required)']", display_name)
    page.fill("input[placeholder='Username (Required)']", username)
    
    page.wait_for_selector("svg.text-green-500", state="visible")
    page.click("text=Complete Registration")
    
    page.wait_for_url(f"{FRONTEND_URL}/")
    print(f"Successfully registered {display_name}")
    return phone

def run_tests():
    print("Starting E2E verification...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        user_a_name = "User A"
        user_a_username = f"usera_{uuid.uuid4().hex[:8]}"
        user_b_name = "User B"
        user_b_username = f"userb_{uuid.uuid4().hex[:8]}"

        context_a = browser.new_context(permissions=["notifications"])
        page_a = context_a.new_page()
        page_a.goto(FRONTEND_URL)
        phone_a = register_user(page_a, user_a_name, user_a_username)
        
        context_b = browser.new_context(permissions=["notifications"])
        page_b = context_b.new_page()
        page_b.goto(FRONTEND_URL)
        phone_b = register_user(page_b, user_b_name, user_b_username)
        
        print("Scenarios 1 & 2: Registration & Login completed.")
        
        # Scenario 3 & 4: Search and add contact (A adds B)
        page_a.click("button[aria-label='New Chat']")
        page_a.fill("input[placeholder='Search Phone, Username, or Display Name']", user_b_username)
        
        # Wait for search results
        page_a.wait_for_selector(f"text=Search Results")
        page_a.wait_for_selector(f"text={user_b_name}")
        
        # Click Add Contact
        page_a.click("button[title='Add Contact']")
        print("Scenario 3 & 4: Contact searched and added.")
        
        # Scenario 5 & 6: Start conversation and send message
        # Wait for the Message icon to appear (since they are now a contact)
        # or just click the user in the contact list after searching again
        page_a.fill("input[placeholder='Search Phone, Username, or Display Name']", "")
        page_a.wait_for_selector("text=Your Contacts")
        page_a.wait_for_selector(f"text={user_b_name}")
        page_a.click(f"text={user_b_name}")
        
        print("Scenario 5: Started direct conversation.")
        
        # Send message
        page_a.wait_for_selector("input[placeholder='Type a message...']")
        test_message = "Hello from User A to User B!"
        page_a.fill("input[placeholder='Type a message...']", test_message)
        page_a.press("input[placeholder='Type a message...']", "Enter")
        print("Scenario 6: Message sent.")
        
        # Scenario 7: Verify Socket.IO receipt on Browser B
        page_b.wait_for_selector(f"text={user_a_name}")
        page_b.click(f"text={user_a_name}") # open the chat
        
        # Check if message arrived
        page_b.wait_for_selector(f"text={test_message}")
        print("Scenario 7: Socket.IO Real-time delivery verified.")
        
        browser.close()

if __name__ == "__main__":
    run_tests()
